# Archive-First Run Diagnostic Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> Current session note: `superpowers:*` is not available in this Codex environment. If you execute this plan here, implement the tasks directly in order and keep the same commit boundaries.

**Goal:** Add a run-level diagnostic archive on top of the current narrow runtime harness without changing orchestrator control semantics or replacing the existing history files.

**Architecture:** Keep `runtime/orchestrator.py` single-path and advisory-only. Add a thin outer archive layer around `run_task_request(...)` that writes `artifacts/runs/<run_id>/` plus a global `artifacts/runs/index.jsonl`, using already-produced runtime outputs such as `task_contract`, `block_selection_report`, `verification_report`, `metrics_summary`, `evaluation_input_bundle`, and `realm_evaluation`.

**Tech Stack:** Python stdlib, dataclasses, pathlib, JSON/JSONL, existing `entrypoints/`, `runtime/`, and `tests/` unittest suite.

---

## Recommended Approach

### Option A: Thin outer archive layer on `run_task_request(...)` (Recommended)

- Pros: reuses current stable outputs, preserves orchestrator semantics, minimal blast radius, aligns with the v2 archive-first docs.
- Cons: first-cut trace is synthesized from entrypoint checkpoints rather than being a full internal event stream.

### Option B: Deep instrumentation inside `runtime/orchestrator.py`

- Pros: richer internal trace detail.
- Cons: higher regression risk, larger semantic footprint, more likely to accidentally create a new control plane.

### Option C: Database-first archive/search layer

- Pros: stronger future querying story.
- Cons: wrong order for this repo stage, higher complexity, conflicts with the v2 requirement to stabilize the artifact contract first.

**Decision:** implement Option A now. Defer B and C.

---

### Task 1: Reposition the Project Boundary in Docs

**Files:**
- Create: `ARCHITECTURE_POSITIONING.md`
- Modify: `README.md`
- Modify: `PROJECT_HANDOFF_v0.5.md`

**Step 1: Write the new positioning doc**

Include these points explicitly:

- The repo is a narrow runtime harness, not a full agent platform.
- The next phase is `archive-first`, not `minimal HTTP/API server shell`.
- `formation_id` and `policy_mode` enter this round only as thin metadata defaults.
- OpenClaw adapter and offline meta-harness loop are deferred.

**Step 2: Update the README next-direction section**

Replace the current “minimal HTTP/API server shell” recommendation with:

- `Phase 0 + Phase 1 + Phase 2` archive-first
- run-level archive directories
- raw diagnostic evidence
- archive index as file-system first

**Step 3: Update the handoff resume note**

Make the next-step section consistent with the new direction so a future agent does not resume into the wrong phase.

**Step 4: Verify the docs are aligned**

Run:

```powershell
rg -n "archive-first|minimal HTTP/API server shell|run-level diagnostic archive" README.md PROJECT_HANDOFF_v0.5.md ARCHITECTURE_POSITIONING.md
```

Expected:

- `README.md` and `PROJECT_HANDOFF_v0.5.md` now point to archive-first.
- No stale “HTTP/API shell is next” statement remains unqualified.

**Step 5: Commit**

```bash
git add ARCHITECTURE_POSITIONING.md README.md PROJECT_HANDOFF_v0.5.md
git commit -m "docs: reposition next phase around archive-first"
```

---

### Task 2: Add Archive Schema and Writer Scaffolding

**Files:**
- Create: `entrypoints/run_archive.py`
- Create: `tests/test_run_archive_writer.py`

**Step 1: Write the failing archive-writer test**

Cover:

- writing `artifacts/runs/<run_id>/`
- writing `manifest.json`
- writing `task_contract.json`
- writing `profile_and_mode.json`
- writing `verification_report.json`
- writing `metrics_summary.json`
- writing `evaluation_summary.json`
- writing `final_output.json`
- writing `archive_index.json`

Example assertion shape:

```python
result = write_run_archive(
    run_result=sample_result,
    archive_root=self.temp_dir / "runs",
    run_id="run-one",
)
assert Path(result["archive_dir"]).exists()
assert (Path(result["archive_dir"]) / "manifest.json").exists()
assert json.loads((Path(result["archive_dir"]) / "manifest.json").read_text())["run_id"] == "run-one"
```

