# archive-first-harness: 项目战略定位与开发路线图

日期：2026-04-11
状态：经过客观验证的项目方案（所有关键判断已联网搜索验证）

---

## 1. 项目定位：Agent Evidence Layer

### 1.1 一句话定位

**archive-first-harness 是一个本地优先、零依赖的 AI Agent 运行证据系统，让每次 agent 运行都可诊断、可比较、可回溯。**

它不是框架、不是 harness、不是 observability 平台。它是 agent 生态中缺失的第四层：**Evidence Layer**。

### 1.2 Agent 生态四层格局（经验证）

| 层级 | 代表项目 | 状态 | 本项目关系 |
|---|---|---|---|
| **框架层** Framework | LangGraph, CrewAI, AutoGen, Semantic Kernel | 红海，成熟 | 无竞争 |
| **Harness 层** Runtime | OpenHarness, OpenHands, Aider, Claude Code | 快速增长，同质化 | 互补（可为其提供 archive 能力） |
| **Observability 层** Tracing | LangSmith, Braintrust, Langfuse, Arize Phoenix | 商业化成熟，SaaS 主导 | 差异化竞争（见下文） |
| **Evidence 层** Archive | **几乎空白** — 仅学术论文 (AgentRx, AgentTrace, EAGER) | 无成熟开源工具 | **本项目定位** |

### 1.3 为什么"第四层"是真实存在的空白

**验证方法**：2026-04-08 至 04-11 联网搜索 "run archive" + "failure localization" + "AI agent"，未找到现成的开源工具。

**最接近的学术工作**：
- **AgentRx**（Microsoft Research, arXiv:2602.02475, 2026年2月）：115 条失败轨迹的 post-hoc 分析框架，10 类失败分类法。MIT 许可，已开源。但它是 *分析框架* ，不是 *运行时 archive 系统*。
- **AgentTrace**（OpenReview 论文）：trace 级别的失败分析，学术原型。
- **EAGER**（学术论文）：agent evaluation 框架。

**这些都不是可以直接嵌入 agent runtime 的 archive 工具。**

---

## 2. 竞品对比：诚实的差异化分析

### 2.1 LangSmith（LangChain 官方）

**LangSmith 已有的能力**：
- Trace 记录与可视化
- Polly AI 分析 trace
- Experiment comparison（side-by-side 分数对比）
- Failure clustering（Insights Agent）
- Trace export（JSONL）

**LangSmith 没有的**：
- 本地文件系统归档（它是 SaaS，数据在云端）
- 四层失败定位（routing / execution / verification / governance）
- Governance 作为独立执行阶段
- 30+ 维度的结构化 run-to-run 对比
- 动态风险再评估（verification 后根据执行结果调整风险等级）

**差异本质**：LangSmith 的 comparison 是 **eval score 级别**（"这个 run 得了 0.8 分，那个得了 0.6 分"），不是 **执行链级别**（"这次在 verification 阶段失败，上次在 routing 阶段失败，governance 从 cleared 变成了 escalated"）。

### 2.2 Braintrust

**Braintrust 已有的能力**：
- Experiment diff mode（green/red highlighting）
- Regression detection
- CI/CD eval gating
- Side-by-side output diff
- Programmatic comparison API

**Braintrust 没有的**：
- 本地归档（SaaS 产品）
- 失败阶段定位
- Governance 状态追踪
- 结构化 transition 分类（failure_transition, verification_transition, governance_transition 等）

**差异本质**：Braintrust 对比的是 eval 实验的 **输出分数和结果**，不是 agent 执行的 **内部阶段状态变化**。

### 2.3 Langfuse（开源 observability）

**Langfuse 有的**：开源、自部署、trace 记录、cost tracking、评分。
**Langfuse 没有的**：run-to-run 结构化对比、失败定位、governance 追踪。
**差异本质**：Langfuse 是 tracing 工具，不是 evidence archive。

### 2.4 本项目真正独有的能力（经验证）

| 能力 | 实现位置 | 竞品最近距离 |
|---|---|---|
| **本地零依赖 archive** | `run_archive.py` — `write_run_archive()` | LangSmith/Braintrust 都是 SaaS |
| **四层失败定位** (routing/execution/verification/governance) | `failure_signature.json` — `failed_stage` 字段 | LangSmith 只有 trace 层 error/success |
| **Governance 作为执行阶段** | `residual_followup.governance` — sandbox 决策、override 追踪 | 竞品均未建模 |
| **30+ 维度结构化 run 对比** | `archive_browse.py` — `compare_run_archives()` 函数，含 6 类 transition | Braintrust 只对比 eval scores |
| **动态风险再评估** | `residual_followup.reassessment` — 根据执行结果调整风险等级 | 完全独有 |

### 2.5 本项目的客观弱势

必须诚实承认：

