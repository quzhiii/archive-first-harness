# 项目架构、理念、当前进展与下一步规划

日期：2026-04-02

## 1. 这是什么项目

这个项目不是一个“大而全”的 AI 平台，也不是现在就要做成一个带 Web、数据库、队列、插件市场的复杂系统。

它当前真正要做的，是一个可运行、可检查、可比较、可逐步扩展的 AI Agent Runtime Harness。

换成更直白的话说：

它的目标不是先把外壳做大，而是先把一条核心执行链打磨稳定，让每次任务从进入系统，到执行，到校验，到归档，都能留下清晰证据，便于后面持续优化。

所以这个项目的核心定位是：

- 一个偏底层的 AI Agent 运行骨架
- 一个面向诊断和演进的本地运行时
- 一个先把执行质量和可观测性做扎实，再逐步扩边界的工程系统

## 2. 做这个项目的目的和背景

这个项目不是为了“再做一个 AI 工具”，也不是为了追热点做一个能聊天、能调工具的壳。

它真正想解决的问题，是现在大多数 AI Agent 系统都有一个共同短板：

- 看起来很聪明
- 演示时很强
- 但一到真实任务里，就容易失控、漂移、不可复盘、不可比较

换句话说，很多系统的问题不是“不会做”，而是“做了以后说不清楚为什么这样做、哪里出了问题、下一次怎么变好”。

所以做这个项目的目的，其实有四层。

### 2.1 第一个目的：把 AI Agent 从演示品变成工程系统

一个真正能长期使用的 Agent，不应该只会完成任务，还应该具备这些能力：

- 每次执行前有明确输入和边界
- 每次执行后有验证结果
- 失败时知道失败在哪一层
- 和上一次相比，能看出到底哪里变了
- 后续优化不是靠感觉，而是靠证据

这个项目本质上就是在做这件事：

把 Agent 从“偶尔表现很好”的模型行为，变成“可以持续诊断、持续优化”的工程对象。

### 2.2 第二个目的：建立一个可以长期进化的 Agent 骨架

如果一开始就把系统做成巨大的平台，通常会有一个问题：

- 外层功能越来越多
- 内部执行链越来越乱
- 最后谁都说不清，问题究竟出在模型、提示词、工具、流程、状态，还是治理边界

所以这个项目故意反过来做。

先把骨架搭稳，再逐步扩。

这意味着：

- 先稳住 runtime 主链
- 先把 archive 证据层建立起来
- 先让 compare 和诊断真的有用
- 再去谈 API、数据库、调度、平台化

这是一种先打地基，再加楼层的思路。

### 2.3 第三个目的：让系统具备可治理性

很多 Agent 项目会把重点放在“让它更自主”。

但这个项目更重视的，是让它在变强的同时，仍然可管、可控、可解释。

所以它不是默认追求最大自治，而是默认追求：

- 边界清楚
- 风险可见
- 失败可查
- 升级有依据

你可以把它理解成：

这个项目不是先追求“最像人”，而是先追求“最像一个靠谱系统”。

### 2.4 第四个目的：为后续多 Agent 协同打基础

虽然当前版本仍然是保守的单主链结构，但底层思路已经不是单 Agent 玩具，而是面向未来协同系统预留空间。

真正要走向更复杂的协同，前提不是先把 Agent 数量堆上去，而是先回答这些问题：

- 每个 Agent 的角色边界是什么
- 谁负责执行，谁负责校验，谁负责治理
- 一次协同失败后，证据怎么留
- 两次不同编排方式之间，怎么做比较

如果这些问题没有底层证据层支撑，多 Agent 只会更乱。

## 3. 这个项目背后的哲学理念

这部分不是文学包装，而是项目设计时真正起作用的几套方法论。

### 3.1 剑阵理念：不是靠单点最强，而是靠结构稳定

“剑阵”这个说法，强调的不是某一把剑最强，而是阵型、位置、配合、节奏和边界。

把它放到这个项目里，对应的是：

- 不迷信单次模型输出
- 不把“某个 prompt 很神”当成系统能力
- 强调不同模块之间的职责分工
- 强调输入、执行、验证、治理、归档之间的阵型关系

