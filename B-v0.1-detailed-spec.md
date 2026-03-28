# B v0.1 详细实施说明（炼气期 / MVP 运行骨架）

## 1. 文档定位

本文件不是 A 的继续扩展，而是 **从 A 进入 B 的首版实现说明**。  
A 是架构规范；B 是实现骨架。A 负责定义问题、原则、术语、拓扑、治理边界与退役逻辑；B 负责把这些概念映射成目录、模块、状态对象、运行主链与最小可运行系统。  
这一关系已经在 A 的 `10-a-to-b-interface` 中明确：**A 是架构规范，B 是实现骨架。** A 中的“兵力估算 / 剑阵编排 / 上下文状态基座 / 技能注册表 / 工具发现基座 / 治理与结界 / 智子观测 / 境界评估”等主要概念，都应映射到 B 的具体实现位点。fileciteturn8file0

本文件的目标是回答三件事：

1. B v0.1 到底做什么，不做什么  
2. B v0.1 的目录结构与模块职责是什么  
3. 如果要让 Codex / Claude Code 等 coding agent 往下推进，应如何给出任务书与验收边界

## 2. A 和 B 的关系：如何理解与定义

### 2.1 一句话定义

**A 是规范，B 是骨架。**  
A 解决“为什么这样设计”和“边界是什么”；B 解决“先把什么做出来”和“它们如何跑起来”。  
A 不直接承担产品入口、运行时文件组织、模块接口与测试落地；B 则要把 A 的这些抽象概念变成仓库中的目录、文件、类、状态对象和运行链路。A v1.1/v1.2 都已经明确了这种关系。fileciteturn8file0turn8file1

### 2.2 更具体的理解

可以把 A 和 B 的关系理解成三层：

#### 层 1：A 定义“词”
例如：
- 什么是 `Task Contract`
- 什么是 `working_context`
- 什么是 `persistent_state`
- 什么是 `Tool Discovery`
- 什么是 `Dynamic Model Routing`
- 什么是 `Build to Delete`

这些术语在 A 的 glossary 里已经明确。fileciteturn8file2

#### 层 2：A 定义“规则”
例如：
- 先立标准，再求达成
- 能单 Agent，不多 Agent
- 默认传状态，不默认传历史
- 技能按需加载，工具按需发现
- 低成本模型优先，高能力模型后置升级
- 连续失败必须触发方法切换
- 关键行为要事件化，不只提示化

这些属于 A 的顶层原则，用来约束 B。fileciteturn8file3

#### 层 3：B 定义“物”
例如：
- `planner/task_contract_builder.py`
- `runtime/orchestrator.py`
- `harness/context/context_engine.py`
- `harness/state/state_manager.py`
- `harness/tools/tool_discovery_service.py`
- `harness/telemetry/tracer.py`

这些才是 B 的内容。它们是 A 的概念在代码层的实体化。A v1.1/v1.2 都已经明确过这些映射关系。fileciteturn8file0turn8file1

### 2.3 一个更容易理解的类比

- **A 像建筑设计图和施工规范**
- **B 像开始打地基、搭钢结构、布线和做最小可用样板间**

所以：
- 没有 A，B 会乱做，今天加一层、明天删一层，没有边界
- 没有 B，A 会停留在“说得很完整，但不能跑”

### 2.4 当前阶段的判断

你现在的状态已经很清楚：

- A 已经基本收口，可以冻结为指导性规范
- 下一步应进入 B，而不是继续扩 A
- B v0.1 的目标不是“做完整系统”，而是“跑通最小运行链”

## 3. B v0.1 的目标边界

### 3.1 B v0.1 要做什么

B v0.1 只做三件事：

1. **跑通最小运行链**
2. **把 A 的关键概念落成最小模块**
3. **为后续 v0.2 / v0.3 保留清晰升级位点**

### 3.2 B v0.1 不做什么

首版明确不做：

