# PROJECT_HANDOFF_v0.4

This handoff is the canonical resume note for continuing the AI agent runtime harness from the frozen `v0.4` baseline in a new chat, a new model, or another coding agent such as Claude Code.

## 1. Current Snapshot

- Project: `AI agent runtime harness`
- Architecture boundary: `entrypoints/ -> runtime/ -> harness/`
- Current frozen baseline: `B v0.4`
- Stable tags:
  - `b-v0.3-baseline`
  - `b-v0.4-baseline`
- `v0.4` checkpoint commit: `d263cba9d3196453b7abc4cc4836532eaaee716a` (`Checkpoint v0.4 rounds 1-5`)
- Current `HEAD`: this closeout baseline commit
- Working tree expectation: clean
- Full-suite verification: `python -m unittest discover -s tests -p "test_*.py"` -> `Ran 172 tests`, `OK`

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

## 3. What Has Been Implemented In v0.4

All `v0.4` rounds below are committed and frozen at the `B v0.4` baseline.

### v0.4 Round 1: Learning Journal Quality Control
Status: committed / frozen

Files:
- `harness/journal/learning_journal.py`
- `tests/test_learning_journal_quality_control.py`

Key behavior:
- `active` / `archived` split
- Fingerprint-based dedup
- TTL-based expiry archives instead of deleting
- Default reads exclude archived lessons
- Low-confidence and duplicate entries can be archived

Boundaries preserved:
- Journal remains a lesson store, not task state, residual history, or sandbox / rollback logs
- Archived lessons do not re-enter normal working context by default

### v0.4 Round 2: Baseline Compare / Regression Diff
Status: committed / frozen

Files:
- `harness/evaluation/baseline_compare.py`
- `tests/test_baseline_compare.py`

Key behavior:
- Explicit baseline JSON loading only
- Supports:
  - `verification_report`
  - `residual_followup`
  - `metrics_summary`
  - `event_trace`
  - `journal_append_trace`
- Outputs a structured diff with:
  - `artifact_type`
  - `status`
  - `missing_fields`
  - `unexpected_fields`
  - `type_mismatches`
  - `value_drifts`
  - `summary`
  - `reason_codes`
- Drift classes:
  - `compatible`
  - `warning`
  - `breaking`

Boundaries preserved:
- Compare output is advisory-only
- No dashboard, gatekeeping pipeline, or runtime control hook was introduced

### v0.4 Round 3: Block-Level Context Selection Refinement
Status: committed / frozen

Files:
- `harness/context/context_engine.py`
- `tests/test_context_block_selection.py`

Key behavior:
- Explicit context block sources:
  - `task_contract`
  - `task_block`
  - `distilled_summary`
  - `residual_state`
  - `project_block`
  - `global_state`
  - `journal_lessons_active`
- Explicit priority ordering and pruning
- Archived journal lessons excluded by default
- Residual state only enters when decision-relevant
- Selection report exposed via `build_block_selection_report(...)`

Boundaries preserved:
- `working_context` stays small and explainable
- State, summary, journal, and residual remain separated instead of collapsing into a dump

### v0.4 Round 4: Evaluator Input Unification
Status: committed / frozen

Files:
- `harness/evaluation/evaluation_input.py`
- `harness/evaluation/realm_evaluator.py`
- `harness/evaluation/baseline_compare.py`
- `tests/test_evaluation_input_bundle.py`

Key behavior:
- Introduces `EvaluationInputBundle`
- Adds pure builders:
  - `build_evaluation_input_bundle(...)`
  - `summarize_task_contract(...)`
  - `summarize_event_trace(...)`
  - `summarize_journal_append_trace(...)`
- Keeps the evaluator input boundary explicit:
  - `verification_report` / `residual_followup` / `metrics_summary` / `block_selection_report` remain structured artifacts
  - `event_trace` / `journal_append_trace` enter only as summaries
  - `task_contract` enters only as a small summary, not a full mirror
- Adds lightweight adapters:
  - `to_baseline_artifacts(bundle)`
  - `RealmEvaluator.evaluate_bundle(bundle)`
  - `BaselineComparator.compare_bundle_artifact(bundle, ...)`

Boundaries preserved:
- Bundle is a read-only evaluation surface, not a new runtime state layer
- Hooks, traces, and contracts were not expanded into dumps

### v0.4 Round 5: Runtime Evaluation Integration
Status: committed / frozen

Files:
- `runtime/orchestrator.py`
- `tests/test_runtime_evaluation_integration.py`

