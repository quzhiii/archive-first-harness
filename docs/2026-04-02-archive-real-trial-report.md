# Archive 真实试用报告

日期：2026-04-02

## 先说结论

这轮不是继续补功能，而是拿现有 `archive` CLI 去做真实试用。

结论很直接：

- 这条链路已经可以进入“内部可用”的阶段
- 找 run、看单条 run、做 compare，这三件事已经基本成立
- 真正还没完全补齐的，不是主流程，而是少数输出细节

换成更白的话说：

现在它已经能帮人更快定位问题了，不只是技术演示。

但还不能说“试用已经完全收尾”，因为 artifact 这一块虽然已经能提示风险，但还缺一条真实的“确实产出了 file_change 一类 artifact”的样本来把判断闭环做满。

## 这次用了哪些真实 run

这次一共看了 5 条真实 run：

- `20260401T014940Z_search_docs_for_runtime_context_958e59`
  场景：成功 retrieval
- `20260401T014940Z_review_runtime_regression_output_3987bb`
  场景：失败 review
- `20260402T033134Z_artifact_summary_probe_bd6de6`
  场景：成功 review
- `20260402T040053Z_design_a_runtime_harness_plan_6b0170`
  场景：失败 planning，且触发 governance review
- `20260402T040053Z_implement_a_tiny_archive_marker_file_2f71dd`
  场景：成功 coding，但出现 expected artifact 未产出警告

说明：

- 前 3 条是之前已经存在的真实 run
- 后 2 条是这轮直接通过真实 `run` 入口补出来的真实样本

## 这轮实际跑过的命令

这轮重点跑了这些命令：

```bash
python -m entrypoints.cli archive --status failed --limit 10
python -m entrypoints.cli archive --task-type review --limit 10
python -m entrypoints.cli archive --task-type planning --limit 10
python -m entrypoints.cli archive --task-type coding --limit 10
python -m entrypoints.cli archive --latest
python -m entrypoints.cli archive --run-id <run_id>
python -m entrypoints.cli archive --compare-run-id <left_run_id> --compare-run-id <right_run_id>
python -m entrypoints.cli run --task "Design a runtime harness plan" --task-type planning
python -m entrypoints.cli run --task "Implement a tiny archive marker file" --task-type coding
```

## 试用记录

### 1. 先扫失败 run

命令：

```bash
python -m entrypoints.cli archive --status failed --limit 10
```

结果：

- 能很快找到失败 run
- `profile / task_type / failure_class` 已经足够做第一轮筛选
- 现在有 2 条失败 run 时，也还能一眼扫完

这一步最有用的一点：

- summary 列表足够短，适合先扫再点开

这一步还缺的东西：

- summary 列表里还看不到 `governance_status`
- 如果失败里混着“普通失败”和“需要治理复核”，现在必须点开单条才能确认

### 2. 看单条 run

命令示例：

```bash
python -m entrypoints.cli archive --run-id 20260402T040053Z_design_a_runtime_harness_plan_6b0170
python -m entrypoints.cli archive --run-id 20260402T040053Z_implement_a_tiny_archive_marker_file_2f71dd
```

结果：

- 单条输出已经足够像“最小诊断卡片”
- 不需要先去翻原始 JSON，已经能看懂基本状态

最有价值的两个真实例子：

- planning 失败样本里，`governance_status: review_required` 和 `governance_required: yes` 非常直观
- coding 成功样本里，`missing_expected_artifact_warning: yes` 很有用，它能告诉你“表面成功，但交付物没到位”

这一步还缺的东西：

- 单条输出里没有直接把 `reassessment_reason_codes` 或 `evaluation_reason_codes` 摘出来
- 如果想知道“为什么变高风险”，还是得去 compare 才更省时间

### 3. 做 compare

这轮做了几组最有代表性的 compare：

- 成功 retrieval vs 失败 review
- 成功 retrieval vs 失败 planning(governance review)
- 成功 retrieval vs 成功 coding(artifact warning)
- 失败 review vs 失败 planning(governance escalated)
- 成功 retrieval vs 成功 review

真实感受：

- `transitions` 很适合做第一眼判断
- `highlights` 基本已经是“人话版摘要”
- `reason_code_diff` 对“为什么变差”有解释力
- compare 这一步已经是整条链里最有价值的部分

最典型的 3 条真实输出：

- retrieval vs failed review
  最有用的一行：`highlights`
  价值：能立刻看到 `failure regressed / verification regressed / evaluation regressed`
- retrieval vs failed planning
  最有用的一行：`transitions`
  价值：直接看到 `governance=escalated`
