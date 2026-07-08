# Three: E31-E58 Experiment Family

## 1. 这一组实验在研究什么

`E31-E58` 是在 `E21-E29` 之后做的更系统化的 follow-up。

核心思路不再是直接扫描某个原始参数，而是把实验条件抽象成两层：

- 第一层：总通信强度 `NCCR_total`
- 第二层：普通数据通信 `CCR_data` 和镜像通信 `IDR_image` 的关系

这一组实验要回答的问题是：

- 当 `NCCR_total` 逐步升高时，`NHEFT` 相对 `DHEFT` 的优势如何变化？
- 当通信中是 `image` 更重、`data` 更重，还是两者大致平衡时，这个趋势是否不同？

---

## 2. 总体设计框架

这组实验统一把 `NCCR_total` 分成 8 个对数桶：

1. `(0.10, 0.18]`
2. `(0.18, 0.32]`
3. `(0.32, 0.56]`
4. `(0.56, 1.00]`
5. `(1.00, 1.78]`
6. `(1.78, 3.16]`
7. `(3.16, 5.62]`
8. `(5.62, 10.00]`

然后再分成 3 个平行实验家族：

- `E31-E38`：`CCR_data ~= IDR_image`
- `E41-E48`：`CCR_data < IDR_image`
- `E51-E58`：`CCR_data > IDR_image`

所以整体上，它是一个：

- `8 个 NCCR 桶`
- `× 3 种 CCR/IDR 关系`

的系统实验设计。

---

## 3. 三个家族分别代表什么

### 3.1 E31-E38

这组是“平衡型”实验。

目标是：

- 让 `CCR_data` 和 `IDR_image` 大致相当
- 然后观察 `NCCR_total` 从低到高时，`HEFT / DHEFT / NHEFT` 的表现趋势

这组适合回答：

- 当普通数据通信和镜像通信处于同一量级时，`NHEFT` 的优势是如何随总通信强度变化的？

### 3.2 E41-E48

这组是“镜像通信主导型”实验。

目标是：

- 让 `CCR_data < IDR_image`
- 并且让两者差距保持在一个明确范围上

实际分析条件采用：

- `CCR_data < IDR_image`
- 相对差距 `>= 20%`

这组适合回答：

- 当 image communication 比普通 dependent data communication 更重时，`NHEFT` 是否更容易占优？

### 3.3 E51-E58

这组是“普通数据通信主导型”实验。

目标是：

- 让 `CCR_data > IDR_image`
- 并且让两者差距保持在一个明确范围上

实际分析条件采用：

- `CCR_data > IDR_image`
- 相对差距 `>= 20%`

这组适合回答：

- 当主要通信压力来自普通数据依赖，而不是镜像下载时，`NHEFT` 的优势是否减弱？

---

## 4. 各目录的对应关系

### 4.1 E31-E38

- `e31` -> `(0.10, 0.18]`
- `e32` -> `(0.18, 0.32]`
- `e33` -> `(0.32, 0.56]`
- `e34` -> `(0.56, 1.00]`
- `e35` -> `(1.00, 1.78]`
- `e36` -> `(1.78, 3.16]`
- `e37` -> `(3.16, 5.62]`
- `e38` -> `(5.62, 10.00]`

### 4.2 E41-E48

- `e41` -> `(0.10, 0.18]`
- `e42` -> `(0.18, 0.32]`
- `e43` -> `(0.32, 0.56]`
- `e44` -> `(0.56, 1.00]`
- `e45` -> `(1.00, 1.78]`
- `e46` -> `(1.78, 3.16]`
- `e47` -> `(3.16, 5.62]`
- `e48` -> `(5.62, 10.00]`

### 4.3 E51-E58

- `e51` -> `(0.10, 0.18]`
- `e52` -> `(0.18, 0.32]`
- `e53` -> `(0.32, 0.56]`
- `e54` -> `(0.56, 1.00]`
- `e55` -> `(1.00, 1.78]`
- `e56` -> `(1.78, 3.16]`
- `e57` -> `(3.16, 5.62]`
- `e58` -> `(5.62, 10.00]`

---

## 5. 代码组织方式

这一组实验的一个重要特点是：

- 每个实验目录都是自洽的小单元

通常每个目录都有：

