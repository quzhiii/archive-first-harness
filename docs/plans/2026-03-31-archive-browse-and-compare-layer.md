# Archive Browse And Compare Layer Plan

日期：2026-03-31

## 这一轮的目标

在已经完成 `archive-first` 写入层之后，补上一层非常薄、非常保守的读取层，让人可以直接回答三个问题：

- 最近有哪些 run
- 某个 run 到底是什么情况
- 两个 run 的状态和失败标签有什么差别

这一步仍然坚持文件系统优先，不上数据库，不上 API，不动 runtime 主控制语义。

## 已完成范围

本轮已经落地的内容：

- 新增 `entrypoints/archive_browse.py`
- 基于 `artifacts/runs/index.jsonl` 提供只读 browse/filter 能力
- 支持按 `workflow_profile_id` 过滤
- 支持按 `status` 过滤
- 支持按 `failure_class` 过滤
- 支持按 `run_id` 精确查询单个 archive
- 支持比较两个 run 的状态、profile、failure class、failed stage、task 是否一致
- 提供稳定的文字摘要格式化输出
- 在 CLI 中新增 `archive` 子命令

## 当前 CLI 形态

当前已经支持：

- `archive --limit <n>`
- `archive --run-id <id>`
- `archive --status <status>`
- `archive --workflow-profile-id <id>`
- `archive --failure-class <name>`
- `archive --compare-run-id <id> --compare-run-id <id>`

说明：

- 这层 CLI 只做只读查询
- 输出是人能直接看的文本，不是原始 JSON
- compare 模式单独使用，不和 browse filter 混用

## 这轮刻意没做的事情

这轮没有做：

- `archive --latest`
- index 缺失时回退扫描全部 run 目录
- SQLite / FTS / query DSL
- HTTP / API shell
- replay / rerun 控制
- archive 写回或修复逻辑

原因很简单：先证明 archive 读层本身是有价值、可读、稳定的，再决定要不要继续做更重的检索能力。

## 验收结果

这轮已经覆盖的验收点：

- archive summary 可以只读浏览最近 run
- 可以按常见诊断字段过滤
- 可以查单个 run 的最小诊断包
- 可以比较两个 run 的最小差异
- CLI 可直接使用
- 浏览和比较不会修改 archive 文件

## 下一步建议

下一步仍然建议保持小步推进，优先级如下：

1. 补 `index.jsonl` 缺失时的目录回退扫描
2. 补 `archive --latest` 这种更顺手的快捷入口
3. 在 compare 结果里增加更多稳定字段，比如 verification status 和 governance 状态
4. 只有当 run 数量明显增长后，再考虑 SQLite/FTS

## 结论

这一步的意义不是“再加一个子系统”，而是把上一轮写出来的 archive 真正变成可查、可看、可比的运行诊断层。