- retrieval vs coding warning
  最有用的一行：`artifact_diff`
  价值：直接看到 `missing_expected=no->yes`

这一步还缺的东西：

- `artifact_diff` 在两边都没有 artifact 时，还会出现 `produced(+none; -none)` 这种低信息量内容
- 这类“无变化文字”会稀释重点

## 这轮总结出来的 4 个常见诊断模式

### 模式 1：普通执行失败

常见信号：

- `status=failed`
- `verification_status=failed`
- `governance_status=clear`
- compare 里常见 `failure=regressed`

怎么用：

- 先看 `failure_class`
- 再拿一个成功 run 做 compare
- 重点看 `highlights` 和 `reason_code_diff`

### 模式 2：治理升级型失败

常见信号：

- `status=failed`
- `governance_status=review_required`
- `governance_required=yes`
- compare 里会出现 `governance=escalated`

怎么用：

- 这类不是单纯“执行坏了”
- 它更像“后续建议超出当前 contract 边界”

### 模式 3：表面成功，但 artifact 不完整

常见信号：

- `status=success`
- `verification_status=passed`
- `missing_expected_artifact_warning=yes`
- compare 里 `artifacts=regressed`

怎么用：

- 这类 run 不能只看 success
- 要继续看 artifact warning

### 模式 4：compare 先于深挖

实际使用里最省事的顺序是：

1. 先用 `--status failed` 或 `--task-type ...` 找样本
2. 再点开单条 run 看最小诊断信息
3. 最后拿成功样本做 compare

这比直接翻 archive 目录快很多。

## 按清单判断，这轮通过了什么

### 1. 能不能快速找到想看的 run

判断：通过

原因：

- `status / task_type / formation_id` 过滤已经够用
- 5 条真实 run 的规模下，几分钟内能定位到目标

### 2. 单条 run 的信息够不够看

判断：通过

原因：

- 单条输出已经能直接看状态、失败阶段、治理状态、artifact 概况
- 不需要先回到 archive 目录翻 JSON

### 3. compare 能不能快速指出关键变化

判断：通过

原因：

- `transitions + highlights + reason_code_diff` 已经形成稳定组合
- 尤其对失败回归和治理升级很有帮助

### 4. artifact 差异有没有实际帮助

判断：部分通过

原因：

- 已经能在真实样本里抓到 `missing_expected=no->yes`
- 说明 artifact 维度不是摆设
- 但还缺“真实 produced artifact 明显变化”的样本，当前这块还不算完全验证完

## 现在最需要优化的 3 个输出问题

### 1. browse summary 里缺 governance 和 artifact warning 提示

这是这轮最明确的输出缺口。

现在扫失败列表时，无法直接区分：

- 普通失败
- 需要治理复核的失败

也无法直接看到：

- `missing_expected_artifact_warning`

### 2. artifact_diff 里还有一些空信息

例如：

- `produced(+none; -none)`
- `baseline(+none; -none)`

这些内容不算错，但真实使用里会抢注意力。

### 3. 缺一条真实的“产出了 artifact”的样本

这不是 browse/compare 本身的结构问题，而是试用覆盖还差一点。

现在已经验证了：

- expected artifact 差异
- missing expected artifact warning

但还没在真实 run 里验证到：

- `produced_artifacts=file_change(...)`

## 我对当前阶段的判断

如果只看 archive 这一条线：

- M1 可以认为已经完成
- M2 已经非常接近完成
- M3 还没完成，但已经进入准备阶段

更具体一点：

- M1：基本完成
- M2：大约 90%
- M3：大约 65%

## 下一步最值得做的事

我建议下一轮不要扩 scope，而是做 3 件小而准的事：

1. 先补 browse summary 行
   目标：把 `governance_status / governance_required / missing_expected_artifact_warning` 直接放进 summary

2. 再收紧 artifact_diff 文案
   目标：去掉 `+none; -none` 这类空信息，让重点更突出

3. 再补 1 条真实 artifact-producing run
   目标：把 artifact 这条线从“部分通过”补到“完全通过”

做完这 3 件事，archive 这条线就更接近“小范围稳定试用”的标准了。

## 同日后续补齐结果

这份报告写完后，又把当时列出来的 3 个缺口补了一轮：

- browse summary 现在已经直接显示 `governance` / `gov_required` / `missing_expected`
- `artifact_diff` 已去掉 `produced(+none; -none)`、`baseline(+none; -none)` 这类空信息段
- 已经补出一条真实 `file_change` 样本：`20260402T042522Z_implement_a_tiny_archive_marker_file_d081a4`

这意味着当时报告里“artifact 只有部分通过”的那一条，现在已经补到了可验证状态。