**Step 2: Run the test and confirm it fails**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_writer.py"
```

Expected:

- FAIL because `entrypoints.run_archive` does not exist yet.

**Step 3: Implement the minimal archive writer**

Create a thin module with helpers like:

```python
def write_run_archive(
    *,
    archive_root: Path,
    run_id: str,
    created_at: datetime,
    surface_request: Mapping[str, Any] | None,
    run_result: Mapping[str, Any],
    formation_id: str = "default",
    policy_mode: str = "default",
    trace_events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    ...
```

Manifest fields minimum:

- `run_id`
- `created_at`
- `workflow_profile_id`
- `formation_id`
- `policy_mode`
- `task_summary`
- `status`
- `archive_version`
- `archive_dir`

Use `Path(...).write_text(..., encoding="utf-8")` with sorted, indented JSON.

**Step 4: Re-run the test and make it pass**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_writer.py"
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add entrypoints/run_archive.py tests/test_run_archive_writer.py
git commit -m "feat: add run archive writer scaffolding"
```

---

### Task 3: Wire the Archive into `run_task_request(...)` Without Changing Control Semantics

**Files:**
- Modify: `entrypoints/task_runner.py`
- Create: `tests/test_run_archive_failure_tolerance.py`
- Modify: `tests/test_surface_task_runner.py`
- Modify: `tests/test_cli_smoke.py`

**Step 1: Write failing tests for integration and failure tolerance**

Cover:

- successful `run_task_request(...)` writes an archive and returns `run_archive`
- archive write failure does not make the run itself fail
- CLI single-run still returns JSON and now carries archive metadata

Example assertions:

```python
assert result["run_archive"]["status"] == "written"
assert Path(result["run_archive"]["archive_dir"]).exists()
```

and

```python
with patch("entrypoints.task_runner.write_run_archive", side_effect=RuntimeError("archive failed")):
    result = run_task_request(...)
assert result["execution_result"]["status"] in {"success", "error"}
assert result["run_archive"]["status"] == "failed"
```

**Step 2: Run the tests and confirm they fail**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_failure_tolerance.py"
python -m unittest discover -s tests -p "test_surface_task_runner.py"
python -m unittest discover -s tests -p "test_cli_smoke.py"
```

Expected:

- FAIL because archive wiring and `run_archive` payload do not exist yet.

**Step 3: Implement best-effort archive wiring**

In `entrypoints/task_runner.py`:

- generate `created_at` once near the top
- derive `run_id` with the existing `build_run_id(...)`
- keep a small in-memory trace list
- after the orchestrator result returns, call `write_run_archive(...)` in `try/except`
- attach a non-controlling payload like:

```python
output["run_archive"] = {
    "status": "written",
    "run_id": run_id,
    "archive_dir": "...",
    "archive_index_file": "...",
}
```

On failure:

```python
output["run_archive"] = {
    "status": "failed",
    "run_id": run_id,
    "error_type": type(exc).__name__,
    "message": str(exc),
}
```

Do not alter exit semantics, verification semantics, or realm evaluation behavior.

**Step 4: Re-run the tests and make them pass**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_failure_tolerance.py"
python -m unittest discover -s tests -p "test_surface_task_runner.py"
python -m unittest discover -s tests -p "test_cli_smoke.py"
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add entrypoints/task_runner.py tests/test_run_archive_failure_tolerance.py tests/test_surface_task_runner.py tests/test_cli_smoke.py
git commit -m "feat: wire run archive into surface task runner"
```

---

### Task 4: Add Minimal Raw Diagnostic Evidence

**Files:**
- Modify: `entrypoints/run_archive.py`
- Create: `tests/test_run_archive_trace.py`

**Step 1: Write the failing raw-evidence test**

Cover these files:

- `context_plan.json`
- `execution_trace.jsonl`
- `failure_signature.json`

Test both a success path and a failure path.

Example assertions:

```python
trace_lines = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
assert any(item["event_type"] == "task_contract_built" for item in trace_lines)
assert any(item["event_type"] == "evaluation_completed" for item in trace_lines)
```

and

```python
signature = json.loads(signature_path.read_text())
assert signature["failed_stage"] == "execution"
assert signature["failure_class"] == "execution_error"
```

**Step 2: Run the test and confirm it fails**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_trace.py"
```

Expected:

- FAIL because the raw evidence files do not exist yet.

**Step 3: Implement the raw evidence extraction**

Use only existing payloads plus entrypoint checkpoints.

`context_plan.json` should be derived from:

- `block_selection_report`
- `surface.workflow_profile_id`
- `task_contract.workflow_profile_id`
- default metadata:
  - `formation_id: "default"`
  - `policy_mode: "default"`

`execution_trace.jsonl` should contain lightweight events such as:

```json
{"event_type":"surface_request_received","status":"ok"}
{"event_type":"task_contract_built","status":"ok"}
{"event_type":"runtime_completed","status":"success"}
{"event_type":"verification_completed","status":"passed"}
{"event_type":"evaluation_completed","status":"ok"}
```

`failure_signature.json` should conservatively derive:

- `failure_class`
- `error_type`
- `failed_stage`
- `message_excerpt`

Prefer stable, boring logic:

- execution error -> stage `execution`
- verification failed -> stage `verification`
- governance review required -> stage `governance`
- otherwise success signature or empty signature

**Step 4: Re-run the test and make it pass**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_trace.py"
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add entrypoints/run_archive.py tests/test_run_archive_trace.py
git commit -m "feat: add minimal raw diagnostic evidence"
```

---

### Task 5: Add Global Archive Index

**Files:**
- Modify: `entrypoints/run_archive.py`
- Create: `tests/test_run_archive_index.py`

**Step 1: Write the failing archive-index test**

Cover:

- appending `artifacts/runs/index.jsonl`
- one line per run
- stable fields for manual grep/diff

Required fields:

- `run_id`
- `created_at`
- `workflow_profile_id`
- `formation_id`
- `policy_mode`
- `status`
- `archive_dir`
- `failure_class`

**Step 2: Run the test and confirm it fails**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_index.py"
```

Expected:

- FAIL because the index writer does not exist yet.

**Step 3: Implement append-only index writing**

Inside `write_run_archive(...)` or a dedicated helper:

```python
def append_run_archive_index(index_file: Path, manifest: Mapping[str, Any], failure_signature: Mapping[str, Any]) -> None:
    ...
```

Rules:

- file path is `archive_root / "index.jsonl"`
- append-only
- no database
- no query DSL
- no rewrite of old entries

**Step 4: Re-run the test and make it pass**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_index.py"
```

Expected:

- PASS

**Step 5: Commit**

```bash
git add entrypoints/run_archive.py tests/test_run_archive_index.py
git commit -m "feat: add append-only run archive index"
```

---

### Task 6: Full Validation and Example Archive Inspection

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_HANDOFF_v0.5.md`
- Optionally update: `ARCHITECTURE_POSITIONING.md`

**Step 1: Run the focused archive test set**

Run:

```bash
python -m unittest discover -s tests -p "test_run_archive_writer.py"
python -m unittest discover -s tests -p "test_run_archive_failure_tolerance.py"
python -m unittest discover -s tests -p "test_run_archive_trace.py"
python -m unittest discover -s tests -p "test_run_archive_index.py"
python -m unittest discover -s tests -p "test_surface_task_runner.py"
python -m unittest discover -s tests -p "test_cli_smoke.py"
python -m unittest discover -s tests -p "test_runtime_evaluation_integration.py"
```

Expected:

- PASS

**Step 2: Run the full suite**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Expected:

- full suite passes

**Step 3: Inspect a real archive tree**

Run:

```powershell
Get-ChildItem -LiteralPath 'artifacts/runs' -Recurse | Select-Object FullName
```

Expected:

- at least one `artifacts/runs/<run_id>/`
- an `artifacts/runs/index.jsonl`
- the expected per-run JSON files

**Step 4: Sync docs with the implemented shape**

Document:

- exact archive tree
- best-effort write semantics
- `formation_id` / `policy_mode` defaults
- known gaps in trace richness

**Step 5: Commit**

```bash
git add README.md PROJECT_HANDOFF_v0.5.md ARCHITECTURE_POSITIONING.md entrypoints/run_archive.py entrypoints/task_runner.py tests/test_run_archive_writer.py tests/test_run_archive_failure_tolerance.py tests/test_run_archive_trace.py tests/test_run_archive_index.py tests/test_surface_task_runner.py tests/test_cli_smoke.py
git commit -m "docs: close out archive-first diagnostic layer"
```

---

## Explicit Deferrals

Do not pull these into this plan:

- `minimal HTTP/API server shell`
- SQLite / FTS / query DSL
- replay / rerun / write-back controls
- real formation selection engine
- OpenClaw adapter or command pack
- offline meta-harness outer loop

---

## Acceptance Criteria

- Every `run_task_request(...)` writes a best-effort archive under `artifacts/runs/<run_id>/`.
- The archive contains stable structured outputs and minimum raw evidence.
- `artifacts/runs/index.jsonl` is append-only and grep-friendly.
- Archive failures do not change runtime control semantics.
- Existing `run_history.jsonl`, `latest_run.json`, and `run_history_summary.json` remain compatible.
- The full unittest suite still passes.

---

## Risks to Watch

- Accidentally moving trace responsibility into `runtime/orchestrator.py` instead of keeping it in the outer archive layer.
- Letting archive payloads mirror too much of the full runtime result and becoming unstable.
- Treating `formation_id` and `policy_mode` as a real subsystem before enough archive evidence exists.
- Changing CLI success/failure behavior because archive persistence is wired incorrectly.