- 不做真正并行 worker pool
- 不做复杂 Methodology Router
- 不做 Learning Journal ranking / forgetting
- 不做自动退役
- 不做代码垂直强执行器包（LSP / AST-Grep / Tmux）
- 不做复杂 hook payload 编排
- 不做共享状态的高并发写入

### 3.3 最小运行链

B v0.1 的最小运行链可收敛为：

**用户输入 → interviewer → task contract → context/state → skill loader → tool discovery → orchestrator → executor → verifier → state writeback / telemetry**

这条链严格对应 A 已经形成的主线：  
任务契约 → 状态优先 → 能力按需暴露 → 主路径执行 → 基础验证 → 写回状态与观测。  
A 也明确强调过：工作时优先读取 `persistent_state`，原始 chat history 不作为默认主输入，每轮结束应优先合并状态，而不是无限追加历史。fileciteturn8file2turn8file3

## 4. B v0.1 推荐目录结构（最终版）

注意：此处采用 `entrypoints/`，而不是 `app/`。  
原因很简单：你当前做的是系统架构与 runtime harness，不是成品应用。`entrypoints/` 更准确地表达“这里只是系统入口，不是核心架构本体”。

```text
project/
├── README.md
├── pyproject.toml
├── .env.example
├── entrypoints/
│   ├── cli.py
│   └── settings.py
├── planner/
│   ├── __init__.py
│   ├── interviewer.py
│   └── task_contract_builder.py
├── runtime/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── executor.py
│   ├── interaction_adapter.py
│   └── verifier.py
├── harness/
│   ├── __init__.py
│   ├── context/
│   │   ├── __init__.py
│   │   └── context_engine.py
│   ├── state/
│   │   ├── __init__.py
│   │   ├── state_manager.py
│   │   └── models.py
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── skill_loader.py
│   │   └── registry.py
│   ├── tools/
│   │   ├── __init__.py
│   │   └── tool_discovery_service.py
│   ├── governance/
│   │   ├── __init__.py
│   │   ├── policy.py
│   │   └── permissions.py
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── sandbox_executor.py
│   │   └── rollback.py
│   ├── telemetry/
│   │   ├── __init__.py
│   │   ├── tracer.py
│   │   └── metrics.py
│   └── evaluation/
│       ├── __init__.py
│       └── realm_evaluator.py
├── artifacts/
│   ├── state/
│   │   ├── global_state.json
│   │   ├── project_block.json
│   │   ├── task_block.json
│   │   └── working_context.json
│   ├── journals/
│   │   └── learning_journal.jsonl
│   ├── contracts/
│   │   └── latest_contract.json
│   └── logs/
│       └── runtime.log
├── skills/
│   ├── meta/
│   │   ├── cautious-claims/
│   │   │   └── SKILL.md
│   │   └── minimal-intervention/
│   │       └── SKILL.md
│   └── general/
│       └── structured-task-execution/
│           └── SKILL.md
└── tests/
    ├── test_task_contract_builder.py
    ├── test_context_engine.py
    ├── test_state_manager.py
    ├── test_tool_discovery_service.py
    ├── test_orchestrator.py
    └── test_sandbox_executor.py
```

这套目录继续遵守 A 里已经写明的边界规则：运行时可以调用 harness，但 harness 不应反向依赖入口层；harness 中的模块尽量保持可复用、可单测。A 中原本用 `app/` 表述这一层，当前可替换为 `entrypoints/`，不影响核心边界规则本身。fileciteturn8file0turn8file1

## 5. 各模块首版职责说明

### 5.1 `entrypoints/`

#### `entrypoints/cli.py`
最外层命令入口。  
只负责：
- 接收用户输入
- 触发一次任务运行
- 调用 orchestrator
- 输出结果或调试信息

建议首版只支持：
- `run`
- `resume`
- `inspect-state`
- `inspect-contract`

#### `entrypoints/settings.py`
读取环境变量和默认配置。  
只管理：
- 默认模型名 / 模型槽位
- artifacts 路径
- sandbox 开关
- telemetry 开关
- 默认预算参数

### 5.2 `planner/`

#### `planner/interviewer.py`
执行前澄清器。  
首版职责：