1. **没有 Web UI** — 全部是 CLI + JSON
2. **没有数据库层** — 纯文件系统（JSONL index + 目录）
3. **没有异步/队列系统** — 同步执行
4. **没有插件生态** — 没有第三方扩展机制
5. **没有多 agent 协调** — 单 agent 运行
6. **不是通用 observability 平台** — 只做 evidence archive
7. **用户基数为零** — 刚开源，没有社区

---

## 3. 战略路线：双轨并行

### 3.1 双轨概述

| 轨道 | 目标 | 价值 |
|---|---|---|
| **A轨：OpenHarness 贡献** | 向 OpenHarness 提交 archive writer PR | 建立开源贡献记录，验证 archive 理念，扩大影响力 |
| **B轨：自身项目演进** | 将 archive-first-harness 打磨为独立的 Evidence Layer 工具 | 核心竞争力建设，形成可复用的开源产品 |

两条轨道互相促进：A轨验证理念并获取用户反馈 → B轨用反馈优化核心实现 → B轨的成熟组件可以反哺 A轨。

### 3.2 优先级排序

**短期（1-2 周）**：以 A轨为主，B轨为辅
- A轨更容易产出可见成果（PR、Issue 讨论、社区认可）
- B轨需要更多时间打磨，但不急

**中期（3-6 周）**：A轨和B轨并行
- A轨的 PR 反馈用来指导 B轨设计决策
- B轨开始做面向外部用户的改进

**长期（2-3 个月）**：以 B轨为主
- B轨目标是成为可独立使用的 CLI 工具（pip install）
- A轨保持社区参与，但不再是主要精力投入

---

## 4. A轨：OpenHarness 贡献计划

### 4.1 已完成

- [x] Fork HKUDS/OpenHarness → quzhiii/OpenHarness
- [x] PR #17（diagnose skill）— **已合并**
- [x] Issue #18（讨论 run archive 集成方向）— 已提交，等待回复
- [x] 留了 bump 评论

### 4.2 下一步：PR #2 — 最小 Archive Writer

**目标**：向 OpenHarness 贡献一个最小化的 run archive writer，让 OpenHarness 的每次 agent 运行可以持久化为结构化文件。

**实现策略**：从 `archive-first-harness` 提取最小子集，适配 OpenHarness 的 `query.py` agent loop。

**具体步骤**：

1. **创建分支** `feature/run-archive` from upstream main
2. **新建文件** `src/openharness/archive/writer.py`
   - 提取 `run_archive.py` 的核心逻辑
   - 简化为只输出 3 个文件：`manifest.json`, `execution_trace.jsonl`, `failure_signature.json`
   - 不引入任何新依赖
3. **新建文件** `src/openharness/archive/__init__.py`
   - 只暴露 `write_run_archive(run_id, events, output_dir)` 函数
4. **修改** `src/openharness/engine/query.py`
   - 在 agent loop 结束后，调用 `write_run_archive()`
   - 用 `try/except` 包裹，确保 archive 失败不影响主流程
   - 通过环境变量 `OPENHARNESS_ARCHIVE_DIR` 控制是否启用
5. **新建测试** `tests/test_archive_writer.py`
   - 测试 manifest 写入格式
   - 测试 execution trace 追加
   - 测试 failure signature 提取
6. **更新** `CHANGELOG.md` 和 `README.md`（简短说明）
7. **提交 PR**，描述中引用 Issue #18

**估计工时**：4-6 小时

**风险**：
- 维护者可能不接受（降低风险：先在 Issue #18 获得正面回应再提交）
- OpenHarness 的 agent loop 结构可能已变化（需要先 sync upstream）

### 4.3 后续可能的贡献

- PR #3：Archive browse / read 命令（CLI 子命令）
- PR #4：Run-to-run comparison（如果社区有需求）
- 参与其他 Issue 的讨论和修复

---

## 5. B轨：自身项目演进计划

### 5.1 当前状态盘点

| 维度 | 状态 |
|---|---|
| 测试 | 291 tests passed |
| Archive 文件 | 11 个结构化输出文件 per run |
| 对比维度 | 30+ 结构化比较字段，6 类 transition |
| CLI | `run`, `archive --latest`, `archive --run-id`, `archive --compare-run-id` |
| 文档 | 架构文档、UAT 检查表、使用日记模板 |
| 弱项 | 首次使用体验差、无 Web UI、无 pip 包 |

### 5.2 Phase 1：First-Run Experience 修复（第 1-2 周）

**目标**：让一个新用户在 5 分钟内完成第一次 run + archive 查看。

**任务**：

