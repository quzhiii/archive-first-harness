# CLI Cross-Platform Command Compatibility Specification

## 1. Overview
This document addresses the compatibility issues encountered during UAT testing on different operating systems and shell environments (CMD, PowerShell, Bash).

## 2. Command Syntax by Shell

### 2.1 Windows PowerShell (Recommended for Windows)
PowerShell requires explicit environment variable setting before the command or on the same line using a semicolon.
```powershell
# Set PYTHONPATH and run
$env:PYTHONPATH="."; python -m entrypoints.cli run --task "ping" --task-type retrieval
```
**Common Pitfall**: Using `PYTHONPATH=.` without `$env:` will result in "Command syntax is incorrect".

### 2.2 Windows CMD
CMD uses `set` and `&` to chain commands.
```cmd
set PYTHONPATH=. & python -m entrypoints.cli run --task "ping" --task-type retrieval
```

### 2.3 Linux / macOS (Bash/Zsh)
Environment variables can be set inline before the command.
```bash
PYTHONPATH=. python3 -m entrypoints.cli run --task "ping" --task-type retrieval
```

## 3. Quoting and Special Characters
- **Double Quotes**: Always wrap the task description in double quotes: `--task "My task description"`.
- **Special Characters**: In PowerShell, characters like `$` or `(` have special meanings. If your task contains them, use single quotes: `--task 'Search for $HOME variable'`.

## 4. Minimal Verification Task (Ping)
To verify the installation and basic harness connectivity without triggering complex logic or timeouts:
```bash
# Run the ping task
python -m entrypoints.cli run --task "ping" --task-type retrieval
```
**Expected Outcome**: A JSON response containing `"status": "success"` and a `run_id` within 10 seconds.

## 5. Implementation Improvements
To improve compatibility across all Python versions and environments, we have added `__init__.py` files to the following directories:
- `entrypoints/`
- `runtime/`
- `harness/` (and subdirectories)
- `planner/`

This ensures that the `python -m` command and internal imports work reliably without relying on implicit namespace packages.