换句话说，这个项目相信的不是“有一个最聪明的大脑就够了”，而是：

系统真正的战斗力，来自结构化编排，而不是单点爆发。

在工程上，它具体体现在这些设计选择里：

- runtime 主链不乱分叉
- verifier、governance、archive 不是附属品，而是阵型的一部分
- compare 不是装饰，而是阵后复盘能力
- policy / formation 先作为薄元数据进入系统，而不是过早做成巨大的控制子系统

所以剑阵理念的核心，不是炫技，而是：

- 有位置
- 有节奏
- 有约束
- 有协同
- 有复盘

### 3.2 三体理念：在高不确定环境里，先建立生存规则

“三体”给这个项目带来的，不是科幻感，而是一个很现实的视角：

在高不确定、高复杂度、信息不完全的环境里，系统首先需要的不是浪漫想象，而是清醒的生存规则。

AI Agent 的真实环境其实就很像这样：

- 模型能力会波动
- 工具调用会失败
- 任务目标常常不完整
- 上下文可能有偏差
- 一次看起来成功的执行，未必真的产生了有效交付

所以这个项目在方法上采取的是一种更偏“黑暗森林式”的工程态度：

- 不默认系统可靠，要验证
- 不默认输出正确，要校验
- 不默认成功就真的成功，要看 artifact
- 不默认一次优化有效，要和基线比较
- 不默认自主扩张安全，要经过 governance

这套思路听起来偏保守，但它非常适合做底层系统。

因为在不确定环境里，先建立生存秩序，比先追求能力扩张更重要。

### 3.3 两套理念怎么落到这个项目里

如果把上面两套理念合起来看，这个项目其实在做的是：

- 用剑阵解决结构问题
- 用三体解决不确定性问题

前者告诉我们：系统不能靠单点聪明，要靠结构稳定。

后者告诉我们：系统不能默认世界友好，要先建立验证、治理、归档、比较这些生存机制。

所以你会看到这个项目一直在坚持这些选择：

- 主链保守
- 证据优先
- 比较优先
- 治理优先于盲目自治
- 归档优先于平台化扩张

这不是慢，而是在给后续复杂系统打基础。

## 4. 这个项目的核心理念

### 4.1 先窄，后宽

先把最重要的一条主链做通，而不是一开始就把所有能力堆上去。

现在项目坚持的是：

- 先把单次任务跑顺
- 再把批量、导出、历史、归档这些外层能力一层层包上去
- 最后才考虑 API、数据库、队列、调度、插件等更重的东西

这是为了避免项目过早平台化，结果外壳很多，核心执行却不稳。

### 4.2 先证据，后扩张

项目现在特别强调“每次 run 都要留下可复盘证据”。

因为真正决定这个系统能不能持续优化的，不是说“它跑过”，而是后面能不能回答这些问题：

- 为什么这次成功了
- 为什么这次失败了
- 失败在哪一层
- 为什么这次和上次不一样
- 这次到底有没有产出预期交付物

这也是为什么这阶段要重点做 archive-first，而不是先上 HTTP 服务。

### 4.3 保持 runtime 核心保守稳定

`runtime/orchestrator.py` 这条主链目前仍然保持单路径、保守、可解释。

意思是：

- 不做复杂的自动控制流分叉
- 不做大规模自我修改
- 不让 evaluator 反过来接管 runtime
- 不让 compare 结果直接变成调度器

这样做的目的，是让每一层职责清晰，出了问题更容易定位。

### 4.4 外层能力可以加，但不能反客为主

现在项目已经逐步加上了：

- 单任务 surface
- batch surface
- export artifacts
- run history
- history summary
- history browse
- archive browse / compare

但这些层都只是“外层能力”，它们的作用是帮助使用、回看、诊断，而不是替代 runtime 核心本身。

## 5. 当前完整架构怎么理解

项目目前最稳定的结构边界可以理解成三层：

### 5.1 `entrypoints/`

这是最外层入口。

主要负责：

- CLI 输入
- 单任务执行入口
- batch 执行入口
- 导出 artifacts
- 写入 run history
- 写入 run archive
- 提供 history / archive browse 能力

它更像“项目的门面层”。

### 5.2 `runtime/`

这是核心执行层。