| # | 任务 | 优先级 | 估计工时 |
|---|---|---|---|
| 1.1 | 写一个 `quickstart.py` 脚本，自动执行 ping → archive --latest | P0 | 2h |
| 1.2 | 简化 `requirements.txt`，确保 `pip install -r` 零报错 | P0 | 1h |
| 1.3 | 修复 Windows PowerShell 下的 PYTHONPATH 设置问题 | P0 | 2h |
| 1.4 | 添加 `--demo` 模式到 CLI，自动生成一对 success/failure run 用于对比演示 | P1 | 3h |
| 1.5 | 重写 README 的 Quick Start 部分（更少步骤、更清晰预期输出） | P1 | 2h |

### 5.3 Phase 2：Archive 核心能力增强（第 3-4 周）

**目标**：让 archive 对比更有实际诊断价值。

| # | 任务 | 优先级 | 估计工时 |
|---|---|---|---|
| 2.1 | 添加 `archive --summary` 子命令：输出最近 N 次 run 的趋势摘要（成功率、常见失败类型、governance 升级趋势） | P0 | 4h |
| 2.2 | 添加 `archive --diff` 子命令：以 human-readable text diff 格式输出两次 run 的关键差异 | P0 | 4h |
| 2.3 | 给 `compare_run_archives()` 的输出增加 `diagnosis` 字段：根据 transition 自动生成一句话诊断建议 | P1 | 3h |
| 2.4 | 添加 `archive --export` 子命令：将一个 run 的 archive 导出为单个 JSON 文件（方便分享和存储） | P2 | 2h |

### 5.4 Phase 3：可复用性和分发（第 5-6 周）

**目标**：让项目可以被其他人作为库使用。

| # | 任务 | 优先级 | 估计工时 |
|---|---|---|---|
| 3.1 | 创建 `pyproject.toml`，支持 `pip install archive-first-harness` | P0 | 3h |
| 3.2 | 将 archive writer 提取为独立模块 `archive_first_harness.writer`，可被外部项目 import | P0 | 4h |
| 3.3 | 将 archive browse/compare 提取为独立模块 `archive_first_harness.browse` | P0 | 4h |
| 3.4 | 编写集成示例：如何在 LangGraph / CrewAI 的 callback 中调用 archive writer | P1 | 4h |
| 3.5 | 发布到 PyPI（或至少 TestPyPI） | P1 | 2h |

### 5.5 Phase 4：生态连接（第 7-10 周）

**目标**：与主流框架建立连接。

| # | 任务 | 优先级 | 估计工时 |
|---|---|---|---|
| 4.1 | 编写 LangGraph callback handler：自动在每次 graph 执行后写入 archive | P1 | 6h |
| 4.2 | 编写 OpenHarness plugin（如果 A轨 PR 被接受，基于已有代码扩展） | P1 | 4h |
| 4.3 | 写一篇技术博客："Why Agent Observability Isn't Enough: The Case for Evidence Archives" | P1 | 4h |
| 4.4 | 在 Reddit r/LocalLLaMA 和 Hacker News 上发帖（如果博客质量足够） | P2 | 1h |

### 5.6 Phase 5：可选扩展（第 10+ 周，视反馈决定）

以下只在有真实用户需求时才做：

| # | 任务 | 前提条件 |
|---|---|---|
| 5.1 | 简单 Web UI（archive 浏览器，只读） | 至少 3 个外部用户请求 |
| 5.2 | SQLite 索引层（替代 JSONL index） | archive 超过 1000 条时性能下降 |
| 5.3 | GitHub Actions 集成（CI 中自动 archive + regression 检测） | 至少 1 个用户在 CI 中使用 |
| 5.4 | 多 agent 场景支持（formation archive） | 已有多 agent 运行的实际 case |

---

## 6. 关键里程碑

| 时间 | 里程碑 | 验收标准 |
|---|---|---|
| **第 1 周末** | A轨 PR #2 提交 | PR 已创建，CI 通过，描述清晰 |
| **第 2 周末** | B轨 Phase 1 完成 | 新用户 5 分钟内完成首次 run + archive 查看 |
| **第 4 周末** | B轨 Phase 2 完成 | `archive --summary` 和 `archive --diff` 可用，有自动诊断建议 |
| **第 6 周末** | B轨 Phase 3 完成 | `pip install archive-first-harness` 可用，有集成示例 |
| **第 8 周末** | B轨 Phase 4 部分完成 | 至少 1 个框架集成（LangGraph 或 OpenHarness） |
| **第 10 周末** | 技术博客发布 | 博客已发布到 Medium / 个人博客 |

---

## 7. 技术决策记录

### 7.1 为什么坚持本地文件而不是数据库？

**决策**：Phase 1-3 保持纯文件系统。

**理由**：
- 零依赖是核心差异化（vs LangSmith/Braintrust 都是 SaaS）
- 文件系统天然支持 git 版本管理
- JSONL index 在 < 10000 条时性能足够
- 数据库层可以在 Phase 5 按需添加，但不应该过早引入

