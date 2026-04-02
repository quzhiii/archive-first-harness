# Archive Browse 第二轮调整总结

日期：2026-03-31

## 一句话总结

这一轮把上一轮“能写 archive”推进成了“能读 archive、能查 archive、能比较 archive”。

如果说上一轮是在给系统补病历，这一轮就是先把最基础的查病历能力补上了，而且仍然保持在很轻、很稳、很容易回退的范围内。

## 这轮具体做了什么

### 1. 新增 archive 读取层

新增文件：

- `entrypoints/archive_browse.py`

这一层现在能做几件很实用的事：

- 看最近几次 run archive
- 按 `workflow_profile_id` 筛
- 按 `status` 筛
- 按 `failure_class` 筛
- 按 `run_id` 精确查一条
- 比较两次 run 的状态和失败签名差异

重点是：

- 只读
- 文件系统优先
- 直接基于 `artifacts/runs/index.jsonl`
- 不引入数据库

### 2. 把 archive browse 接进 CLI

更新文件：

- `entrypoints/cli.py`

现在可以直接在终端里跑：

```bash
python -m entrypoints.cli archive --limit 5
python -m entrypoints.cli archive --status failed
python -m entrypoints.cli archive --run-id <run_id>
python -m entrypoints.cli archive --compare-run-id <run_a> --compare-run-id <run_b>
```

现在输出的是人能直接看的文本，不是大块 JSON。

### 3. 补上了这层的专项测试

新增文件：

- `tests/test_archive_browse.py`

这轮重点测了：

- browse/filter 是否工作
- 单 run 查询是否返回最小诊断包
- compare 是否能识别状态和失败差异
- CLI 输出是不是稳定、可读
- browse/compare 是否保持只读，不修改 index 或 archive 文件

## 这轮验证结果

已跑全量测试：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 259 tests in 2.451s
OK
```

说明这轮新增 archive browse/compare 层后，没有把已有能力打坏。

## 这轮的边界控制

这轮有意识地没往外扩，没做这些：

- 没做数据库检索
- 没做 HTTP/API 接口
- 没做 replay/retry 控制
- 没做复杂 query 语言
- 没碰 runtime/orchestrator 主控制流

也就是说，这轮仍然是在“把 archive 层变得可用”，而不是“再造一个大系统”。

## 这一轮之后，项目状态怎么理解

现在这个项目在 archive 方向上已经有两层：

1. 写入层：每次单任务运行会留下独立 archive
2. 读取层：可以浏览、查询、比较这些 archive

这意味着后面你再做 formation 比较、失败归因、离线分析，就已经有一个比较像样的 run-level evidence 基础了。

## 下一步最建议做什么

下一步仍然建议小步走，优先顺序我建议是：

1. 补 `index.jsonl` 丢失时的目录扫描回退
2. 增加 `archive --latest` 这种更顺手的快捷命令
3. 让 compare 再多带一点稳定字段，比如 verification/governance 差异
4. 等 run 量明显增大以后，再考虑 SQLite/FTS

## 最后一层判断

到这一步，项目已经不只是“把结果跑出来”，而是开始具备“把一次运行解释清楚”的能力。

这是后面继续做 AI agent 工程化优化时，最值钱的基础层之一。
