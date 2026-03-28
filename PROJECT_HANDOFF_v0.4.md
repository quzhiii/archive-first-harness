# PROJECT_HANDOFF_v0.4

This file is a compact handoff note for continuing the AI agent runtime harness in a new chat, a new model, or another coding agent such as Claude Code.

## 1. Current Snapshot

- Project: `AI agent runtime harness`
- Architecture boundary: `entrypoints/ -> runtime/ -> harness/`
- Current committed baseline: `B v0.3`
- Git tag: `b-v0.3-baseline`
- Current `HEAD`: `385d669` (`Freeze B v0.3 baseline`)
- Important status: `v0.4` work exists in the working tree and is not committed yet

## 2. What Is Already Done

### v0.1
- Minimal runnable skeleton
- Task contract builder, state models, state manager, context engine
- Tool discovery, orchestrator, executor
- Verifier, sandbox stub, rollback stub, telemetry, metrics, realm evaluator, CLI, README
- Integration smoke and baseline artifacts for v0.1

### v0.2
- `ModelRouter`
- `MethodologyRouter`
- Minimal residual-risk loop
- `Interviewer`
- `task_id` / `contract_id` split
- Minimal residual writeback into `task_block`
- Minimal learning journal read/write integration

### v0.3
- `HookOrchestrator`
- Minimal hook event set and payload contracts
- Eventized advisory chain:
  - verification report
  - residual follow-up
  - governance check
- Conditional sandbox gating and minimal rollback
- Journal write timing unified at `on_journal_append`
- v0.3 smoke scenarios and baseline artifacts
- v0.3 freeze docs and tag

## 3. What Has Been Implemented In v0.4 So Far

### v0.4 Round 1: Learning Journal Quality Control
Status: implemented in working tree, not committed

Files:
- `harness/journal/learning_journal.py`
- `tests/test_learning_journal_quality_control.py`

Key behavior:
- `active` / `archived` split
- fingerprint-based dedup
- TTL-based expiry -> archive, not delete
- default reads exclude archived
- low-confidence and duplicate entries can be archived
- journal boundary remains narrow and does not mirror runtime/state objects

### v0.4 Round 2: Baseline Compare / Regression Diff
Status: implemented in working tree, not committed

Files:
- `harness/evaluation/baseline_compare.py`
- `tests/test_baseline_compare.py`

Key behavior:
- explicit baseline JSON loading only
- supports:
  - `verification_report`
  - `residual_followup`
  - `metrics_summary`
  - `event_trace`
  - `journal_append_trace`
- outputs structured diff with:
  - `artifact_type`
  - `status`
  - `missing_fields`
  - `unexpected_fields`
  - `type_mismatches`
  - `value_drifts`
  - `summary`
  - `reason_codes`
- drift classes:
  - `compatible`
  - `warning`
  - `breaking`

### v0.4 Round 3: Block-Level Context Selection Refinement
Status: implemented in working tree, not committed

Files:
- `harness/context/context_engine.py`
- `tests/test_context_block_selection.py`

Key behavior:
- explicit context block sources:
  - `task_contract`
  - `task_block`
  - `distilled_summary`
  - `residual_state`
  - `project_block`
  - `global_state`
  - `journal_lessons_active`
- explicit priority ordering
- archived journal lessons excluded by default even if passed in
- residual state only enters when actionable / decision-relevant
- selection report available via `build_block_selection_report(...)`
- working context remains small and explainable

### v0.4 Round 4: Evaluator Input Unification
Status: implemented in working tree, not committed

Files:
- `harness/evaluation/evaluation_input.py`
- `harness/evaluation/realm_evaluator.py`
- `harness/evaluation/baseline_compare.py`
- `tests/test_evaluation_input_bundle.py`

Key behavior:
- introduces `EvaluationInputBundle`
- adds pure builders:
  - `build_evaluation_input_bundle(...)`
  - `summarize_task_contract(...)`
  - `summarize_event_trace(...)`
  - `summarize_journal_append_trace(...)`
- keeps evaluator input boundary explicit:
  - `verification_report` / `residual_followup` / `metrics_summary` / `block_selection_report` remain structured artifacts
  - `event_trace` / `journal_append_trace` enter the bundle only as summaries
  - `task_contract` enters only as a small summary, not a full mirror
- adds lightweight adapters:
  - `to_baseline_artifacts(bundle)`
  - `RealmEvaluator.evaluate_bundle(bundle)`
  - `BaselineComparator.compare_bundle_artifact(bundle, ...)`
- does not modify orchestrator control flow or widen runtime semantics

### v0.4 Round 5: Runtime Evaluation Integration
Status: implemented in working tree, not committed

Files:
- `runtime/orchestrator.py`
- `tests/test_runtime_evaluation_integration.py`

Key behavior:
- orchestrator now builds `evaluation_input_bundle` after verification, residual follow-up, writeback, and journal append have already settled
- real runs now expose stable evaluation-facing outputs:
  - `block_selection_report`
  - `metrics_summary`
  - `evaluation_input_bundle`
  - `baseline_compare_results`
  - `realm_evaluation`
- baseline compare and realm evaluator now consume the same bundle base during a real runtime run
- compare and evaluator remain advisory-only and do not alter execution flow, sandbox gating, or follow-up routing
- missing optional inputs remain stable:
  - no journal append trace -> bundle still builds
  - no block selection report builder -> bundle still builds with an empty report

