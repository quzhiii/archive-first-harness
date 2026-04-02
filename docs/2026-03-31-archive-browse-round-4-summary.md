# Archive Browse 第四轮调整总结

日期：2026-03-31

## 一句话总结

这一轮继续只做很小的一刀：把 archive compare 从“能看 failure / verification / governance”推进到“还能看 reassessment / evaluation 的稳定差异和变化方向”。

## 这轮做了什么

更新文件：

- `entrypoints/archive_browse.py`
- `tests/test_archive_browse.py`

这轮主要补了两块 compare 信息：

### 1. reassessment 差异

现在 compare 会带出：

- `reassessed_level`
- `followup_needed`

并判断：

- `same_reassessed_level`
- `same_followup_needed`
- `reassessment_transition`

其中 `reassessment_transition` 会按风险等级顺序判断：

- 风险升高 -> `regressed`
- 风险降低 -> `improved`
- 一样 -> `unchanged`

### 2. realm evaluation 差异

现在 compare 会带出：

- `evaluation_status`
- `evaluation_recommendation`
- `evaluation_human_review`

并判断：

- `same_evaluation_status`
- `same_evaluation_recommendation`
- `same_evaluation_human_review`
- `evaluation_transition`

这里的重点不是去比较大段 summary 文本，而是只盯稳定字段：

- recommendation 有没有变
- 是否变成需要人工 review

这样更适合后面做工程化诊断，而不是做文本 diff。

## 这轮顺手修掉的一个语义问题

这轮在补 compare 时，顺手修掉了一个真实的 transition 判定 bug。

之前 `verification_passed` 和 `governance_required` 共用了同一种布尔 transition 规则，但这两类布尔值的“好坏方向”其实相反：

- `verification_passed=True` 是更好
- `governance_required=True` 是更差

现在已经改成按字段语义分别判断，所以：

- verification 失败会被判成 `regressed`
- governance 升级成 required 会被判成 `escalated`

这个修正比单纯加字段更重要，因为它让 compare 的结论方向变对了。

## 现在 compare 能看什么

现在一条 compare 结果里，已经能稳定看到这些层面：

- status
- failure_class / failed_stage
- verification
- reassessment
- evaluation
- governance

也就是说，现在对两次 run 的比较已经不只是“有没有失败”，而是开始能回答：

- 风险是不是上升了
- 是不是需要 followup 了
- evaluator 的 recommendation 变了没有
- 是否从无需人工 review 变成需要人工 review 了
- governance 是否升级了

## 测试覆盖

更新文件：

- `tests/test_archive_browse.py`

这轮新增覆盖点：

- success run 对 failed run 时，reassessment / evaluation diff 是否正确
- success run 对 governance-review run 时，governance diff 是否正确
- compare 输出里的 transition 文本是否和真实方向一致

## 验证结果

已跑：

```bash
python -m unittest discover -s tests -p "test_archive_browse.py"
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 261 tests
OK
```

## 这轮之后的状态

到这一步，archive compare 已经有五层可读差异：

1. failure
2. verification
3. reassessment
4. evaluation
5. governance

这已经非常接近“一个足够轻的 run-level 诊断对比层”了。

## 下一步建议

如果继续保持小步推进，我建议下一步优先做：

1. compare 再补 `reason_codes` 的稳定集合差异
2. 视情况补 `artifact` 层面的更轻量 compare 摘要
3. 等 run 量明显变大后，再考虑更重的索引或数据库方案