### 7.2 为什么不做 Web UI？

**决策**：短期内不做，Phase 5 视需求决定。

**理由**：
- CLI 对目标用户（agent 开发者）足够
- Web UI 会引入前端依赖，破坏零依赖原则
- 如果做，应该是独立项目（`archive-viewer`），不是核心功能
- 过早做 UI 会分散精力，偏离核心价值

### 7.3 A轨 PR 策略：最小化 vs 完整功能？

**决策**：最小化。

**理由**：
- OpenHarness 维护者活跃但对外部方向保守（Issue #18 未回复）
- 最小 PR（3 文件输出 + 环境变量开关）更容易被接受
- 被接受后再迭代追加功能（browse, compare）
- 即使被拒绝，代码也可以直接用在 B轨的 integration example 中

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| OpenHarness 不接受 PR | 中 | 低 — 不影响 B轨 | 代码转为 B轨 integration example |
| 没有外部用户 | 高 | 中 — 影响方向判断 | 主动在 Reddit/HN/Discord 推广 |
| LangSmith 添加类似功能 | 低 | 高 — 差异化被削弱 | 加速 Phase 3 发布，占领"本地 archive"心智 |
| 项目范围蔓延 | 中 | 高 — 精力分散 | 严格遵守 Phase 5 的前提条件 |
| AgentRx 从学术转为产品 | 低 | 中 — 直接竞争 | 保持关注，利用先发的工程化优势 |

---

## 9. 成功指标

### 短期（6 周内）

- [ ] OpenHarness 至少 1 个新 PR 被接受或进入讨论
- [ ] `pip install` 可用
- [ ] 至少 1 个框架集成示例可运行
- [ ] README 获得至少 5 个 GitHub stars（含自然流量）

### 中期（3 个月内）

- [ ] 至少 3 个外部用户实际使用过 archive 功能
- [ ] 技术博客发布
- [ ] archive-first-harness 出现在至少 1 个 "awesome agent tools" 列表中

### 长期（6 个月内）

- [ ] PyPI 下载量 > 100
- [ ] 至少 1 个外部 PR 贡献
- [ ] 至少 1 个其他 agent 项目集成了 archive writer

---

## 10. 附录

### 10.1 核心代码资产

| 文件 | 行数 | 核心功能 |
|---|---|---|
| `entrypoints/run_archive.py` | 447 | Archive writer — `write_run_archive()` |
| `entrypoints/archive_browse.py` | 1037 | Browse, read, compare — `compare_run_archives()`, `browse_run_archives()`, `read_latest_run_archive()` |
| `entrypoints/cli.py` | - | CLI 入口 |
| `runtime/verifier.py` | - | 验证能力 |
| `harness/governance/policy.py` | - | 治理策略 |
| `harness/evaluation/baseline_compare.py` | - | 基线对比 |

### 10.2 Compare 输出的 30+ 维度

以下是 `compare_run_archives()` 实际输出的结构化对比字段：

**状态对比**：same_status, same_workflow_profile_id, same_task_type, same_formation_id, same_task

**Artifact 对比**：same_expected_artifacts, expected_artifacts_added/removed, same_produced_artifact_types, produced_artifact_types_added/removed, same_produced_artifact_count, same_baseline_compare_status, same_baseline_compared_artifact_types, baseline_compared_artifact_types_added/removed, same_baseline_status_counts, same_missing_expected_artifact_warning

**失败对比**：same_failure_class, same_failed_stage

**验证对比**：same_verification_status

**风险对比**：same_reassessed_level, same_followup_needed, same_reassessment_reason_codes, reassessment_reason_codes_added/removed

**评估对比**：same_evaluation_status, same_evaluation_recommendation, same_evaluation_human_review, same_evaluation_reason_codes, evaluation_reason_codes_added/removed

**治理对比**：same_governance_status, same_governance_required

**Transition 分类**：failure_transition, verification_transition, reassessment_transition, evaluation_transition, governance_transition, artifact_transition

### 10.3 外部引用

- AgentRx: https://github.com/microsoft/AgentRx — MIT, 115 失败轨迹 benchmark
- OpenHarness: https://github.com/HKUDS/OpenHarness — ~4.8k stars
- OpenHarness Issue #18: https://github.com/HKUDS/OpenHarness/issues/18
- OpenHarness PR #17 (merged): https://github.com/HKUDS/OpenHarness/pull/17
- LangSmith Docs: https://docs.smith.langchain.com/
- Braintrust Docs: https://www.braintrust.dev/docs/
- Langfuse: https://langfuse.com/

---

*本文档中所有"经验证"的判断均基于 2026-04-08 至 04-11 期间的联网搜索结果。竞品能力描述基于其官方文档，可能随版本更新而变化。*