## 4. Current Working Tree Changes

At the time of writing, `git status --short` shows:

- modified: `harness/context/context_engine.py`
- modified: `harness/evaluation/realm_evaluator.py`
- modified: `harness/journal/learning_journal.py`
- modified: `runtime/orchestrator.py`
- untracked: `PROJECT_HANDOFF_v0.4.md`
- untracked: `harness/evaluation/baseline_compare.py`
- untracked: `harness/evaluation/evaluation_input.py`
- untracked: `tests/test_baseline_compare.py`
- untracked: `tests/test_context_block_selection.py`
- untracked: `tests/test_evaluation_input_bundle.py`
- untracked: `tests/test_learning_journal_quality_control.py`
- untracked: `tests/test_runtime_evaluation_integration.py`

Interpretation:
- v0.3 is frozen and committed
- v0.4.1 / v0.4.2 / v0.4.3 / v0.4.4 / v0.4.5 are implemented locally but not yet frozen or tagged

## 5. Current Verification State

Last verified command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Last known result:

- `Ran 172 tests`
- `OK`

Focused verification also passed:

```bash
python -m unittest tests.test_learning_journal_quality_control
python -m unittest tests.test_baseline_compare
python -m unittest tests.test_context_block_selection
python -m unittest tests.test_evaluation_input_bundle
python -m unittest tests.test_realm_evaluator
python -m unittest tests.test_runtime_evaluation_integration
```

This means the current working tree is test-green despite being ahead of the `b-v0.3-baseline` commit.

## 6. Important Files To Read First

If another agent takes over, read these first:

1. `README.md`
2. `KNOWN_GAPS_v0.1.md`
3. `KNOWN_GAPS_v0.2.md`
4. `KNOWN_GAPS_v0.3.md`
5. `harness/context/context_engine.py`
6. `harness/journal/learning_journal.py`
7. `harness/evaluation/baseline_compare.py`
8. `harness/evaluation/evaluation_input.py`
9. `harness/evaluation/realm_evaluator.py`
10. `runtime/orchestrator.py`
11. `tests/test_learning_journal_quality_control.py`
12. `tests/test_baseline_compare.py`
13. `tests/test_context_block_selection.py`
14. `tests/test_evaluation_input_bundle.py`
15. `tests/test_runtime_evaluation_integration.py`

## 7. Architecture Rules That Must Still Be Preserved

- Keep the one-way boundary: `entrypoints/ -> runtime/ -> harness/`
- Do not let `harness/` depend on `entrypoints/`
- Do not turn hooks into a new control plane
- Do not turn journal into:
  - task state
  - distilled summary
  - failure journal
  - residual history
  - sandbox / rollback log store
- Do not let archived journal lessons re-enter `working_context` by default
- Do not let `working_context` become an undifferentiated dump
- Keep methodology/model advice advisory-only unless a future round explicitly changes that
- Keep evaluator input unification as a read-only / summary-only layer, not a new runtime state system
- Keep compare/evaluator outputs advisory-only after runtime integration

## 8. Explicit Non-Goals Still In Force

Still not implemented, by design:

- parallel worker / subagent runtime
- async event bus / queue platform
- database-backed state
- semantic retrieval
- embedding / vector store
- complex ranking models
- failure journal as a separate subsystem
- automatic methodology execution
- automatic model execution
- automatic governance override
- complex recovery engine / transaction rollback
- dashboard / observability platform
- CLI / surface wrappers for the v0.4 evaluator bundle
- automatic compare gating or runtime rerouting from evaluator output
- v0.5 abilities

## 9. Baseline / Artifact Notes

### v0.3 freeze baseline
- directory: `artifacts/baselines/v03`
- baseline rule: only top-level `*.json` are part of the frozen baseline set
- ignore temporary directories and non-JSON spillover

### Known temp-dir quirk
- there was a problematic inaccessible temp directory under `artifacts/baselines/v03/`
- the repo-level rule is to ignore temp spillover and compare only explicit top-level JSON baselines
- do not introduce privileged cleanup steps unless there is a real need

## 10. Recommended Next Step For A New Agent

Recommended next move: freeze the current v0.4 progress before expanding scope again.

Suggested steps:
1. inspect `git diff`
2. re-run full tests
3. commit the v0.4.1 / v0.4.2 / v0.4.3 / v0.4.4 / v0.4.5 work
4. optionally create a new checkpoint tag or freeze note
5. only then continue with the next v0.4 round

## 11. Minimal Resume Commands

```bash
git status --short
git log --oneline --decorate -n 5
python -m unittest discover -s tests -p "test_*.py"
```

For focused verification of the current uncommitted v0.4 work:

```bash
python -m unittest tests.test_learning_journal_quality_control
python -m unittest tests.test_baseline_compare
python -m unittest tests.test_context_block_selection
python -m unittest tests.test_evaluation_input_bundle
python -m unittest tests.test_realm_evaluator
python -m unittest tests.test_runtime_evaluation_integration
```

## 12. Short Human Summary

The project is stable through `v0.3` and frozen at tag `b-v0.3-baseline`.
The current working tree already contains five additional `v0.4` slices that are implemented and green:
- journal quality control
- baseline comparison
- finer block-level context selection
- evaluator input unification
- runtime evaluation integration

Nothing in the current state suggests a broken main path.
The biggest practical handoff fact is still this:
`v0.4` progress exists, passes tests, but has not been committed yet.
