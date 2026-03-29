# PROJECT_HANDOFF_v0.5

This handoff is the canonical resume note for continuing the AI agent runtime harness from the narrow `v0.5.x` profile-aware surface checkpoint in a new chat, a new model, or another coding agent such as Claude Code or OpenCode.

## 1. Current Snapshot

- Project: `AI agent runtime harness`
- Architecture boundary: `entrypoints/ -> runtime/ -> harness/`
- Base frozen baseline: `B v0.4` via `b-v0.4-baseline`
- Current stable continuation slice: narrow `v0.5.x` profile-aware surface layer
- Stable tags:
  - `b-v0.3-baseline`
  - `b-v0.4-baseline`
  - `b-v0.5-profile-surface`
- Current `HEAD`: the tagged `v0.5.x` closeout checkpoint commit
- Working tree expectation after closeout: clean
- Full-suite verification command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

- Expected closeout result: `Ran 198 tests`, `OK`
- Resume point lineage: this checkpoint is built on top of `b-v0.4-baseline`, not as a replacement for it

## 2. What Has Been Added Since v0.4

### A. Workflow Profile Minimal Layer

Added narrow task-semantic profile support without creating a controller:

- `WorkflowProfile`
- default profile plus a small built-in profile set
- `workflow_profile_id` carried into `TaskContract`
- `task_contract_summary` now includes minimal profile semantics:
  - `workflow_profile_id`
  - `intent_class`
  - `success_focus`
- `ContextEngine` applies only lightweight profile bias for block ordering and preference

Key files:
- `harness/contracts/workflow_profile.py`
- `harness/state/models.py`
- `planner/task_contract_builder.py`
- `harness/context/context_engine.py`
- `harness/evaluation/evaluation_input.py`
- `tests/test_workflow_profile.py`

### B. Profile-Aware Interpretation Layer

Added a shared interpretation helper so compare/evaluator look at the same profile semantics:

- `ProfileInterpretation`
- `build_profile_interpretation(...)`
- `BaselineComparator` now emits profile-aware metadata and calibrated summaries
- `RealmEvaluator` now uses the same interpretation source

Key files:
- `harness/evaluation/profile_interpretation.py`
- `harness/evaluation/baseline_compare.py`
- `harness/evaluation/realm_evaluator.py`
- `tests/test_profile_interpretation.py`
- `tests/test_baseline_compare.py`
- `tests/test_realm_evaluator.py`
- `tests/test_runtime_evaluation_integration.py`

### C. Profile Input Adapter / Surface Normalization

Added a thin external-input normalization layer so profile aliases no longer drift across entry surfaces:

- `profile_input_adapter.py`
- `ProfileInputResolution`
- fixed precedence and fallback rules
- `TaskContractBuilder` now consumes normalized `workflow_profile_id` instead of maintaining its own alias parsing logic

Supported external fields:
- `workflow_profile_id`
- `workflow_profile`
- `mission_profile_id`
- `task_type` for conservative fallback only

Key files:
- `harness/contracts/profile_input_adapter.py`
- `planner/task_contract_builder.py`
- `tests/test_profile_input_adapter.py`
- `tests/test_task_contract_builder.py`

### D. Minimal CLI / Task Runner Surface

Added a thin external surface that still routes through the same normalized path:

- `SurfaceTaskRequest`
- `run_task_request(...)`
- profile-aware CLI arguments on the existing thin CLI
- external input path now becomes:
  - CLI / function request
  - `profile_input_adapter`
  - `TaskContractBuilder`
  - existing runtime/orchestrator
  - existing evaluation outputs

Key files:
- `entrypoints/task_runner.py`
- `entrypoints/cli.py`
- `tests/test_surface_task_runner.py`
- `tests/test_cli_smoke.py`
- `tests/test_integration_smoke.py`

## 3. What Did NOT Change

These boundaries are still intentionally preserved:

- `runtime/orchestrator.py` control semantics remain single-path and conservative
- compare/evaluator root rules did not become gates or controllers
- no new control plane was introduced
- no journal/context/evaluation boundary expansion was introduced
- archived lessons still do not flow back into ordinary working context by default
- `EvaluationInputBundle` is still a read-only evaluation surface, not a config/state dump
- no HTTP server / FastAPI shell was added
- no batch worker / queue / async runtime was added

## 4. Verification State

Primary verification command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Expected closeout result:

- `Ran 198 tests`
- `OK`

Focused tests that cover the `v0.5.x` slice:

```bash
python -m unittest discover -s tests -p "test_workflow_profile.py"
python -m unittest discover -s tests -p "test_profile_interpretation.py"
python -m unittest discover -s tests -p "test_profile_input_adapter.py"
python -m unittest discover -s tests -p "test_surface_task_runner.py"
python -m unittest discover -s tests -p "test_runtime_evaluation_integration.py"
```

## 5. Stable Resume Guidance

Use `b-v0.4-baseline` when:

- you want the hardening baseline before profile semantics were introduced
- you need to compare against the narrow v0.4 runtime/evaluation chain only
- you want the smallest already-frozen recovery point

Use `b-v0.5-profile-surface` when:

- you need `WorkflowProfile` semantics
- you need profile-aware compare/evaluator metadata
- you need stable profile input normalization
- you want to enter the system through the minimal task runner / CLI surface

In short:
- `v0.4` is the last profile-agnostic frozen baseline
- `v0.5.x` is the narrow stable restore point for profile-aware work

## 6. Important Files To Read First

If another agent takes over from this checkpoint, read these first:

1. `README.md`
2. `PROJECT_HANDOFF_v0.4.md`
3. `PROJECT_HANDOFF_v0.5.md`
4. `harness/contracts/workflow_profile.py`
5. `harness/contracts/profile_input_adapter.py`
6. `harness/evaluation/profile_interpretation.py`
7. `harness/evaluation/baseline_compare.py`
8. `harness/evaluation/evaluation_input.py`
9. `harness/evaluation/realm_evaluator.py`
10. `planner/task_contract_builder.py`
11. `entrypoints/task_runner.py`
12. `entrypoints/cli.py`
13. `runtime/orchestrator.py`
14. `tests/test_workflow_profile.py`
15. `tests/test_profile_interpretation.py`
16. `tests/test_profile_input_adapter.py`
17. `tests/test_surface_task_runner.py`
18. `tests/test_runtime_evaluation_integration.py`

## 7. Recommended Next Step

The next most compatible direction is:

### `batch / automation-friendly surface`

Reason:
- the current function-level surface is already in place
- batch / automation reuse extends the same request normalization path
- it preserves the current non-server boundary
- it is a smaller semantic step than introducing an HTTP/API server shell immediately

A minimal HTTP/API server shell is now feasible, but it is the larger next step and should stay out of this closeout.

## 8. Short Human Summary

`v0.5.x` is now a stable, narrow continuation layer on top of the frozen `v0.4` baseline.

What was added is not a bigger runtime controller.
It is a controlled profile-aware slice:
- profile semantics
- shared interpretation metadata
- stable profile input normalization
- a thin external surface through function call and CLI

The most important operational fact for a new agent is this:
resume from `b-v0.5-profile-surface` if the work depends on profile-aware input, interpretation, or surface handling; otherwise resume from `b-v0.4-baseline`.
