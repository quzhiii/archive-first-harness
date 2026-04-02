# archive-first-harness

[English](README.md) | 简体中文

一个面向 AI Agent 的“诊断优先”运行时骨架。

这个项目的核心目标，不是把 Agent 做成一个看起来很强的演示系统，而是把 Agent 的执行过程变成一个可检查、可比较、可治理、可持续优化的工程系统。

它当前刻意保持克制。它不是一个完整平台，而是一个保守稳定的 runtime 主链，加上一层 archive-first 的证据层，帮助你在 run 之后真正回答“发生了什么、为什么会这样、下一步该怎么改”。

## 为什么要做这个项目

大多数 AI Agent 系统都有同一个问题：

- 演示时很亮眼
- 单次跑得很顺时很像“已经可用”
- 但一到真实任务里失败，就很难回答最基本的问题

比如：

- 为什么这次失败？
- 失败在什么阶段？
- 为什么这次比上次差？
- 这次到底有没有产出预期交付物？
- 问题出在模型、工具、契约、验证还是治理？

这个仓库就是为了解决这一类问题而做的。

## 这个项目的核心优势

这个项目真正的优势，不是功能堆得多，而是工程判断更克制。

### 1. 诊断优先，不是演示优先

每一次 run 都应该在事后能够被解释，而不是只在当下看起来聪明。

### 2. Archive-first 证据层

每次 run 都可以落到 `artifacts/runs/<run_id>/` 下，形成结构化证据，包括 task contract、verification、evaluation、failure signature、execution trace 等内容。

### 3. 稳定的比较回路

当前最实用的一条闭环是：

`run -> latest -> browse -> run-id -> compare`

这意味着你可以直接比较两次 run 的差异，而不是翻一堆原始 JSON 猜原因。

### 4. 保守的 runtime 核心

运行时主链仍然是单路径、可解释、保守的。compare 和 evaluation 不会偷偷变成一个不透明的控制平面。

### 5. 面向长期进化，而不是过早平台化

这个项目优先解决“基础是否稳、证据是否清楚”，而不是一开始就扩成 API、DB、队列、多 Agent 平台。

## 当前架构

当前边界故意保持简单：

- `entrypoints/`：CLI、task runner、batch runner、history、archive 入口层
- `runtime/`：orchestrator、executor、verifier、模型与方法路由
- `harness/`：contracts、state、context、tools、hooks、journal、sandbox、telemetry、evaluation
- `planner/`：task contract 与规划辅助层
- `tests/`：单测、冒烟测试、archive/history/integration 测试

### Runtime 主链

