# archive-first-harness

<div align="center">

**一个面向 AI Agent 的 archive-first 运行时骨架，让每次运行都能被诊断、比较和治理。**

[![Python](https://img.shields.io/badge/python-3.13.2-blue?logo=python&logoColor=white)](https://www.python.org/)
[![阶段](https://img.shields.io/badge/阶段-public%20alpha-1f6feb)](#当前状态)
[![重点](https://img.shields.io/badge/重点-archive--first-111111)](#为什么要做这个项目)
[![测试](https://img.shields.io/badge/测试-291%20项通过-brightgreen)](#验证情况)

[中文文档](README.zh-CN.md) | [**English**](README.md)

[快速开始](#快速开始) • [为什么要做这个项目](#为什么要做这个项目) • [核心优势](#核心优势) • [当前架构](#当前架构) • [验证情况](#验证情况) • [路线图](#路线图)

</div>

---

## 这是什么

`archive-first-harness` 不是一个上来就想做成“大而全平台”的 AI Agent 项目。

它当前只聚焦一个很硬的工程问题：

**当一次 Agent run 成功、失败、或者相对上一版退化时，我们能不能用证据解释清楚，而不是靠感觉猜。**

为了解这个问题，项目现在采取的是 archive-first 的路线：

- runtime 主链先保持克制
- 每次 run 落结构化证据
- 让 run 在事后可以浏览、定位、比较
- 用诊断闭环驱动优化，而不是靠单次 demo 的观感

如果你关心的是可复盘、可验证、可比较的 Agent 工程能力，而不是表面上看起来多聪明，这个仓库就是为这件事做的。

## 为什么要做这个项目

很多 Agent 系统在演示时很亮眼，但一旦进入真实任务，就会立刻暴露一个问题：**事后说不清楚。**

最常见的问题包括：

| 问题 | 为什么重要 |
|---|---|
| 为什么这次失败？ | 不知道原因，就无法改进。 |
| 失败发生在哪一层？ | 需要区分是路由、执行、验证还是治理出了问题。 |
| 为什么这次比上次差？ | 没有比较能力，就只能凭印象调参。 |
| 这次到底有没有产出预期交付物？ | “看起来成功”不等于真的成功。 |
| 下一步应该改哪里？ | 优化应该由证据驱动，而不是靠主观判断。 |

这个仓库存在的意义，就是把这些问题变成可以回答的问题。

## 核心优势

### 1. archive-first，而不是 demo-first

每次 run 都被当作一个可以事后复盘的工程事件，而不是一次性的效果展示。

### 2. 诊断证据是一级产物

每次 run 可以落到 `artifacts/runs/<run_id>/`，典型内容包括：

- `manifest.json`
- `verification_report.json`
- `failure_signature.json`
- `execution_trace.jsonl`
- `final_output.json`

### 3. 已经形成一条可用的比较闭环

当前最实用的闭环是：

`run -> latest -> browse -> run-id -> compare`

这比人工翻原始 JSON 去猜哪里变了，更接近真实工程里的使用方式。

### 4. runtime 主链保持保守

项目现在不会让 evaluator 或 compare 反过来悄悄接管执行控制面。主链依旧保持窄、稳、可定位。

### 5. 明确克制边界

当前故意不做数据库、队列、插件市场、平台化 API 和大规模多 Agent 编排。先把地基打稳，再谈扩边界。

## 当前架构

当前结构可以理解为“稳定的 runtime 主链 + archive 证据层”。

| 层级 | 主要职责 |
|---|---|
| `entrypoints/` | CLI 入口、task runner、batch runner、history、archive 入口 |
| `runtime/` | orchestrator、executor、verifier、路由与治理衔接 |
| `harness/` | state、contracts、context、tools、journal、telemetry、evaluation 基础设施 |
| `planner/` | task contract 与规划辅助 |
| `tests/` | 单测、冒烟、archive/history/integration 验证 |

### Runtime 主链

`request -> 输入标准化 -> task contract -> state/context -> execution -> verification -> governance -> 必要时 rollback -> journal -> telemetry -> evaluation inputs`

### Archive 诊断链

`run -> write_run_archive(...) -> artifacts/runs/<run_id>/ -> archive --latest / --run-id / --compare-run-id`

### 当前设计原则

先把它做成一个可靠的底层骨架，而不是先做成一个边界很大的平台。

## 当前状态

这个仓库目前处于 **public alpha** 阶段。

已经可用的部分：

- profile-aware 输入标准化
- 单任务 CLI 执行
- 顺序 batch 执行
- append-only 历史记录与 latest 快捷读取
- 单次 run 的 archive 归档
- archive 浏览
- run 间 compare 对比

明确暂缓的部分：

- 托管 API 服务
- 数据库检索层
- async queue / worker
- 插件生态
- 大规模多 Agent 协调

## 验证情况

这个项目现在不是只停留在文档层，核心链路已经被实际跑过。

### 已验证结果

- 本地全量测试：`291` 项通过
- 已完成成功、失败、governance-review、coding-artifact 等真实场景下的 smoke flow
- `archive --latest`、`archive --run-id`、`archive --compare-run-id` 都已经在真实 run 上验证
- 外部 UAT 结果显示，当前主要问题是首次进入门槛，而不是 archive 逻辑本身失效

### 当前最关键的结论

**archive 闭环已经有用了，但第一次上手体验还不够顺。**

这是一个可以接受的 alpha 问题，说明现在的瓶颈更偏向 onboarding，而不是底层架构完全站不住。

## 快速开始

### 环境

- 推荐 Python `3.13.2`
- 当前 baseline 不依赖第三方运行时库
- 当前主要验证环境是 Windows PowerShell 和 CMD

### 克隆仓库

```bash
git clone https://github.com/quzhiii/archive-first-harness.git
cd archive-first-harness
```

### PowerShell

```powershell
$env:PYTHONPATH="."
python -m entrypoints.cli inspect-state
python -m entrypoints.cli run --task "ping" --task-type retrieval
python -m entrypoints.cli archive --latest
```

### CMD

```cmd
set PYTHONPATH=.
python -m entrypoints.cli inspect-state
python -m entrypoints.cli run --task "ping" --task-type retrieval
python -m entrypoints.cli archive --latest
```

### 第一次运行会看到什么

对于 `ping` 任务，你应该看到：

- 一次成功的 `run` 返回
- 一个新的 `run_id`
- 一份可读的 `archive --latest` 归档摘要

第一次体验时，建议先看 `archive --latest`，不要一上来就盯着完整 `run` JSON。

## 适合谁

这个项目更适合：

- 在做 AI Agent runtime 质量问题的人
- 关心回归诊断和可复盘性的开发者
- 想先把 run-level evidence 做扎实，再扩系统边界的团队
- 想研究 Agent 如何变得更可诊断、更可治理的人

它现在还不适合普通终端用户直接拿来当成熟产品使用。

## 文档索引

如果你想继续往下看，建议从这些文档开始：

- [项目架构、进展与路线图](PROJECT_ARCHITECTURE_STATUS_AND_ROADMAP.md)
- [真实开发场景的 archive smoke test](docs/2026-04-02-archive-real-dev-smoke-test.md)
- [外部 UAT 快速开始](docs/2026-04-02-external-uat-quickstart.md)
- [M3 硬验收清单](docs/2026-04-02-m3-hard-acceptance-checklist.md)
- [真实使用日记模板](docs/2026-04-02-real-usage-diary-template.md)
- [项目背景与范式文档](docs/background/README.md)

## 路线图

接下来优先做的事很明确：

1. 继续降低首次上手门槛
2. 收集更多公开 alpha 测试反馈
3. 继续提高 archive 输出的信噪比
4. 用真实使用日记替代继续空转写架构
5. 在 repeated-use 被证明之前，继续保持 runtime 边界稳定

## Public Alpha 说明

如果你愿意测试这个仓库，最有价值的反馈不是“看起来很酷”。

真正有用的反馈是：

- 你卡在哪一步
- 哪些输出读起来费劲
- `compare` 有没有真的帮助你判断问题
- archive 浏览有没有帮你节省时间

这也是这个项目当前最核心的优化方向。
