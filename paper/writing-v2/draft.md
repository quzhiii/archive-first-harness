# archive-first-harness: A Local-First Evidence Layer for Diagnosing AI Agent Failures

## 0. Meta

- **Target venue**: EMNLP 2026 System Demonstrations
- **Status**: working draft v2
- **Page budget**: 6+1 pages

---

## Abstract

As AI agents become more capable, debugging them remains surprisingly primitive. In practice, developers often inspect long execution traces, compare logs by hand, and infer what changed between a successful run and a failed one. Existing tools support agent construction, orchestration, tracing, and evaluation, but they do not directly provide a compact evidence layer for run-to-run diagnosis. We present **archive-first-harness**, a local-first evidence layer for AI agent debugging. The system archives each run into a structured evidence bundle and supports direct comparison across failure stage, verification outcome, reassessed risk, governance escalation, and artifact production. We position this layer as distinct from frameworks, harnesses, and observability systems. In an initial empirical study, we map **73 annotated failures** from the public AgentRx benchmark splits into the archive-first stage model and find that the released data can be covered without leaving an unmapped category. We further provide deterministic case-study pipelines for retrieval-augmented generation and multi-step tool-use failures, along with a proxy evaluation showing that archive compare materials have 31–116% higher diagnostic information density and require fewer inference steps than raw logs. A blind LLM-as-evaluator study using two frontier models achieves 100% cause attribution accuracy across all conditions, with a single stage-label ambiguity surfaced as a schema finding. Together, these results suggest that an explicit evidence layer can make agent debugging more structured, local, and comparable.

---

## 1. Introduction

AI agents increasingly operate through long-horizon, tool-mediated trajectories. They search the web, call APIs, manipulate files, produce artifacts, and coordinate multiple intermediate steps before returning a final answer. While the capabilities of such systems have grown rapidly, their debugging workflows have lagged behind. When an agent fails, developers typically inspect raw traces, scan tool outputs, re-run the task, and manually guess what changed. This process is especially painful when the failure is subtle: a plan shifts slightly, a tool output is misread, an expected artifact is missing, or a policy layer blocks one branch but not another.

Current agent tooling helps with adjacent parts of the lifecycle. Frameworks help build agents. Harnesses help execute them. Observability platforms help trace them. Evaluation systems help score them. Yet there remains a practical gap between **seeing** a run and **diagnosing** why one run differs from another. In particular, developers often need a compact answer to a concrete question: *what materially changed between yesterday’s successful run and today’s failure?*

We argue that this gap motivates a distinct layer in the agent stack: an **Evidence Layer**. Rather than storing only raw traces or aggregate metrics, an Evidence Layer turns each run into a structured evidence bundle and emphasizes run-to-run comparison. Our system, **archive-first-harness**, implements this idea as a local-first command-line tool. For each run, it writes a stable archive containing task summary, execution outcome, verification report, failure signature, evaluation summary, and artifact metadata. It then supports browsing and comparing those archives across dimensions such as failure class, failed stage, verification transition, reassessed risk, governance escalation, and artifact regressions.

The key design choice is to optimize for diagnosis rather than monitoring. Monitoring tools are excellent for observing many runs; an evidence layer is optimized for explaining why a specific pair of runs diverged. This difference matters in practice. A long trace may show *everything that happened*, but a useful debugging primitive should reveal *what changed in a way that matters*. archive-first-harness therefore aims to sit between observability and debugging: more structured than raw tracing, but lighter-weight and more local than a hosted experiment platform.

This paper makes four contributions:

1. **Conceptual contribution.** We articulate the **Agent Evidence Layer** as a missing layer in the agent tooling stack, distinct from frameworks, harnesses, observability systems, and evaluators.
2. **System contribution.** We design a structured archive schema and a comparison model for agent runs, centered on stage-aware debugging across routing, execution, verification, and governance-relevant outcomes.
3. **Implementation contribution.** We implement a zero-dependency local CLI tool that supports archive creation, browsing, and run-to-run comparison using product-facing interfaces rather than research-only code paths.
4. **Empirical contribution.** We provide initial empirical evidence through real AgentRx failure-to-stage mapping, deterministic case-study pipelines, information density quantification, and a blind LLM proxy evaluation across two frontier models.

Our goal is not to claim that archive-first-harness fully solves agent debugging. Rather, we aim to show that an explicit evidence layer is both practically implementable and empirically useful enough to merit a distinct place in the agent stack.

---

## 2. Related Work

### 2.1 Agent failure diagnosis and trajectory analysis

