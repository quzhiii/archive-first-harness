# Archive Browse 第五轮调整总结

日期：2026-04-01

## 这轮只做了什么

这一步继续保持小步推进，只补了 archive compare 里两个一直缺的能力：

1. `reason_codes` 的稳定集合对比
2. 一条更容易看懂的 compare 摘要

没有扩展到数据库、HTTP API、回放系统，也没有改 runtime 主流程。

## 这轮新增的对比信息

更新文件：

- `entrypoints/archive_browse.py`
- `tests/test_archive_browse.py`

现在 compare 除了原来的 status、failure、verification、reassessment、evaluation、governance 之外，还会补出两组原因码：

- `reassessment_reason_codes`
- `evaluation_reason_codes`

并且会稳定给出：

- `same_reassessment_reason_codes`
- `reassessment_reason_codes_added`
- `reassessment_reason_codes_removed`
- `same_evaluation_reason_codes`
- `evaluation_reason_codes_added`
- `evaluation_reason_codes_removed`

这里刻意按“集合差异”来做，不按文本顺序做 diff。这样更稳，也更适合后面继续做诊断层。

## 输出现在更容易看懂了

`format_archive_brief(...)` 现在除了原来的几行结构化对比，还会多两行：

- `reason_code_diff:`
- `highlights:`

其中：

- `reason_code_diff` 负责把 added / removed 的原因码直接打出来
- `highlights` 负责用一句短话总结这次 compare 最值得注意的变化

比如现在可以直接看出：

- failure 是不是退化了
- verification 是不是退化了
- 风险是不是升高了
- evaluator 是否从 `keep` 变成 `observe`
- 是不是开始需要人工 review 了
- 具体是哪些 `reason_codes` 新增或消失了

## 这轮测试结果

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

到这一步，archive compare 已经具备：

1. failure 对比
2. verification 对比
3. reassessment 对比
4. evaluation 对比
5. governance 对比
6. reassessment / evaluation 的 reason code 差异
7. 面向人的简短摘要

这意味着它已经不只是“能查 run”，而是开始具备“轻量诊断对比层”的基本形态。

## 下一步建议

继续按小步推进的话，我建议下一步优先做下面两个方向之一：

1. 给 browse / latest / compare 增加更明确的 `task_type` / `formation_id` 过滤和展示
2. 给 archive compare 再补一层更轻量的 artifact 摘要差异，只看有没有关键产物缺失或变化

我更推荐先做第 1 个，因为它更直接影响“找得到”和“看得懂”。
