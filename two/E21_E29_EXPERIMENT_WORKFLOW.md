# E21-E29 实验脚本统一说明（通用工作流）

## 1. 适用范围
本文档面向 `experiments/e21` 到 `experiments/e29` 这一组实验目录。  
虽然每个实验的筛选条件（B1~B9）不同，但脚本设计思路和使用流程是统一的。

每个实验目录都遵循同一套结构：

- `run_experiment.py`
- `analyze_results.py`
- `pretty_single_seed_report.py`
- `analyze_single_seed_no_dag.py`
- `analyze_single_seed_with_dag.py`
- `bX.properties`（该实验使用的参数集）

---

## 2. 推荐执行顺序（统一流程）

1. 批量跑实验：`run_experiment.py`
2. 汇总统计与画图：`analyze_results.py`
3. 找出/重跑单个 seed：`analyze_single_seed_no_dag.py` 或 `analyze_single_seed_with_dag.py`
4. 把单 seed 大日志转可读报告：`pretty_single_seed_report.py`

---

## 3. 脚本说明

## 3.1 `run_experiment.py`
用途：按随机种子批量调用 Java 仿真，产出原始结果与每个 seed 的日志。

典型命令（在对应实验目录下执行）：

```bash
python3 run_experiment.py
```

常见环境变量（不同实验前缀不同，例如 `E21_`、`E22_`）：

- `E2X_MASTER_SEED`：主随机种子（默认一般是 `150`）
- `E2X_NUM_SEEDS`：本次采样 seed 数量（默认一般是 `100`）
- `E2X_DRY_RUN=1`：仅打印命令，不实际执行
- `E2X_LIMIT_RUNS`：仅跑前 N 条（调试用）

生成目录命名：

- `run_{timestamp}_{MASTER_SEED}_{NUM_SEEDS_DEFAULT}`

注意：
- 目录名最后一段是脚本内默认值（通常 `100`），不一定等于你运行时覆盖后的实际 seed 数。
- 实际使用的 seed 数和 seed 列表请以 `run_manifest.json` 为准。

---

## 3.2 `analyze_results.py`
用途：读取 `run_*` 目录，按该实验的 B 条件筛选有效 seed，输出统计表、图和 NHEFT 失利 seed 的 JSON。

典型命令：

```bash
python3 analyze_results.py run_20260601_022936_150_100
```

也支持传绝对路径，或传目录名前缀（脚本会尝试解析）。

关键行为：

- 自动保证日志位于 `run_xxx/logs/`（会把旧布局日志搬运到 `logs/`）
- 从每个 seed 日志中提取 `CCR_data / IDR_image / NCCR_total`
- 先过滤算法有效数据（HEFT/DHEFT/NHEFT 都有效）
- 再按该实验 B 条件过滤（比如 B1/B2/.../B9）
- 所有 win-rate、gain、p-value 都基于“满足该 B 条件”的样本计算

---

## 3.3 `pretty_single_seed_report.py`
用途：把单 seed 大日志解析成“按执行顺序”的人类可读 Markdown 报告。

典型命令：

```bash
python3 pretty_single_seed_report.py debug_1466
python3 pretty_single_seed_report.py debug_1466 ""
python3 pretty_single_seed_report.py debug_1466 dheft
python3 pretty_single_seed_report.py debug_1466 nheft
```

参数说明：

- 第 1 参数：目标文件夹（通常是 `debug_{seed}`）
- 第 2 参数可选：
  - 空/不传：输出 DHEFT+NHEFT 合并报告
  - `dheft`：仅 DHEFT
  - `nheft`：仅 NHEFT

输出通常为：

- `*.dheft_nheft.ordered.pretty.md`
- `*.dheft.ordered.pretty.md`
- `*.nheft.ordered.pretty.md`

---

## 3.4 `analyze_single_seed_no_dag.py` 和 `analyze_single_seed_with_dag.py`
这两个脚本建议合并理解：它们都是为了“追踪单个 seed，定位 NHEFT 失去优势的原因”。

### `analyze_single_seed_no_dag.py`
典型命令：

```bash
python3 analyze_single_seed_no_dag.py 1466
```

### `analyze_single_seed_with_dag.py`
典型命令：

```bash
python3 analyze_single_seed_with_dag.py 1466
python3 analyze_single_seed_with_dag.py 1466 --no-dag
```

特点：

- `with_dag` 版本默认 `DAG` 开启（可用 `--no-dag` 关闭）
- 会捕获 Java 输出里的 DAG 导出目录，并写入 `*.dag_output.txt`
- `no_dag` 版本更轻量，适合快速复盘

两者共同输出到：

- `debug_{seed}/single_seed_seed{seed}_{timestamp}.log`
- `debug_{seed}/single_seed_seed{seed}_{timestamp}.properties`

