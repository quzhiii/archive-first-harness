# External UAT Quickstart

Date: 2026-04-02  
Version: v1.2

This document is for public alpha testers who want to verify the core archive loop with the smallest possible setup cost.

The goal is not to understand the whole architecture first. The goal is to finish one real loop:

`inspect-state -> run -> archive --latest -> compare`

---

## Before You Start

### Recommended Environment

- Windows PowerShell or CMD
- Python `3.13.2`
- Repository cloned locally

### Dependency Note

Current baseline runtime dependencies: **none**  
There is no required third-party package install for the current baseline.

### Important First-Impression Advice

For the first try:

- do not start by reading the full raw `run` JSON
- start with `archive --latest`
- treat the test as "Can I understand what happened?" rather than "Can I make it look impressive?"

---

## Step 1: Inspect State

### PowerShell

```powershell
$env:PYTHONPATH="."
python -m entrypoints.cli inspect-state
```

### CMD

```cmd
set PYTHONPATH=.
python -m entrypoints.cli inspect-state
```

### Expected Result

The command should return a normal state summary without throwing import or path errors.

---

## Step 2: Run a Minimal Task

### PowerShell

```powershell
$env:PYTHONPATH="."
python -m entrypoints.cli run --task "ping" --task-type retrieval
```

### CMD

```cmd
set PYTHONPATH=.
python -m entrypoints.cli run --task "ping" --task-type retrieval
```

### Expected Result

You should see:

- `"status": "success"`
- a newly generated `run_id`
- a normal JSON response instead of a crash

---

## Step 3: Read the Latest Archive

```bash
python -m entrypoints.cli archive --latest
```

### What To Look For

- Can you quickly understand what this run was?
- Can you find the `run_id`, task type, and key output summary?
- Does the archive summary feel easier to read than the raw `run` JSON?

---

## Step 4: Browse by Filter

Try one or both of these:

```bash
python -m entrypoints.cli archive --task-type retrieval --limit 10
python -m entrypoints.cli archive --status failed --limit 10
```

### What To Look For

- Can you find the run you want without opening raw files?
- Do the filters feel understandable?

---

## Step 5: Compare Two Runs

Pick two real run ids and compare them:

```bash
python -m entrypoints.cli archive --compare-run-id <id_1> --compare-run-id <id_2>
```

### What To Look For

- Can you tell why one run is better or worse?
- Does the compare output help you make a diagnosis faster?
- Would you use this instead of manually reading two raw outputs?

---

## What We Actually Want Feedback On

The most useful feedback is not "this is cool."

Please focus on these questions:

1. Where did you get stuck?
2. Which command or output was confusing?
3. Did `archive --latest` help more than raw `run` output?
4. Did `compare` actually help you reason about differences?
5. If this were part of your workflow, what would still block real use?

---

## Pass Criteria

A tester can be counted as "basic pass" if they can do all of the following:

- run `inspect-state`
- run the `ping` task successfully
- open `archive --latest`
- understand what happened without reading every raw artifact file

An "extended pass" means they can also:

- browse filtered runs
- compare two runs
- explain which output is more useful and why

---

## Known Current Friction

Based on the current UAT evidence, the main friction points are:

- first-run shell differences between PowerShell and CMD
- users paying too much attention to raw `run` JSON at the start
- onboarding still being more technical than it should be

The archive logic itself is not the main problem at this stage. The main problem is first-run clarity.
