# KNOWN_GAPS_v0.2

This file freezes the intentionally unimplemented items for the B v0.2 baseline.
It is a scope boundary document, not a backlog for immediate expansion.

## Current Baseline

- Baseline stage: `B v0.2`
- Freeze date: `2026-03-27`
- Integration status: minimal v0.2 path runnable with routing, residual follow-up, interviewer, ID split, and minimal learning journal reuse
- Target baseline tag: `b-v0.2-baseline`

## Known Gaps Kept Out Of v0.2

- `learning_journal` has no ranking.
- `learning_journal` has no forgetting.
- `learning_journal` has no complex retrieval or semantic search.
- `learning_journal` has no multi-writer concurrency control.
- CLI does not expose an explicit journal on/off switch.
- `sandbox` and `rollback` still exist largely as isolated components and are not fully wired into the main execution path.
- methodology and model escalation remain advisory only; they do not auto-execute.
- There is still no database-backed state.
- There are still no parallel workers.
- There is still no full residual recovery chain or failure-journal system.
- There is still no hook orchestration layer.
- There are still no heavy code capability packs such as LSP, AST-Grep, or tmux integration.

## Why These Gaps Stay

These items are intentionally excluded so v0.2 remains:

- low-drift
- inspectable
- testable
- easy to compare against later versions

## Exit Rule

Any work that closes the gaps above should be treated as v0.3+ scope unless it is a strict bug fix required to preserve the documented v0.2 baseline behavior.
