# KNOWN_GAPS_v0.1

This file freezes the intentionally unimplemented items for the B v0.1 baseline.
It is a scope boundary document, not a backlog for immediate expansion.

## Current Baseline

- Baseline stage: `B v0.1`
- Freeze date: `2026-03-26`
- Integration status: minimal main path runnable through CLI

## Known Gaps Kept Out Of v0.1

- `planner/interviewer.py` is not implemented.
- `task_id` and `contract_id` are still effectively coupled in the current minimal flow.
- `sandbox` and `rollback` exist as isolated stubs, but are not wired into the CLI main path.
- There is no `model_router.py`.
- There is no `methodology_router.py`.
- There is no automatic retirement flow.
- There is no database-backed state.
- There are no parallel workers.
- There is no retrieval / RAG / vector store system.
- There is no complex hook orchestration layer.
- There are no heavy code capability packs such as LSP, AST-Grep, or tmux integration.

## Why These Gaps Stay

These items are intentionally excluded so v0.1 remains:

- low-drift
- inspectable
- testable
- easy to compare against later versions

## Exit Rule

Any work that closes the gaps above should be treated as v0.2+ scope unless it is a strict bug fix required to preserve the documented v0.1 baseline behavior.