Key behavior:
- Orchestrator builds `evaluation_input_bundle` only after verification, residual follow-up, writeback, and journal append have settled
- Real runs now expose stable evaluation-facing outputs:
  - `block_selection_report`
  - `metrics_summary`
  - `evaluation_input_bundle`
  - `baseline_compare_results`
  - `realm_evaluation`
- Baseline compare and realm evaluator consume the same bundle base during a real run
- Missing optional inputs remain stable:
  - no journal append trace -> bundle still builds
  - no block selection report -> bundle still builds with an empty report

Boundaries preserved:
- Compare and evaluator remain advisory-only
- Runtime control flow, sandbox gating, and follow-up routing stay unchanged

## 4. Current Verification State

Baseline verification command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Current result:

- `Ran 172 tests`
- `OK`

Focused verification that should still pass:

```bash
python -m unittest tests.test_learning_journal_quality_control
python -m unittest tests.test_baseline_compare
python -m unittest tests.test_context_block_selection
python -m unittest tests.test_evaluation_input_bundle
python -m unittest tests.test_realm_evaluator
python -m unittest tests.test_runtime_evaluation_integration
```

## 5. Important Files To Read First

If another agent takes over, read these first:

1. `README.md`
2. `KNOWN_GAPS_v0.1.md`
3. `KNOWN_GAPS_v0.2.md`
4. `KNOWN_GAPS_v0.3.md`
5. `PROJECT_HANDOFF_v0.4.md`
6. `harness/context/context_engine.py`
7. `harness/journal/learning_journal.py`
8. `harness/evaluation/baseline_compare.py`
9. `harness/evaluation/evaluation_input.py`
10. `harness/evaluation/realm_evaluator.py`
11. `runtime/orchestrator.py`
12. `tests/test_learning_journal_quality_control.py`
13. `tests/test_baseline_compare.py`
14. `tests/test_context_block_selection.py`
15. `tests/test_evaluation_input_bundle.py`
16. `tests/test_runtime_evaluation_integration.py`

## 6. Architecture Rules That Must Still Be Preserved

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

## 7. Explicit Non-Goals Still In Force

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
- `workflow_profile` / `mission_profile`
- broader `v0.5` abilities

## 8. Baseline / Artifact Notes

### Frozen comparison base
- The canonical frozen JSON comparison set is still `artifacts/baselines/v03`
- This remains the stable explicit baseline pack for regression diffing
- Rule: only top-level `*.json` files under `artifacts/baselines/v03` are part of the frozen set

### v0.4 runtime outputs
- `v0.4` adds runtime-facing evaluation outputs rather than a second frozen artifact directory:
  - `evaluation_input_bundle`
  - `baseline_compare_results`
  - `realm_evaluation`
- These outputs are validated by tests and can be observed from real orchestrator runs, but they are not yet frozen as a separate `artifacts/baselines/v04` pack

### Known temp-dir quirk
- There is an inaccessible temp directory under `artifacts/baselines/v03/`
- The repo rule is unchanged: ignore temp spillover and compare only explicit top-level JSON baselines
- Do not introduce privileged cleanup steps unless there is a real need

## 9. Recommended Next Step For A New Agent

Two safe next-step options:

1. Verify the `b-v0.4-baseline` tag and use it as the stable resume point
2. Start a narrow-scope `v0.5.1` on top of this baseline, focused on a minimal `workflow_profile` / `mission_profile` layer

Do not reopen `v0.4` by expanding scope sideways before one of those two choices is explicit.

## 10. Minimal Resume Commands

```bash
git status --short
git log --oneline --decorate -n 5
git tag --list
python -m unittest discover -s tests -p "test_*.py"
```

Focused verification:

```bash
python -m unittest tests.test_learning_journal_quality_control
python -m unittest tests.test_baseline_compare
python -m unittest tests.test_context_block_selection
python -m unittest tests.test_evaluation_input_bundle
python -m unittest tests.test_realm_evaluator
python -m unittest tests.test_runtime_evaluation_integration
```

## 11. Short Human Summary

`v0.4` is no longer a working-tree-only state.
It is committed, frozen, and resume-safe.

The frozen `v0.4` baseline includes five completed slices:
- journal quality control
- baseline comparison
- finer block-level context selection
- evaluator input unification
- runtime wiring for bundle / compare / evaluator

The main path remains stable and conservative.
The most important practical fact for a new agent is this:
start from the `b-v0.4-baseline` tag, keep the existing boundaries intact, and only then open a narrow `v0.5.1` scope.
