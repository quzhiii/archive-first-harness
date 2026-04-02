# M3 硬验收清单

日期：2026-04-02

说明：

- 这份清单只看 pass / fail，不看百分比
- 全部通过，才算 M3 完成
- 任何一条失败，都说明还不能说“小范围稳定试用完成”

## Checklist

- [ ] 一个非作者测试者能在 5 分钟内完成 `run -> latest -> browse -> compare` 的最小流程
- [ ] 一个非作者测试者在没有口头解释的情况下，能看懂 `archive --run-id` 输出中的核心字段
- [ ] `archive --latest` 在 10 次连续真实 run 后零报错
- [ ] 至少 3 条真实使用日记表明 archive 输出真的改变了排查或决策方式
- [ ] coding 类型任务的 `produced_artifacts` 在 10 次连续真实 run 中零丢失
- [ ] `archive --status failed --limit 10` 能在 30 秒内帮助使用者定位最值得先看的失败 run
- [ ] `archive --compare-run-id` 能在 30 秒内帮助使用者判断“这次为什么比上次差”或“这次为什么比上次好”
- [ ] `artifacts/runs/index.jsonl` 在 50 次真实 run 后保持可读且无损
- [ ] 至少完成 1 次非作者端到端人工验收，并留下问题清单
- [ ] 全量测试保持通过，且 archive 相关测试没有新增不稳定项

## 通过标准

- 全部勾选完成：M3 完成
- 任意一条未完成：M3 未完成
