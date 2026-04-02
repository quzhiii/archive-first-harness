# Archive 真实开发流 Smoke Test

日期：2026-04-02

## 先说结论

这轮 smoke test 可以判定为通过。

更直白地说：

- `run -> latest -> browse -> run-id -> compare` 这条真实链路已经跑通
- 现在已经不只是能看测试样例，也能看真实 run
- 中途还抓出一个真实问题：`artifacts/runs/index.jsonl` 出现坏行，导致 `archive` 命令直接报错
- 这个问题已经补了两层修复：代码层容错 + 当前索引文件重建

所以现在的状态不是“理论上能用”，而是“这条 archive 诊断链路已经能拿来做内部试用”。

## 这次 smoke test 实际验证了什么

这次不是补字段，而是把真实命令顺序完整走了一遍。

实际走的路径是：

1. 先通过真实 `run` 产出几类样本
2. 用 `archive --latest` 看最新一次 run
3. 用 `archive` browse 模式按条件筛选
4. 用 `archive --run-id` 看单条诊断卡片
5. 用 `archive --compare-run-id` 看两次 run 的关键变化

覆盖到的真实场景有 4 类：

- retrieval 成功
- review 从失败到成功
- planning 失败并触发治理复核
- coding 成功且真实产出 `file_change`

## 这次用到的真实 run

### retrieval 成功

- `20260402T065322Z_search_docs_for_runtime_context_6098d9`

### review 对照

- 失败：`20260401T014940Z_review_runtime_regression_output_3987bb`
- 成功：`20260402T065322Z_review_runtime_regression_output_56d8c1`

### planning 失败 / governance review

- `20260402T065322Z_design_a_runtime_harness_plan_e25af2`

### coding 成功且真实产出 artifact

- `20260402T065322Z_implement_a_tiny_archive_marker_file_1c1dba`

## 实际命令与结果

### 1. latest

命令：

```bash
python -m entrypoints.cli archive --latest
```

结果要点：

- 能直接拿到最新 run
- 最新样本就是 coding 成功 run
- 输出里已经能直接看到：
  - `expected_artifacts: code_patch`
  - `produced_artifacts: file_change`
  - `missing_expected_artifact_warning: no`

这说明“真实 coding run 的 artifact 产出”已经被 archive 正常记录并展示出来了。

### 2. browse

命令：

```bash
python -m entrypoints.cli archive --task-type coding --limit 5
python -m entrypoints.cli archive --status failed --limit 10
```

结果要点：

- coding browse 能一眼区分：
  - 旧样本里哪个 run 有 `missing_expected=yes`
  - 新样本里哪个 run 真正产出了 `file_change`
- failed browse 能一眼区分：
  - 普通执行失败
  - governance review 类型失败

这一步的可用性已经比较高，因为列表行本身就带了：

- `task_type`
- `failure`
- `governance`
- `gov_required`
- `missing_expected`

用户不必先打开单条 run 才知道该先看哪条。

### 3. run-id

命令：

```bash
python -m entrypoints.cli archive --run-id 20260402T065322Z_search_docs_for_runtime_context_6098d9
python -m entrypoints.cli archive --run-id 20260402T065322Z_design_a_runtime_harness_plan_e25af2
python -m entrypoints.cli archive --run-id 20260402T065322Z_implement_a_tiny_archive_marker_file_1c1dba
```

结果要点：

- retrieval 成功样本能直接看出：这是一个 `answer` 型交付
- planning 失败样本能直接看出：
  - `failure_class: no_candidate_tools`
  - `verification_status: failed`
  - `governance_status: review_required`
  - `governance_required: yes`
- coding 成功样本能直接看出：
  - `expected_artifacts: code_patch`
  - `produced_artifacts: file_change`
  - `produced_artifact_count: 1`

这一层已经基本是“最小诊断卡片”，不需要再翻 archive 目录里的 JSON 文件。

### 4. compare

最有代表性的 3 组对比：

#### retrieval 成功 vs planning 失败

结果最有价值的点：

- `failure=regressed`
- `verification=regressed`
- `reassessment=regressed`
- `evaluation=regressed`
- `governance=escalated`

`highlights` 这一行已经能直接读成一句人话：

- 从成功退化到失败
- 风险升高
- 需要治理复核

#### retrieval 成功 vs coding 成功且产出 artifact

结果最有价值的点：

- 两边都成功，但 artifact 明显不同
- `artifact_diff` 能直接看到：
  - `expected(+code_patch; -answer)`
  - `produced(+file_change; -none)`

这说明 compare 不只是拿来看失败，也能看“为什么这次 run 的交付物不同”。

#### review 失败 vs review 成功

结果最有价值的点：

- `failure=resolved`
- `verification=improved`
- `reassessment=improved`
- `evaluation=improved`

这组对比很适合做回归修复确认，因为一眼就能看到是“真的变好了”，不是只换了个状态字。

## smoke test 中发现的真实问题

这轮不是完全无异常。

真实跑到一半时，`archive --latest` / `archive --task-type ...` 一开始报错：

- `CLI error: Expecting value: line 1 column 1 (char 0)`

排查后发现原因很具体：

- `artifacts/runs/index.jsonl` 最后一行变成了一个孤立的 `}`
- 同时有 2 个真实 run 目录已经写出来，但没有进入索引

这个问题说明：

- 之前的 browse 实现过于信任 `index.jsonl`
- 只要索引脏一行，整条 archive 命令就会崩

## 这轮已经补掉的修复

### 修复 1：archive browse 对坏索引行容错

现在即使 `index.jsonl` 有坏行：

- 不会整条命令报错
- 会跳过坏行继续读

### 修复 2：索引缺行时自动补扫 archive 目录

现在即使索引没写全：

- 也会自动扫描 `artifacts/runs/*`
- 把缺失的 run 合并回来

### 修复 3：重建当前真实环境的索引文件

为了让当前工作区马上恢复到正常状态，这轮还把现有：

- `artifacts/runs/index.jsonl`

按真实 archive 目录重建了一遍。

结果是：

- 现在 `archive --latest` 又回到了 `source: index_file`
- 当前真实数据已经恢复一致

## 现在到底能不能用

我的判断是：可以开始用，而且已经适合内部小范围试用。

更具体一点：

### 现在已经适合的场景

- 看最新一次 run 到底发生了什么
- 按 `task_type` 或 `status` 过滤最近 run
- 拿一个成功 run 和一个失败 run 做 compare
- 看 coding run 有没有真实产出 artifact
- 看某次 run 是普通失败，还是治理升级型失败

### 现在还不算完全收尾的地方

- 还没有做更长时间的连续试用
- 还没验证更大 run 量下的使用体验
- 端到端人工验收还没正式打勾

## 里程碑更新

基于这次 smoke test，我对进度的判断更新为：

- M1：约 100%，已完成
- M2：约 98%，基本完成
- M3：约 78%，进入小范围稳定试用准备阶段

原因很简单：

- M2 最关键的真实链路已经跑通
- 这轮还补掉了一个真实稳定性缺口
- 但 M3 还差连续试用与最终人工验收

## 下一步最值得做的事

不要再急着扩功能了，最划算的是继续做收口：

1. 再经历 1 到 2 轮真实改动，确认 archive 诊断输出持续稳定
2. 做一次端到端人工验收，把“真的怎么用”走一遍
3. 如果后面 run 量开始上来，再判断是否需要更重的索引或查询层

## 一句话判断

archive 这条线现在已经到了“可以内部试用，不必再当纯演示看”的阶段。
