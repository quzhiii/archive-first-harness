# Paper Update Proposal For Case A (2026-04-13)

This document proposes how to update the paper text after the 2026-04-13 Case A
experiment work, without modifying the original paper sources.

The main constraint is accuracy:

- Case A now has a usable success/failure archive pair.
- The success run is a repository-grounded real Aider run.
- The failure-prone run is based on a reduced-scope paper excerpt
  (`failure_prone_sample.md`), not a full-paper rewrite result.
- Therefore, the paper should not claim that a full-paper Case A rewrite pair
  has been completed.

## Recommended Positioning

Use the following framing consistently:

- Case A is no longer only a planned capture workflow.
- Case A now includes a real success run and a reduced-scope failure-prone run
  that were both normalized into the archive schema.
- The reduced-scope failure sample is still meaningful because it captures a
  realistic factual-overstatement failure under repository-grounded writing
  conditions.
- Case A should be described as a repository-grounded coding-agent case with a
  completed archive pair, while clearly noting that the failure sample was
  collected from a reduced-scope paper excerpt rather than a full-paper edit.

## Suggested Replacement Text For `draft.md`

### Case-study section

Suggested replacement for the current Case A bullets and descriptive paragraph:

```md
- **Case A**: a repository-grounded coding-agent scenario with a completed
  archive pair consisting of a real Aider success run and a reduced-scope
  failure-prone writing sample,
- **Case B**: a retrieval-augmented generation scenario with a success/failure
  archive pair,
- **Case C**: a multi-step tool-use scenario with a success/failure archive pair.

The current repository already includes deterministic scripts for Cases B and C
that generate archives using the same production archive writer as the main
system. For Case A, the repository now includes a completed Aider-based archive
pair collected through the same archive-facing interfaces. The success run is a
repository-grounded real coding-agent edit, while the failure-prone run is a
reduced-scope paper excerpt designed to test whether the agent overstates Case A
completion under realistic writing conditions. This matters because Case A is
now represented in the same compare-ready archive format as the other cases,
rather than remaining only a planned ingestion workflow.

In Case A, the failure-prone sample shows a concrete factual-overstatement
pattern: the agent rewrites the text so that Case A appears to already have a
completed success/failure pair, even though the underlying repository state does
not support that stronger claim. This provides a realistic comparison point for
the archive-first evidence layer because the failure is not a raw crash, but a
subtle state-description error that would be easy to miss in ordinary editing
workflows.
```

### Limitations section

Suggested replacement for the current Case A limitation paragraph:

```md
Second, **Case A** now includes a usable success/failure archive pair, but the
current failure sample is intentionally reduced in scope. The success run is a
real repository-grounded Aider edit, whereas the failure-prone run is collected
from a condensed paper excerpt rather than a full-paper rewrite. This means the
current Case A evidence is sufficient for archive-based comparison, but still
leaves room to extend the study toward larger-scope coding-agent and writing
tasks.
```

### Next-steps section

Suggested replacement for the current first next-step bullet:

```md
1. extend Case A from the current real-success / reduced-scope-failure pair to
   a broader set of repository-grounded coding-agent and writing samples,
```

## Suggested Replacement Text For `paper.tex`

### Case-study section

Suggested LaTeX replacement:

```tex
We organize the case-study portion into three tracks: (1) a repository-grounded
coding-agent scenario with a completed archive pair consisting of a real Aider
success run and a reduced-scope failure-prone writing sample, (2) a
retrieval-augmented generation scenario with a success/failure archive pair,
and (3) a multi-step tool-use scenario with a success/failure archive pair.

The current repository already includes deterministic scripts for Cases B and C
that generate archives using the same production archive writer as the main
system. For Case A, the repository now includes a completed Aider-based archive
pair collected through the same archive-facing interfaces. The success run is a
repository-grounded real coding-agent edit, while the failure-prone run is a
reduced-scope paper excerpt designed to test whether the agent overstates Case A
completion under realistic writing conditions. This matters because Case A is
now represented in the same compare-ready archive format as the other cases,
rather than remaining only a planned ingestion workflow.

In Case A, the failure-prone sample shows a concrete factual-overstatement
pattern: the agent rewrites the text so that Case A appears to already have a
completed success/failure pair, even though the underlying repository state does
not support that stronger claim. This provides a realistic comparison point for
the archive-first evidence layer because the failure is not a raw crash, but a
subtle state-description error that would be easy to miss in ordinary editing
workflows.
```

### Limitations section

Suggested LaTeX replacement:

```tex
Second, \textbf{Case A} now includes a usable success/failure archive pair, but
the current failure sample is intentionally reduced in scope. The success run is
a real repository-grounded Aider edit, whereas the failure-prone run is
collected from a condensed paper excerpt rather than a full-paper rewrite. This
means the current Case A evidence is sufficient for archive-based comparison,
but still leaves room to extend the study toward larger-scope coding-agent and
writing tasks.
```

### Next-steps section

Suggested LaTeX replacement:

```tex
extend Case A from the current real-success / reduced-scope-failure pair to a
broader set of repository-grounded coding-agent and writing samples,
```

## Recommended Usage

If you later decide to update the actual paper files, copy from this proposal
selectively instead of applying everything blindly. The key requirement is to
preserve the distinction between:

- a real repository-grounded success run, and
- a reduced-scope failure-prone writing sample.

That distinction keeps the Case A claim strong enough to be useful while still
remaining academically accurate.
