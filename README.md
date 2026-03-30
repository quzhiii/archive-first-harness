# AI Agent Runtime Harness

This repository contains a staged implementation skeleton for an AI agent runtime harness.
It remains intentionally narrow: the main path is runnable, inspectable, and easy to compare across versions.
It is not a full agent platform.

## Current Stable Slice

The frozen baseline is still `B v0.4` via `b-v0.4-baseline`.
On top of that baseline, the current stable recovery slice is a narrow `v0.5.x` layer focused on profile semantics, sequential batch execution, stable export artifacts, and a thin manifest-derived history summary layer.

The current `v0.5.x` slice adds:

- `WorkflowProfile` with a default profile and a small set of built-in profiles
- `workflow_profile_id` carried through `TaskContract` and summarized into evaluator input
- shared profile-aware interpretation metadata for `BaselineComparator` and `RealmEvaluator`
- `profile_input_adapter` with fixed precedence and fallback rules
- `SurfaceTaskRequest` and `run_task_request(...)` as a thin external request surface
- `SurfaceBatchRequest`, `run_batch_request(...)`, and `load_batch_request_file(...)` as a thin sequential batch surface
- `BatchExportOptions` and `export_batch_results(...)` as a thin export layer for batch artifacts
- `RunHistoryEntry`, `append_run_history_entry(...)`, and `list_run_history(...)` as an append-only export history manifest layer
- `RunHistorySummaryEntry`, `write_latest_run_pointer(...)`, and `write_run_history_summary(...)` as a thin latest-run pointer and recent-history summary layer
- a thin CLI surface that forwards batch execution, export, history, and summary options through the same outer entry path

This is still a conservative runtime harness. It does not implement HTTP serving, async workers, queue orchestration, auto-execution governance, or rich memory systems.

## Current Runtime Chain

The current execution and evaluation chain is still single-path inside the runtime:

`surface request / CLI -> profile_input_adapter -> task contract -> state manager -> context engine -> execution -> verification -> residual follow-up -> governance -> conditional sandbox -> rollback when needed -> journal append -> telemetry/metrics -> evaluation input bundle -> baseline compare / realm evaluator`

The current batch, export, and history path is only a thin outer layer:

`batch request / --batch-file -> SurfaceBatchRequest -> run_batch_request(...) -> repeated run_task_request(...) -> export_batch_results(...) -> append_run_history_entry(...) -> write_latest_run_pointer(...) / write_run_history_summary(...)`

The chain remains deliberately advisory-only.

## Current Directory Shape

- `entrypoints/`: thin CLI, settings loader, single-task runner, minimal batch runner surface, batch export helper, run history manifest helper, and history summary helper
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
- `tests/`: focused unit, smoke, integration, batch surface, export, run history, and history summary tests

## Freeze Status

- Base baseline tag: `b-v0.4-baseline`
- Intermediate `v0.5.x` profile-aware surface tag: `b-v0.5-profile-surface`
- Intermediate `v0.5.x` batch surface tag: `b-v0.5-batch-surface`
- Intermediate `v0.5.x` batch export tag: `b-v0.5-batch-export`
- Current stable `v0.5.x` history summary closeout tag: `b-v0.5-history-summary`
- Base baseline closeout commit: `d03be5565642ce385cf529d9eb65ddb199d32215`
- Expected full-suite verification command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

- Expected current result at closeout: `Ran 226 tests`, `OK`

`v0.5.x` does not replace the meaning of the frozen `v0.4` baseline.
It is a narrow profile-aware, batch-capable, export-capable, and history-summary-capable outer surface layer on top of that baseline.

## Running The Minimal CLI

Basic single-task execution:

```bash
python -m entrypoints.cli run --task "Search docs for runtime context"
```

Sequential batch execution from a JSON or JSONL file:

```bash
python -m entrypoints.cli run --batch-file tasks.json
```

Sequential batch execution with default export artifacts plus default history manifest and latest-run pointer:

```bash
python -m entrypoints.cli run --batch-file tasks.json --output-dir exports
```

Sequential batch execution with a compact recent-history summary:

```bash
python -m entrypoints.cli run --batch-file tasks.json --output-dir exports --write-history-summary --history-summary-limit 10
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

The minimal function-level surfaces are:

- `run_task_request(...)` for a single `SurfaceTaskRequest`
- `run_batch_request(...)` for a sequential `SurfaceBatchRequest`
- `load_batch_request_file(...)` for `.json` and `.jsonl` batch request files
- `BatchExportOptions` for thin export configuration
- `export_batch_results(...)` for writing stable batch artifacts
- `append_run_history_entry(...)` and `list_run_history(...)` for append-only export history
- `write_latest_run_pointer(...)` and `write_run_history_summary(...)` for derived history files

The append-only truth source is `run_history.jsonl`.
`latest_run.json` and `run_history_summary.json` are derived files only.
They do not rewrite batch, export, or runtime payloads.
This surface is intended for tests, automation, and future entry surfaces.
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
It keeps the explicit `v0.3` comparison pack and adds profile-aware interpretation plus minimal single-task, batch, export, history, and history-summary surface handling on top of the existing runtime outputs.

## What The Current System Explicitly Does Not Do

The current version still does not implement:

- HTTP server / FastAPI shell
- queue / scheduler / async worker infrastructure
- batch-driven adaptive replanning or cross-task mutation
- history browsing or latest-run convenience commands
- artifact search or filter engine
- database-backed state
- full-text search or query DSL
- report templating engines or dashboard systems
- parallel worker pools or subagent runtime
- async event bus / queue infrastructure
- plugin systems
- automatic model or methodology execution
- automatic governance override
- compare/evaluator-driven control flow
- journal ranking, forgetting, or semantic retrieval
- failure journal as a separate system
- complex recovery chains or transaction systems

## Suggested Next Direction

The next narrow, compatible extension is `history browsing / latest-run convenience commands`.

Reason:

- the history summary layer already produces stable manifest-derived files
- browsing/convenience commands extend the current outer history layer without expanding runtime control semantics
- it is a smaller and safer step than adding an HTTP server shell immediately

A minimal HTTP/API server shell is now feasible, but it is still the larger next step and should stay out of this checkpoint.
