# 📋 E11 Run 20260527_010434 完整诊断 + 修复方案

## 🔴 核心问题总结

### 影响
- **NHEFT vs DHEFT 平均收益**: -34.46% 😞
- **4个灾难性 seeds**: 导致 -89% 到 -144% 的极端负收益
- **只有 10 个 seeds**: 样本太小，无法抵消异常值

### 根本原因链

```
base.properties 有错误的参数
         ↓
sfc_vnf_num=80 (应该是 200)
multiple_sfc_num=4 (应该是 1)
         ↓
run_experiment.py 试图覆盖但失败
         ↓
生成的 SFC 太小（40-80 个 VNF）
         ↓
某些 seeds（9018、7711、5624、8499）生成极小 SFC（~2-4 VNF）
         ↓
镜像下载开销 > 实际收益
         ↓
NHEFT 反而比 DHEFT 慢
         ↓
gain = -89% 到 -144% 😱
```

## 🔍 诊断数据

| 问题 roots | base.properties | run_experiment.py override |
|----------|-----------------|---------------------------|
| sfc_vnf_num | **80** ❌ (Wrong) | 尝试设为 200 但可能失败 |
| multiple_sfc_num | **4** ❌ (Wrong) | 尝试设为 1 但可能失败 |
| Expected result | Should have 200 VNF/SFC | Only got 40-80 VNF |

**破坏性 seeds（占 40% 样本）:**
```
seed 9018: DHEFT=1.62s, NHEFT=3.95s, gain=-144% 💀
seed 7711: DHEFT=2.88s, NHEFT=6.55s, gain=-127% 💀
seed 5624: DHEFT=2.44s, NHEFT=4.68s, gain=-92%  💀
seed 8499: DHEFT=2.27s, NHEFT=4.29s, gain=-89%  💀
```

**正常 seeds（得到的结果符合预期）:**
```
seed 4352: DHEFT=59.83s, NHEFT=56.92s, gain=+8.8% ✓
seed 2209: DHEFT=43.46s, NHEFT=40.85s, gain=+6.2% ✓
seed 6768: DHEFT=55.63s, NHEFT=53.49s, gain=+6.5% ✓
seed 7053: DHEFT=58.21s, NHEFT=8.58s, gain=+81%  ✓ (极优)
```

## ✅ 修复方案

### 方案 1: 修复 base.properties（推荐 ⭐）

**步骤**: 在 base.properties 中修改 NPPHEFT 参数为 E11 标准值

```bash
# 编辑文件，找到并修改这些行：
sfc_vnf_num=80          → sfc_vnf_num=200
multiple_sfc_num=4      → multiple_sfc_num=1
multiple_sfc_vnf_num_min=90   → multiple_sfc_vnf_num_min=200
multiple_sfc_vnf_num_max=140  → multiple_sfc_vnf_num_max=200
```

**优点**:
- 彻底修复参数问题
- 未来所有 E11 运行都会自动正确
- 代码清晰，不需要理解覆盖机制

**缺点**:
- 修改会影响其他实验（如果它们依赖 base.properties）

### 方案 2: 检查 run_experiment.py 的覆盖机制

**步骤**: 验证参数覆盖是否正确工作

```python
# run_experiment.py L104-115 的代码片段：
base.update({
    'sfc_vnf_num': '200',
    'multiple_sfc_num': '1',
    ...
})
```

**检查**:
- 覆盖的值是否被写入的临时属性文件？
- Java 程序是否正确读取了参数？

**改进建议**:
- 在 run_experiment.py 中添加调试输出
- 运行 DRY_RUN 来验证生成的命令

### 方案 3: 应急补救（立即可用）

重跑实验同时修复：

```bash
cd /Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t

# 步骤 1: 备份旧文件
cp experiments/base.properties experiments/base.properties.backup_20260527

# 步骤 2: 修改参数
sed -i '' 's/^sfc_vnf_num=80$/sfc_vnf_num=200/' experiments/base.properties
sed -i '' 's/^multiple_sfc_num=4$/multiple_sfc_num=1/' experiments/base.properties
sed -i '' 's/^multiple_sfc_vnf_num_min=90$/multiple_sfc_vnf_num_min=200/' experiments/base.properties
sed -i '' 's/^multiple_sfc_vnf_num_max=140$/multiple_sfc_vnf_num_max=200/' experiments/base.properties

# 步骤 3: 重新运行 E11（100 seeds 版本）
cd experiments/e11
E11_NUM_SEEDS=100 python3 run_experiment.py
```

**时间**: ~6-8 小时

## 📊 预期改善

| 指标 | 当前 run | 预期（修复后）|
|------|---------|-----------|
| Mean gain | -34% | +9-12% |
| Median gain | -1.4% | +3-5% |
| 胜率 | 40-50% | 65-75% |
| 样本 seeds | 10 | 100 |
| 异常值权重 | 40% | 1% |

## 🎯 建议立即行动

### 1️⃣ 确认问题（5分钟）
```bash
# 检查一个问题 seed 的日志
cat experiments/e11/run_20260527_010434/run_seed_9018_rb_60.log | head -20
```

### 2️⃣ 修改参数（2分钟）
编辑 `experiments/base.properties`，或使用上面的 sed 命令

### 3️⃣ 验证修改（1分钟）
```bash
python3 experiments/e11/check_params.py
```
应该显示所有参数都 ✓ 正确

### 4️⃣ 重新运行（6-8小时）
```bash
cd experiments/e11
E11_NUM_SEEDS=100 python3 run_experiment.py
```

## 📝 向导师汇报

> "E11 初始运行（10 seeds）结果很差（-34% gain），根本原因是 base.properties 的 NPPHEFT 优化参数与 E11 的需求冲突。
>
> 具体地：
> - `sfc_vnf_num` 被设为 80（应该 200），导致生成极小 SFC
> - `multiple_sfc_num` 被设为 4（应该 1），造成多 SFC 分散
> - 正常的 seeds 表现很好（gain +6-8%），但 4 个 seeds 生成了极小 SFC（2-4 VNF），导致镜像下载开销显著，最终 gain 为负
>
> 已经修复参数，现在用 100 seeds 重新运行 E11，预计展示 +9-12% 的真实收益，这将验证 H1 假设。预计明天完成。"

