# Archive Browse 第七轮调整总结

日期：2026-04-02

## 这轮做了什么

这一步继续只做一刀，而且是很轻的一刀：

给 archive compare 补上了 `artifact` 摘要差异。

注意，这里不是去对比产物正文，也不是去做目录 diff，更不是开始做回放系统。只是把已经稳定存在的产物信号提炼成一层可读摘要，然后接进 compare 输出。

## 这轮新增了哪些 artifact 信号

更新文件：

- `entrypoints/archive_browse.py`
- `tests/test_archive_browse.py`

现在 archive entry / compare 会稳定读出这些 artifact 摘要：

- `expected_artifacts`
- `produced_artifact_types`
- `produced_artifact_count`
- `baseline_compare_status`
- `baseline_compared_artifact_types`
- `baseline_status_counts`
- `missing_expected_artifact_warning`

这些信号都来自现有 archive 文件：

- `task_contract.json`
- `final_output.json` 里的 `execution_result`
- `evaluation_summary.json` 里的 `baseline_compare_results`
- `verification_report.json`

所以这轮没有引入新存储，也没有改 runtime 主语义。

## compare 输出现在多了什么

compare 的文本输出现在新增：

- `artifacts_left:`
- `artifacts_right:`
- `artifact_diff:`

同时 `transitions:` 里多了一个维度：

- `artifacts=...`

`highlights:` 里也会在有变化时总结：

- expected artifacts 有没有变
- produced artifacts 有没有变
- baseline compare 涉及的 artifact 类型有没有变
- 这次 artifact 变化整体更像是 `unchanged / changed / improved / regressed`

## 这轮的价值

前几轮 archive compare 已经能回答：

- 有没有失败
- 风险是不是升高了
- evaluator 是不是变严了
- governance 有没有升级

这轮之后，它开始还能回答：

- 任务原本期望交付什么产物
- 这次实际产出了什么类型的产物
- 产物数量有没有变化
- baseline compare 这次到底比较了哪些 artifact
- artifact 层面是在变好、变坏，还是只是有变化

这会让 compare 更接近“内部诊断层”，而不只是“执行结果对比层”。

## 测试结果

已跑：

```bash
python -m unittest discover -s tests -p "test_archive_browse.py"
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 287 tests
OK
```

## 这轮之后的状态

到 2026-04-02 这一步，archive compare 已经有 7 个稳定维度：

1. failure
2. verification
3. reassessment
4. evaluation
5. governance
6. reason code 差异
7. artifact 摘要差异

这意味着 archive 这一条线，已经不只是“能查”和“能比”，而是开始具备“能快速诊断”的骨架了。

## 下一步建议

接下来最值得做的，不是再堆新字段，而是把“人怎么用”补完整：

1. 补 5 到 8 个真实命令示例
2. 用 5 到 10 条真实 run 做一次人工试用
3. 总结 3 到 5 条常见诊断模式

这三步做完，里程碑 M2 会更接近真正成立。