`with_dag` 额外输出：

- `debug_{seed}/single_seed_seed{seed}_{timestamp}.dag_output.txt`
  - 文件中是一行路径，指向 `dag_outputs/seed_{seed}_{timestamp}` 之类的 DAG 元数据目录

---

## 4. 主要输出文件说明（run 目录）

以 `run_xxx` 为例，常见产物如下（`e21`、`e22`...前缀会随实验变化）：

- `logs/run_seed_<seed>.log`：每个 seed 的 Java 原始输出日志
- `grid_e2x_results.csv`：逐 seed 原始结果（HEFT/DHEFT/NHEFT/time）
- `grid_e2x_summary.csv`：汇总统计（均值、中位数、wins、win_rate、p-value 等）
- `run_manifest.json`：本次实验元信息（master seed、seeds_used、num_seeds、timestamp）
- `bX_properties_snapshot.properties`：本次运行参数快照
- `e2x_seed_metrics_with_bX_flag.csv`：每个 seed 的指标 + 是否满足 B 条件
- `e2x_nheft_loss_seeds_by_scenario.json`：NHEFT 输给 DHEFT 的 seed 字典（含每个 seed 的详细数值）
- `e2x_summary_table.png`：主汇总表图片
- `e2x_robust_table.png`：稳健统计表图片
- `e2x_makespan_mean_comparison.png`：HEFT/DHEFT/NHEFT 均值对比柱状图
- `e2x_makespan_boxplot.png`：三算法 makespan 分布箱线图
- `e2x_gain_histogram.png`：NHEFT 相对 DHEFT gain 分布图

---

## 5. 主要输出文件说明（debug 目录）

`debug_{seed}` 目录用于“单 seed 深度复盘”，常见文件：

- `single_seed_seed...log`：单 seed 大日志（最原始）
- `single_seed_seed...properties`：该次运行参数（可复现实验）
- `single_seed_seed....dag_output.txt`：DAG 元数据目录指针（仅 with_dag）
- `single_seed_seed....ordered.pretty.md`：可读化报告（由 `pretty_single_seed_report.py` 生成）

---

## 6. 建议的日常使用模板

1. 批量跑：
```bash
python3 run_experiment.py
```

2. 汇总：
```bash
python3 analyze_results.py run_xxx
```

3. 找到 NHEFT 失利 seed 后，单点复盘：
```bash
python3 analyze_single_seed_with_dag.py <seed>
python3 pretty_single_seed_report.py debug_<seed>
```

---

## 7. 跨实验聚合脚本（E21-E23 / E24-E26 / E27-E29）

除了每个实验目录内的 5 个核心脚本，`experiments/` 根目录还有 3 个“分组三联实验”的聚合脚本：

- `analyze_e21_e22_e23_latest.py`
- `analyze_e24_e25_e26_latest.py`
- `analyze_e27_e28_e29_latest.py`

用途：

- 自动寻找每个实验目录下“最新的 `run_*` 结果目录”
- 读取各自的 `grid_e2x_summary.csv`
- 做跨场景（3 组）的二次汇总与对比作图

典型命令（在项目根目录执行）：

```bash
python3 experiments/analyze_e21_e22_e23_latest.py
python3 experiments/analyze_e24_e25_e26_latest.py
python3 experiments/analyze_e27_e28_e29_latest.py
```

输出目录：

- `experiments/e21_e22_e23/<timestamp>/`
- `experiments/e24_e25_e26/<timestamp>/`
- `experiments/e27_e28_e29/<timestamp>/`

每次聚合的常见产物（以 `e21_e22_e23` 为例，另外两组同理）：

- `e21_e22_e23_latest_summary.csv`：三个实验最新结果的统一汇总表
- `makespan_mean_comparison.png`：三组条件下 HEFT/DHEFT/NHEFT 的组合柱图（可叠加 win-rate 与 gain 折线）
- `e21_e22_e23_win_rate_bar.png`：NHEFT 相对 DHEFT 的胜率柱图
- `e21_e22_e23_gain_median_bar.png`：NHEFT 相对 DHEFT 的中位 gain 柱图
- `summary.txt`：本次聚合所引用的 run 目录、日志路径和关键数值说明

补充：

- 这三个脚本都内置了可视化开关（例如是否显示 win-rate 折线、gain 折线）和样式参数。
- 它们的逻辑是“最新 run 自动聚合”，适合你在每轮实验后快速生成组间对比图。

---

## 8. 补充说明

- e21-e29 的核心差异在于“B 条件定义”，不是脚本骨架。
- 因此跨实验迁移时，优先复用流程，不要重复发明脚本结构。
- 若你只做性能统计，`no_dag` 更快；若你要结构化定位原因（路径、节点级对比），用 `with_dag`。
