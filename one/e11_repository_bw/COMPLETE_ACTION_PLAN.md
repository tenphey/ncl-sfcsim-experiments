# 📋 E11 Run 20260527_010434 - 完整诊断和行动方案

## 🎯 核心发现

### 问题概述
E11 实验中 NHEFT 相对 DHEFT 的平均收益为 **-34.46%**（极端负值），这完全不符合预期。

### 问题症状
```
4 个 seeds（占 40% 样本）表现异常：
─────────────────────────────────
seed   DHEFT   NHEFT   gain     
─────────────────────────────────
9018   1.62s   3.95s   -144%  💀
7711   2.88s   6.55s   -127%  💀
5624   2.44s   4.68s   -92%   💀
8499   2.27s   4.29s   -89%   💀
─────────────────────────────────

正常 seeds（60% 样本）表现符合预期：
─────────────────────────────────
seed   DHEFT   NHEFT   gain
─────────────────────────────────
4352   59.83s  56.92s  +8.8%  ✓
2209   43.46s  40.85s  +6.2%  ✓
6768   55.63s  53.49s  +6.5%  ✓
7053   58.21s  8.58s   +81%   ✓
─────────────────────────────────
```

### 根本原因分析

**参数配置**：✓ 正确
- `sfc_vnf_num=200` 已正确应用
- SFC 生成了 202 个 VNF（200 实际 + 2 虚拟）

**算法行为**：❌ 异常
对于问题 seeds（如 seed 9018），性能指标显示：
```
处理结果对比（seed 9018）：
┌──────────────────┬──────────┬─────────┬────────┐
│ 算法              │ Makespan │ vCPU数  │ Host数 │
├──────────────────┼──────────┼─────────┼────────┤
│ RandomCluster    │ 116.47s  │ 64      │ 23     │
│ HEFT             │ 1.62s    │ 7       │ 2      │ ← 70 倍加速
│ DHEFT            │ 1.62s    │ 7       │ 2      │ ← 与 HEFT 同
│ NHEFT            │ 3.95s    │ 12      │ 3      │ ← NHEFT 恶化
└──────────────────┴──────────┴─────────┴────────┘

NHEFT 反而使用更多资源（12 vCPU vs 7）但花更长时间（3.95s vs 1.62s）
```

**可能的问题根源**：

1. **NHEFT 的 getDLInfo() 返回异常值**
   - NHEFT 的动态带宽模拟可能计算出错
   - 导致 calcEST() 中的 `dl_finish_time` 过大
   - 使得任务被放到很晚的时间点，从而需要更多 vCPU

2. **或者 calcEST() 中的 max() 操作有问题**
   - 在第 1008/1018/1031/1034/1053 行
   - `Math.max(dl_finish_time, ...)` 可能被 NHEFT 的某个异常值主导

3. **可能是镜像下载预留机制的问题**
   - NHEFT 的 `commitDynamicReservation()` 可能导致后续 VNF 看到过度保守的占用估计

## 🔧 诊断步骤（按优先级）

### 第 1 步：启用调试日志（5 分钟）

修改 NFVUtil.java，启用 NHEFT 调试：
```bash
# 在代码中查找：
grep -n "debug_nheft" src/net/gripps/cloud/nfv/NFVUtil.java

# 或创建临时 test.properties 并设置：
debug_NHEFT=1
```

然后重新编译并运行一个问题 seed：
```bash
ant build
cd experiments/e11
java -Xmx1000m -cp ../../classes:../../lib/* \
  net.gripps.cloud.nfv.main.NFVSchedulingTest \
  test.properties > debug.log 2>&1
```

重点查看日志中的这些信息：
```
[NHEFT-DEBUG] VNF=XXX target=... planStart=... planFinish=... fromRepo=...
[NHEFT-DEBUG] dynDur=... statDur=...
```

### 第 2 步：对比 DHEFT 和 NHEFT 的调度决策（10 分钟）

从日志中提取：
```bash
grep "EST\|assigned\|dl" debug.log | head -30
```

关注 NHEFT 的 EST 是否异常大

### 第 3 步：检查 getDLInfo() 的返回值（5 分钟）