`surface request / CLI -> profile_input_adapter -> task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

### Archive 诊断链

`run -> write_run_archive(...) -> artifacts/runs/<run_id>/ -> archive --latest / --run-id / browse filters / --compare-run-id`

## 技术路线

这个项目遵循的是分阶段技术路线。

### 第一阶段：稳住 runtime 主链

- 保持执行链条窄而清晰
- 保持每层职责明确
- 保持失败可诊断

### 第二阶段：建立 archive 证据层

- 持久化单次 run 的结构化产物
- 让 run 可以浏览、定位、比较
- 降低回归和失败排查成本

### 第三阶段：用真实使用验证价值

- 外部 UAT
- 真实使用日记
- 用硬验收清单代替主观百分比

### 当前明确延后

在 archive 诊断闭环被真实验证之前，这些东西都故意不先做：

- HTTP / API 服务层
- 数据库检索与 query DSL
- async worker / queue
- plugin 生态
- replay / rerun 编排
- 大规模多 Agent runtime 扩张

## 当前状态

这个仓库目前处在 alpha 阶段，重点是“证明这条诊断闭环在真实工作里有用”。

### 已经具备的能力

- profile-aware 输入标准化
- 单任务执行 surface
- 顺序 batch surface
- batch export artifacts
- append-only run history
- latest / summary / lookup shortcuts
- archive-first 单次 run 归档
- archive browse / compare

### 已经验证过的内容

- 成功、失败、governance-review、coding-artifact 等真实场景下的 archive smoke flow
- 本地全量测试通过
- Windows 导向的 CLI/UAT 预处理和 shell 区分说明

### 当前验证结果

- 本地全量测试：`291` 项通过
- archive 核心诊断链路已在真实 run 上完成 smoke test
- `archive --latest`、`archive --run-id`、`archive --compare-run-id` 已完成真实场景验证

## 为什么这个项目值得关注

如果你关心的是“AI Agent 怎么真正进入工程实践”，这个项目的价值在于：

- 它优化的是 run 的可解释性，而不只是 run 的完成率
- 它把 verification 和 governance 当成一等公民
- 它能让 artifact 层差异变得可见
- 它比过早膨胀的平台更容易推断和演进
- 它为未来更复杂的多 Agent 协同打地基，但不在今天就把系统做乱

## 当前已知限制

当前已知限制包括：

- 外部 UAT 仍然有限，易用性还没有被广泛验证
- Windows 首次运行仍然依赖 shell 区分说明
- `run` 的原始 JSON 对第一次使用者来说仍偏重
- archive 当前每次 run 会写出较多文件，信噪比还需要通过真实使用继续验证
- 这还不是托管产品，也不是生产级平台

## 快速开始

### Windows PowerShell

```powershell
$env:PYTHONPATH="."; python -m entrypoints.cli inspect-state
$env:PYTHONPATH="."; python -m entrypoints.cli run --task "ping" --task-type retrieval
python -m entrypoints.cli archive --latest
```

### Windows CMD

```cmd
set PYTHONPATH=. & python -m entrypoints.cli inspect-state
set PYTHONPATH=. & python -m entrypoints.cli run --task "ping" --task-type retrieval
python -m entrypoints.cli archive --latest
```

### 第一次运行预期会看到什么

对于 `ping` 任务，你应该看到：

- `run` 返回成功 JSON
- 输出里包含新的 `run_id`
- `archive --latest` 返回清晰的归档摘要

重要提示：第一次体验时，不建议把注意力放在完整 `run` JSON 上。先看 `archive --latest`，再看 browse / compare，会更容易理解这个系统的价值。

## 建议阅读顺序

如果你想认真评估这个仓库，建议按这个顺序看：

1. `README.md`
2. `README.zh-CN.md`
3. `PROJECT_ARCHITECTURE_STATUS_AND_ROADMAP.md`
4. `docs/2026-04-02-archive-real-dev-smoke-test.md`
5. `docs/2026-04-02-external-uat-quickstart.md`
6. `docs/2026-04-02-m3-hard-acceptance-checklist.md`

## 适合谁

这个仓库更适合这些人：

- 正在做 AI Agent runtime 或执行质量问题的人
- 关注回归诊断的人
- 想先把 run-level evidence 做扎实，再扩系统边界的人
- 想研究如何让 AI Agent 更可检查、更可治理的人

它现在还不适合普通终端用户直接使用。

## 下一步路线

短期重点：

1. 继续优化首次运行入口
2. 完成真人外部 UAT
3. 积累真实使用日记
4. 提高 archive 输出的信噪比
5. 在扩边界前先验证重复运行稳定性

## 测试与验证材料

相关文档包括：

- `tests/uat_results/observation_logs/2026-04-02-pre-check-report.md`
- `tests/uat_results/observation_logs/2026-04-02-uat-observation-summary.md`
- `tests/uat_results/reports/2026-04-02-cli-cross-platform-compatibility.md`
- `docs/2026-04-02-archive-real-dev-smoke-test.md`
- `docs/2026-04-02-m3-hard-acceptance-checklist.md`

## Alpha 说明

这是一个 alpha 阶段的工程仓库。

如果你愿意测试，最有价值的反馈不是“这个很酷”，而是：

- 你卡在了哪一步
- 哪些字段名看不懂
- `compare` 有没有真的帮助你判断差异
- archive 输出有没有帮你省时间

这类反馈，才是真正能推动这个仓库变得更好的东西。