主要负责：

- orchestrator
- executor
- verifier
- model router
- methodology router

这里是项目的主链引擎，也是最不应该随便做复杂扩展的地方。

### 5.3 `harness/`

这是支撑能力层。

里面按能力拆分了多个子模块：

- `contracts/`：任务契约、profile 相关定义
- `state/`：状态模型和状态管理
- `context/`：工作上下文组装
- `tools/`：工具发现与注册
- `hooks/`：本地 hook 编排
- `journal/`：学习日志
- `sandbox/`：隔离与回滚抽象
- `telemetry/`：追踪和指标
- `evaluation/`：baseline compare、evaluation input、realm evaluator

可以把它理解成 runtime 的零部件和支撑层。

## 6. 当前主执行链路

到今天为止，这个项目最重要的一条主链，仍然是这条：

`surface request / CLI -> profile_input_adapter -> task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

这条链的价值在于：

- 输入先被标准化
- 中间有明确 contract
- 执行后有 verification
- 后面有 governance 和 sandbox
- 最后还能形成 evaluation 和 compare 证据

也就是说，这个系统不是让模型直接乱跑，而是给它套了一条比较规整的工程化执行链。

## 7. 当前外层能力链路

除了核心主链，项目外面还包了一层越来越完整的使用层。

目前已经形成的外层能力，大致是这样：

### 7.1 单任务 surface

通过 `SurfaceTaskRequest` 和 CLI `run --task ...`，可以让外部用更稳定的方式触发单个任务。

### 7.2 批量执行 surface

通过 `SurfaceBatchRequest` 和 `run --batch-file ...`，可以顺序执行一批任务。

### 7.3 导出层

batch 结果可以导出成：

- JSON
- JSONL
- Markdown summary

这让它既能被脚本消费，也能被人快速查看。

### 7.4 历史层

通过 `run_history.jsonl`、`latest_run.json`、`run_history_summary.json`，现在已经可以：

- 看最近一次 run
- 看最近几次摘要
- 精确查某个 run_id

### 7.5 archive 诊断层

这部分是最近推进最快、也是当前最关键的一层。

现在每次单任务 run 已经可以自动写到：

- `artifacts/runs/<run_id>/`

并留下这些关键文件：

- `manifest.json`
- `task_contract.json`
- `profile_and_mode.json`
- `verification_report.json`
- `metrics_summary.json`
- `evaluation_summary.json`
- `final_output.json`
- `context_plan.json`
- `execution_trace.jsonl`
- `failure_signature.json`
- `archive_index.json`

同时还有一个全局索引：

- `artifacts/runs/index.jsonl`

在这个基础上，CLI 已经支持：

- `archive --latest`
- `archive --run-id <id>`
- `archive --task-type ...`
- `archive --status ...`
- `archive --compare-run-id <left> --compare-run-id <right>`

## 8. 目前已经完成到什么程度

如果按阶段来理解，项目现在已经不是早期搭骨架了，而是到了“核心链路稳定化 + 诊断能力补全”的阶段。

### 8.1 已经稳定完成的部分

已经比较稳的能力包括：

- workflow profile 最小层
- profile-aware interpretation
- profile input adapter
- 单任务 surface
- batch surface
- batch export
- run history manifest
- history summary
- history browse
- history shortcuts
- archive-first 单次 run 归档
- archive browse / compare

### 8.2 最近这轮补强了什么

最近这一轮主要补的是 archive 诊断层，重点不是再加新系统，而是让它更接近真实可用。

这轮已经完成：

- browse summary 现在能直接显示 `governance`、`gov_required`、`missing_expected`
- compare 现在能看 failure / verification / reassessment / evaluation / governance 的变化
- compare 现在能看 `reason_code_diff`
- `artifact_diff` 的噪音已经压掉，不再输出大量空变化段
- coding 真实 run 已经能看到 `produced_artifacts: file_change`
- archive browse 已补索引坏行容错和索引缺行自动补扫
- 当前真实环境的 `artifacts/runs/index.jsonl` 已重建修复

### 8.3 真实 smoke test 的结论

这轮不是只跑测试样例，而是跑了真实开发流 smoke test。

已经验证通过的链路是：

`run -> latest -> browse -> run-id -> compare`

并且覆盖了这些真实场景：

- retrieval 成功
- review 从失败到成功
- planning 失败并触发 governance review
- coding 成功且真实产出 `file_change`

这意味着 archive 这条线现在已经不是概念上成立，而是真实命令链路已经跑通。

## 9. 当前进展怎么判断

如果只看 archive 这条主推进线，我现在的判断是：

- M1：约 100%，已完成
- M2：约 98%，基本完成
- M3：约 78%，已进入小范围稳定试用准备阶段

换成更白的话说：

- 已经可以内部使用
- 已经可以做真实排查
- 还没到完全收尾
- 还差端到端人工验收和连续几轮真实使用稳定性确认

## 10. 现在这个项目已经适合做什么

### 10.1 已经适合的场景

现在已经很适合做这些事：

- 看最新一次 run 到底发生了什么
- 按 `task_type` / `status` / `formation_id` 找某类 run
- 对比成功 run 和失败 run 的关键差异
- 对比两次成功 run 的 artifact 差异
- 快速判断某次失败是不是 governance 升级型失败
- 快速判断 coding run 有没有真的产出预期 artifact

### 10.2 还不适合完全依赖的场景

现在还不建议把它当成最终形态去依赖：

- 还不适合当完整交付级平台
- 还不适合一上来就做 Web/API 平台化
- 还不适合直接扩成数据库检索系统
- 还不适合做大规模自动调度和异步 worker 系统

因为这些扩展都应该建立在当前 archive 证据层已经足够稳的前提上。

## 11. 当前明确不做什么

这是项目现在非常重要的边界意识。

当前版本明确还不做：

- HTTP server / FastAPI shell
- queue / scheduler / async worker
- 数据库驱动的状态层
- 全文检索 / query DSL
- plugin runtime
- 自动 governance override
- compare / evaluator 直接反向控制 runtime
- 大规模 parallel worker pools
- 完整 replay / rerun 控制系统
- 复杂的 memory ranking / forgetting / semantic retrieval 系统

这些都不是永远不做，而是现在不该做。

## 12. 接下来最合理的规划

我建议接下来的规划仍然保持“小步、稳定、可验证”的节奏。

### 12.1 第一优先级：端到端人工验收

这是下一步最该做的事。

原因很简单：

现在 smoke test 已经通过了，但还需要确认一个真实使用者照着命令走，能不能顺手完成：

- 找 run
- 看 run
- 比较 run
- 判断问题

如果这一轮也顺，archive 这条线就能真正进入小范围稳定试用。

### 12.2 第二优先级：再经历 1 到 2 轮真实改动验证稳定性

现在已经修掉了一个真实问题：索引坏行会把 `archive` 命令打死。

但工程上真正稳不稳，不是看修掉一次，而是看后面连续几轮修改后它还稳不稳。

所以接下来要继续观察：

- archive 索引是否持续稳定
- browse / compare 输出是否还足够清晰
- 新增 run 类型后是否还需要新的过滤维度

### 12.3 第三优先级：根据真实使用反馈再决定要不要扩边界

只有当前 archive 层稳定之后，才值得讨论这些更大的问题：

- 要不要加 API
- 要不要加 DB / 查询层
- 要不要做更重的索引
- 要不要做 host adapter
- 要不要继续往 formation / policy 扩展

顺序不能反。

## 13. 我对这个项目现阶段的总体判断

这个项目现在最有价值的地方，不是“看起来像个完整 Agent 平台”，而是它已经开始具备一个好 runtime 系统该有的几个关键特征：

- 主链清楚
- 边界清楚
- 外层能力分层清楚
- 每次 run 有证据
- 失败和变化可以比较
- 迭代节奏是小步、可验证、可回退的

这说明它的方向是对的。

下一阶段最重要的不是做更大，而是让这条已经成型的链路变得更稳、更顺手、更适合真实试用。

## 14. 一句话总结

这个项目现在的本质，是一个以“保守 runtime 主链 + archive-first 证据层”为核心的 AI Agent 运行骨架；当前已经完成核心诊断链路的可用化，接下来要做的是把它从“内部可用”推进到“小范围稳定试用”。