Recent work has begun to study AI agent failure more directly. **AgentRx** frames agent debugging as a root-cause attribution problem and provides a labeled benchmark of failed trajectories. This line of work is valuable because it treats failure analysis as a first-class research problem rather than a byproduct of evaluation. Related trajectory-analysis efforts, such as AgentTrace-style tooling and failure taxonomy work, similarly attempt to explain what went wrong inside complex agent executions.

Our work differs in emphasis. These systems are primarily **post-hoc analytic frameworks** over benchmarked or collected trajectories. By contrast, archive-first-harness is designed as a **runtime-adjacent, local-first system primitive**: it writes structured evidence during normal usage and supports direct run-to-run comparison in a product workflow. In other words, AgentRx helps us understand failure taxonomies; archive-first-harness focuses on operationalizing diagnosis for everyday debugging.

### 2.2 Observability, tracing, and evaluation platforms

Platforms such as **LangSmith**, **Braintrust**, and **Langfuse** provide tracing, monitoring, experiment views, and evaluation infrastructure for LLM applications and agents. These systems are highly useful for observability and aggregate inspection. However, their design center is typically broader than local debugging. They record runs, surface traces, and organize experiments, but they are not primarily built around a compact, stage-oriented evidence bundle with explicit run-to-run diffs over artifacts, verification, governance, and follow-up state.

We do not position archive-first-harness as a replacement for these platforms. Instead, we view it as complementary: tracing answers *what happened*, while an evidence layer answers *what materially changed*.

### 2.3 Positioning: Evidence Layer vs. adjacent layers

The core positioning claim of this paper is that there is a missing layer between observability and debugging:

- **Frameworks** define how agents are built.
- **Harnesses** define how agents are executed.
- **Observability systems** show traces, metrics, and runtime events.
- **Evidence Layer systems** convert runs into stable, comparable evidence artifacts for diagnosis.

This distinction is subtle but important. The Evidence Layer does not need to replace traces, hosted dashboards, or evaluators. Its purpose is narrower and more practical: making individual failures easier to compare, localize, and explain.

---

## 3. System

### 3.1 The Evidence Layer abstraction

archive-first-harness is built around a simple idea: every run should leave behind a compact, structured archive that is small enough to inspect and rich enough to compare. The system therefore treats a run not as a raw trace alone, but as a bundle of evidence spanning task contract, execution result, verification, evaluation, follow-up, and artifact production.

We position this as an **Evidence Layer** in the stack:

- Framework: build agents
- Harness: run agents
- Observability: trace and monitor agents
- **Evidence Layer**: archive and compare runs for diagnosis

The abstraction is intentionally modest. It does not require new model behavior, a hosted backend, or specialized instrumentation infrastructure. Instead, it relies on stable JSON/JSONL outputs and a local archive root.

### 3.2 Archive schema

Each run is archived as a directory containing structured files such as:

- `manifest.json`
- `task_contract.json`
- `profile_and_mode.json`
- `verification_report.json`
- `evaluation_summary.json`
- `failure_signature.json`
- `final_output.json`
- `execution_trace.jsonl`
- `archive_index.json`

These files are designed to separate concerns. For example, `failure_signature.json` answers *where and how the run failed*, while `verification_report.json` captures whether the result met expected criteria, and `evaluation_summary.json` records whether a run merits observation or human review. `final_output.json` and artifact metadata record what was actually produced, which becomes essential when a run technically “completes” but omits a required output.

This schema captures more than a binary success/failure label. It allows the system to preserve:

- the expected artifacts for a task,
- the artifacts actually produced,
- the stage at which failure occurred,
- whether verification regressed,
- whether risk or governance status changed,
- and whether downstream review became necessary.

### 3.3 Comparison model

The compare command operates over archived runs rather than raw trajectories. It computes differences across dimensions including:

- failure class and failed stage,
- verification status,
- reassessed risk level and reason codes,
- evaluation recommendation and human-review requirement,
- governance escalation state,
- expected artifacts, produced artifacts, and baseline artifact status.

These differences are normalized into transition labels such as `regressed`, `resolved`, `unchanged`, `improved`, and `cleared`. This produces a concise diagnostic surface. Instead of manually reading two traces line-by-line, a developer can quickly see that a run regressed in **verification**, **artifacts**, and **evaluation**, while governance remained unchanged.

### 3.4 Local-first CLI workflow

archive-first-harness exposes a local-first CLI workflow:

1. run a task,
2. archive the evidence bundle,
3. browse latest or filtered runs,
4. inspect a specific run,
5. compare two runs side-by-side.