- `run_experiment.py`
- `analyze_results.py`
- `README.md`
- `bXX.properties`

例如：

- `e31` 使用自己的 `run_experiment.py` 和 `b31.properties`
- `e41` 使用自己的 `run_experiment.py` 和 `b41.properties`
- `e58` 使用自己的 `run_experiment.py` 和 `b58.properties`

也就是说：

- `E31` 不会去调用 `b41.properties`
- `E41` 也不会去调用 `b51.properties`

每个目录都用自己的 tuned property profile 去打目标桶和目标条件。

---

## 6. 单个实验怎么执行

### 6.1 一般执行顺序

每个实验目录的推荐流程都是：

1. 跑批量 seed
2. 汇总分析
3. 如果要追某个特殊 seed，再做单 seed 复盘

### 6.2 以 E31 为例

正常运行：

```bash
python3 experiments/e31/run_experiment.py
```

少量 seed 测试：

```bash
E31_NUM_SEEDS=10 python3 experiments/e31/run_experiment.py
```

只打印命令不实际执行：

```bash
E31_DRY_RUN=1 python3 experiments/e31/run_experiment.py
```

分析某一轮结果：

```bash
python3 experiments/e31/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

### 6.3 以 E41 为例

```bash
python3 experiments/e41/run_experiment.py
python3 experiments/e41/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

### 6.4 以 E51 为例

```bash
python3 experiments/e51/run_experiment.py
python3 experiments/e51/analyze_results.py run_YYYYMMDD_HHMMSS_150_100
```

---

## 7. 重要的统计规则

这组实验虽然是“定向打桶”，但并不是说每个 seed 都一定会落进目标条件。

统一规则是：

1. `run_experiment.py` 先把所有 seed 都执行并保存原始结果
2. `analyze_results.py` 再从日志里重新解析 `CCR_data / IDR_image / NCCR_total`
3. 只有真正满足目标桶和目标关系的 seed，才会进入最终统计

所以要注意：

- 原始运行数不等于最终有效样本数
- 最终统计以筛选后的 qualified seeds 为准

---

## 8. 组内聚合脚本

三大家族各自都有一个聚合脚本：

- `analyze_e3x.py`：汇总 `E31-E38`
- `analyze_e4x.py`：汇总 `E41-E48`
- `analyze_e5x.py`：汇总 `E51-E58`

对应输出目录分别是：

- `experiments/e31_e38/`
- `experiments/e41_e48/`
- `experiments/e51_e58/`

典型命令：

```bash
python3 experiments/analyze_e3x.py
python3 experiments/analyze_e4x.py
python3 experiments/analyze_e5x.py
```

这些脚本会自动去找对应家族里最新的一轮结果，并生成：

- 汇总 CSV
- makespan 对比图
- win rate / gain rate 信息
- vCPU 使用图

---

## 9. 三大家族总汇总

如果要把 `E31-E38`、`E41-E48`、`E51-E58` 进一步放在一起比较，可以使用：

```bash
python3 experiments/analyze_e345x.py
```

它会把三大家族的聚合结果再汇总到：

- `experiments/e3x_e4x_e5x/`

这个层级适合做：

- 跨家族 makespan 对比
- 跨家族 gain / win rate / vCPU 使用对比
- 论文中的总表或总图

---

## 10. 如何理解这一整组实验

如果用一句话概括：

- `E31-E58` 不是在继续扫原始参数
- 而是在一个统一通信解释框架下，系统比较 `DHEFT` 和 `NHEFT`

如果再拆开说：

- `E31-E38` 看平衡条件
- `E41-E48` 看 image-dominant 条件
- `E51-E58` 看 data-dominant 条件

再配合 8 个 `NCCR_total` 桶，就可以较系统地回答：

- `NHEFT` 什么时候更强
- 强多少
- 强的代价是什么

---

## 11. 建议阅读顺序

如果第一次接触这一组实验，推荐按下面顺序理解：

1. 先读本文件，理解整体设计
2. 再读 `e31/README.md`，理解平衡型第一桶
3. 再读 `e41/README.md`，理解 image-dominant 第一桶
4. 再读 `e51/README.md`，理解 data-dominant 第一桶
5. 最后结合 `analyze_e3x.py / analyze_e4x.py / analyze_e5x.py / analyze_e345x.py` 看聚合结果