- 澄清目标是否明确
- 澄清成功标准是否足够具体
- 补齐明显缺失的约束
- 只在“确实不足”时才追问

停止条件建议与 A 保持一致：

- 成功标准已明确
- 关键约束已明确
- 风险等级可判断
- 缺失信息已降到阈值以下

#### `planner/task_contract_builder.py`
把澄清后的信息写成结构化 `Task Contract`。  
首版至少输出：

- `contract_id`
- `schema_version`
- `task_type`
- `success_criteria`
- `allowed_tools`
- `write_permission_level`
- `token_budget`
- `latency_budget`
- `uncertainty_level`
- `residual_risk_level`
- `stop_conditions`
- `expected_artifacts`

这些字段来自 A 中已经明确的任务契约结构。fileciteturn8file2

### 5.3 `runtime/`

#### `runtime/orchestrator.py`
主控，对应诛仙剑。  
职责：
- 解释 task contract
- 决定本轮是否单 Agent 直跑
- 组装最小运行链
- 调度 executor
- 触发 verifier
- 在每轮结束时写回 state / telemetry

**首版默认单主路径，不做并行 worker pool。**  
A 已明确：能单 Agent 不多 Agent，多 Agent 只在确有收益时引入。fileciteturn8file3

#### `runtime/executor.py`
执行器，对应戮仙剑。  
职责：
- 执行工具调用
- 运行最小外部交互
- 产出结构化中间结果
- 不负责全局调度，不负责治理判定

首版默认串行。

#### `runtime/interaction_adapter.py`
交互适配器，对应陷仙剑。  
职责：
- 将内部对象转成用户可读输出
- 处理必要的澄清问题
- 控制外部呈现样式

#### `runtime/verifier.py`
验证器，对应绝仙剑。  
职责：
- 输出前的格式检查
- 基础逻辑检查
- 高风险残差的首版主责重估模块

当前 B 启动前决议应写死：

- `verifier.py` 主导 residual risk 重估
- `methodology_router.py` 后续只提供策略候选
- `governance` 仅处理越界与冲突

### 5.4 `harness/context/`

#### `harness/context/context_engine.py`
上下文装配器。  
职责：
- 从 `task_contract + persistent_state + distilled_summary + retrieval needs` 装配 `working_context`
- 保证“历史聊天不是默认主输入”
- 允许清理旧工具结果与过时上下文

它对应 A 中“默认传状态，不默认传历史”“上下文优先由状态重建”这类硬规则。fileciteturn8file3turn8file2

### 5.5 `harness/state/`

#### `harness/state/models.py`
定义状态对象 schema。  
至少应包含：
- `GlobalState`
- `ProjectBlock`
- `TaskBlock`
- `WorkingContext`
- `TaskContract`

#### `harness/state/state_manager.py`
状态真值维护器。  
职责：
- 读写 `global_state`、`project_block`、`task_block`
- 合并本轮新信息
- 覆盖失效信息
- 生成 `working_context` 的基础材料

首版并发策略走保守版：
- 单进程串行写
- 写入带版本号
- 版本冲突时拒绝覆盖并写日志

### 5.6 `harness/skills/`

#### `harness/skills/registry.py`
技能元数据注册表。  
管理：
- `name`
- `description`
- `trigger_signals`
- `required_tools`
- `resources`
- `risk_level`
- `lifecycle`

#### `harness/skills/skill_loader.py`
按需加载 `skills/` 目录中的 `SKILL.md`。  
职责：
- 根据 task signals 选择技能
- 只注入命中的技能
- 统计 skill hit rate

A 已明确：技能与工具必须分离，不能把所有能力都塞进同一上下文层。fileciteturn8file3

### 5.7 `harness/tools/`

#### `harness/tools/tool_discovery_service.py`
按需工具发现器。  
最小流程：

1. 返回少量候选工具签名  
2. 真正调用前再拉取完整 schema  
3. 调用结束后允许卸载或清理

