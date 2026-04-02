# Archive Browse 第六轮调整总结

日期：2026-04-01

## 这轮做了什么

这一步继续保持小步推进，目标只有一个：让 archive 更容易被人真正拿来查。

本轮新增内容：

1. `archive browse` 支持按 `task_type` 过滤
2. `archive browse` 支持按 `formation_id` 过滤
3. browse 输出里补上了 `task_type` 和 `formation` 展示
4. compare 输出里补上了 `task_type` 和 `formation` 展示
5. archive index 行补上了 `task_type`
6. 对旧 index 做了缺失字段回填，避免老档案完全用不上新过滤

没有改 runtime 主流程，也没有扩展到数据库、HTTP API、回放或重执行。

## 这轮改了哪些文件

- `entrypoints/run_archive.py`
- `entrypoints/archive_browse.py`
- `entrypoints/cli.py`
- `tests/test_archive_browse.py`
- `tests/test_run_archive_index.py`

## 现在能做什么

现在 archive 这一层已经能直接支持这些命令场景：

```bash
python -m entrypoints.cli archive --latest
python -m entrypoints.cli archive --run-id <run_id>
python -m entrypoints.cli archive --compare-run-id <left> --compare-run-id <right>
python -m entrypoints.cli archive --task-type research
python -m entrypoints.cli archive --formation-id discovery
python -m entrypoints.cli archive --workflow-profile-id evaluation_regression --status failed
```

如果 run 数量开始变多，`task_type` 和 `formation_id` 会明显提升查找效率。

## 为什么这一步重要

前几轮更像是在把 archive compare 做得“更会看”。

这一轮更像是在把 archive browse 做得“更找得到”。

对真实使用来说，后者很关键，因为当 archive 只有几条时，所有功能都看起来够用；但只要 run 稍微多起来，如果没有可用的过滤维度，人就会很快放弃用它。

## 测试结果

已跑：

```bash
python -m unittest discover -s tests -p "test_archive_browse.py"
python -m unittest discover -s tests -p "test_run_archive_index.py"
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 261 tests
OK
```

## 到这一步的状态

到 2026-04-01 这一步，archive 诊断链路已经具备：

1. per-run archive 写入
2. latest / run-id / browse / compare 读取
3. failure / verification / reassessment / evaluation / governance 对比
4. reason code 差异
5. 面向人的短摘要
6. 按 `workflow_profile_id / task_type / formation_id / status / failure_class` 过滤

这条线已经开始进入“内部试用可行”的阶段了。
