# archive-first-harness

<div align="center">

**Agent Evidence Layer — Debug AI agent runs with evidence, not guesswork.**

[![Python](https://img.shields.io/badge/python-3.13.2-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Stage](https://img.shields.io/badge/stage-public%20alpha-1f6feb)](#current-status)
[![Tests](https://img.shields.io/badge/tests-291%20passed-brightgreen)](#validation)

[**中文文档**](README.zh-CN.md) | [English](README.md)

</div>

---

## What Is This

**The missing fourth layer in AI agent stack.**

Current agent ecosystem has three layers:

```
┌────────────────────────────────────────┐
│  Framework      │  LangGraph, CrewAI   │  ← Build agents
├────────────────────────────────────────┤
│  Harness        │  OpenHands, Aider    │  ← Run agents  
├────────────────────────────────────────┤
│  Observability  │  LangSmith, Langfuse │  ← Trace & monitor
├────────────────────────────────────────┤
│  Evidence Layer │  archive-first-harness│  ← Diagnose & compare ← YOU ARE HERE
└────────────────────────────────────────┘
```

**Framework** helps you build agents. **Harness** gives you runtime. **Observability** shows you traces.

But when your agent worked yesterday and fails today, you need the **fourth layer**: a system that archives structured evidence of every run and lets you compare them precisely.

This is **Evidence Layer**: local-first, zero-dependency, purpose-built for "what changed?" debugging.

---

## Problems We Solve

| Pain Point | Traditional Approach | Archive-First |
|------------|---------------------|---------------|
| Debugging agent failures | Dig through logs, guess, retry | Structured archives with precise diffs |
| "It worked yesterday" | No idea what changed | `--compare` shows exact differences |
| Failure localization | Search logs for errors | Automatic failure classification |
| Success but no output | Thought it worked, but no artifacts | Verification checks expected outputs |
| Tuning by trial-and-error | Change params, hope for best | Compare data between runs |

---

## 30-Second Quick Start

```bash
git clone https://github.com/quzhiii/archive-first-harness.git
cd archive-first-harness
python quickstart.py
```

**Expected output:**

```
archive-first-harness quickstart
================================
[1/3] inspect-state       → ok | 30 state files
[2/3] run ping            → success | run_id=20260412_143022_7a3f
[3/3] archive --latest    → verification=passed | artifacts=1 file

✅ First run complete! Try:
   python -m entrypoints.cli demo
   python -m entrypoints.cli archive --summary
```

---

## Core Capabilities

### 1. Run = Archive

Every `run` automatically saves structured evidence:

```
artifacts/runs/<run_id>/
├── manifest.json              # Task request, status, timestamp
├── verification_report.json   # Verification results, artifacts list
├── failure_signature.json     # Failure type, stage, reason
├── execution_trace.jsonl      # Step-by-step execution log
└── final_output.json          # Final output
```

### 2. Browse & Compare

| Command | Purpose |
|---------|---------|
| `archive --latest` | View latest run summary |
| `archive --run-id <id>` | View specific run details |
| `archive --compare-run-id <id1> <id2>` | Compare two runs side-by-side |
| `archive --summary` | Aggregate trends (success/failure distribution) |
| `demo` | Create sample data to try comparison |

**Comparison output example:**

```
Compare: run_20260412_143022 vs run_20260412_143045
===================================================
Status:         success      →   failed
Failure type:   -            →   timeout
Verification:   passed       →   failed
Artifacts:      1 file       →   0 files
Duration:       2.3s         →   30.0s (timeout)
```

---

## Architecture

### Layer Structure

```
┌─────────────────────────────────────────┐
│  UI Layer    │  CLI (quickstart.py)     │
├─────────────────────────────────────────┤
│  Runtime     │  Task Runner → Executor  │
│  Layer       │  → Verifier              │
├─────────────────────────────────────────┤
│  Evidence    │  manifest / verification │
│  Layer       │  / failure / trace       │
├─────────────────────────────────────────┤
│  Query       │  --latest / --compare    │
│  Layer       │  / --summary             │
└─────────────────────────────────────────┘
```

### Design Principles

1. **Archive-first**: Evidence is a first-class citizen, not an afterthought
2. **Conservative runtime**: Simple, predictable execution path with no hidden logic
3. **Zero dependencies**: Pure Python standard library, no external packages
4. **Local-first**: Data stored in local files, fully under your control

---

## Typical Workflow

```
Daily Development              Troubleshooting
──────────────────────────────────────────────────
1. Run task          →        Spot anomaly
2. archive --latest  →        archive --compare
   Verify results              Compare runs
3. Continue dev      →        Pinpoint issue
                               Verify fix
```

### Scenario Example

**Scenario: Agent worked yesterday, times out today**

```bash
# Find yesterday's and today's runs
python -m entrypoints.cli archive --summary --status failed
# → Found 3 timeouts today

# Compare most recent success vs failure
python -m entrypoints.cli archive \
  --compare-run-id 20260411_success \
  --compare-run-id 20260412_timeout

# Output shows:
# - Same task input
# - Same execution steps
# - But duration: 2s → 30s (timeout)
# → Conclusion: External API slowed down,
#    need retry logic or longer timeout
```

---

## Current Status

**Public Alpha** — Core functionality stable, collecting usage feedback.

### Available Now ✅

- Single-task CLI execution
- Automatic archiving (manifest/verification/failure/trace)
- Browse: latest, by ID, filtered lists
- Side-by-side comparison with diff highlighting
- Aggregate trend summaries
- 291 tests passing
- Verified on Windows / Linux / macOS

### Not Available ❌

- Web UI (CLI-first)
- Database storage (filesystem is sufficient)
- Async queues (sequential is sufficient)
- Hosted service (local tool)

These are intentionally delayed until the core archive loop is proven in real use.

---

## Who Should Use This

**Good fit if you:**
- Build AI agents and need to debug failures
- Want to compare runs rather than rely on memory
- Care about "did it produce artifacts" not just "did it not crash"
- Prefer simple tools that do one thing well

**Not a fit if you:**
- Need a complete end-user product today
- Want a hosted API service
- Need enterprise features (SSO, audit logs, etc.)

---

## Development Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| v0.1 | Basic run + archive | ✅ Complete |
| v0.2 | Browse + Compare queries | ✅ Complete |
| v0.3 | Quickstart + Demo experience | ✅ Complete |
| v0.4 | **Collect external feedback** | 🚧 Current |
| v0.5 | Archive signal-to-noise improvements | 📋 Planned |
| v1.0 | Stable release | 📋 Planned |

---

## Join Testing

We're recruiting testers! If you'd like to try it and provide feedback:

1. **Quick experience**: `python quickstart.py`
2. **Check feedback checklist**: [docs/2026-04-12-external-feedback-checklist.md](docs/2026-04-12-external-feedback-checklist.md)
3. **Submit an issue**: [GitHub Issues](https://github.com/quzhiii/archive-first-harness/issues)

**Most valuable feedback:**
- Where did you get stuck?
- Which output was confusing?
- Did comparison actually help you locate the problem?

---

## Documentation

- [Quick Start Guide](docs/2026-04-02-external-uat-quickstart.md) — Detailed steps
- [Feedback Checklist](docs/2026-04-12-external-feedback-checklist.md) — Testing checklist
- [Architecture Details](docs/diagrams/architecture-overview.md) — Diagrams

---

<div align="center">

**[↑ Back to Top](#archive-first-harness)**

</div>
