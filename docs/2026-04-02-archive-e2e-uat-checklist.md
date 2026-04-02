# Archive 端到端人工验收清单

日期：2026-04-02

## 这份清单是干什么的

这不是开发文档，是给实际试用时照着走的。

目标只有一个：

确认 archive 这条诊断链路，在真实使用里到底是不是“真的顺手”。

## 验收前准备

先确认这几个条件：

- 当前代码已经是最新本地版本
- 当前全量测试已通过
- `artifacts/runs/` 下已经至少有 retrieval / review / planning / coding 这几类真实 run
- `python -m entrypoints.cli archive --latest` 能正常输出

## 验收路径 A：从最新 run 开始看

### 步骤

1. 跑一条新的真实 run
2. 执行：

```bash
python -m entrypoints.cli archive --latest
```

### 验收标准

- 能直接看到最新 run_id
- 能直接看到 `task_type`
- 能直接看到 `status`
- 如果是 coding run，能直接看到 `expected_artifacts` 和 `produced_artifacts`
- 不需要再翻原始 JSON 文件

## 验收路径 B：从列表里找问题 run

### 步骤

执行：

```bash
python -m entrypoints.cli archive --status failed --limit 10
python -m entrypoints.cli archive --task-type coding --limit 10
```

### 验收标准

- 能在失败列表里一眼区分普通失败和 governance review
- 能在 coding 列表里一眼看出哪个 run 有 `missing_expected=yes`
- 看到 summary 行之后，知道下一条该点开哪一个 run

## 验收路径 C：看单条 run 卡片

### 步骤

挑 3 条 run 分别查看：

- 一条 retrieval 成功
- 一条 planning 失败
- 一条 coding 成功

执行：

```bash
python -m entrypoints.cli archive --run-id <run_id>
```

### 验收标准

- retrieval 成功样本能直接看出是 `answer` 型交付
- planning 失败样本能直接看出失败原因和 governance 状态
- coding 成功样本能直接看出是否产出了 `file_change`
- 单条输出已经足够作为“最小诊断卡片”

## 验收路径 D：做 compare

### 步骤

至少做 3 组 compare：

1. 成功 retrieval vs 失败 planning
2. 成功 retrieval vs 成功 coding
3. 失败 review vs 成功 review

执行：

```bash
python -m entrypoints.cli archive --compare-run-id <left_run_id> --compare-run-id <right_run_id>
```

### 验收标准

- 能通过 `transitions` 快速判断是变好还是变差
- 能通过 `highlights` 快速知道要不要继续深挖
- 能通过 `artifact_diff` 看出交付物差异
- compare 输出已经足够支持“先判断，再决定要不要翻细节”

## 重点观察 5 件事

试用时不要泛泛地看，重点看这 5 件事：

1. 是否 10 秒内就能找到想看的 run
2. 是否 summary 行已经足够决定先看哪条
3. 是否单条 run 输出已经足够，不必再翻 JSON
4. 是否 compare 的 `highlights` 真能帮你快速下判断
5. 是否 artifact 信息已经能支持 coding 场景排查

## 什么情况算通过

满足下面 4 条，就算这次人工验收通过：

- 真实使用者能独立走完整条链路
- 中途不需要开发者解释字段含义
- 能靠 archive 输出快速判断“哪里出问题了”
- 能靠 compare 输出快速判断“这次和上次差在哪”

## 什么情况算不通过

只要出现下面任意一种，就算还需要继续收口：

- summary 行看完仍不知道先点哪条
- 单条 run 输出仍然需要回去翻 JSON 才能理解
- compare 虽然有信息，但还是很难快速下判断
- coding 场景里 artifact 信息还是不够用

## 验收后要记录什么

人工验收结束后，建议立刻补一份简短记录：

- 哪 3 个点最好用
- 哪 3 个点仍然卡手
- 有没有新冒出来的过滤维度需求
- 现在能不能正式进入小范围稳定试用

## 一句话目标

这份验收不是为了证明“功能都有了”，而是为了确认“真实用户照着命令走，能不能真地省时间”。
