# Archive-First 第一轮调整总结

日期：2026-03-31

## 一句话总结

这轮没有把项目继续做大，而是先给它补上了“每次运行的独立档案系统”。

以前这个项目已经能跑、能导出、能记录最近历史，但更像“流水账”。
现在它开始具备“病历系统”的雏形：每次单任务运行结束后，都会留下一个独立的 run 档案，后面可以用来查原因、看差异、做对比。

---

## 这轮为什么要这样改

这轮的核心判断是：

- 当前项目最缺的不是 HTTP/API server
- 也不是插件系统
- 更不是把 formation、OpenClaw、meta-harness 一次性做大

当前真正缺的是：

- 这次为什么成功
- 这次为什么失败
- 失败卡在哪一步
- 两次不同 run 到底差在哪

如果这些证据层没有先补起来，后面你要做 formation 比较、OpenClaw 适配、离线优化，都会比较虚，因为没有稳定的 run-level evidence。

---

## 这轮实际做了什么

### 1. 先把项目方向校准了

这轮先把文档里的“下一步”从 `minimal HTTP/API server shell` 改成了 `archive-first`。

调整后的意思很简单：

- 先把每次运行的诊断档案做好
- 再考虑更大的外部边界扩展

相关文件：

- `ARCHITECTURE_POSITIONING.md`
- `README.md`
- `PROJECT_HANDOFF_v0.5.md`

---

### 2. 新增了单任务 run 的独立档案目录

现在每次 `run_task_request(...)` 执行后，都会 best-effort 写出：

```text
artifacts/runs/<run_id>/
```

这一层是新增的薄外层，不是改写主 runtime。

---

### 3. 每个 run 现在会落这些核心文件

每个 `artifacts/runs/<run_id>/` 下面会有：

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

这些文件分工大致是：

- `manifest.json`：这次 run 的最小总说明
- `task_contract.json`：任务合同
- `profile_and_mode.json`：profile 和默认 mode 信息
- `verification_report.json` / `metrics_summary.json` / `evaluation_summary.json`：已有评估结果的稳定落盘
- `final_output.json`：这次运行的核心输出摘要
- `context_plan.json`：这次上下文是怎么拼出来的
- `execution_trace.jsonl`：关键阶段事件轨迹
- `failure_signature.json`：失败时的最小失败标签
- `archive_index.json`：这个 run 目录内部的文件索引

---

### 4. 新增了全局 archive 索引

除了每次 run 各自的目录，这轮还新增了：

```text
artifacts/runs/index.jsonl
```

这个文件的作用类似“病例总表”，每次 run 会追加一行，便于后面做快速检索。

当前它至少会记录这些信息：

- `run_id`
- `created_at`
- `workflow_profile_id`
- `formation_id`
- `policy_mode`
- `status`
- `archive_dir`
- `failure_class`

目前还是文件系统级方案，没有引入数据库。

---

### 5. archive 写入不会改变主运行语义

这是这轮非常重要的边界。

现在 archive 是 best-effort：

- 如果 archive 写成功，结果里会带 `run_archive`
- 如果 archive 写失败，任务本身不会跟着失败
- 失败信息只会记录在 `run_archive` 字段里

也就是说，这一层只是“附加档案层”，不是新的控制平面。

---

### 6. raw evidence 现在已经有最小可用版

这轮没有做全链路 observability 平台，只做了够用的最小版：

- `context_plan.json`：来自现有 block selection 和上下文摘要
- `execution_trace.jsonl`：记录入口层几个关键阶段
- `failure_signature.json`：给失败贴一个稳定标签

这已经足够支撑后面回答一些关键问题：

- 这次是 execution 失败还是 verification 失败
- 这次用了什么 profile
- 这次上下文大概是什么结构

---

## 这轮明确没有做什么

这轮刻意没有碰这些东西：

