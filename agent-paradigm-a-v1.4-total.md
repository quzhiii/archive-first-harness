# Agent Paradigm A v1.4 总文件

> 本文件整合了 A 冻结稿 v1.4 的 19 个首版正文，作为 **A 阶段的收口版本** 与 **B 阶段的启动底稿**。
>
> 相比 v1.3.2，本版不再继续扩张 A 的世界观，而是完成三件事：
> 1. 锁定 **B 启动前决议卡**，明确残差风险重估主责、Methodology Router 的越权边界、v0.3 executor 的并发策略与 contract baseline；
> 2. 把“下一步要做什么”从分散待办收敛成 **B 路线图**，按阶段、主链、退役时序三条线给出实现顺序；
> 3. 将 A 的最终主线压缩为：**任务契约 → 状态选择 → 能力暴露 → 主路径 → 残差纠偏 → 治理退役**。
>
> 本版继续保留原有文化隐喻：诛仙剑阵、三省六部、三体机制、面壁者、Build to Delete / 剑阵自化、修仙境界等；但所有隐喻都必须映射到工程职责，不再作为独立扩层理由。

---

## 目录

- [00-problem-statement.md](#00-problem-statementmd)
- [01-principles.md](#01-principlesmd)
- [02-glossary.md](#02-glossarymd)
- [03-topology.md](#03-topologymd)
- [04-task-contract.md](#04-task-contractmd)
- [05-context-state.md](#05-context-statemd)
- [06-skills-registry.md](#06-skills-registrymd)
- [07-tool-discovery.md](#07-tool-discoverymd)
- [07a-model-router.md](#07a-model-routermd)
- [07b-learning-journal.md](#07b-learning-journalmd)
- [07c-methodology-router.md](#07c-methodology-routermd)
- [08-governance-sandbox.md](#08-governance-sandboxmd)
- [08a-event-payloads.md](#08a-event-payloadsmd)
- [09-observability-retirement.md](#09-observability-retirementmd)
- [10-a-to-b-interface.md](#10-a-to-b-interfacemd)
- [11-external-pattern-absorption.md](#11-external-pattern-absorptionmd)
- [12-next-steps.md](#12-next-stepsmd)
- [13-b-start-decision-card.md](#13-b-start-decision-cardmd)
- [14-b-roadmap.md](#14-b-roadmapmd)

---

# 00-problem-statement.md

# 问题陈述：为什么需要“剑阵范式”

## 0.1 问题不是“模型不够强”，而是系统代价结构变了

AI Agent 从单轮问答走向多步规划、工具调用和长任务执行后，系统的核心矛盾已经不再只是“模型能力是否足够”，而是：如何在可接受的 token、延迟、失败恢复成本下，让系统保持稳定、可控、可退役。

传统软件系统的主要成本来自固定基础设施；而 Agent 系统的主要成本来自可变的智能计算过程。一次看似成功率不低的 Agent 任务，在生产环境中只要存在显著失败概率，就会进一步诱发重试、反思、交叉验证、人工接管和回滚，从而形成“额外成本层”。本架构将这一现象统称为 **不可靠性税**。

## 0.2 当前主流 Agent 的四类核心病理

### （1）不可靠性税
单次任务失败并不是局部问题。它会引出重试、验证、补救、人工复核和状态恢复，从而让系统总体成本远高于“单次调用价格”的表面数字。

### （2）上下文腐化
在真实运行中，吞噬 token 的往往不是用户提示本身，而是：
- 工具定义
- 对话历史
- 检索文本
- 中间日志
- 遥测与状态信息

这些内容会在多轮循环中不断重复发送到模型上下文中，导致：
- token 成本上升
- 注意力被噪声稀释
- 中途遗忘真正重要的目标
- 出现循环调用、误用工具、幻觉扩散

### （3）静态工具暴露悖论
为了让 Agent 足够“全能”，开发者往往会把大量工具 schema 直接放进系统上下文。结果是：
- 工具越多，初始 prompt 越重
- 每轮调用都要支付相同的工具预热成本
- 工具选择质量反而下降
- 模型注意力被工具说明书稀释

### （4）模型过度使用
不是所有步骤都应该调用最高能力、最高成本的大模型。大量基础环节都可以由低成本模型或确定性组件完成。如果不做预算与路由，系统会把 80% 的基础任务都交给最高成本算力处理，形成明显的资源错配。

## 0.3 为什么不是“一个大模型 + 一堆工具”就够了

如果没有额外架构，单模型系统通常会面临以下问题：

1. 任务一长，上下文不断膨胀
2. 工具一多，schema 常驻成本上升
3. 一旦失败，恢复与补救逻辑混乱
4. 经验知识只能写在 prompt 里，难以沉淀
5. 模型能力一旦提升，旧 harness 不会自动退出

因此，需要一个范式来同时回答六个问题：

- 任务如何定义完成标准？
- 上下文如何维持高信噪比？
- 历史状态如何被选择性继承？
- 工具如何按需暴露而非静态预载？
- 失败后如何只修高风险残差，而不是全局重跑？
- 旧组件何时应当退役？

## 0.4 剑阵范式的目标

“剑阵范式”不是为了增加叙事复杂度，而是为了提供一套可落地的 Agent Harness 设计语言，用来同时处理：

- 可靠性
- token 经济学
- 能力编排
- 安全边界
- 组织知识复用
- 状态外置与选择性继承
- Build to Delete

它的核心目标不是“让系统看起来完整”，而是：

> 在尽可能低的上下文负担、尽可能小的执行副作用、尽可能清晰的完成标准下，让 Agent 系统稳定运行，并允许其在模型能力提升后，有节制地删去自己。

## 0.5 本版的总设计判断

本版做出以下基本判断：

1. 长任务 agent 的核心问题首先是上下文与状态，而不是 prompt 文采。
2. 技能应当是独立资产，而不是散落在提示词里的经验片段。
3. 工具系统必须动态化，否则规模一上去就会反噬上下文。
4. 不是所有任务都值得用最强模型完成。
5. 历史状态不应被固定同权继承，而应被内容相关地选择性继承。
6. 默认应先走低成本主路径，只对高风险残差追加纠偏。
7. 优化自身也会产生管理税，必须被统计、比较和退役。

## 0.6 本范式的最小运行链

本范式将所有复杂机制压缩为一条最小运行链：

1. **定义任务契约与预算**
2. **选择最小状态块与工作上下文**
3. **按需暴露技能、工具与模型能力**
4. **优先走低成本主路径**
5. **仅对高风险残差启动纠偏链**
6. **持续记录管理税并推动组件退役**

如果一个新增机制无法清楚回答“它属于哪一步”，则它不应进入当前主骨架。

---

# 01-principles.md

# 顶层原则

本文件定义剑阵范式的顶层设计原则。所有后续模块、目录结构、运行时行为与评估机制，都不得违反这些原则。

## 原则 1：先立标准，再求达成

在开始执行之前，必须先定义：
- 什么算完成
- 什么算失败
- 哪些副作用不可接受
- 何时必须停止
- 何时需要人工接管

任何没有完成标准的任务，都不应直接进入执行阶段。

### 落地要求
- 每个任务都必须先生成 `Task Contract`
- `Task Contract` 必须包含成功判据与停止条件
- 没有成功判据时，默认先澄清，而不是直接执行

---

## 原则 2：前台极简，后台复杂

对用户暴露的入口应尽量少、尽量稳。复杂的子代理、技能、工具发现、模型路由、恢复协议都应隐藏在后台，不要求用户先理解完整系统图才能使用。

### 落地要求
- 对外只暴露少量入口命令或按钮
- 任务契约、skills、tools、router、hooks 由后台自动协调
- 复杂度只对维护者开放，不对终端用户显露

---

## 原则 3：能单 Agent，不多 Agent

多 Agent 不是默认更优，只是在单 Agent 无法稳定满足目标时的补偿手段。只有在以下情况之一满足时，才引入多 Agent：

- 任务天然分解为正交角色
- 子任务之间的上下文隔离有明显收益
- 并行带来的收益大于编排成本
- 校验/执行/交互职责必须分离

### 多角色升级判据（最小集合）

只有满足下列条件之一，才允许从单 Agent 升级为多角色路径：

1. **角色目标天然正交**：例如执行、校验、交互三者的输入输出边界清晰。
2. **上下文隔离收益显著**：拆分后可明显降低主上下文污染或 token 成本。
3. **并行收益为正**：预期节省的总时延或搜索成本大于编排税。
4. **权限边界必须分离**：高风险写操作、高权限工具调用、最终校验不能由同一角色独占。
5. **主路径已证明不足**：单 Agent 在同类任务上持续出现失败、循环或不可解释的质量波动。

### 不升级的默认情形

下列情形默认保持单 Agent：
- 任务仍可由单一上下文稳定完成
- 多角色只带来“看起来更复杂”的心理收益
- 校验可由局部规则或轻量 verifier 完成
- 并发开销预计高于收益

### 落地要求
- 默认从单 Agent 路径开始设计
- 多 Agent 拓扑必须写明“为什么不能单 Agent”
- 编排层必须可裁剪、可简化、可退役
- 是否升级为多角色，必须在 `Task Contract` 中留下可追踪理由

---

## 原则 4：能读取不写入，能建议不执行

系统对外部世界的干预必须遵循最小必要原则。默认优先级如下：

1. read
2. query
3. propose
4. write
5. destructive_write

### 落地要求
- 所有工具必须声明权限级别
- 高权限操作必须显式审批或确认
- destructive 操作必须具备快照和回滚能力

---

## 原则 5：默认传状态，不默认传历史

历史聊天记录不是长期任务的最优记忆形式。系统应优先维护结构化状态，而不是不断堆叠原始对话。

### 落地要求
- 工作时优先读取状态对象而不是原始聊天历史
- 原始 chat history 不作为默认主输入
- 每轮结束应优先合并状态，而不是无限追加历史

---

## 原则 6：历史不做同权累加，只做选择性继承

历史状态、技能、中间产物、失败记录与召回内容，不应被固定同权继承，而应依据当前任务内容、预算和风险等级，被选择性聚合到工作上下文中。

### 落地要求
- 先定义块级状态对象，再决定是否细粒度选择
- 选择器必须考虑相关性、成本、风险与新鲜度
- 无法解释选择理由的历史对象，不默认进入 `working_context`

---

## 原则 7：技能按需加载，工具按需发现

技能与工具是两类不同对象：

### 技能（Skills）
- 是流程知识
- 是组织经验
- 是工作流模板
- 是领域规范
- 以文档或目录形式沉淀

### 工具（Tools）
- 是运行时能力接口
- 是外部系统连接器
- 是可调用动作
- 是 schema 与执行器

### 落地要求
- Skills 通过 Registry 按需注入
- Tools 通过 Discovery 按需暴露
- 不允许默认把所有 skills 和 tools 全量注入上下文
- 技能应可绑定资源依赖，并在任务结束后卸载局部资源

---

## 原则 8：低成本主路径优先，高能力组件后置升级

不是所有步骤都需要最强模型。系统必须优先让低成本组件承担基础性、重复性、格式性工作，把高能力模型和高强度校验留给真正复杂或高不确定性的步骤。

### 适合低成本模型或确定性组件的任务
- 意图分类
- 结构化抽取
- 轻量摘要
- 工具候选过滤
- 状态合并
- 简单格式检查

### 适合高能力模型的任务
- 复杂规划
- 模糊目标澄清
- 长链决策
- 多约束综合判断
- 高风险文本生成

### 落地要求
- 任务契约中必须包含预算字段
- 路由器必须支持升级阈值
- 升级必须可追踪、可解释、可统计

---

## 原则 9：主路径优先，残差后修

系统应优先用低成本主路径完成大部分任务，只对高风险残差追加纠偏，而不是默认全量 verifier、全量 audit、全量高模型。

### 落地要求
- 任务契约中必须存在 `residual_risk_level`
- 失败恢复与 verifier 应优先局部触发，而非全局重跑
- 纠偏链必须可统计其额外收益与额外成本

---

## 原则 10：不确定时暂停、澄清、或显式声明边界

系统不应通过“硬猜”维持流畅感。在以下情况下，应优先澄清或停止：
- 目标模糊
- 权限不清
- 结果不可验证
- 成本明显超预算
- 上下文污染严重
- 工具返回异常且不可恢复

### 落地要求
- 任务契约中保留 `uncertainty_level`
- 超过阈值时触发澄清或升级
- 对外输出可显式声明不确定性

---

## 原则 11：连续失败必须触发方法切换，而不是盲目重试

失败不是简单的次数问题，而是路径问题。连续失败意味着当前方法、上下文、工具组合或预算配置可能已经失效。

### 落地要求
- 维护 `failure_streak` 与 `failed_methodologies`
- 连续失败应触发方法论路由切换
- 不允许在同一路径上无限重试
- 恢复协议应首先针对“残差问题”而不是全局重跑

---

## 原则 12：关键行为要事件化，不只提示化

一部分关键原则不能只存在于 prompt 和文档中，而必须落到系统事件上，例如：
- session start
- tool fail
- pre compact
- stop
- high-risk write

### 落地要求
- 系统必须定义关键事件节点
- 恢复、保存、审计、降级等行为应可挂到事件上自动执行
- 无法事件化的高价值原则，应至少可被中间件统一拦截

---

## 原则 13：内外分离

Agent Harness、AI 推理内核、应用层必须边界清晰。应用层可以使用 harness，但 harness 不应反向依赖上层业务实现。

### 落地要求
- `app/` 不应成为 `harness/` 的隐式前提
- `harness/` 只定义通用执行与治理逻辑
- `runtime/` 与 `app/` 之间通过接口通信，而不是共享隐式状态

---

## 原则 14：每个 Harness 组件都必须有退役条件

Harness 不是永恒层。每一个额外组件的存在，都必须回答两个问题：
1. 它现在解决的是什么缺陷？
2. 当模型能力提升时，它何时应该消失？

### 落地要求
- 组件诞生时即声明退役标准
- 退役必须依赖指标，不依赖直觉
- 退役后必须可回退
- 未声明退役条件的组件不得进入核心骨架

---

## 原则 15：优化必须计算优化自身的管理税

优化本身也会带来新的 token、延迟、心智负担与运维成本。任何 skill、tool、verifier、hook、orchestrator，如果其管理税持续高于带来的质量收益，应被降级、合并或退役。

### 落地要求
- 观测层必须统计管理税指标
- 退役层必须对管理税与收益做比较
- “提升了可靠性”不能替代“值得长期保留”的判断

---

# 02-glossary.md

# 术语表

本文件定义剑阵范式的核心术语。除本文件外，其他文档不应重复发明主术语。

## 2.1 核心问题术语

### 不可靠性税（Unreliability Tax）
指 Agent 在生产环境中的失败，不仅带来单次任务损失，还会进一步引出重试、反思、交叉验证、人工介入、回滚与审计等额外成本层。

### 上下文腐化（Context Rot）
指长任务运行中，工具定义、对话历史、检索文本、日志与状态反复进入上下文，导致注意力被噪声稀释、成本上升与质量下降。

### 周边上下文（Peripheral Context）
指不是任务核心内容，但会在运行中持续占用上下文预算的对象，例如日志、schema、旧 tool result、无关对话等。

### 静态工具暴露悖论（Static Tool Exposure Paradox）
指为了获得“全能性”而把大量工具 schema 常驻上下文，最终反而损伤注意力和工具选择质量的现象。

### 管理税（Management Tax）
指某个 harness 组件为带来局部收益而额外引入的 token、延迟、事件噪声、心智负担和运维复杂度。

## 2.2 任务与治理术语

### 兵力估算
指对任务可行性、预算、风险与升级阈值的前置判断。

### 任务契约（Task Contract）
指执行前定义的任务对象，固定目标、完成标准、权限边界、预算、方法族、停止条件与交付物。

### 升级阈值（Escalation Threshold）
指触发高成本模型、更多工具、更多审计或人工接管的阈值。

### 残差风险（Residual Risk）
指在主路径执行后，仍需额外纠偏、验证或恢复处理的高风险残余问题。

### 最小干预
指默认优先读、查、建议，而不是直接写入或破坏性操作。

### 内外分离
指 `app/`、`runtime/`、`harness/` 三类边界清晰，harness 不反向依赖应用层。

## 2.3 上下文与状态术语

### 工作上下文（working_context）
当前回合进入模型的最小必要上下文集合。

### 全局状态（global_state）
跨任务稳定存在的高层规则、风格、偏好、长期边界等状态。

### 项目块（project_block）
某一项目级别的目标、阶段、依赖、边界和长期中间产物。

### 模块块（module_block）
某一模块、目录或子主题的局部状态块。

### 任务块（task_block）
当前任务的短周期状态对象，优先反映正在进行的目标、假设、阻碍与下一步。

### 蒸馏摘要（distilled_summary）
高密度、低噪声的阶段性摘要，用于跨轮维持主线。

### 持久状态（persistent_state）
存储在上下文之外、可结构化检索与更新的长期状态。

### 召回包（retrieval_packet）
按需从外部状态、知识库或历史中召回的局部上下文对象。

### 会话重建包（session_rebuild_packet）
跨 session 恢复任务所需的最小状态包。

### 选择性继承（Selective Inheritance）
不是把历史和状态同权累积，而是依据当前任务、预算和风险，只把高价值状态块带入工作上下文。

## 2.4 能力系统术语

### 诛仙剑阵
指围绕主控、执行、交互、校验、治理形成的可裁剪多角色编排结构。

### 功法秘籍（Skills）
指以文档/目录形式沉淀的流程知识、组织经验、方法模板与风格规范。

### 技能注册表（Skills Registry）
负责技能发现、元数据管理、触发、注入与生命周期控制的系统。

### 工具发现（Tool Discovery）
负责按需返回工具候选、轻量签名、完整 schema 拉取与调用后清理的能力层。

### 动态模型路由（Dynamic Model Routing）
根据任务类型、预算、风险与不确定性，在多个模型能力档位间自动切换。

### 方法论路由（Methodology Router）
根据任务类型或失败模式，在多种解决方法之间选择主方法与备选方法。

### 失败升级策略（Failure Escalation Policy）
定义连续失败后如何切方法、加审计、加恢复、升模型、或转人工接管。

### 事件编排器（Hook Orchestrator）
负责将关键行为挂接到统一事件节点的中间件层。

### 经验日志（Learning Journal）
跨回合保存失败教训、成功模式与局部经验的状态对象。

## 2.5 评估与演化术语

### 智子观测
指运行过程中的 tracing、metrics、logs 与评估对照机制。

### 境界评估
指用修仙境界标签描述成熟度阶段的辅助沟通方式；它不是决策本身，决策仍由指标与边际收益主导。

### Build to Delete
指所有 harness 都以“可删减、可合并、可退役”为前提构建，而不是默认永久存在。

## 2.6 远期研究术语（不进入当前主骨架）

以下内容仅保留为远期研究方向，不进入当前主骨架：
- 完全去中心化无主控网格
- 节点间潜空间直接通信
- 隐式推理作为默认主路径
- 图谱内核型长期记忆骨架
- 直接复用底层模型结构创新作为 agent 主模块

---

# 03-topology.md

# 系统拓扑

## 3.1 总体结构

本版拓扑不再继续扩层，而是在现有骨架上明确五段主逻辑：

1. **任务契约与预算层**
2. **上下文与状态选择层**
3. **诛仙剑阵执行与能力层**
4. **残差纠偏与失败恢复层**
5. **三体治理、观测与退役层**

## 3.2 五层主逻辑

### 层 0：面壁者 / 兵力估算层
职责：
- 澄清需求
- 生成任务契约
- 设定预算与升级阈值
- 判断是否需要多角色协作

### 层 1：炼化归藏层
职责：
- 维护块级状态对象
- 选择性继承历史状态
- 装配最小工作上下文
- 负责会话重建与状态外置

### 层 2：诛仙剑阵层
职责：
- 主控任务编排
- 调用 skills、tools、models
- 管理执行器、交互器、校验器与治理器
- 输出结构化中间结果与最终交付物

### 层 3：破壁纠偏层
职责：
- 连续失败检测
- 方法论切换
- 触发 targeted verifier / local audit
- 只对高风险残差启动纠偏链

### 层 4：三体治理层
职责：
- 权限控制
- 沙箱隔离
- 注入污染检测
- 运行观测
- 成熟度评估
- 组件退役判断

## 3.3 诛仙剑阵角色拓扑

### 诛仙剑（Orchestrator）
职责：
- 解释任务契约
- 决定是否需要多角色协作
- 维护任务级调度视图
- 触发异常裁决

### 戮仙剑（Executor）
职责：
- 执行工具调用
- 运行代码与命令
- 处理外部系统交互
- 产出结构化中间结果

### 陷仙剑（Interactor）
职责：
- 澄清需求
- 接受用户反馈
- 管理交互轮次
- 负责结果呈现适配

### 绝仙剑（Verifier）
职责：
- 格式校验
- 逻辑检查
- 风险检测
- 输出前把关
- 在高风险残差闭环中承担定向重估与局部验证职责（但不是唯一决策者）

### 三省六部（Governance）
职责：
- 规划审批
- 权限控制
- 审计与回滚
- 高风险分支拦截

## 3.4 五类横切基座

### 基座 A：上下文与状态基座
负责：
- 块级状态组织
- 选择性继承
- 状态外置
- 会话重建

### 基座 B：技能基座
负责：
- 技能发现
- 技能元数据管理
- 普通 skill 与 meta skill 注入
- 生命周期与退役依赖

### 基座 C：工具发现基座
负责：
- 工具候选返回
- schema 按需拉取
- 调用后清理
- 资源绑定与卸载

### 基座 D：治理与结界基座
负责：
- 权限控制
- 审批与沙箱
- 快照与回滚
- 失败升级与事件化触发

### 基座 E：观测与退役基座
负责：
- 运行指标采集
- benchmark 对照
- 管理税统计
- harness 组件退役判断

## 3.5 拓扑约束

1. 主流程层不再新增主层。  
2. 横切能力只允许进入五类基座之一。  
3. 任何新概念若无法映射到主流程或五类基座，不进入当前骨架。  
4. 工具与技能必须分离，不可混并。  
5. 治理与执行不可无边界耦合。  
6. 恢复与纠偏不是附属补丁，而是主路径后的条件分支。  
7. 理想版与实用版可并存，但当前默认优先实用版。

## 3.6 当前不纳入主拓扑的内容

以下内容仅保留为远期研究方向：
- 完全去中心化无主控网格
- 节点间潜空间直接通信
- 隐式推理作为默认主路径
- 图谱内核型长期记忆骨架
- 细粒度全对象状态注意力选择器

当前版本优先保证：
- 可落地
- 可调试
- 可裁剪
- 可退役
- 可统计管理税

---

# 04-task-contract.md

# 任务契约规范

## 4.1 目的

任务契约用于在执行前固定：
- 任务目标
- 成功判据
- 允许工具
- 权限边界
- 资源预算
- 风险等级
- 方法族
- 升级阈值
- 停止条件
- 交付物类型

没有任务契约的任务，不进入执行主循环。

## 4.2 字段定义

### 必填字段

#### schema_version
任务契约 schema 版本号，用于后续迁移与兼容判断。

#### contract_id
当前任务契约的唯一标识。

#### task_type
任务类型，例如：
- qa
- research
- retrieval
- generation
- coding
- execution
- planning
- review

#### goal
任务目标的自然语言说明。

#### success_criteria
什么算完成，必须尽量可检验。

#### expected_artifacts
预期交付物类型，例如：
- answer
- report
- markdown
- code_patch
- spreadsheet
- plan
- audit_note

#### allowed_tools
当前任务允许暴露和调用的工具集合。

#### write_permission_level
写权限级别：
- read
- query
- propose
- write
- destructive_write

#### stop_conditions
必须停止、升级或转人工的条件。

### 预算字段

#### token_budget
当前任务可接受的 token 上限或区间。

#### latency_budget
当前任务可接受的延迟上限或区间。

#### retrieval_budget
当前任务允许的检索预算。

#### verification_budget
当前任务允许的校验预算。

#### escalation_budget
当前任务允许的升级预算。

### 评估字段

#### uncertainty_level
当前任务的不确定性级别。

#### residual_risk_level
主路径完成后，仍需额外关注的残差风险级别。

#### escalation_threshold
触发升级到更强模型、更多工具、更强审计或人工接管的阈值。

#### escalation_policy
升级路径说明。

#### methodology_family
当前任务默认采用的方法族，例如：
- debug
- build
- research
- architecture
- performance
- writing
- compliance

#### failure_escalation_policy
连续失败后的方法切换和恢复规则。

## 4.2.1 版本与迁移策略

### 最小要求
- 每个 Task Contract 必须带 `schema_version`
- 运行时读取旧契约时，必须先经过迁移或兼容适配
- 不允许让旧契约直接静默落入新执行器

### 建议策略
- `schema_version` 采用显式字符串，如 `v1`, `v1.1`, `v2`
- 提供 `contract_migrator`，把旧字段映射到新字段
- 无法安全迁移时，退回人工澄清或重新生成契约

## 4.3 生成规则

### 规则 1
没有 `success_criteria`，默认先澄清，不执行。

### 规则 2
没有 `write_permission_level`，默认不写。

### 规则 3
没有预算字段，默认使用保守预算。

### 规则 4
没有 `methodology_family` 时，由 `planner/interviewer` 先路由方法族。

### 规则 5
若 `uncertainty_level` 高于阈值，应先补信息而不是直接升级执行强度。

### 规则 6
若 `residual_risk_level` 高，应提前定义局部 verifier 或 recovery 路径。

### 规则 7
高风险任务必须同时定义停止条件与人工接管条件。

## 4.3.1 Interviewer 的停止条件

`planner/interviewer` 的目标不是“问得越多越好”，而是在足够信息下尽快结束访谈并产出契约。默认满足以下任一条件即可停止：

1. **成功标准已可检验**：`success_criteria` 已足以区分完成/未完成。
2. **权限边界已明确**：`allowed_tools` 与 `write_permission_level` 已可确定。
3. **预算边界已确定**：至少能给出保守预算与升级阈值。
4. **主要歧义已收敛**：剩余不确定性不会改变主方法族与主交付物。
5. **用户明确拒绝继续澄清**：则以保守契约执行，并显式记录边界。

### 必须继续访谈的情形
- 成功标准仍无法检验
- 写权限与副作用边界不清
- 高风险任务但接管条件未定义
- 任务类型或交付物类型仍存在关键歧义

### 访谈终止输出
Interviewer 停止后必须至少产出：
- `task_type`
- `goal`
- `success_criteria`
- `expected_artifacts`
- `write_permission_level`
- `uncertainty_level`
- 初始预算字段

## 4.4 示例

```yaml
TaskContract:
  task_type: research
  goal: 评估某一外部项目中可借鉴的 agent 运行机制，并给出是否吸收入现有架构的判断
  success_criteria:
    - 能明确区分进入 A、进入 B、暂不吸收三类内容
    - 关键判断具有可追溯理由
  expected_artifacts:
    - markdown
    - absorption_table
  allowed_tools:
    - web_search
    - file_search
    - summarizer
  write_permission_level: propose
  token_budget: medium
  latency_budget: medium
  retrieval_budget: medium
  verification_budget: low
  escalation_budget: medium
  uncertainty_level: medium
  residual_risk_level: medium
  escalation_threshold:
    - 来源冲突
    - 关键事实无法核验
    - 预算明显不足
  escalation_policy:
    - 先补检索
    - 再补局部校验
    - 仍不足则显式声明边界
  methodology_family: research
  failure_escalation_policy:
    - 连续失败两次切换检索策略
    - 连续失败三次改写问题拆解
    - 连续失败四次触发人工边界提示
  stop_conditions:
    - 无可信来源
    - 用户目标未定义
    - 所需操作越权
```

## 4.5 残差风险测量闭环

`residual_risk_level` 不是一次性字段，而是一个闭环变量。

### 阶段 A：执行前预估
在任务开始前，由 `planner/interviewer` 或 `task_contract_builder` 基于以下因素给出初始值：
- 任务复杂度
- 目标歧义度
- 预算紧张程度
- 权限风险
- 历史同类任务失败率

### 阶段 B：主路径后重估
主路径完成后，由 **`verifier` 主导重估**；`methodology_router` 提供方法信号与候选切换路径；`governance` 只在越界、冲突或高权限分支上介入。重估信号至少包括：
- 输出是否满足 `success_criteria`
- 是否存在未解释的关键跳步
- 是否触发高风险工具或高权限写操作
- 是否存在重复失败模式或异常 tool residue
- 是否出现重要信息缺口或来源冲突
- 当前方法族是否已被高置信失败路径命中

### 阶段 C：触发纠偏
若重估后的 `residual_risk_level` 高于阈值，则只触发局部纠偏，而不是默认全局重跑。纠偏动作可包括：
- targeted verifier
- local audit
- retrieval 再补充
- methodology switch
- 升级模型或转人工边界提示

### 阶段 D：写回状态
重估结果必须写回：
- `task_block`
- `learning_journal`（若形成可复用经验）
- 观测层指标

## 4.6 与后续模块的关系

- `planner/interviewer` 负责协助生成任务契约
- `context-state` 负责根据契约装配状态和 working context
- `tool discovery` 依据 `allowed_tools` 和预算返回候选
- `model router` 依据 `uncertainty_level`、`residual_risk_level`、预算与回滞规则做升级或降级
- `failure recovery` 依据 `failure_escalation_policy` 执行方法切换
- `verifier` 在主路径后主导重新评估 `residual_risk_level`；`methodology_router` 提供方法切换候选；`governance` 仅处理越界与冲突

---

# 05-context-state.md

# 炼化归藏层：上下文与状态基座

## 5.1 目的

本层不是简单的“记忆层”，而是负责：
- 把长期历史从主上下文中剥离
- 维护块级状态对象
- 决定哪些状态应被继承
- 组装最小工作上下文
- 在 session 切换或压缩后重建任务连续性

本层的目标不是“记住更多”，而是：

> 让真正重要的历史，以尽可能低的成本、尽可能高的信噪比，被当前任务选择性继承。

## 5.2 五个核心对象

### 5.2.1 global_state
跨任务稳定存在的高层状态。

#### 典型内容
- 长期风格规范
- 稳定权限边界
- 固定组织原则
- 高频禁忌与硬约束

### 5.2.2 project_block
项目级状态块。

#### 典型内容
- 项目目标
- 当前阶段
- 关键依赖
- 历史里程碑
- 稳定背景信息

### 5.2.3 module_block
模块级状态块。

#### 典型内容
- 某一目录/模块/子主题的局部状态
- 局部假设、局部未决问题、局部规范

### 5.2.4 task_block
当前任务的短周期状态块。

#### 典型内容
- 当前目标
- 当前假设
- 当前阻碍
- 当前下一步
- 当前已知风险

### 5.2.5 working_context
真正进入模型的最小必要上下文。

#### 典型内容
- 当前任务契约
- 当前需要的状态块摘要
- 当前必要 skill 注入
- 当前必要 tool signature
- 当前必要 retrieval packet

#### 不应长期驻留的内容
- 大量原始 chat history
- 已失效 tool result
- 旧版本日志
- 已完成子任务的脚手架文本

## 5.3 其他辅助对象

### distilled_summary
阶段性高密度摘要，用于跨轮维持主线。

### persistent_state
上下文外的长期结构化状态存储。

### retrieval_packet
按需召回的临时局部上下文对象。

### session_rebuild_packet
跨 session 恢复任务所需的最小重建包。

### learning_journal
跨会话经验体，记录失败教训、成功模式与可复用经验。

## 5.4 三条硬规则

### 规则 1：历史聊天不是默认主输入
原始 chat history 不作为长期任务的默认主输入。

### 规则 2：旧工具结果必须可清理
任何中间结果只要不再服务当前任务，就必须可卸载。

### 规则 3：每轮结束优先更新状态，而不是追加历史
状态优先于历史增长。

## 5.5 选择性继承规则

系统默认不做状态同权继承，而做块级选择性继承。

### 继承判断维度
- 相关性（relevance）
- 成本（cost）
- 风险（risk）
- 新鲜度（freshness）
- 残差价值（residual value）

### 实用版策略（当前优先）
只在以下四类块对象上做选择：
- `global_state`
- `project_block`
- `module_block`
- `task_block`

### 理想版策略（远期）
对细粒度对象（skill、failure entry、retrieval packet、局部中间产物）做更精细的选择性继承。

## 5.6 上下文装配流程

### 输入
- Task Contract
- 当前状态块
- 必要 retrieval packet
- 必要 skills
- 必要 tool signatures

### 处理
1. 读取 `task_block`
2. 判断是否需要 `module_block`
3. 判断是否需要 `project_block`
4. 仅在必要时引入 `global_state`
5. 生成 `working_context`

### 输出
- 最小 working context
- 更新后的 state selection record

## 5.7 状态更新流程

1. 收集本轮产生的新事实、未决问题和关键决策
2. 合并进 `task_block`
3. 视价值决定是否上卷到 `module_block` 或 `project_block`
4. 生成 `distilled_summary`
5. 必要时更新 `session_rebuild_packet`

## 5.8 触发清台仪式的条件

- 上下文成本持续超预算
- tool residue 明显堆积
- 子任务已经切换阶段
- session 被压缩或中断
- 失败恢复后需要重新装配状态

## 5.9 与记忆系统的关系

本层不等于“记住一切”。

- 记忆系统回答“保存什么”
- 选择性继承回答“这轮带什么进 working context”
- 状态系统回答“以什么对象形式保存和重建”

## 5.10 并发状态冲突（首版约束）

当多个 Executor 或子任务并行运行时，`state_manager` 不允许无约束并发写入同一状态块。首版采用保守策略：

### 首版规则
1. `task_block` 允许单任务独占写入。
2. `module_block` 与 `project_block` 默认采用串行合并。
3. 并行子任务只能写入各自的局部草稿状态，不能直接覆盖共享状态。
4. 最终合并必须经过 orchestrator 或 state_manager 的显式 merge 步骤。

### 后续可扩展方向
- 乐观锁版本号
- merge policy
- append-only journal
- conflict resolution hook

## 5.11 成功标准

- 原始历史不再作为默认主输入
- 系统能稳定生成最小 working context
- 状态块可独立更新、独立清理、独立召回
- 选择性继承逻辑可被解释与统计

## 5.12 首版不做的事

- 不做细粒度全对象选择器
- 不做隐式向量态继承
- 不做潜空间直接通信
- 不把长期记忆骨架改造成图谱内核

---

# 06-skills-registry.md

# 功法秘籍层：技能注册表

## 6.1 目的

技能不是提示词碎片，而是组织经验、流程知识和领域方法的可复用资产。技能注册表负责：
- 技能发现
- 技能元数据管理
- 普通 skill 与 meta skill 注入
- 生命周期控制
- 与资源依赖的绑定

## 6.2 技能的最小定义

一个技能至少应包含：
- `name`
- `description`
- `trigger_signals`
- `required_tools`
- `resources`
- `inputs`
- `outputs`
- `risk_level`
- `lifecycle`
- `retirement_dependency`

## 6.3 skills 与 meta skills

### 普通 skill
用于特定任务族的工作流、方法模板、文档规范、领域做法。

### meta skill
用于影响全局行为，例如：
- 任务前澄清
- 风险声明
- 状态优先
- 输出格式约束
- 失败后切方法

### meta skill 与 global_state 的边界

两者都可能影响系统的全局行为，但职责不同：

#### global_state 回答的是
- 长期稳定存在的偏好、风格、权限边界与硬约束
- 不依赖单个任务族、应跨任务长期保持的状态

#### meta skill 回答的是
- 某类任务在当前阶段需要施加的行为协议
- 可按任务触发、可卸载、可替换的方法性约束

#### 冲突处理原则
1. **硬边界优先于方法约束**：`global_state` 中的硬约束优先级高于 meta skill。
2. **任务性规则优先于通用建议**：当任务契约显式要求某行为时，meta skill 仅能增强，不得覆盖契约。
3. **可卸载优先于常驻**：能由 meta skill 承担的短期行为，不应提升为 `global_state` 常驻项。
4. **冲突必须可记录**：若 meta skill 与 `global_state` 或 Task Contract 冲突，必须留下决策记录。

## 6.4 技能生命周期

1. 创建
2. 注册
3. 触发
4. 注入
5. 执行后保留或卸载
6. 评估收益
7. 合并、降级或退役

## 6.5 技能触发原则

- 任务特征匹配才触发
- 风险和预算允许才触发
- 不能因为“可能有用”就默认常驻
- 技能应可绑定所需资源，并在任务结束后释放局部资源

## 6.6 首版技能目录建议

```text
skills/
├── planning/
├── research/
├── writing/
├── coding/
├── governance/
├── recovery/
└── meta/
```

## 6.7 首版不做的事

- 不做自动生成海量 skill
- 不做技能人格化排名系统
- 不做未声明生命周期与退役依赖的 skill

---

# 07-tool-discovery.md

# 工具发现基座

## 7.1 目的

工具发现层负责解决静态工具暴露悖论。它不让所有工具 schema 常驻上下文，而是：
- 先按任务返回候选
- 再按需拉取完整 schema
- 调用后清理局部工具残留
- 统计工具发现带来的收益与管理税

## 7.2 为什么单独成层

### 技能回答的是：
- 应该怎么做
- 有哪些流程知识可复用
- 哪些规则与风格应遵循

### 工具回答的是：
- 现在能调用什么能力
- 需要什么参数
- 会产生什么副作用
- 调用后怎样清理

因此，skills 与 tools 必须分层。

## 7.3 四个核心对象

### 7.3.1 tool_catalog

#### 建议字段
- `tool_name`
- `tool_description`
- `permission_level`
- `cost_hint`
- `risk_level`
- `category`
- `residency_hint`

### 7.3.2 tool_discovery_query

#### 输入
- 任务类型
- 当前目标
- 预算
- 风险等级
- 已激活 skills

#### 输出
- 少量候选工具
- 每个候选的轻量签名

### 7.3.3 tool_signature

#### 应包含
- 工具名
- 作用摘要
- 权限级别
- 参数摘要
- 副作用提醒

#### 不应包含
- 冗长自然语言说明书
- 无当前任务价值的全部实现细节

### 7.3.4 tool_schema_fetch

#### 原则
- 只有在明确要调用时，才拉完整 schema
- schema 用完后不默认常驻上下文

## 7.4 工作流程

### 步骤 1：发现
根据任务契约和状态，发起工具发现查询。

### 步骤 2：候选返回
只返回 top-k 候选工具及轻量签名。

### 步骤 3：工具选择
由 orchestrator 结合预算、风险与当前方法族选择。

### 步骤 4：schema 拉取
只拉当前调用所需工具的完整 schema。

### 步骤 5：调用执行
进入执行器。

### 步骤 6：卸载与清理
任务完成或阶段结束后，卸载局部工具上下文残留。

## 7.5 硬规则

### 规则 1
默认只返回少量候选工具。

### 规则 2
完整 schema 只在即将调用时拉取。

### 规则 3
调用结束后，工具上下文不默认常驻。

### 规则 4
所有工具必须声明权限级别与副作用。

### 规则 5
工具发现层必须统计自身的管理税。

## 7.6 与任务契约的关系

`allowed_tools`、`write_permission_level`、预算字段与 `residual_risk_level` 会直接影响工具发现结果。

## 7.7 与执行器的关系

执行器不负责“决定暴露什么工具”，执行器只负责“调用已选工具”。工具选择应前置于 discovery 与 routing。

## 7.8 成功标准

- 工具不再默认全量暴露
- schema 拉取按需发生
- 用后可清理
- 工具发现收益与管理税可统计

## 7.9 附加指标

- `tool_schema_tax`
- `tool_residency_time`
- `dynamic_tool_discovery_latency`
- `tool_misuse_count`

## 7.10 首版不做的事

- 不做跨组织公共工具市场
- 不做无限制自动发现
- 不做工具人格化包装


---

# 07a-model-router.md

# 模型路由器规范

## 7a.1 目的

Model Router 负责把任务契约中的预算、风险和不确定性，转化为具体的模型能力档位选择。它不是简单的“选一个更强模型”，而是决定：

- 什么时候继续使用低成本主路径
- 什么时候升级到更强模型
- 什么时候降级回更轻路径
- 如何避免在两个模型档位间来回抖动

## 7a.2 输入信号

至少读取以下输入：
- `task_type`
- `methodology_family`
- `token_budget`
- `latency_budget`
- `verification_budget`
- `uncertainty_level`
- `residual_risk_level`
- 当前失败 streak
- 当前是否处于 recovery 模式

## 7a.3 输出

Model Router 至少输出：
- `model_tier`
- `routing_reason`
- `upgrade_or_downgrade_action`
- `cooldown_window`
- `expected_cost_band`

### 建议的能力档位
- `light`：分类、抽取、轻量摘要、格式任务
- `standard`：常规规划、普通写作、一般性判断
- `deep`：复杂规划、长链分析、多约束综合判断
- `critical`：高风险文本、高权限任务、关键分歧裁决

## 7a.4 升级规则

满足任一条件即可升级：
1. `uncertainty_level` 高于阈值
2. 主路径后 `residual_risk_level` 高于阈值
3. 连续失败超过允许次数
4. 当前输出涉及高风险写操作或高权限调用
5. 当前方法族明确要求更高推理强度

## 7a.5 降级规则

满足以下条件时允许降级：
1. 当前阶段已转入结构化、重复性、低歧义任务
2. `residual_risk_level` 已降到安全区间
3. 连续一段窗口内未触发升级条件
4. 降级不会破坏当前恢复链的一致性

## 7a.6 回滞（Hysteresis）规则

为避免在两个模型档位之间反复跳跃，必须定义回滞规则：

- 升级后在 `cooldown_window` 内不立即降级
- 只有在连续若干轮都满足降级条件时才允许降级
- 频繁抖动必须被记录为 `router_oscillation_event`

## 7a.7 与残差风险的关系

Model Router 必须参与 `residual_risk_level` 的闭环：
- 执行前：根据初始风险估计能力档位
- 执行后：根据 verifier / governance 的反馈决定是否升级
- 恢复后：根据残差是否消除决定是否保留高能力档位

## 7a.8 成功标准

- 路由决策可解释
- 升降级规则可追踪
- 回滞可防止来回抖动
- 升级带来的收益与成本可统计

---

# 07b-learning-journal.md

# Learning Journal 规范

## 7b.1 目的

Learning Journal 不是普通日志，而是系统的最小经验体。它只保存对后续任务真正有复用价值的内容：

- 失败模式
- 有效恢复策略
- 高收益方法切换
- 局部成功模式
- 特定场景下的风险提示

## 7b.2 与其他状态对象的边界

### 与 `task_block` 的边界
- `task_block` 记录当前任务的短周期状态
- `learning_journal` 记录跨任务可复用经验

### 与 `distilled_summary` 的边界
- `distilled_summary` 维持当前主线
- `learning_journal` 沉淀可迁移经验

### 与 `failure journal` 的边界
- `failure journal` 可以记录原始失败事件
- `learning_journal` 只保留已提炼的教训与对策

## 7b.3 条目结构（MVP）

每条 Journal Entry 至少包含：
- `entry_id`
- `timestamp`
- `task_type`
- `methodology_family`
- `situation`
- `signal`
- `action_taken`
- `outcome`
- `lesson`
- `reuse_hint`
- `confidence`

## 7b.4 写入时机

满足以下任一条件时写入：
1. 连续失败后切换方法并成功恢复
2. 某一恢复策略显著降低了残差风险
3. 某一错误模式重复出现并被稳定识别
4. 某一技能/工具绑定方式被证明显著有效
5. 人工明确指出某次经验应保留

## 7b.5 读取条件

默认不全量读取。只有满足以下条件时才读取：
- 当前任务类型与历史条目高度相似
- 当前失败模式与某条 Journal Entry 的 `signal` 匹配
- 当前方法族需要借用既有经验
- 当前 residual risk 高且预算允许经验检索

## 7b.6 与 Task Contract 的关系

Learning Journal 不参与定义任务目标，但可影响：
- `methodology_family`
- `failure_escalation_policy`
- `residual_risk_level` 的保守估计
- 是否提前启用某些 verifier 或 recovery action

## 7b.7 保留、归档与淘汰机制（MVP）

Learning Journal 必须显式控制条目数量，避免长期演化成噪声库。

### 最小控制字段
每条 Journal Entry 建议额外维护：
- `last_accessed_at`
- `ttl_days`
- `utility_score`
- `archive_status`（`active` / `archived`）

### 最小规则
1. **最大活跃条目数**：超过 `max_active_entries` 时，优先把低 `utility_score` 条目转入归档层。  
2. **TTL 规则**：超过 `ttl_days` 且长期未命中的条目，进入归档候选。  
3. **低置信度清理**：`confidence` 低且长期未被复用的条目可清除。  
4. **归档优先于删除**：高价值但低时效条目优先归档，而不是直接删除。  
5. **删除必须可审计**：被删除条目应至少保留删除原因与时间戳。  

### 读取层级
- `active`：默认可参与匹配与召回  
- `archived`：仅在高残差风险或人工指定时参与深层检索

## 7b.8 成功标准

- 条目数量可控，而不是无限堆积
- 条目写入有明确时机
- 条目读取有明确条件
- 条目存在归档与清理策略
- Journal 的复用收益可被观测层统计

---

# 07c-methodology-router.md

# 方法论路由器规范

## 7c.1 目的

Methodology Router 决定的不是“用多强的模型”，而是“用哪种方法”。

它负责在以下对象之间做运行时选择：
- 主方法族
- 备选方法族
- 失败后的切换路径
- 是否需要触发局部审计、补检索、补验证或人工边界提示

如果 `Model Router` 解决的是**资源强度问题**，那么 `Methodology Router` 解决的是**问题求解路径问题**。

## 7c.2 与 Task Contract 的关系

`Task Contract` 中的 `methodology_family` 与 `failure_escalation_policy` 提供的是：
- 默认方法边界
- 默认失败升级脚本
- 不允许采用的方法
- 预算与权限约束

`Methodology Router` 负责的是：
- 在这些边界内做运行时动态判断
- 当实际失败模式不符合预设脚本时，提供 fallback 方案
- 当 fallback 超出契约边界时，转交治理层

### 硬规则

**Task Contract 提供默认边界；Methodology Router 在边界内动态选择；超出边界时必须触发治理层。**

## 7c.3 输入

至少读取以下输入：
- `task_type`
- `methodology_family`
- `failure_escalation_policy`
- `failure_tier`
- `residual_risk_level`
- `tool_outcome`
- `evidence_quality`
- `context_health`
- `budget_remaining`
- `repeated_failure_path_count`
- `learning_journal` 的相关命中条目（如有）

## 7c.4 输出

Methodology Router 至少输出：
- `selected_methodology`
- `selection_reason`
- `is_within_contract`
- `requires_governance_override`
- `expected_next_action`
- `fallback_methodology`（如有）

## 7c.5 默认方法族（MVP）

首版至少支持以下方法族：
- `debug`
- `build`
- `research`
- `architecture`
- `performance`
- `writing`
- `compliance`

### 方法族示意
- `debug`：根因分析、依赖映射、最小复现、局部验证
- `build`：增量构建、先删后建、低耦合实现
- `research`：检索优先、证据优先、来源对齐
- `architecture`：working backwards、边界先行、接口先行
- `performance`：benchmark-first、数据驱动、热点优先
- `writing`：结构先行、证据支撑、版本对照
- `compliance`：规则检查、边界确认、人工升级优先

## 7c.6 运行时决策规则

### 规则 1：默认先走契约中的主方法族
若当前信号未显示主方法失效，则保持 `methodology_family` 不变。

### 规则 2：连续失败优先切方法，而不是直接全局重跑
当满足 `failure_escalation_policy` 的阈值时，优先切到契约中预定义的备选方法。

### 规则 3：失败模式未命中预设脚本时，允许 fallback 选择
当失败不符合预设模式，或预设脚本明显与当前失败原因不匹配时，Methodology Router 可以在契约边界内自行选择 fallback methodology。

### 规则 4：fallback 超出边界时，必须转交治理层
以下情形必须设置 `requires_governance_override = true`：
- fallback 需要新的高权限工具
- fallback 明显突破当前预算边界
- fallback 会改变当前写权限级别
- fallback 会跳出当前任务契约定义的方法边界

### 规则 5：不得重复走已证实失败的路径
当某一方法路径已被标记为高置信失败，必须先切换方法，再考虑升模型或转人工。

## 7c.7 与 Failure Escalation Policy 的分工

- `failure_escalation_policy`：静态预设，给出默认脚本与阈值
- `Methodology Router`：动态判断，决定当前是否执行预设脚本、选择哪条备选路径、何时使用 fallback
- `Governance`：当动态判断试图突破静态边界时，负责兜底裁决

## 7c.8 与 Residual Risk 闭环的关系

Methodology Router 必须参与 `residual_risk_level` 闭环：
- 执行前：根据任务类型与历史经验建议主方法族
- 执行后：根据失败类型、证据质量与上下文健康度重判是否切换方法
- 纠偏后：根据残差是否下降，判断是否维持新方法或回归主方法族

## 7c.9 成功标准

- 方法选择理由可解释
- 静态脚本与动态判断边界清楚
- 不会在失败后机械重复旧路径
- fallback 方案有治理兜底
- 与残差风险闭环和失败升级策略对齐

---

# 08-governance-sandbox.md

# 三体治理层：治理与结界基座

## 8.1 目的

本层负责：
- 权限控制
- 沙箱执行
- 快照与回滚
- 污染监测
- 失败升级
- 关键行为事件化

它对应的文化隐喻包括：
- 思想钢印：硬约束
- 黑暗森林感知：注入/污染检测
- 摇篮系统：隔离、快照、回滚
- 水滴：高确定性执行器

## 8.2 权限级别

- `read`
- `query`
- `propose`
- `write`
- `destructive_write`

高权限级别必须有更高审计要求。

## 8.3 核心组件

### 审批器
处理高权限写入与高风险调用。

### 沙箱执行器
在隔离环境中运行命令、脚本、外部调用。

### 快照管理器
在关键阶段保存可回滚状态。

### 回滚器
在写入失败或副作用超界时执行恢复。

### 污染监测器
检测 prompt injection、context pollution、异常工具返回。

### 失败升级器
根据 `failure_escalation_policy` 执行方法切换或升级。

### 事件编排器
统一响应关键事件，例如：
- `on_session_start`
- `on_tool_fail`
- `on_user_frustration`
- `on_pre_compact`
- `on_stop`
- `on_high_risk_write`

## 8.4 硬规则

1. `destructive_write` 必须有快照与回滚方案。  
2. 高风险工具调用必须声明副作用。  
3. 关键事件必须可被治理层拦截。  
4. 失败升级优先切方法，再考虑全局重跑。  
5. 恢复协议应优先处理高风险残差，而非默认扩大系统强度。

## 8.5 成功标准

- 高权限操作有清晰边界
- 沙箱可用、快照可回退
- 关键行为可事件化触发
- 连续失败不再无限重试同一路径

---

# 08a-event-payloads.md

# Hook 事件最小 Payload 契约

## 8a.1 目的

A 文档不展开完整 runtime API，但必须给 `hook_orchestrator.py` 一个最小可实现的事件契约，避免只给事件名不给载荷结构。

## 8a.2 统一字段

所有事件 payload 建议至少包含：
- `event_id`
- `timestamp`
- `task_id`
- `session_id`
- `contract_id`
- `schema_version`

## 8a.3 关键事件 Payload（MVP）

### `on_session_start`
- `task_type`
- `goal`
- `uncertainty_level`
- `write_permission_level`
- `global_state_ref`
- `project_block_ref`

### `on_tool_fail`
- `tool_name`
- `tool_call_id`
- `error_type`
- `failure_tier`
- `current_methodology`
- `budget_remaining`
- `residual_risk_level`

### `on_user_frustration`
- `frustration_signal`
- `current_stage`
- `failure_streak`
- `current_methodology`
- `pending_recovery_action`

### `on_pre_compact`
- `working_context_ref`
- `distilled_summary_ref`
- `task_block_ref`
- `journal_candidates`
- `failure_state`

### `on_stop`
- `completion_status`
- `success_criteria_satisfied`
- `residual_risk_level`
- `journal_writeback_required`
- `next_step_recommendation`

### `on_high_risk_write`
- `tool_name`
- `target_resource`
- `write_permission_level`
- `rollback_available`
- `requires_approval`

## 8a.4 设计要求

1. Payload 必须足以支持治理层决策，不能只有事件名。  
2. Payload 必须尽量引用状态对象，而不是重复拷贝整段上下文。  
3. 高风险事件必须包含权限、回滚与残差风险相关字段。  
4. 未来如扩展事件，不得破坏统一字段集合。

---

# 09-observability-retirement.md

# 观测与退役基座

## 9.1 目的

本层负责把“看起来合理”的架构变成“可统计、可比较、可退役”的系统。境界名称可以保留为文化沟通标签，但不主导决策。真正主导决策的是：
- 指标来源
- 管理税
- 边际收益
- 退役条件
- 回退条件

## 9.2 Telemetry 指标

### 主能力指标
- `task_success_rate`
- `completion_quality`
- `human_takeover_rate`
- `rollback_rate`
- `skill_hit_rate`
- `model_routing_win_rate`
- `router_oscillation_event_count`

### 上下文与状态指标
- `context_size`
- `state_recall_hit_rate`
- `history_to_state_compression_gain`
- `residual_context_trigger_rate`
- `context_overhead_ratio`

### 工具与技能指标
- `tool_schema_tax`
- `skill_load_cost`
- `tool_misuse_count`
- `dynamic_tool_discovery_latency`
- `resource_binding_precision`

### 恢复与纠偏指标
- `failure_tier_distribution`
- `methodology_switch_success_rate`
- `local_verifier_trigger_rate`
- `residual_issue_resolution_rate`
- `repeated_failure_path_count`
- `journal_reuse_hit_rate`

### 管理税指标
- `orchestration_token_tax`
- `verification_latency_tax`
- `hook_trigger_noise`
- `skill_management_tax`
- `tool_schema_tax`
- `context_overhead_ratio`

## 9.3 境界评估

境界名称只作为沟通标签，不作为决策依据。可保留为：
- 炼气：MVP 可运行
- 筑基：稳定可用
- 金丹：主控稳定
- 元婴：状态与路由成熟
- 化神：治理与退役成熟
- 合体：前台复杂度极低、后台自动删减明显

## 9.4 退役规则

### 组件可退役的前提
- 已有替代路径
- 收益长期低于管理税
- 高能力模型或更简单机制已吸收其职责
- 退役后可回退

### 组件不可退役的情形
- 仍是关键安全边界
- 仍显著降低高风险错误
- 尚无可验证替代路径
- 管理税低而收益高

## 9.5 退役判断方式

对每个组件至少回答：
1. 它当前解决什么问题？
2. 它带来什么收益？
3. 它带来什么管理税？
4. 更简单路径是否已足够？
5. 退役后如何回退？

## 9.6 首版成熟度级别

首版目标不是“合体期”，而是：
- 能定义任务契约
- 能稳定管理状态与工具
- 能在失败后切换方法
- 能对核心组件统计管理税
- 能对至少一两个组件做退役判断

## 9.7 首版不做的事

- 不追求全自动退役
- 不用境界标签替代实际指标
- 不做纯叙事化成熟度报告

---

# 10-a-to-b-interface.md

# A 到 B 的接口映射

## 10.1 目的

A 不是孤立的世界观文本。它必须能映射到 B 的实现位点。任何无法映射到目录、状态对象、服务接口、事件节点或评估器的概念，都不应停留在当前主骨架中。

## 10.2 核心映射

| A 模块 | B 实现位点 |
|---|---|
| 面壁者 / 兵力估算 | `planner/task_contract_builder.py` |
| 契约迁移器 | `planner/contract_migrator.py` |
| 澄清式规划 | `planner/interviewer.py` |
| 诛仙剑 | `runtime/orchestrator.py` |
| 戮仙剑 | `runtime/executor.py` |
| 陷仙剑 | `runtime/interaction_adapter.py` |
| 绝仙剑 | `runtime/verifier.py` |
| 三省六部 | `harness/governance/` |
| 上下文与状态选择引擎 | `harness/context/context_engine.py` |
| 持久状态与块级状态 | `harness/state/state_manager.py` |
| 会话重建包 | `harness/state/session_rebuilder.py` |
| 技能注册表 | `harness/skills/skill_loader.py` |
| 工具发现基座 | `harness/tools/tool_discovery_service.py` |
| 模型类别路由 | `harness/runtime/model_router.py` |
| 方法论路由 | `harness/governance/methodology_router.py` |
| 失败升级策略 | `harness/governance/failure_escalation_policy.py` |
| 事件编排器 | `harness/governance/hook_orchestrator.py` |
| 经验日志 | `harness/state/learning_journal.py` |
| 沙箱与回滚 | `harness/sandbox/` |
| 智子观测 | `harness/telemetry/` |
| 境界评估 | `harness/evaluation/realm_evaluator.py` |

## 10.3 目录边界建议

```text
project/
├── app/
├── runtime/
├── planner/
├── harness/
│   ├── context/
│   ├── state/
│   ├── skills/
│   ├── tools/
│   ├── governance/
│   ├── sandbox/
│   ├── telemetry/
│   ├── evaluation/
│   └── journals/
└── artifacts/
```

## 10.4 边界规则

- `app/` 可以调用 `runtime/`、`planner/` 与 `harness/`
- `runtime/` 可以调用 `harness/`
- `planner/` 可以调用 `harness/`，但不依赖 `app/`
- `harness/` 不应依赖 `app/`
- `harness/` 中的模块尽量保持可复用、可单测

## 10.5 接口优先级

B 的首批实现应优先覆盖：
1. task contract / interviewer
2. context-state selection engine
3. tool discovery
4. governance / sandbox
5. telemetry / management tax
6. methodology routing / failure recovery
7. hook orchestration
8. model router

这些是当前最直接决定系统稳定性的骨架。

---

# 11-external-pattern-absorption.md

# 外部项目吸收说明

## 11.1 目的

本文件用于说明：当前 A v1.3 从外部项目、公开方法与研究参考中吸收了哪些可验证机制，哪些只保留为风格参考，哪些暂不进入当前骨架。

## 11.2 来自 oh-my-openagent 的吸收项

进入 A 的内容：
- 前台极简、后台承载复杂度
- 访谈式规划并入任务契约生成
- 层级上下文文件并入 context bootstrap
- 技能绑定资源，按需启用并在任务后卸载
- 类别到模型的路由原则

进入 B 的内容：
- `planner/interviewer`
- `context_bootstrapper`
- `tool_discovery_service`
- `model_router.py`
- `subagent_runtime`
- `code_execution_pack`（仅限代码垂直包）

不直接吸收的内容：
- 军团化宣传叙事
- 把通用体系锁死到代码代理赛道
- 过强结果承诺

## 11.3 来自 pua 的吸收项

进入 A 的内容：
- 连续失败必须触发方法切换
- 关键行为必须支持事件化触发
- 恢复协议应被设计为系统级对象，而不是临时提示
- 局部跨会话经验体可作为状态外置的一部分

进入 B 的内容：
- `failure_escalation_policy.py`
- `methodology_router.py`
- `hook_orchestrator.py`
- `learning_journal.py`
- `quality_selfcheck` 与 `full_chain_audit` 相关检查器

不直接吸收的内容：
- 高压话术外壳
- 人格化等级包装
- 以修辞替代治理与指标

## 11.4 来自 TurboQuant 的吸收项

进入 A 的内容：
- 瓶颈优先，而不是先扩世界观
- 主路径优先、残差后修
- 优化必须计算优化自身的 side overhead / 管理税
- 预算分层思维可迁移到 token、latency、verification、retrieval 与 escalation 预算

进入 B 的内容：
- 将预算字段写入 `Task Contract`
- 在 telemetry 中显式统计管理税
- 在 recovery / verifier 中优先做局部 residual correction，而不是全局重跑

不直接吸收的内容：
- 量化算法本身
- 任何“零损失压缩”式强承诺

## 11.5 来自 Attention Residuals 的吸收项

进入 A 的内容：
- 历史不做同权累加，只做内容相关的选择性继承
- 状态系统优先采用块级表示，再决定是否需要细粒度选择器
- 理想版与实用版分离：先做 block-level 实用版，再做细粒度理想版

进入 B 的内容：
- 在 `context_engine.py` 中优先实现块级状态选择器
- 在 `state_manager.py` 中把状态组织成 `global/project/module/task` 四层块对象
- 在 task contract 中引入 `residual_risk_level`

不直接吸收的内容：
- 把模型结构创新直接照搬成 agent 模块
- 将“层间注意力”误写成当前系统的主实现目标

## 11.6 当前总判断

A v1.3 不试图变成任何一个外部项目或论文方向的翻版。当前吸收策略是：

- 用 `oh-my-openagent` 补前台入口、层级上下文、资源按需与强执行器思路
- 用 `pua` 补失败恢复协议、方法论切换、事件化触发与局部跨会话经验体
- 用 TurboQuant 补预算分层、主路径/残差链与管理税意识
- 用 Attention Residuals 补“选择性继承”与“块级实用版优先”的结构思想
- 保留本体系在状态外置、任务契约、治理、观测与 Build to Delete 上的主骨架

## 11.7 吸收完成度判断

### 已进入原则层
- 前台极简
- 澄清式规划
- 技能绑定资源
- 连续失败切方法
- 关键行为事件化
- 主路径优先、残差后修
- 选择性继承
- 管理税评估

### 已进入接口层
- `planner/interviewer`
- `context/state engine`
- `tool discovery`
- `model router`
- `failure escalation policy`
- `methodology router`
- `hook orchestrator`
- `learning journal`

### 仍停留在参考层
- 强执行器的具体代码实现细节
- 更激进的自我演化话术
- 细粒度全对象状态选择器

### 暂不吸收
- 去中心化无主控网格
- 潜空间直接通信
- 直接采用底层模型结构创新作为主骨架
- 高压人格外壳与营销式强承诺

## 11.8 版本边界

本版只吸收“可以直接映射到工程对象”的部分。凡是无法落到以下对象之一的内容，均不进入当前骨架：
- 原则
- 状态对象
- 服务模块
- 事件节点
- 评估指标
- 退役规则



---

# 12-next-steps.md

# 之后要做的（从 A v1.4 转入 B）

本节不再把待办散落在维护者记忆中，而是把 **A 结束后、B 开始前** 的工作按优先级显式固定。

## 12.1 结论：A 在本版收口，下一步应启动 B

本版完成后，A 的职责是：
- 固定问题定义
- 固定最小运行链
- 固定模块边界与命名
- 固定 A → B 接口
- 固定启动 B 前必须锁定的责任边界

因此，下一步不建议继续膨胀 A，而应进入 **B v0.1**。

## 12.2 P0：B 启动前必须锁定的五条决议

1. **Residual Risk 主责归 `verifier.py`**  
   `methodology_router.py` 提供方法候选与切换建议；`governance` 仅处理越界与冲突。
2. **Methodology Router 不负责越权**  
   它只能在 `Task Contract` 给定边界内动态决策；超出边界必须上交治理层。
3. **B v0.3 前 executor 默认不做共享状态并发写**  
   v0.3 允许后台只读/搜索型子代理；真正的共享状态并发写入推迟到 v0.4，再由 `state_manager` 引入一致性策略。
4. **Contract schema baseline = v1**  
   B 阶段以 `schema_version = v1` 作为最小稳定契约；迁移器是长寿命兼容层，但不是默认永久核心。
5. **A 的总主线冻结为唯一解释入口**  
   即：任务契约 → 状态选择 → 能力暴露 → 主路径 → 残差纠偏 → 治理退役。

## 12.3 P1：B v0.1–v0.2 必须落地的内容

1. `task_contract_builder.py`
2. `interviewer.py`
3. `context_engine.py`
4. `state_manager.py`
5. `orchestrator.py`
6. `executor.py`
7. `tool_discovery_service.py`
8. `sandbox / rollback`
9. `telemetry`
10. `hook_orchestrator.py`（最小事件集）

## 12.4 P2：进入 B 后再逐步补齐的内容

1. `model_router.py` 的更细回滞参数
2. `methodology_router.py` 的更丰富 fallback 家族
3. `learning_journal.py` 的 ranking / forgetting 机制
4. `state_manager` 的并发一致性策略
5. `targeted verifier` 的细分与插件化
6. 自动退役建议器

## 12.5 本版明确暂不做

- 不进入无主控去中心化网格
- 不把底层模型结构创新直接改写成 agent 主模块
- 不把代码垂直能力包强行提升为通用内核
- 不用营销式强承诺替代评估与治理

## 12.6 版本命名建议

- **A v1.4**：A 阶段收口版，作为 B 的启动底稿
- **B v0.1**：MVP 运行骨架
- **B v0.2**：稳定骨架 + 治理 + 观测
- **B v0.3**：路由 + 方法论 + 残差纠偏接入
- **B v0.4**：状态成熟 + 经验沉淀 + 并发一致性

---

# 13-b-start-decision-card.md

# B 启动前决议卡

本节是 **开始 B 之前必须锁定** 的最小决议集合。若没有这些决议，B 会在责任边界和实现顺序上来回摇摆。

## 13.1 决议 1：Residual Risk 的重估主责归 `verifier.py`

- `verifier.py`：主导阶段 B 的重估
- `methodology_router.py`：提供方法切换候选与理由
- `governance`：只在越界、冲突、高权限写入或高风险分支介入

### 解释
这条决议的目的是避免“联合重估”变成“无人主责”。

## 13.2 决议 2：Methodology Router 的权限边界

Methodology Router 决定“用什么方法”，但不决定越权。

### 规则
- 在 `Task Contract` 边界内，可动态切换方法族
- 若 fallback 需要突破预算、权限或禁止项，必须设置 `requires_governance_override = true`
- 不允许 Methodology Router 自行改写 contract 边界

## 13.3 决议 3：v0.3 的 executor 仍以串行主路径为主

为了避免过早引入共享状态一致性复杂度：
- v0.3 允许 **只读/搜索型后台子代理**
- v0.3 不允许 **共享状态并发写入** 成为默认路径
- 真正的并发写一致性推迟到 v0.4，由 `state_manager` 明确策略后开启

## 13.4 决议 4：Contract schema baseline = v1

从 B v0.1 起，所有 Task Contract 至少包含：
- `contract_id`
- `schema_version = v1`
- `task_type`
- `success_criteria`
- `allowed_tools`
- `write_permission_level`
- `token_budget`
- `latency_budget`
- `retrieval_budget`
- `verification_budget`
- `escalation_budget`
- `uncertainty_level`
- `residual_risk_level`
- `methodology_family`
- `failure_escalation_policy`
- `stop_conditions`
- `expected_artifacts`

### 迁移策略
- `contract_migrator` 作为长寿命兼容层保留
- 但不默认标记为“永不退役”基础设施
- 当 schema 长期稳定且迁移调用接近零时，可转入低频兼容层并复评

## 13.5 决议 5：A 的唯一解释入口冻结

从本版开始，任何新增机制都必须能明确映射到以下主线之一：

1. 任务契约
2. 状态选择
3. 能力暴露
4. 主路径执行
5. 残差纠偏
6. 治理退役

若不能映射，则不进入当前 B 主骨架。

---

# 14-b-roadmap.md

# B 路线图（从 A v1.4 到 B v0.4）

本路线图从三个视角组织：
1. **实现阶段**：先做什么、后做什么
2. **运行主链**：系统怎么最小化跑起来
3. **退役时序**：哪些组件未来可弱化、合并或退役

## 14.1 实现阶段图（文本版）

### 炼气期 · B v0.1（MVP 运行骨架）
**P0**
- `task_contract_builder.py`
- `interviewer.py`
- `context_engine.py`
- `state_manager.py`
- `orchestrator.py`
- `executor.py`

### 筑基期 · B v0.2（稳定骨架 + 治理 + 观测）
**P0**
- `tool_discovery_service.py`
- `sandbox + rollback`

**永不退役**
- `telemetry`

**P1**
- `hook_orchestrator.py`（最小事件集）
- `verifier.py`
- `skill_loader.py`（MVP）

### 金丹期 · B v0.3（路由 + 方法论 + 纠偏链）
**P0**
- `model_router.py`
- `methodology_router.py`
- `residual risk` 闭环接入

**P1**
- `failure_escalation_policy.py`
- `meta_skill_injector.py`

### 元婴期 · B v0.4（状态成熟 + 经验沉淀）
**P0**
- `learning_journal.py`（完整）

**P1**
- `session_rebuilder.py`
- `state_manager` 并发一致性
- `targeted verifier`（拆分格式/逻辑/风险重估）

### 化神 / 合体（长远方向）
**永不退役**
- `realm_evaluator.py`

**P2 / 长期复评**
- `journal ranking + forgetting`
- 路由器联合优化（model + methodology）
- 自动退役建议器
- `contract_migrator.py`（长寿命兼容层，非天然永久）

## 14.2 最小运行链（B 的实现视角）

### 主路径
用户输入  
→ `interviewer.py`（澄清）  
→ `task_contract_builder.py`（定义完成标准）  
→ `context_engine.py`（装配最小工作状态）  
→ `skill_loader.py`（按需注入技能）  
→ `tool_discovery_service.py`（按需暴露工具）  
→ `model_router.py`（选定能力档位）  
→ `executor.py`（低成本主路径执行）

### 纠偏链（条件触发）
`verifier.py` 主导重估 `residual_risk_level`  
→ `methodology_router.py` 选择切换路径  
→ `model_router.py` 必要时升级档位  
→ `governance` 在越界/冲突时介入  
→ 写回 `task_block` / `learning_journal` / telemetry

### 横切基座（始终在线）
- `telemetry`
- `hook_orchestrator`
- `sandbox + rollback`
- `realm_evaluator`

## 14.3 退役时序（文本版）

### 可进入退役评估的组件
- 任务分解器：端到端成功率 > 95%，且用户不再需要显式步骤说明
- 轻量规则校验：模型长期零违规，且外部校验偏差持续很低
- `context_engine` 中的强压缩子模块：模型原生上下文管理准确率稳定
- `model_router.py`：模型自主资源调度持续优于显式路由
- `methodology_router.py`：模型自主方法选择稳定优于外部路由
- `skill_loader.py`：任务质量与显式技能装载已无显著差异
- `learning_journal.py`：连续多个评估窗口内，utility-weighted reuse 低于其检索/管理税
- `verifier.py`（格式/逻辑部分）：主 agent 自评与外部评估偏差持续 < 2%

### 永不退役或默认长期驻留
- `telemetry`
- `sandbox + rollback`
- `realm_evaluator`

### 退役硬规则
- 退役前必须可回退
- 安全边界组件不参与“自动退役”
- 管理税持续高于收益才触发退役评估
- `contract_migrator` 只作为长寿命兼容层复评，不默认永久核心

## 14.4 开始 B 时的唯一未闭问题

A 结束时剩下的唯一真正需要在 B 开工前锁定的问题，是：

**阶段 B 的残差风险重估责任已固定由 `verifier.py` 主导；`methodology_router.py` 和 `governance` 仅作为输入与越界裁决方。**

换言之，这个问题在 v1.4 已经从“未闭”变成“已决议”，B 可直接开工。
