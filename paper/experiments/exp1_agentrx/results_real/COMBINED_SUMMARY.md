# AgentRx Real-Split Mapping Summary

## Processed splits

- `tau_retail.jsonl`: 29 failed trajectories
- `magentic_one.jsonl`: 44 failed trajectories

## Total processed

- **73 annotated failed trajectories**

## Evidence-layer stage totals

| Evidence stage | Count |
|---|---:|
| routing | 35 |
| execution | 29 |
| governance | 9 |
| unknown | 0 |

## Split-level breakdown

### tau_retail

| Evidence stage | Count |
|---|---:|
| routing | 20 |
| execution | 9 |
| governance | 0 |

Dominant categories:
- Underspecified User Intent: 8
- Intent-Plan Misalignment: 7
- Misinterpretation of Tool Output: 7

### magentic_one

| Evidence stage | Count |
|---|---:|
| routing | 15 |
| execution | 20 |
| governance | 9 |

Dominant categories:
- Misinterpretation of Tool Output: 15
- Guardrails Triggered: 9
- Instruction/Plan Adherence Failure: 8

## Interpretation

This real-data pass suggests that the four-layer Evidence Layer abstraction is already expressive enough to absorb the public AgentRx failure labels without leaving an unmapped bucket on the two released benchmark splits. In particular:

- retail workflows are dominated by **routing-stage** failures,
- multi-agent Magentic-One trajectories are more balanced between **routing** and **execution**,
- and **governance-stage** failures appear clearly in the guardrail-triggered subset.

This provides a concrete first empirical argument that the Evidence Layer stage model is not merely conceptual, but can serve as a compact abstraction over an existing agent-failure taxonomy.
