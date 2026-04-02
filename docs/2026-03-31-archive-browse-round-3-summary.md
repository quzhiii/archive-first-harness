# Archive Browse 第三轮调整总结

日期：2026-03-31

## 一句话总结

这一轮把 archive 读层从“能查”继续推进到“更抗丢、更顺手、更能比较”。

上两轮已经做到：

- 单次 run 会写 archive
- 可以 browse / lookup / compare archive

这一轮补的是三个很关键但很轻的小能力：

- `index.jsonl` 不在时，archive 读层可以直接扫描 run 目录回退
- CLI 支持 `archive --latest`
- compare 不只看 failure，还会一起看 verification 和 governance 差异

## 这轮具体做了什么

### 1. 补了 index 缺失时的目录回退

更新文件：

- `entrypoints/archive_browse.py`

现在 archive 读层不再强依赖 `artifacts/runs/index.jsonl`。

如果 index 在，就继续优先走 index。

如果 index 不在，就直接扫描：

- `artifacts/runs/<run_id>/manifest.json`
- `artifacts/runs/<run_id>/failure_signature.json`
- `artifacts/runs/<run_id>/profile_and_mode.json`

然后临时拼出最小 entry 列表，再继续做 browse / latest / find。

这一步的意义很直接：archive 层不再因为索引文件缺失而整层失效。

### 2. 新增 `archive --latest`

更新文件：

- `entrypoints/archive_browse.py`
- `entrypoints/cli.py`

新增了 `read_latest_run_archive(...)`，CLI 也接上了：

```bash
python -m entrypoints.cli archive --latest
```

现在想看最新一次 archive，不需要自己再手动加 `--limit 1` 再看哪一条是最后的。

这属于小改动，但实际使用体验会顺很多。

### 3. compare 多看了 verification / governance

更新文件：

- `entrypoints/archive_browse.py`

这轮 compare 读取的信息比上一轮更多了：

- `verification_report.json`
- `final_output.json` 里的 `residual_followup.governance`

所以现在 compare 不只会告诉你：

- status 一样不一样
- failure class 一样不一样

还会告诉你：

- verification status 一样不一样
- governance status 一样不一样
- governance 是否升级成需要人工 review

同时增加了更直观的 transition 判断：

- `failure_transition`
- `verification_transition`
- `governance_transition`

这样两次 run 一比，能更快看出来是：

- 失败回归了
- verification 退化了
- governance 风险升级了

## 现在 CLI 能做什么

当前可以直接这样用：

```bash
python -m entrypoints.cli archive --latest
python -m entrypoints.cli archive --limit 5
python -m entrypoints.cli archive --status failed
python -m entrypoints.cli archive --run-id <run_id>
python -m entrypoints.cli archive --compare-run-id <run_a> --compare-run-id <run_b>
```

并且：

- `--latest` 不能和 `--run-id` / `--compare-run-id` 混用
- compare 模式不能和 browse filter 混用
- 输出仍然是人能直接看的文本，不是大块 JSON

## 这轮测试覆盖了什么

更新文件：

- `tests/test_archive_browse.py`

新增覆盖点：

- index 存在时 latest 走 index
- index 缺失时 latest 回退到目录扫描
- index 缺失时 browse 也能继续工作
- compare 能看见 verification / governance 差异
- CLI 的 `archive --latest` 可用
- browse / latest / compare 继续保持只读，不改 archive 文件

## 验证结果

已跑：

```bash
python -m unittest discover -s tests -p "test_archive_browse.py"
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 260 tests
OK
```

说明这轮增强没有把前两轮 archive-first 改坏。

## 这轮边界控制

这轮依然没有扩出去做这些事：

- 没做数据库
- 没做 HTTP/API
- 没做 replay / rerun
- 没做复杂 query 语言
- 没改 runtime/orchestrator 主控制语义

也就是说，这轮还是在做“把 archive 读层打磨成真能用的工具”，而不是把项目拉进更重的新阶段。

## 下一步建议

这轮做完后，archive 方向上已经有三层能力：

1. 写 archive
2. 查 archive
3. latest / compare / fallback

下一步如果继续小步推进，我建议优先顺序是：

1. 让 compare 再多带一点 reassessment / evaluation 的稳定差异字段
2. 视情况补 index 为空或部分损坏时的更保守回退策略
3. 等 run 数量明显变多之后，再考虑 SQLite/FTS
