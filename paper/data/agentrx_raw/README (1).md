---
license: cc-by-4.0
configs:
  - config_name: default
    data_files:
      - split: tau_retail
        path: tau_retail.jsonl
      - split: magentic_one
        path: magentic_one.jsonl

  - config_name: trajectories
    data_files:
      - split: magentic_dataset
        path: magentic_dataset.jsonl
      - split: tau_retail
        path: tau_retail_dataset.jsonl
---

# AgentRx Benchmark

## 1. Dataset Summary

**Name:** AgentRx (Agent Root Cause Attribution Benchmark)

**Purpose:**  
AgentRx is designed to support research on diagnosing failures in multi-agent LLM systems. The dataset contains failed agent trajectories annotated with step-level failure categories and a designated root cause failure. It enables research on root cause localization, agent debugging, trajectory-level reasoning, and constraint-based supervision

**Domains:**
- tau_retail
- magentic_one

**License:** cc-by-4.0

---

## 2. Data Fields / Format

Each row corresponds to a single failed trajectory.

- `trajectory_id` (string): Unique identifier for the trajectory.
- `failure_summary` (string): High-level natural language description of what went wrong.
- `failures` (list of dicts): All the failures in the trajectory along with step number and the failure category
  - `failure_id` (string)
  - `step_number` (int)
  - `step_reason` (string)
  - `failure_category` (string)
  - `category_reason` (string)
  - `failed_agent` (string)
- `root_cause` (dict): The first unrecoverable critical failure in the entire trajectory
  - `failure_id` (string)
  - `reason_for_root_cause` (string)
- `root_cause_failure_id` (string)
- `root_cause_reason` (string)
- `num_failures` (int)

---

## 3. Split Structure

The dataset is organized into two domain splits:

- `tau_retail` — Retail agentic workflows.
- `magentic_one` — Complex multi-agent web and file workflows.

Each split contains failed trajectories with structured failure annotations.

---

## 4. Intended Uses

This dataset is intended for:

- Root cause localization
- Failure classification
- Agent debugging research
- Multi-agent reasoning analysis
- Constraint-based training signals
---

## 5. Citation

If you use AgentRx, please cite:

```bibtex
@article{barke2026agentrx,
  title={AgentRx: Diagnosing AI Agent Failures from Execution Trajectories},
  author={Barke, Shraddha and Goyal, Arnav and Khare, Alind and Singh, Avaljot and Nath, Suman and Bansal, Chetan},
  journal={arXiv preprint arXiv:2602.02475},
  year={2026}
}