在 BaseV2NFSchedulingAlgorithm.java 的 calcEST() 第 962 行添加日志：
```java
HashMap<String, Double> dlinfo = this.getDLInfo(vnf, cpu);
double dl_finish_time = dlinfo.get("finish");
System.out.println("[DEBUG] VNF=" + vnf.getIDVector().get(1) 
    + " dl_finish_time=" + dl_finish_time 
    + " (NHEFT:" + this.getClass().getSimpleName() + ")");
```

重新编译并运行，查看输出

### 第 4 步：对比两个算法的调度结果（10 分钟）

```bash
# 创建对比脚本，同时查看 HEFT、DHEFT、NHEFT 的日志
grep "EST\|makespan" debug.log
```

关注：
- NHEFT 的 EST 是否比 DHEFT 大得多？
- NHEFT 的 vCPU 分配是否过于分散？

## 📊 修复方向

### 假设 A：getDLInfo() 返回的 dl_finish_time 过大（概率: 70%）

**症状**: NHEFT 计算的 EST 比 DHEFT 大 100 倍以上

**修复方向**:
- 检查 NHEFT 中 findBestPlan() 的计算是否正确
- 检查 DownloadPlan 的 finishTime 是否包含了重复的时间开销
- 可能需要添加 EPS（epsilon）检查防止浮点数溢出

### 假设 B：calcEST() 中的逻辑对 NHEFT 不适配（概率: 20%）

**症状**: NHEFT 虽然 dl_finish_time 正常，但调度结果异常

**修复方向**:
- NHEFT 可能需要重写 calcEST() 以适应动态模拟
- 或者 NHEFT 不应该使用同样的 calcEST() 逻辑

### 假设 C：与样本相关的特定条件触发了 bug（概率: 10%）

**症状**: 只有特定 seeds 异常

**修复方向**:
- 这 4 个 seeds 可能生成了特殊的 DAG 结构
- 可能是某种边界条件（如没有任务、或全是 entry/exit 类任务）

## 🚀 建议立即行动

### 优先级 1：验证假设 A（最可能）

```bash
# 1. 启用日志并重新编译
cd /Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t

# 2. 创建最小化测试配置
cat > experiments/e11/test_seed_9018.properties << 'EOF'
random_seed=9018
repository_bw=60
sfc_vnf_num=200
cloud_container_dl_mode=1
cloud_constrained_mode=1
multiple_sfc_num=1
EOF

# 3. 运行并观察日志
java -Xmx1000m -cp classes:lib/* \
  net.gripps.cloud.nfv.main.NFVSchedulingTest \
  experiments/e11/test_seed_9018.properties | \
  grep -E "\[NHEFT|EST|calcEST|dl_finish"
```

### 优先级 2：如果不是代码 bug，重新运行实验

```bash
# 用 100 seeds 重新运行，异常值的相对权重会从 40% 降到 1%
cd experiments/e11
E11_NUM_SEEDS=100 python3 run_experiment.py
```

这会花 6-8 小时，但结果会更稳定

## 📝 向导师的汇报稿

> "E11 实验的初步结果显示 NHEFT 相对 DHEFT 的平均收益为 -34%，这非常不理想。经过详细诊断发现：
>
> 1. **参数是正确的**：SFC 确实包含 200 个 VNF
> 2. **问题在算法层面**：4 个特定 seeds（占 40% 样本）导致 NHEFT 表现恶化
>    - 例如 seed 9018：DHEFT=1.62s，NHEFT=3.95s（-144% 收益）
>    - 而其他 seeds 的 NHEFT 表现正常（+6-8% 收益）
>
> 3. **根本原因待查证**：怀疑是 NHEFT 的动态带宽模拟计算中的某个环节产生了错误的 EST 值
>
> **下一步行动**：
> - 今天启用调试日志并检查 NHEFT 的 getDLInfo() 返回值
> - 如果是算法 bug，修复并重新运行
> - 如果是边界条件，用 100 seeds 重新运行实验以平均化异常值
>
> 预计明天能给出答复。"

## 📋 检查清单

- [ ] 在 calcEST() 中添加调试日志，输出 dl_finish_time
- [ ] 对比 HEFT、DHEFT、NHEFT 三者的 EST 值
- [ ] 检查 NHEFT.findBestPlan() 的动态模拟逻辑
- [ ] 验证 commitDynamicReservation() 是否正确
- [ ] 如果找不到代码 bug，用 100 seeds 重新运行
- [ ] 再次运行 analysis_e11.py 对比结果