This workflow is designed for practical debugging sessions. A developer can keep all archives locally, inspect them with plain text tools, and still benefit from structured comparison. The system therefore targets the debugging loop directly rather than requiring adoption of a remote platform.

---

## 4. Evaluation and Current Artifacts

Our evaluation goal is not yet to prove superiority over every debugging workflow, but to establish that the Evidence Layer abstraction is concrete enough to support three forms of evidence: taxonomy alignment, realistic case studies, and a user-facing debugging task setup.

### 4.1 AgentRx mapping experiment

We map AgentRx’s root-cause categories into the Evidence Layer stage abstraction. Using the two released benchmark splits (`tau_retail` and `magentic_one`), we processed **73 annotated failed trajectories** and translated each root-cause category into one of three operational stages used by archive-first-harness: **routing**, **execution**, and **governance**.

The current real-data pass yields the following totals:

- **routing**: 35
- **execution**: 29
- **governance**: 9
- **unknown**: 0

At the split level, the retail trajectories are dominated by routing-oriented failures such as underspecified user intent and intent-plan misalignment, while the Magentic-One trajectories show a stronger execution component and a distinct governance cluster caused by guardrail-triggered failures. This matters because it demonstrates that the stage model is not merely a conceptual reframing; it can absorb the released AgentRx labels without leaving an unmapped bucket on the public data.

This experiment is intentionally modest. It does not yet claim superiority over AgentRx’s taxonomy. Instead, it supports a narrower but important claim: a compact stage abstraction can summarize a richer benchmark taxonomy in a way that aligns with operational debugging workflows.

### 4.2 Case studies

We organize the case-study portion into three tracks:

- **Case A**: a repository-grounded coding-agent scenario with a completed archive pair consisting of a real Aider success run and a reduced-scope failure-prone writing sample,
- **Case B**: a retrieval-augmented generation scenario with a success/failure archive pair,
- **Case C**: a multi-step tool-use scenario with a success/failure archive pair.

The current repository already includes deterministic scripts for Cases B and C that generate archives using the same production archive writer as the main system. For Case A, the repository now includes a completed Aider-based archive pair collected through the same archive-facing interfaces. The success run is a repository-grounded real coding-agent edit, while the failure-prone run is a reduced-scope paper excerpt designed to test whether the agent overstates Case A completion under realistic writing conditions. This matters because Case A is now represented in the same compare-ready archive format as the other cases, rather than remaining only a planned ingestion workflow.

In Case A, the failure-prone sample shows a concrete factual-overstatement pattern: the agent rewrites the text so that Case A appears to already have a completed success/failure pair, even though the underlying repository state does not support that stronger claim. This provides a realistic comparison point for the archive-first evidence layer because the failure is not a raw crash, but a subtle state-description error that would be easy to miss in ordinary editing workflows.

In all three cases, the compare view exposes meaningful regressions across multiple dimensions. For example, in the RAG case (Case B), the successful run emits both `answer` and `retrieval_report`, while the failed run emits only `answer`, triggers a missing-expected-artifact warning, and shifts the evaluation recommendation from `keep` to `observe`. In the multi-step case (Case C), the failed run loses the expected `plan_note`, shifts from success to execution failure, and causes parallel regressions in verification, reassessment, and artifact status. In the coding-agent case (Case A), the compare output shows regressions in failure status, verification outcome, reassessment, and evaluation while governance remains unchanged, illustrating how the evidence layer can surface subtle factual-overstatement errors rather than only hard crashes. These are precisely the kinds of structured differences that are hard to recover quickly from raw traces alone.

### 4.3 User study assets and proxy evaluation

We prepare a small A/B debugging study contrasting raw logs versus archive compare outputs on failure localization tasks. The repository contains a moderator script, a post-study questionnaire, a score-sheet template, and two quantitative proxy evaluations that provide evidence ahead of the human study.

**Information density analysis.** We quantify the proportion of each material that directly supports diagnosis (i.e., text that answers "which stage failed" and "what was the root cause") relative to total character count. The results are summarized in Table 1.

| Material | Total chars | Diagnostic chars | Info density | Inference steps |
|---|---|---|---|---|
| S1 raw\_logs | 1,219 | 221 | 18.1% | 3 |
| S1 archive\_compare | 1,376 | 540 | 39.2% | 2 |
| S2 raw\_logs | 1,365 | 485 | 35.5% | 4 |
| S2 archive\_compare | 1,147 | 534 | 46.6% | 2 |

