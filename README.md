# AI Agent Runtime Harness

This repository contains a staged implementation skeleton for an AI agent runtime harness.
It is not a full agent platform. The current baseline is intentionally narrow so the main path stays runnable,
inspectable, and easy to compare across versions.

## Current Baseline

The current frozen baseline is `B v0.4`.
It preserves the v0.1 minimal runtime chain, keeps the v0.2 routing and residual-risk extensions,
keeps the v0.3 evented integration layer, and adds the narrow v0.4 hardening slices:

- learning journal quality control with `active` / `archived`, dedup, and TTL-based archiving
- baseline compare / regression diff for key runtime artifacts
- finer block-level context selection with explicit inclusion rules
- `EvaluationInputBundle` as a shared evaluator input base
- minimal runtime wiring for bundle production, baseline compare, and realm evaluation

This is still a conservative runtime harness. It does not implement a full async event platform,
auto-execution governance, workflow-profile control logic, or rich memory systems.

## Minimal Runtime Chain

The current v0.4 integration chain is:

`task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

The chain remains deliberately single-path and conservative.

## Current Directory Shape

- `entrypoints/`: thin CLI and settings loader
- `planner/`: task contract builder and interviewer
- `runtime/`: orchestrator, executor, verifier, model router, methodology router
- `harness/state/`: state models and state manager
- `harness/context/`: working context assembly
- `harness/tools/`: minimal tool discovery registry
- `harness/hooks/`: synchronous local hook orchestrator and payload contracts
- `harness/journal/`: minimal cross-task learning journal
- `harness/sandbox/`: stub isolation and rollback abstractions
- `harness/telemetry/`: local tracing and metrics aggregation
- `harness/evaluation/`: rule-based evaluation suggestion
- `tests/`: focused unit and smoke tests

## v0.4 Freeze Status

- Freeze date: `2026-03-29`
- Tested Python version: `3.13.2`
- Baseline tag: `b-v0.4-baseline`
- v0.4 checkpoint commit: `d263cba9d3196453b7abc4cc4836532eaaee716a`
- Frozen comparison artifacts directory: `artifacts/baselines/v03`

`v0.4` is frozen as the narrow hardening baseline on top of `v0.3`.
Regression comparison still uses the explicit samples in `artifacts/baselines/v03`;
`v0.4` adds stable runtime evaluation outputs rather than a second frozen artifact pack.

## Running the Minimal CLI

The CLI remains a thin local entrypoint for the minimal harness path:

```bash
python -m entrypoints.cli run "Search docs for runtime context"
```

Inspect persisted state summary:

```bash
python -m entrypoints.cli inspect-state
```

Inspect the latest task contract summary:

```bash
python -m entrypoints.cli inspect-contract
```

## Running v0.3 Smoke Tests

Run the v0.3 integration smoke scenarios:

```bash
python -m unittest tests.test_v03_integration_smoke
```

Run the full suite:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Baseline Artifacts

The frozen comparison samples are still stored under `artifacts/baselines/v03`:

- `success_event_trace.json`
- `sandbox_success_trace.json`
- `rollback_path_trace.json`
- `governance_followup_trace.json`
- `journal_append_trace.json`
- `success_verification_report.json`
- `success_residual_followup.json`
- `success_metrics_summary.json`

Baseline collection rule:

- only top-level `*.json` files in `artifacts/baselines/v03` are part of the frozen baseline
- ignore temporary directories and non-JSON spillover under that directory
- future baseline diffs should enumerate these JSON files directly or glob only top-level `*.json`

`v0.4` does not add a frozen `artifacts/baselines/v04` directory.
Instead, real orchestrator runs now expose stable evaluation-facing outputs such as:

- `block_selection_report`
- `metrics_summary`
- `evaluation_input_bundle`
- `baseline_compare_results`
- `realm_evaluation`

## What v0.4 Explicitly Does Not Do

The current version does not implement:

- parallel worker pools or subagent runtime
- database-backed state
- async queue or full event bus infrastructure
- plugin systems
- automatic model or methodology execution
- automatic governance override
- journal ranking, forgetting, or semantic retrieval
- failure journal as a separate system
- complex recovery chains or transaction systems
- automatic retirement flows
- `workflow_profile` / `mission_profile`

## What Later Versions May Add

Later versions may extend this skeleton with:

- a minimal profile layer for task-type semantics
- stronger hook consumers and richer event-driven coordination
- more mature recovery controls
- broader governance and execution policy layers

Those upgrades are intentionally outside the frozen v0.4 scope.