A 已明确，静态工具暴露会造成上下文腐化，因此工具应动态发现、按需拉取、按需卸载。fileciteturn8file2turn8file3

### 5.8 `harness/governance/`

#### `harness/governance/policy.py`
治理硬规则容器。  
职责：
- 校验越权写操作
- 检查 contract 边界
- 决定是否触发人工接管
- 为 sandbox / rollback 提供判断依据

#### `harness/governance/permissions.py`
权限分级。  
首版只定义：
- `read`
- `query`
- `propose`
- `write`
- `destructive_write`

这与 A 的最小干预原则一致。fileciteturn8file3

### 5.9 `harness/sandbox/`

#### `harness/sandbox/sandbox_executor.py`
隔离执行器。  
职责：
- 在隔离环境执行高风险操作
- 记录最小快照
- 返回结构化执行结果

#### `harness/sandbox/rollback.py`
回滚器。  
职责：
- 记录关键操作前状态
- 支持失败后最小回滚
- 与治理层联动

### 5.10 `harness/telemetry/`

#### `harness/telemetry/tracer.py`
运行链追踪器。  
首版至少记录：

- `token_count`
- `latency_ms`
- `cost_estimate`
- `retry_count`
- `rollback_count`
- `tool_misuse_count`
- `context_size`
- `skill_hit_rate`
- `human_handoff_count`

这些指标与 A 中的智子观测是一致的。fileciteturn8file0turn8file1

#### `harness/telemetry/metrics.py`
指标聚合与导出。  
只做：
- 结构化写日志
- 输出简单统计
- 为 `realm_evaluator` 提供输入

### 5.11 `harness/evaluation/`

#### `harness/evaluation/realm_evaluator.py`
境界评估器 / 首版退役建议器。  
首版职责：
- 不自动删模块
- 只基于 telemetry 给出“建议保留 / 建议观察 / 建议退役”
- 记录评估原因
- 明确“可回退”

A 已明确：首版只先实现“建议退役 + 可回退”，不做完全自动退役。fileciteturn8file0turn8file1

## 6. B v0.1 的最小开工顺序

建议按下面顺序推进：

1. `planner/task_contract_builder.py`
2. `harness/state/models.py`
3. `harness/state/state_manager.py`
4. `harness/context/context_engine.py`
5. `harness/tools/tool_discovery_service.py`
6. `runtime/orchestrator.py`
7. `runtime/executor.py`
8. `runtime/verifier.py`
9. `harness/sandbox/*`
10. `harness/telemetry/*`
11. `harness/evaluation/realm_evaluator.py`

原因很简单：这条顺序最符合 A→B 映射里已经写明的首批实现优先级：task contract、context/state、tool discovery、governance/sandbox、telemetry。v1.2 则进一步把 methodology routing / failure recovery / hook orchestration 放在后续增强位。fileciteturn8file0turn8file1

## 7. 如果让 Codex 或 Claude Code 往下推进，可以怎么做

### 7.1 不要一句话把整个 B 扔给它
最差的方式是：

> 帮我把 B v0.1 全部实现出来。

这种说法会让 agent：
- 自行补全大量未锁定细节
- 过早引入复杂依赖
- 把后续阶段能力偷渡进 v0.1

更好的方式是：**按模块和边界逐步推进。**

### 7.2 给 agent 的任务书，必须包含 5 类内容

#### （1）背景
只给必要背景，不把 A 全文塞进去。  
建议摘要化为：
- 项目目标
- A→B 的核心映射
- 当前只做 B v0.1
- 当前不做什么

#### （2）本轮范围
例如：

- 只实现 `planner/task_contract_builder.py`
- 不实现 `model_router.py`
- 不引入数据库
- 不做并发写
- 不做自动退役

#### （3）文件边界
明确列出：
- 可以新增哪些文件
- 不要改哪些文件
- 不能越过的目录边界

#### （4）输出要求
要求 agent 输出：
- 目录变更
- 文件职责
- 关键 class / function
- 测试点
- 未决问题列表

#### （5）验收标准
这是最重要的。  
例如：