- 没做 HTTP/API server
- 没做 SQLite / FTS / query DSL
- 没做 replay / rerun
- 没做 OpenClaw adapter
- 没做 formation selection engine
- 没做 offline meta-harness outer loop
- 没改 `runtime/orchestrator.py` 的控制语义

也就是说，这轮是“先把证据层站住”，不是“继续把系统做大”。

---

## 这轮改动涉及的关键代码文件

### 文档层

- `ARCHITECTURE_POSITIONING.md`
- `README.md`
- `PROJECT_HANDOFF_v0.5.md`
- `docs/plans/2026-03-31-archive-first-run-diagnostic-layer.md`

### 实现层

- `entrypoints/run_archive.py`
- `entrypoints/task_runner.py`

### 测试层

- `tests/test_run_archive_writer.py`
- `tests/test_run_archive_failure_tolerance.py`
- `tests/test_run_archive_trace.py`
- `tests/test_run_archive_index.py`

---

## 测试结果

这轮已经跑过全量测试：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

结果：

```text
Ran 253 tests in 1.977s
OK
```

说明这轮 archive-first 第一刀已经接上，而且没有把现有窄 runtime 主链打坏。

---

## 当前状态

当前工作树状态可以概括为：

- 方向已从“HTTP/API next”切换到“archive-first next”
- 单任务 run 已经有独立档案目录
- 已经有最小 raw evidence
- 已经有全局 archive index
- 全量测试已通过
- 当前还没有 commit

---

## 这轮的价值到底是什么

这轮最大的价值不是“多了几个 JSON 文件”。

真正的价值是：

1. 项目开始从“能跑”走向“可诊断”
2. 后面不同模式、不同 formation 才有真实证据可比较
3. 给宿主适配层和离线优化层打了地基
4. 以后遇到失败，不再只能看最终结果，而是能回看 run-level evidence

简单说，这轮是在给后面的所有优化建立“证据基础设施”。

---

## 下一步最推荐做什么

下一步我不建议立刻去做更大的东西。

最推荐的下一步是：

# 第二轮：补 archive 的检索和回看能力

目标是让这些 archive 不只是“存起来”，还要“找得到、看得回去、能比较”。

### 建议优先做的内容

#### 1. 先做文件系统级 archive helper

例如提供一些最小 helper：

- 按 `run_id` 查一个 run
- 按 `workflow_profile_id` 查最近几次 run
- 按 `status` 查失败 run
- 按 `failure_class` 查相似失败

这一步先不要上数据库，直接基于：

- `artifacts/runs/index.jsonl`
- 每个 run 目录里的 JSON 文件

做轻量 helper 就够了。

#### 2. 再做最小的 archive browse / compare helper

重点不是复杂系统，而是先支持这些日常问题：

- 最近一次失败是什么
- 同一个 profile 最近几次表现怎样
- 两个 run 的 failure signature 差在哪
- 某次 run 的 context plan 和 verification 结果是什么

#### 3. 然后再考虑是否需要 SQLite/FTS

只有当 run 数量开始明显变多、文件系统 helper 不够用了，再考虑 SQLite/FTS。

当前阶段没必要抢跑。

---

## 下一步暂时不要做什么

下一轮仍然不建议直接跳去做：

- HTTP/API shell
- OpenClaw adapter
- formation engine
- meta-harness outer loop

原因不变：

现在最值钱的是把 archive 从“能写”继续推进到“能查、能比、能回看”。

---

## 推荐的下一轮顺序

建议下一轮按这个顺序做：

1. 先做 `archive helper` 的数据读取层
2. 再做最小 CLI / function surface
3. 再补 compare / browse 测试
4. 最后再决定是否需要 SQLite/FTS

---

## 最后一句话

这轮的本质不是“继续加功能”，而是把项目从“有 history”推进到了“开始有 diagnostic archive”。

下一步最合理的方向，不是继续扩边界，而是把这层 archive 变成真正可用的检索和分析基础设施。
