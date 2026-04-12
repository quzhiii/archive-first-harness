# archive-first-harness

<div align="center">

**Debug AI agent runs with evidence, not guesswork.**

[![Python](https://img.shields.io/badge/python-3.13.2-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Stage](https://img.shields.io/badge/stage-public%20alpha-1f6feb)](#current-status)
[![Tests](https://img.shields.io/badge/tests-291%20passed-brightgreen)](#validation)

[**中文文档**](README.zh-CN.md) | [English](README.md)

</div>

---

## What This Does

**See exactly what your AI agent did and why—without digging through raw logs.**

When your AI agent runs a task, this tool automatically captures a structured record of:
- What input was given
- How it was executed step by step  
- Whether verification passed or failed
- What artifacts were produced
- Where and why it failed (if it did)

You can then:
- **Browse** the latest run with a human-readable summary
- **Compare** two runs to see exactly what changed
- **Filter** runs by task type, status, or failure class

Think of it as a **flight recorder for AI agents**: lightweight, always on, and designed for debugging real issues rather than polishing demos.

```mermaid
flowchart TB
    subgraph Traditional["❌ Traditional Debugging"]
        T1[Run Task] --> T2[Check Logs]
        T2 --> T3[Guess What Changed]
        T3 --> T4[Run Again]
        T4 --> T2
    end

    subgraph ArchiveFirst["✅ Archive-First Approach"]
        A1[Run Task] --> A2[Auto-save Structured Evidence]
        A2 --> A3[archive --latest]
        A3 --> A4[Pinpoint Issue with Evidence]
        A4 --> A5[Fix & Compare]
        A5 --> A6[archive --compare to Verify]
    end
```

---

## Quick Start (30 seconds)

### Prerequisites
- Python 3.13+ installed
- Git

### Run This

```bash
git clone https://github.com/quzhiii/archive-first-harness.git
cd archive-first-harness
python quickstart.py
```

**What happens:**
1. Checks system state
2. Runs a minimal "ping" task  
3. Shows you a readable summary of what just happened

That's it. No setup, no dependencies, no configuration.

### Try the Demo

```bash
python -m entrypoints.cli demo
```

Creates two sample runs (success + failure) so you can immediately try the comparison feature:

```bash
python -m entrypoints.cli archive --compare-run-id demo_success_ping --compare-run-id demo_failure_guardrail
```

---

## Real-World Usage Pattern

Here's how you actually use this in practice:

```mermaid
sequenceDiagram
    participant You as Developer
    participant CLI as CLI
    participant Runtime as Agent Runtime
    participant Archive as Archive Storage

    You->>CLI: python -m entrypoints.cli run --task "Research X" --task-type retrieval
    CLI->>Runtime: Execute task
    Runtime->>Runtime: Run steps + verify
    Runtime->>Archive: Save structured evidence<br/>(manifest, verification, failures, artifacts)
    
    You->>CLI: archive --latest
    CLI->>Archive: Read latest run
    Archive-->>CLI: Human-readable summary
    CLI-->>You: "Status: success | Task: Research X | Artifacts: report.md"
    
    Note over You: Later: something breaks
    
    You->>CLI: archive --compare-run-id run_old --compare-run-id run_new
    CLI->>Archive: Fetch both runs
    Archive-->>CLI: Diff analysis
    CLI-->>You: "Verification: passed → failed<br/>Failure class: none → timeout<br/>Artifacts: +report.md"
```

### Common Commands

```bash
# Run a task
python -m entrypoints.cli run --task "Summarize this article" --task-type retrieval

# View the latest run (human readable)
python -m entrypoints.cli archive --latest

# Find a specific run
python -m entrypoints.cli archive --run-id 20260411T133512Z_ping_3eef61

# Compare two runs
python -m entrypoints.cli archive --compare-run-id <id1> --compare-run-id <id2>

# View trends across filtered runs
python -m entrypoints.cli archive --summary --task-type retrieval
```

---

## Why This Exists

Most AI agent systems look great in demos but become painful in production:

| Problem | Why It Matters |
|---------|---------------|
| "It worked yesterday, what's different now?" | Without comparison, debugging is guesswork |
| "The logs say it succeeded, but where's the output?" | Success without artifacts is failure in disguise |
| "Something failed, but where?" | You need to know: routing? execution? verification? |

**This tool makes these questions answerable.**

Every run produces structured evidence you can query, compare, and act on—instead of scrolling through unstructured logs hoping to spot the difference.

---

## How It Works (Architecture)

```mermaid
flowchart TB
    subgraph Input["Input Layer"]
        CLI["CLI Commands<br/>run / inspect / archive / demo"]
        Quickstart["quickstart.py<br/>One-command onboarding"]
    end

    subgraph Runtime["Runtime Layer"]
        Task["Task Runner"]
        Exec["Executor<br/>Runs the actual task"]
        Verify["Verifier<br/>Checks outputs"]
    end

    subgraph Evidence["Evidence Layer (Archive)"]
        direction TB
        M["manifest.json<br/>What was requested"]
        V["verification_report.json<br/>Did it pass checks"]
        F["failure_signature.json<br/>Why it failed"]
        T["execution_trace.jsonl<br/>Step-by-step log"]
    end

    subgraph Query["Query Layer"]
        L["--latest<br/>View newest"]
        C["--compare<br/>Diff two runs"]
        S["--summary<br/>Aggregated trends"]
    end

    CLI --> Task
    Quickstart --> Task
    Task --> Exec
    Task --> Verify
    Exec --> Evidence
    Verify --> Evidence
    Evidence --> Query
```

**Key design principles:**

1. **Archive-first**: Evidence is a first-class output, not an afterthought
2. **Conservative runtime**: The execution path stays narrow and diagnosable
3. **No hidden control flow**: Evaluation and comparison don't silently change how things run
4. **Standard library only**: Zero runtime dependencies for the core system

---

## Current Status

**Public Alpha** – Core functionality is solid, onboarding is actively improving.

### What's Working

- ✅ Single-task CLI execution
- ✅ Sequential batch execution  
- ✅ Automatic per-run archival with structured evidence
- ✅ Browse: latest run, specific run ID, filtered lists
- ✅ Compare: side-by-side diff of any two runs
- ✅ Summary: aggregate trends across runs
- ✅ 291 tests passing
- ✅ Verified on real tasks: success, failure, governance review, coding artifacts

### What's Not Here Yet

- ❌ Web UI (use CLI for now)
- ❌ Database backend (filesystem only)
- ❌ Async workers (sequential execution)
- ❌ Hosted service (local tool)

These are intentionally delayed until the core archive loop is proven in real use.

---

## Who Should Use This

**Good fit if you:**
- Build AI agents and need to debug why runs fail or behave differently
- Want run-level evidence before building bigger infrastructure
- Care more about "can I explain what happened" than "does it look impressive"
- Prefer tools that do one thing well over platforms that do everything

**Not a fit if you:**
- Need a complete end-user product today
- Want a hosted API service
- Require enterprise features (auth, multi-tenant, etc.)

---

## Project Roadmap

```mermaid
timeline
    title Development Roadmap
    
    section Now (Public Alpha)
        Core Loop : Task execution
                  : Archive evidence
                  : Browse & compare
                  : Quickstart onboarding
                  
    section Next (Feedback Phase)
        Polish : External tester feedback
               : Documentation refinement
               : Archive UX improvements
               
    section Later
        Expand : Additional task types
               : Advanced filtering
               : Batch optimizations
               
    section Future
        Platform : Optional API layer
                 : Pluggable storage
                 : Optional web UI
```

Near-term priorities are concrete:

1. **Reduce first-run friction** ← you are here
2. Collect public alpha feedback
3. Improve archive signal-to-noise ratio
4. Accumulate real usage patterns
5. Keep runtime boundary stable until usage proves the archive loop

---

## Documentation

- [Quick Start Guide](docs/2026-04-02-external-uat-quickstart.md) – Step-by-step first run
- [Tester Feedback Checklist](docs/2026-04-12-external-feedback-checklist.md) – What to look for when testing
- [Architecture & Roadmap](PROJECT_ARCHITECTURE_STATUS_AND_ROADMAP.md) – Deep dive
- [Real Usage Diary Template](docs/2026-04-02-real-usage-diary-template.md) – Track your experience

---

## Feedback Welcome

Testing this? The most valuable feedback:

- Where did you get stuck?
- Which output was confusing?
- Did `compare` actually help you understand a difference?
- Would you use this in your actual workflow?

[Open an issue](https://github.com/quzhiii/archive-first-harness/issues) or reference the [feedback checklist](docs/2026-04-12-external-feedback-checklist.md).

---

<div align="center">

**[⬆ Back to Top](#archive-first-harness)**

</div>