- 能生成结构化 `TaskContract`
- 通过 `tests/test_task_contract_builder.py`
- schema_version 存在
- 未引入多余依赖
- 没有越过 `entrypoints -> runtime -> harness` 的边界

### 7.3 推荐推进方式：一轮一个模块

建议你让 Codex / Claude Code 这样推进：

#### 第 1 轮
只做：
- `harness/state/models.py`
- `planner/task_contract_builder.py`
- 对应测试

#### 第 2 轮
只做：
- `harness/state/state_manager.py`
- `harness/context/context_engine.py`
- 对应测试

#### 第 3 轮
只做：
- `harness/tools/tool_discovery_service.py`
- `runtime/orchestrator.py`
- `runtime/executor.py`

#### 第 4 轮
只做：
- `runtime/verifier.py`
- `harness/sandbox/*`
- `harness/telemetry/*`

#### 第 5 轮
只做：
- `realm_evaluator.py`
- README / CLI 最小闭环
- 端到端 smoke test

这样最稳。

## 8. 可直接给 Codex / Claude Code 的通用任务模板

下面这段你可以直接复用。

### 模板 1：单模块实现任务

```md
你正在为一个 AI agent runtime harness 项目实现 B v0.1。

## 背景
- A 是架构规范，B 是实现骨架
- 当前只做 B v0.1（炼气期 / MVP）
- 当前目标是跑通最小运行链，不做并行 worker、复杂 method router、自动退役、重型代码能力包

## 本轮任务
请只实现以下文件：
- harness/state/models.py
- planner/task_contract_builder.py
- tests/test_task_contract_builder.py

## 必须遵守的边界
- 使用 `entrypoints/ -> runtime/ -> harness/` 的单向依赖
- 不引入数据库，先用文件 / Pydantic schema 即可
- 不实现 model_router、methodology_router、learning_journal ranking
- 不改其他目录结构

## 需要输出
1. 你新增/修改了哪些文件
2. 每个文件的职责
3. 核心类/函数设计
4. 测试如何覆盖
5. 仍未解决的问题

## 验收标准
- 能生成结构化 TaskContract
- 含 contract_id 和 schema_version
- 至少包含 task_type、success_criteria、allowed_tools、write_permission_level、token_budget、latency_budget、uncertainty_level、residual_risk_level、stop_conditions、expected_artifacts
- 测试能通过
```

### 模板 2：目录与骨架初始化任务

```md
请为 B v0.1 初始化最小实现仓库。

## 只做这些
- 生成目录结构
- 生成空文件和最小注释
- 生成 pyproject.toml
- 生成 .env.example
- 生成 README 首稿
- 生成 tests 占位文件

## 不做这些
- 不写完整业务逻辑
- 不接外部模型 API
- 不引入数据库
- 不实现并发
- 不自动补充未在目录里声明的模块

## 目录边界
entrypoints/
planner/
runtime/
harness/
artifacts/
skills/
tests/

## 输出要求
- 每个文件顶部都写职责注释
- README 说明 v0.1 目标、当前不做什么、最小运行链
- 保持代码可读、可测、低依赖
```

## 9. 你自己推进时最该盯住的 4 个点

1. **不要让 coding agent 偷偷提前做 v0.2 / v0.3 的事**  
   例如并行 worker、复杂 Methodology Router、自动退役、细粒度 hook 系统。

2. **每一轮都要把“本轮不做什么”写进任务书**  
   这比“做什么”同样重要。

3. **先锁 schema，再写运行链**  
   不然状态和 contract 很快会漂移。

4. **每轮输出都要求“未决问题列表”**  
   这样后续不会把隐性假设埋进实现里。

## 10. 当前建议

如果你现在就要往下推进，最合理的顺序是：

- 先用 Codex / Claude Code 帮你 **初始化目录和 schema**
- 再逐轮实现 `task contract → state → context → tool discovery → orchestrator`
- 不要让它第一轮就“帮你做完整项目”

这个阶段最需要的是 **低漂移、可回看、可测试**，而不是一次性自动生成很多代码。
