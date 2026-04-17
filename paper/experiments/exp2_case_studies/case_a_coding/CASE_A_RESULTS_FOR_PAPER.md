# Case A Results For Paper

This document summarizes the final usable Case A experiment outcome in
paper-ready form without modifying the main paper files.

## One-Paragraph Result Summary

Case A now provides a usable archive-based success/failure comparison for the
coding-agent track. The success run is a repository-grounded real Aider edit in
which the agent correctly updated the Case A README and added the requested JSON
example. The failure-prone run is intentionally reduced in scope: instead of
editing the full paper, the agent was asked to revise a condensed paper excerpt
that describes Case A. In that setting, Aider rewrote the text so that Case A
appeared to already contain a completed success/failure pair, even though the
underlying repository state did not support that stronger claim. After both runs
were normalized into the archive schema, the compare output showed regressions
in failure status, verification outcome, reassessment, and evaluation, while
governance remained unchanged. This makes Case A suitable as a repository-
grounded example of how archive-based comparison can surface subtle
factual-overstatement failures rather than only raw execution crashes.

## Short Abstract-Style Version

We completed a usable Case A coding-agent archive pair consisting of a real
repository-grounded Aider success run and a reduced-scope failure-prone writing
sample. The failure sample is especially informative because it does not fail by
crashing or refusing the task; instead, it overstates the completion status of
Case A and thereby creates a realistic factual-consistency error. When archived
and compared through the same evidence layer as the other case studies, the pair
produces clear regressions in verification and evaluation without requiring any
change to the governance state.

## Method Note

The final Case A setup should be described carefully.

- The success run was executed on the real repository and edited only the target
  README file.
- The original large-scope failure-prone design, which targeted the full paper
  files, was not stable enough for primary use because of provider
  incompatibility on one backend and token-limit issues on another.
- The final usable failure sample was therefore collected from a reduced-scope
  paper excerpt stored in `failure_prone_sample.md`.
- This reduced-scope design preserved the intended semantic risk: the agent was
  still asked to improve a paper-like description of Case A and, in doing so,
  incorrectly strengthened the completion claim beyond what the repository state
  justified.

## Suggested Case-Study Text

Use this when you want a concise case-study description:

```text
Case A is a repository-grounded coding-agent scenario with a completed
archive-based comparison pair. The success run is a real Aider edit collected
from the repository, while the failure-prone run is drawn from a reduced-scope
paper excerpt designed to test factual overstatement under realistic writing
conditions. In the failure sample, the agent rewrites the text so that Case A
appears to already include a completed success/failure pair, even though the
repository state still supports only a narrower claim. The resulting archives
show regressions in verification and evaluation while leaving governance
unchanged, illustrating how the evidence layer can expose subtle state-
description errors rather than only hard failures.
```

## Suggested Limitations Text

```text
Case A now includes a usable success/failure archive pair, but the failure
sample is intentionally reduced in scope. The success run is a real
repository-grounded Aider edit, whereas the failure-prone run is collected from
a condensed paper excerpt rather than a full-paper rewrite. This makes the
current Case A evidence sufficient for archive-based comparison while still
leaving room to extend the study toward larger-scope coding-agent and writing
tasks.
```

## Suggested Next-Step Text

```text
Extend Case A from the current real-success / reduced-scope-failure pair to a
broader set of repository-grounded coding-agent and writing samples.
```

## Compare Output Interpretation

The current compare output can be summarized as follows:

- success run: verified, low risk, keep, no human review
- failure run: failed verification, high risk, observe, human review required
- transition summary:
  - `failure=regressed`
  - `verification=regressed`
  - `reassessment=regressed`
  - `evaluation=regressed`
  - `governance=unchanged`

This pattern is useful because it shows that the failure-prone sample is not
just "different"; it is worse along the exact dimensions that matter for the
archive-first comparison surface.

## Reviewer-Safe Framing

If you need the most conservative phrasing for a paper, use this:

```text
Case A now includes a completed archive pair for a repository-grounded success
run and a reduced-scope failure-prone writing sample. We do not claim that the
current failure sample is a full-paper rewrite result; rather, it is a
controlled excerpt-level test that preserves the factual-overstatement risk
relevant to archive-based diagnosis.
```
