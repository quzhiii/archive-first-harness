# archive-first-harness

English | [简体中文](README.zh-CN.md)

A diagnostic-first runtime harness for AI agents.

This project is built for one core purpose: turning AI agent execution from a demo-style black box into an inspectable, comparable, and governable engineering system.

It is intentionally narrow. It is not trying to be a full agent platform yet. Instead, it focuses on a stable runtime core plus an archive-first evidence layer that makes runs easier to inspect, compare, and improve over time.

## Why This Project Exists

Most AI agent systems share the same weakness:

- they can look impressive in demos
- they can appear highly capable on a single run
- but once they fail in real work, it becomes hard to answer simple questions

For example:

- Why did this run fail?
- Where exactly did it fail?
- Why is this run worse than the previous one?
- Did the run actually produce the expected artifact?
- Is the issue in the model, the tool call, the contract, the verification layer, or governance?

This repository exists to solve that class of problem.

## Core Value Proposition

This project is differentiated by engineering discipline, not surface feature count.

### 1. Diagnostic-first, not demo-first

Every run is treated as something that should be explainable after the fact, not just something that should look smart in the moment.

### 2. Archive-first evidence layer

Each run can persist structured evidence under `artifacts/runs/<run_id>/`, including contract, verification, evaluation, failure signature, and execution trace data.

### 3. Stable comparison loop

The practical loop is:

`run -> latest -> browse -> run-id -> compare`

This makes it possible to reason about regressions and improvements across runs without manually digging through raw JSON.

### 4. Conservative runtime core

The runtime remains intentionally single-path and advisory-first. It does not allow comparison or evaluation layers to silently become a control plane.

### 5. Built for iterative hardening

The goal is not to expand the boundary too early. The goal is to build a reliable substrate first, then expand with evidence.

## Current Architecture

The current boundary is deliberately simple and stable:

- `entrypoints/`: CLI surface, task runner, batch runner, history helpers, archive helpers
- `runtime/`: orchestrator, executor, verifier, model routing, methodology routing
- `harness/`: contracts, state, context, tools, hooks, journal, sandbox, telemetry, evaluation
- `planner/`: task contract and planning helpers
- `tests/`: focused unit, smoke, archive, history, and integration tests

### Runtime Flow

`surface request / CLI -> profile_input_adapter -> task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

### Archive Flow

`run -> write_run_archive(...) -> artifacts/runs/<run_id>/ -> archive --latest / --run-id / browse filters / --compare-run-id`

## Technology Direction

This project follows a staged technical strategy.

### Stage 1: Stabilize the runtime core

- keep the execution chain narrow
- keep responsibilities explicit
- keep failures diagnosable

### Stage 2: Build the archive evidence layer

- persist per-run artifacts
- make runs readable and comparable
- reduce regression diagnosis time

### Stage 3: Validate with real usage

- external UAT
- repeated real usage diaries
- hard acceptance checklist instead of subjective progress percentages

### Deferred on purpose

The following are intentionally deferred until the archive loop is proven in real work:

- HTTP / API server layer
- database-backed search or query DSL
- async queue / worker infrastructure
- plugin ecosystem
- replay / rerun orchestration
- large-scale multi-agent runtime expansion

## Current Status

This repository is currently at an alpha-stage validation phase.

### What is already working

- profile-aware task input normalization
- single-task surface via CLI and programmatic entrypoints
- sequential batch surface
- batch export artifacts
- append-only run history and latest-run shortcuts
- archive-first per-run diagnostic persistence
- archive browsing and comparison

### What has been validated

- real archive smoke flow across success, failure, governance-review, and coding-artifact scenarios
- full local test suite passing
- Windows-oriented CLI/UAT prep and shell-specific startup guidance

### Verified results

- Full test suite: `291` tests passed locally
- Archive smoke loop validated on real runs
- `archive --latest`, `archive --run-id`, and `archive --compare-run-id` all exercised on real diagnostic cases

## Strengths

Why this project may be useful to serious builders:

- It optimizes for explainability of runs, not only run completion
- It treats verification and governance as first-class concerns
- It makes artifact-level differences visible
- It is easier to reason about than larger systems that over-expand too early
- It creates a path toward future multi-agent coordination without starting with uncontrolled complexity

## Known Limitations

Current known issues and limitations:

- external UAT is still limited; usability is not yet broadly validated
- first-run setup on Windows requires shell-specific instructions
- raw `run` JSON is still heavier than ideal for first-time users
- the archive contract currently writes many files per run; signal-to-noise ratio still needs more validation through repeated use
- this is not yet a hosted product or production platform

## Quick Start

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

### Expected first-run outcome

For the `ping` task, you should see:

- a successful JSON result from `run`
- a new `run_id`
- a readable latest archive summary from `archive --latest`

Important: for first-time evaluation, do not spend time reading the full raw `run` JSON. Start with `archive --latest` first.

## Recommended Read Order

If you are evaluating the repository seriously, read these files in order:

1. `README.md`
2. `README.zh-CN.md`
3. `PROJECT_ARCHITECTURE_STATUS_AND_ROADMAP.md`
4. `docs/2026-04-02-archive-real-dev-smoke-test.md`
5. `docs/2026-04-02-external-uat-quickstart.md`
6. `docs/2026-04-02-m3-hard-acceptance-checklist.md`

## Who This Is For

This repository is best suited for:

- builders working on AI agent runtime quality
- developers who care about regression diagnosis
- teams that want run-level evidence before expanding architecture
- people exploring how to make AI agent systems more inspectable and governable

It is not yet aimed at casual end users.

## Roadmap

Near-term focus:

1. improve first-run usability
2. complete external UAT with real users
3. accumulate real usage diary evidence
4. improve archive signal-to-noise ratio
5. validate repeated-run stability before boundary expansion

## Testing & Validation Materials

Relevant documents:

- `tests/uat_results/observation_logs/2026-04-02-pre-check-report.md`
- `tests/uat_results/observation_logs/2026-04-02-uat-observation-summary.md`
- `tests/uat_results/reports/2026-04-02-cli-cross-platform-compatibility.md`
- `docs/2026-04-02-archive-real-dev-smoke-test.md`
- `docs/2026-04-02-m3-hard-acceptance-checklist.md`

## Alpha Notice

This is an alpha-stage engineering repository.

If you want to test it, the most useful feedback is not “this looks cool,” but concrete observations such as:

- where you got stuck
- which field names were confusing
- whether `compare` changed your diagnosis or decision
- whether the archive output saved time

That kind of feedback is what this repository is designed to turn into real improvements.
