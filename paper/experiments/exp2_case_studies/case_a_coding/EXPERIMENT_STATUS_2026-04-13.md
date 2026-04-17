# Case A Experiment Status (2026-04-13)

## Summary

Case A now has a usable success/failure archive pair for the paper experiment.

- The **success run** was executed with Aider and successfully modified the target README file only.
- The original large-scope **failure-prone run** against `paper/writing/paper.tex` and `paper/writing/draft.md` was not stable enough for use:
  - one provider path failed due to response-shape incompatibility,
  - the official DeepSeek path worked but the two-file prompt hit token limits.
- A reduced-scope failure-prone experiment was then created and executed against
  `paper/experiments/exp2_case_studies/case_a_coding/failure_prone_sample.md`.
- In that reduced-scope run, Aider falsely rewrote the sample so that Case A
  appeared to already have a completed success/failure pair. This is a valid
  factual-overstatement failure example.

## Final Artifacts

- Success record template:
  `paper/experiments/exp2_case_studies/case_a_coding/template_success.json`
- Failure record template:
  `paper/experiments/exp2_case_studies/case_a_coding/template_failure.json`
- Reduced-scope failure sample:
  `paper/experiments/exp2_case_studies/case_a_coding/failure_prone_sample.md`
- Archive root:
  `paper/data/case_study_archives/case_a_coding/`

## Operational Notes

- Aider installation is working through `uv tool install --python 3.12 aider-chat`.
- Official DeepSeek (`openai/deepseek-chat`) passed:
  - raw API response-shape check
  - minimal Aider compatibility check
- The paper-wide failure-prone prompt is still too large for stable use with the
  current DeepSeek configuration and should not be treated as the primary Case A
  failure sample.

## Recommended Paper Framing

If the paper mentions the completed Case A pair, it should do so carefully:

- the success run is a repository-grounded real Aider run,
- the failure-prone sample is a reduced-scope paper excerpt designed to test
  factual overstatement under realistic writing conditions,
- the failure sample should not be described as a full-paper rewrite result.

## Compare Result Snapshot

The generated compare output shows:

- `failure=regressed`
- `verification=regressed`
- `reassessment=regressed`
- `evaluation=regressed`
- `governance=unchanged`

This is sufficient to support a Case A success/failure comparison in the archive
format used by the rest of the project.
