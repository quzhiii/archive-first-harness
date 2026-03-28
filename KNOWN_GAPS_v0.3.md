# KNOWN_GAPS_v0.3

This file freezes the intentionally unimplemented items for the B v0.3 baseline.
It is a scope boundary document, not a backlog for immediate expansion.

## Current Baseline

- Baseline stage: `B v0.3`
- Freeze date: `2026-03-28`
- Integration status: minimal v0.3 path runnable with evented follow-up wiring, conditional sandbox gating, minimal rollback, and journal append unification
- Target baseline tag: `b-v0.3-baseline`

## Known Gaps Kept Out Of v0.3

- There is no parallel worker or subagent runtime.
- There is no async event bus or queue.
- Hooks remain synchronous, in-process triggers only.
- methodology and model advice remain advisory only; they do not auto-execute.
- governance does not auto-override contract boundaries.
- `learning_journal` has no ranking.
- `learning_journal` has no forgetting.
- `learning_journal` has no semantic retrieval or richer retrieval pipeline.
- `learning_journal` is not a failure journal and not a long-term knowledge base.
- rollback only supports the current minimal rollback abstraction; it is not a recovery engine or transaction system.
- sandbox is still a stub isolation path; it is not a production-grade isolated execution environment.
- There is still no database-backed state.
- There is still no plugin system.
- There is still no automatic retirement flow.
- There are still no heavy code capability packs such as LSP, AST-Grep, or tmux integration.

## Why These Gaps Stay

These items are intentionally excluded so v0.3 remains:

- low-drift
- inspectable
- testable
- easy to compare against later versions

## Exit Rule

Any work that closes the gaps above should be treated as v0.4+ scope unless it is a strict bug fix required to preserve the documented v0.3 baseline behavior.
