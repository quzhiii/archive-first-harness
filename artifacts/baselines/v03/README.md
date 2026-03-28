# v0.3 Baseline Samples

This directory stores the frozen v0.3 baseline samples used for later regression and diff checks.

## Recognition Rule

Only top-level `*.json` files in this directory are baseline samples.
Ignore temporary directories, inaccessible temp folders, and non-JSON spillover.
Any future collector should enumerate the known JSON files directly or glob only top-level `*.json`.

## Frozen JSON Samples

- `success_event_trace.json`
- `sandbox_success_trace.json`
- `rollback_path_trace.json`
- `governance_followup_trace.json`
- `journal_append_trace.json`
- `success_verification_report.json`
- `success_residual_followup.json`
- `success_metrics_summary.json`