Archive compare materials show substantially higher information density (+116% for S1, +31% for S2) and require fewer inference steps to reach a complete diagnosis (2 steps in both archive conditions versus 3–4 steps in the raw log conditions). Notably, the archive format achieves this with comparable or shorter total length, indicating that the gain comes from reduced noise rather than added verbosity.

**LLM-as-evaluator (blind).** To further validate the materials, we run a blind proxy evaluation using two frontier models (DeepSeek-Chat and GLM-5.1) as stand-in evaluators. Each model receives either the raw log or the archive compare output for each scenario without being told which condition it is reading, and is asked to identify the failure stage and root cause. We repeat each condition three times per model (n=6 per cell after aggregating across models).

Cause attribution accuracy is 100% across all conditions and both models. Stage accuracy is 100% in three of four conditions (Table 2).

| Scenario | Condition | Stage accuracy | Cause accuracy | Mean confidence |
|---|---|---|---|---|
| S1 | raw\_logs | 100% (6/6) | 100% (6/6) | 4.5 |
| S1 | archive\_compare | 0% (0/6) | 100% (6/6) | 4.8 |
| S2 | raw\_logs | 100% (6/6) | 100% (6/6) | 4.5 |
| S2 | archive\_compare | 100% (6/6) | 100% (6/6) | 5.0 |

The single exception is Scenario 1 under the archive\_compare condition, where both models consistently classify the failure stage as `execution` rather than `verification` (0/6). We interpret this as a genuine semantic ambiguity: retrieval strategy degradation occurs during execution but is surfaced by the verification report, making the stage boundary ambiguous when reading the archive output. Root cause identification is unaffected—all six evaluations correctly identify the retrieval strategy regression as the underlying cause. This finding is discussed further in Section 5.

The planned lightweight human study (3–5 participants) will measure time-to-localize, correctness of diagnosis, and subjective usefulness using the same materials. The proxy results above provide an initial quantitative baseline for that comparison.

---

## 5. Limitations and Next Steps

This work remains an early-stage systems contribution, and several limitations are important.

First, our current empirical evidence is strongest on **taxonomy alignment** and **case-study generation**. The proxy evaluation in Section 4.3 provides quantitative support for the archive format's diagnostic clarity, but a full human user study has not yet been executed. The proxy results should therefore be read as a lower bound on the expected human-study signal rather than a substitute for it.

Second, the LLM proxy evaluation surfaces a **stage label ambiguity** in the archive schema. For Scenario 1, both frontier models consistently classify the failure stage as `execution` rather than `verification` when reading the archive compare output (0/6 correct). The underlying cause is that retrieval strategy degradation is an execution-time behavior, yet the archive schema surfaces it through the verification report. This suggests that stage labels for retrieval-specific failures may benefit from an additional sub-label or disambiguation note in future schema versions. Importantly, root cause identification is unaffected by this ambiguity.

Third, **Case A** now includes a usable success/failure archive pair, but the current failure sample is intentionally reduced in scope. The success run is a real repository-grounded Aider edit, whereas the failure-prone run is collected from a condensed paper excerpt rather than a full-paper rewrite. This means the current Case A evidence is sufficient for archive-based comparison, but still leaves room to extend the study toward larger-scope coding-agent and writing tasks.

Fourth, the current system is **CLI-first and single-agent oriented**. While this is a deliberate design choice for local-first debugging, it means the present implementation does not yet fully explore richer multi-agent archive browsing or hosted collaboration features.

Finally, the current AgentRx mapping experiment establishes coverage and interpretability, but not yet downstream benefits such as reduced debugging time or higher root-cause accuracy. Those questions are exactly what the planned human user study is meant to test.

The immediate next steps are therefore:

1. run the lightweight human user study to validate the proxy evaluation results with real participants,
2. extend Case A from the current real-success / reduced-scope-failure pair to a broader set of repository-grounded coding-agent and writing samples,
3. convert the current markdown draft into a submission-ready format,
4. and extend the archive adapter from labeled summaries to richer trajectory-level analysis over the raw benchmark files.

---

## 6. Conclusion

archive-first-harness argues for an Evidence Layer in agent tooling: a local, structured, comparison-oriented layer between observability and debugging. By turning each run into a compact archive and exposing stage-aware diffs, the system makes it easier to answer a practical question that raw traces alone often leave unresolved: *what materially changed between two runs?*

Our current results show that this idea is already concrete enough to support real-data taxonomy mapping, deterministic case-study comparisons, and user-study-ready debugging tasks. We view this as an argument not only for one tool, but for a broader design principle: agent systems need better evidence surfaces, not just more traces.
