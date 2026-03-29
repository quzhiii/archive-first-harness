# AI Agent Runtime Harness

This repository contains a staged implementation skeleton for an AI agent runtime harness.
It remains intentionally narrow: the main path is runnable, inspectable, and easy to compare across versions.
It is not a full agent platform.

## Current Stable Slice

The frozen baseline is still `B v0.4` via `b-v0.4-baseline`.
On top of that baseline, the current stable recovery slice is a narrow `v0.5.x` layer focused on profile semantics and minimal external surface handling.

The current `v0.5.x` slice adds:

- `WorkflowProfile` with a default profile and a small set of built-in profiles
- `workflow_profile_id` carried through `TaskContract` and summarized into evaluator input
- shared profile-aware interpretation metadata for `BaselineComparator` and `RealmEvaluator`
- `profile_input_adapter` with fixed precedence and fallback rules
- `SurfaceTaskRequest` and `run_task_request(...)` as a thin external request surface
- a thin CLI surface that forwards profile-aware input through the same normalization path

This is still a conservative runtime harness. It does not implement HTTP serving, async workers, batch orchestration, auto-execution governance, or rich memory systems.

## Current Runtime Chain

The current execution and evaluation chain is:

`surface request / CLI -> profile_input_adapter -> task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

The chain remains deliberately single-path and advisory-only.

## Current Directory Shape

- `entrypoints/`: thin CLI, settings loader, and minimal task runner surface
- `planner/`: task contract builder and interviewer
- `runtime/`: orchestrator, executor, verifier, model router, methodology router
- `harness/contracts/`: workflow profiles and profile input normalization
- `harness/state/`: state models and state manager
- `harness/context/`: working context assembly
- `harness/tools/`: minimal tool discovery registry
- `harness/hooks/`: synchronous local hook orchestrator and payload contracts
- `harness/journal/`: minimal cross-task learning journal
- `harness/sandbox/`: stub isolation and rollback abstractions
- `harness/telemetry/`: local tracing and metrics aggregation
- `harness/evaluation/`: baseline compare, evaluator input bundle, profile interpretation, realm evaluator
- `tests/`: focused unit, smoke, and integration tests

## Freeze Status

- Base baseline tag: `b-v0.4-baseline`
- Current stable `v0.5.x` closeout tag: `b-v0.5-profile-surface`
- Base baseline closeout commit: `d03be5565642ce385cf529d9eb65ddb199d32215`
- Expected full-suite verification command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

- Expected current result at closeout: `Ran 198 tests`, `OK`

`v0.5.x` does not replace the meaning of the frozen `v0.4` baseline.
It is a narrow profile-aware extension layer on top of that baseline.

## Running The Minimal CLI

Basic single-task execution:

```bash
python -m entrypoints.cli run --task "Search docs for runtime context"
```

Profile-aware execution through the thin surface:

```bash
python -m entrypoints.cli run --task "Review runtime regression output" --task-type review --workflow-profile "evaluation regression"
```

Inspect persisted state summary:

```bash
python -m entrypoints.cli inspect-state
```

Inspect the latest task contract summary:

```bash
python -m entrypoints.cli inspect-contract
```

## Programmatic Surface

The minimal function-level surface is `run_task_request(...)`.
It accepts `SurfaceTaskRequest` and uses the same profile normalization path as the CLI.
It is intended for tests, automation, and future entry surfaces.
It is not an HTTP server.

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

`v0.5.x` does not introduce a new frozen baseline artifact pack.
It keeps the explicit `v0.3` comparison pack and adds profile-aware interpretation and surface handling on top of the existing runtime outputs.

## What The Current System Explicitly Does Not Do

The current version still does not implement:

- HTTP server / FastAPI shell
- batch runner or automation queue
- parallel worker pools or subagent runtime
- database-backed state
- async event bus / queue infrastructure
- plugin systems
- automatic model or methodology execution
- automatic governance override
- compare/evaluator-driven control flow
- journal ranking, forgetting, or semantic retrieval
- failure journal as a separate system
- complex recovery chains or transaction systems

## Suggested Next Direction

The next narrow, compatible extension is a `batch / automation-friendly surface` on top of the current function-level runner.
That is a smaller and safer step than adding an HTTP server shell immediately.
