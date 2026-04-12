# External Tester Feedback Checklist

Date: 2026-04-12  
Scope: public alpha first-run feedback

This checklist is for external testers who use the new onboarding flow:

- `python quickstart.py`
- `python -m entrypoints.cli demo`
- `python -m entrypoints.cli archive --latest`
- `python -m entrypoints.cli archive --compare-run-id ... --compare-run-id ...`

The goal is not broad product feedback.

The goal is to learn whether a first-time tester can finish the smallest useful archive loop with low friction and understand what happened.

---

## Tester Info

- Date:
- Tester name or alias:
- OS / shell: PowerShell / CMD / other
- Python version:
- First time using this repo: yes / no

---

## Part 1: First-Run Path

Ask the tester to run:

```bash
python quickstart.py
```

Capture:

- Did it run successfully: yes / no
- If no, where did it fail:
- Was the output easy to follow: yes / somewhat / no
- Did the tester understand that it ran `inspect-state -> ping -> archive --latest`: yes / no
- Did the tester still feel they needed to read raw `run` JSON immediately: yes / no

Notes:

- What was the first confusing line, if any?
- What would make this feel more obvious?

---

## Part 2: Manual Archive Reading

Ask the tester to run:

```bash
python -m entrypoints.cli archive --latest
```

Capture:

- Could the tester identify the `run_id`: yes / no
- Could the tester identify the task type: yes / no
- Could the tester explain what happened in one sentence: yes / no
- Did this feel easier than reading raw run JSON: yes / no

Notes:

- Which field or section helped the most?
- Which field or section felt noisy or unclear?

---

## Part 3: Demo Compare Path

Ask the tester to run:

```bash
python -m entrypoints.cli demo
```

Then ask them to run the compare command printed by that output.

Capture:

- Was it clear that the created runs were demo runs, not real runs: yes / no
- Could the tester find the success-like and failure-like pair: yes / no
- Could the tester explain why one run was better or worse: yes / no
- Did compare help faster than manually reading two outputs: yes / no

Notes:

- What part of compare was most useful?
- What part of compare was hard to interpret?

---

## Part 4: Friction Scoring

Please score each item from 1 to 5:

- First command friction (`python quickstart.py`):
- Archive readability:
- Compare usefulness:
- Windows setup clarity:
- Confidence after first run:

Interpretation:

- 1 = very poor
- 3 = acceptable but rough
- 5 = smooth and clear

---

## Part 5: Blockers

Answer in plain language:

1. Where did you get stuck?
2. Which command or output was most confusing?
3. What almost made you stop?
4. What would need to change before you would use this again?

---

## Part 6: Pass / Fail

Mark the session as **basic pass** only if the tester could:

- run `python quickstart.py`
- understand the latest archive summary
- run a compare flow using the demo pair or two real runs
- explain what changed between two runs

Mark the session as **extended pass** only if the tester could also:

- browse runs without help
- say which output was signal vs noise
- suggest a concrete improvement based on actual usage

---

## One-Sentence Summary

- Would this tester use the repo again after this first experience: yes / no
- Why:
