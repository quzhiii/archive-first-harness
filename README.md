# archive-first-harness

<div align="center">

**An archive-first runtime harness for AI agents that need to be diagnosable, comparable, and governable.**

[![Python](https://img.shields.io/badge/python-3.13.2-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Stage](https://img.shields.io/badge/stage-public%20alpha-1f6feb)](#current-status)
[![Focus](https://img.shields.io/badge/focus-archive--first-111111)](#why-this-project-exists)
[![Tests](https://img.shields.io/badge/tests-291%20passed-brightgreen)](#validation)

[**中文文档**](README.zh-CN.md) | [English](README.md)

[Quick Start](#quick-start) • [Why This Project Exists](#why-this-project-exists) • [What Makes It Different](#what-makes-it-different) • [Architecture](#architecture) • [Validation](#validation) • [Roadmap](#roadmap)

</div>

---

## What This Is

`archive-first-harness` is not trying to be a full AI agent platform on day one.

It is a deliberately narrow runtime harness built around one hard engineering question:

**when an agent run succeeds, fails, or regresses, can you explain why with evidence instead of intuition?**

The current answer is an archive-first execution model:

- keep the runtime chain conservative
- persist structured evidence for every run
- make runs readable and comparable after the fact
- improve the system through diagnostics instead of demo impressions

If you care more about repeatability, verification, and run-level evidence than about surface-level autonomy, this is the problem this repository is solving.

## Why This Project Exists

Many agent systems can look impressive in a demo but become hard to reason about in real work.

Typical questions are surprisingly hard to answer:

| Question | Why it matters |
|---|---|
| Why did this run fail? | Failure without localization is not actionable. |
| Where did it fail? | You need to know whether the issue was routing, execution, verification, or governance. |
| Why is this run worse than the previous one? | Without comparison, optimization becomes guesswork. |
| Did the run actually produce the expected artifact? | "Looks successful" is not enough. |
| What should be changed next? | Improvement needs evidence, not vibes. |

This repository exists to make those questions answerable.

## What Makes It Different

### 1. Archive-first, not demo-first

Each run is treated as an engineering event that should remain inspectable after execution.

### 2. Diagnostic evidence is a first-class output

Runs can persist structured files under `artifacts/runs/<run_id>/`, including:

- `manifest.json`
- `verification_report.json`
- `failure_signature.json`
- `execution_trace.jsonl`
- `final_output.json`

### 3. It supports a practical comparison loop

The current working loop is:

`run -> latest -> browse -> run-id -> compare`

That loop is much more useful in practice than reading raw JSON and guessing what changed.

### 4. The runtime core stays conservative

The project does not let evaluation or comparison silently turn into an opaque control plane. The execution path remains intentionally narrow and diagnosable.

### 5. Scope is intentionally constrained

This repository is delaying platform expansion on purpose. No database layer, no async worker system, no plugin marketplace, no premature multi-agent orchestration.

## Architecture

The current architecture is organized around a stable runtime core plus an evidence layer.

| Layer | Responsibility |
|---|---|
| `entrypoints/` | CLI surface, task runner, batch runner, history helpers, archive helpers |
| `runtime/` | Orchestrator, executor, verifier, routing, governance handoff |
| `harness/` | State, contracts, context, tools, journal, telemetry, evaluation plumbing |
| `planner/` | Task-contract and planning helpers |
| `tests/` | Unit, smoke, archive, history, and integration coverage |

### Runtime Flow

`request -> input normalization -> task contract -> state/context -> execution -> verification -> governance -> rollback when needed -> journal -> telemetry -> evaluation inputs`

### Archive Flow

`run -> write_run_archive(...) -> artifacts/runs/<run_id>/ -> archive --latest / --run-id / --compare-run-id`

### Design Principle

The system is trying to become a reliable substrate first, not a large platform first.

## Current Status

This repository is in **public alpha**.

What is already working:

- profile-aware task input normalization
- single-task CLI execution
- sequential batch execution
- append-only history and latest-run lookup
- archive writing for per-run evidence
- archive browsing by latest run or specific run id
- run-to-run comparison for diagnostic review

What is intentionally not done yet:

- hosted API service
- database-backed search
- async queue or worker layer
- plugin ecosystem
- large-scale multi-agent coordination

## Validation

The current build is not just documented; it has been exercised.

### Verified Results

- Local full test suite: `291` tests passed
- Real smoke flow validated across success, failure, governance-review, and coding-artifact scenarios
- `archive --latest`, `archive --run-id`, and `archive --compare-run-id` all verified on real runs
- External UAT showed the main friction is first-run shell entry, not the archive logic itself

### UAT Takeaway

The most important finding so far is simple:

**the archive loop is already useful, but the first-run experience still needs polishing.**

That is a good alpha-stage problem. It means the bottleneck is onboarding clarity rather than complete architectural failure.

## Quick Start

### Environment

- Recommended: Python `3.13.2`
- Current baseline runtime dependencies: **none**
- Current testing focus: Windows PowerShell and CMD

### Clone

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

### Expected First Run

For the `ping` task, you should see:

- a successful `run` result
- a new `run_id`
- a readable archive summary from `archive --latest`

For first-time evaluation, start with `archive --latest` instead of the full raw `run` output.

## Who This Is For

This project is a fit for:

- builders working on AI agent runtime quality
- developers who care about regression diagnosis
- teams that want run-level evidence before expanding architecture
- researchers exploring diagnosable and governable agent systems

It is not yet aimed at casual end users or production deployment teams.

## Documentation Map

Start here if you want the deeper project context:

- [Project Architecture, Status, and Roadmap](PROJECT_ARCHITECTURE_STATUS_AND_ROADMAP.md)
- [Archive Real Dev Smoke Test](docs/2026-04-02-archive-real-dev-smoke-test.md)
- [External UAT Quickstart](docs/2026-04-02-external-uat-quickstart.md)
- [M3 Hard Acceptance Checklist](docs/2026-04-02-m3-hard-acceptance-checklist.md)
- [Real Usage Diary Template](docs/2026-04-02-real-usage-diary-template.md)
- [Background and Paradigm Notes](docs/background/README.md)

## Roadmap

Near-term priorities are concrete:

1. reduce first-run friction for external testers
2. collect more public alpha usage feedback
3. improve archive signal-to-noise ratio
4. accumulate real usage diaries instead of more architectural speculation
5. hold the runtime boundary steady until repeated use proves the archive loop

## Public Alpha Note

If you test this repository, the most valuable feedback is not "looks cool."

The best feedback is:

- where you got stuck
- what output felt confusing
- whether `compare` changed your diagnosis
- whether archive browsing actually saved time

That is the feedback loop this project is built around.
