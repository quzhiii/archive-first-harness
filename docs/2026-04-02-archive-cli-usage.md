# Archive CLI 使用示例

日期：2026-04-02

## 这份文档是干什么的

这份文档只回答一个问题：

现在 archive 这一套，具体怎么用？

你不需要先懂内部实现，只要会按下面这些命令跑，就已经能开始内部使用了。

## 先记住一句话

如果你想：

- 看最新一次 run
- 看某一条 run
- 找某一类 run
- 比较两次 run 到底差在哪

就用：

```bash
python -m entrypoints.cli archive ...
```

## 1. 看最新一次 run

```bash
python -m entrypoints.cli archive --latest
```

适合场景：

- 刚跑完一次任务，想马上看结果
- 不确定最新 run_id 是什么，但想先看最新诊断信息

你会看到：

- run_id
- workflow_profile_id
- task_type
- status
- verification / governance 状态
- expected_artifacts / produced_artifacts

## 2. 看某一条指定 run

```bash
python -m entrypoints.cli archive --run-id <run_id>
```

例子：

```bash
python -m entrypoints.cli archive --run-id 20260402T101500Z_review_runtime_output_ab12cd
```

适合场景：

- 你已经知道 run_id
- 你想单独看这一条 run 的诊断摘要

## 3. 浏览最近几条 run

```bash
python -m entrypoints.cli archive --limit 10
```

适合场景：

- 你只想先快速扫一眼最近发生了什么
- 你还不知道具体要点开哪一条

## 4. 找某一类任务

```bash
python -m entrypoints.cli archive --task-type research --limit 10
```

也可以换成别的类型：

```bash
python -m entrypoints.cli archive --task-type review --limit 10
python -m entrypoints.cli archive --task-type retrieval --limit 10
```

适合场景：

- 你只想看研究类 run
- 你只想看 review 类 run
- 你开始积累很多 run，需要按任务类型缩小范围

## 5. 找某一种 formation

```bash
python -m entrypoints.cli archive --formation-id discovery --limit 10
```

也可以换成别的 formation：

```bash
python -m entrypoints.cli archive --formation-id review --limit 10
python -m entrypoints.cli archive --formation-id delivery --limit 10
```

适合场景：

- 你想看同一种工作形态下的 run
- 你怀疑某个 formation 更容易出问题

## 6. 只看失败 run

```bash
python -m entrypoints.cli archive --status failed --limit 10
```

如果你还想继续缩小范围，可以叠加：

```bash
python -m entrypoints.cli archive --task-type review --status failed --limit 10
```

适合场景：

- 你只想排查坏掉的 run
- 你不关心成功样本，只想先看问题面

## 7. 只看某种失败类型

```bash
python -m entrypoints.cli archive --failure-class surface_execution_failure --limit 10
```

也可以叠加其他过滤：

```bash
python -m entrypoints.cli archive --task-type review --failure-class surface_execution_failure --limit 10
```

适合场景：

- 你怀疑某种失败在重复发生
- 你想确认失败是不是集中在某个任务类型

## 8. 比较两次 run

```bash
python -m entrypoints.cli archive --compare-run-id <left_run_id> --compare-run-id <right_run_id>
```

例子：

```bash
python -m entrypoints.cli archive --compare-run-id 20260402T101500Z_review_runtime_output_ab12cd --compare-run-id 20260402T102200Z_review_runtime_output_ef34gh
```

适合场景：

- 你想看“成功版”和“失败版”差在哪
- 你改了一轮逻辑，想看前后变化
- 你想看 artifact 层面有没有变化

## compare 输出重点看哪里

一条 compare 输出，优先看这几块：

### 1. `transitions:`

这是最先看的总览。

重点看：

- `failure=...`
- `verification=...`
- `reassessment=...`
- `evaluation=...`
- `governance=...`
- `artifacts=...`

如果出现：

- `regressed`
- `escalated`
- `changed`

通常就值得继续往下看。

### 2. `highlights:`

这是最像“人话总结”的一行。

如果你没时间细看，先看这一行就够了。

### 3. `reason_code_diff:`

这行适合看：

- 哪些原因码是新冒出来的
- 哪些原因码消失了

### 4. `artifact_diff:`

这行适合看：

- expected artifact 有没有变
- 实际 produced artifact 有没有变
- baseline compare 看的 artifact 类型有没有变
- artifact 层面整体是在变差还是只是变化了

## 最实用的 4 套组合命令

### 组合 A：先扫失败，再点开具体 run

```bash
python -m entrypoints.cli archive --status failed --limit 10
python -m entrypoints.cli archive --run-id <run_id>
```

### 组合 B：先按任务类型缩小，再看最新一条

```bash
python -m entrypoints.cli archive --task-type review --limit 10
python -m entrypoints.cli archive --run-id <run_id>
```

### 组合 C：比较修复前后两次 run

```bash
python -m entrypoints.cli archive --compare-run-id <old_run_id> --compare-run-id <new_run_id>
```

### 组合 D：先看某个 formation 的失败样本

```bash
python -m entrypoints.cli archive --formation-id review --status failed --limit 10
```

## 一开始最推荐你怎么用

如果你现在就想开始内部使用，我建议固定用下面顺序：

1. 先看最近失败 run

```bash
python -m entrypoints.cli archive --status failed --limit 10
```

2. 再挑一条点开

```bash
python -m entrypoints.cli archive --run-id <run_id>
```

3. 最后找一个成功样本做 compare

```bash
python -m entrypoints.cli archive --compare-run-id <success_run_id> --compare-run-id <failed_run_id>
```

这样最容易快速建立直觉。

## 什么时候说明它已经有用了

如果你已经能用这套命令完成下面 3 件事，就说明 archive 这条线已经开始产生实际价值了：

- 你能在几分钟内找到想看的 run
- 你能看懂这条 run 的最小诊断信息
- 你能用 compare 快速知道前后差异大概在哪
