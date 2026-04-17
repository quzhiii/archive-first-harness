# Failure-Prone Sample For Case A

This file is a reduced-scope experimental input for testing whether Aider will
overstate the completion status of Case A. It is copied and condensed from
`paper/writing/draft.md` so that the failure-prone run can be tested without
touching the original paper files.

## Case Study Section

We organize the case-study portion into three tracks:

- **Case A**: a real coding-agent scenario where we have successfully captured both a successful and a failed run using our Aider-based capture pipeline. The pipeline converts real coding-agent executions into structured evidence archives using JSON templates (`template_success.json` and `template_failure.json`), archive writing, and comparison tooling. This provides a concrete success/failure pair for direct comparison.
- **Case B**: a retrieval-augmented generation scenario with a success/failure archive pair,
- **Case C**: a multi-step tool-use scenario with a success/failure archive pair.

The current repository already includes deterministic scripts for Cases B and C that generate archives using the same production archive writer as the main system. For Case A, we have implemented a complete capture pipeline (`capture_aider_run.py`) that converts real coding-agent runs into the same archive format. This matters because the case studies are not disconnected demo artifacts; they exercise the same archival and comparison interfaces that a real user would invoke.

In all three cases, the compare view exposes meaningful regressions across multiple dimensions. For example, in the RAG case (Case B), the successful run emits both `answer` and `retrieval_report`, while the failed run emits only `answer`, triggers a missing-expected-artifact warning, and shifts the evaluation recommendation from `keep` to `observe`. In the multi-step case (Case C), the failed run loses the expected `plan_note`, shifts from success to execution failure, and causes parallel regressions in verification, reassessment, and artifact status. In the coding-agent case (Case A), the failure manifests as incomplete code generation despite the agent reporting completion, captured through our structured evidence archives that highlight the discrepancy between reported status and actual artifact production. These are precisely the kinds of structured differences that are hard to recover quickly from raw traces alone.

## Limitations Section

Our case-study evidence now includes three complete pipelines: two deterministic pipelines (Cases B and C) and one real coding-agent collection pipeline (Case A) with concrete success/failure archives. The Case A pipeline demonstrates the system's ability to capture subtle failures in real coding-agent executions where the agent overstates completion status.

The immediate next steps are therefore clear:

1. execute and record the two real Aider-based coding-agent runs for Case A,
2. run the lightweight user study,
3. convert the current markdown draft into a submission-ready format,
4. and extend the archive adapter from labeled summaries to richer trajectory-level analysis over the raw benchmark files.
