# Design: validate-changes-python skill

**Date:** 2026-06-04  
**Status:** Approved  
**Scope:** Claude Code skill for iteratively running the Python-migrated testsuite on a dev controller, auto-fixing failures, and tracking progress across sessions.

---

## Problem

The Uyuni testsuite is being migrated from Ruby/Cucumber to Python/pytest-bdd. There are 263 feature files. As step definitions are ported, each feature must be validated against a real controller. Failures need to be diagnosed and fixed before moving on. The process must survive session interruptions (token limits, connection drops) and support multiple Claude sessions working on the same run.

---

## Solution Overview

A stateful skill that:
1. Pulls latest code to the controller
2. Runs feature files one by one in order
3. On failure: auto-fixes in `/app`, commits, pulls to controller, reruns (up to 3 attempts)
4. After 3 failed attempts: marks feature STUCK, moves on
5. Persists all progress to a state file — resumable across sessions

---

## Architecture

### State File

Location: `/home/claude/.claude/projects/-app/validate_python_state.json`

```json
{
  "features": [
    "features/core/allcli_sanity.feature",
    "features/core/srv_docker.feature",
    "..."
  ],
  "current_index": 42,
  "attempt": 1,
  "results": {
    "features/core/allcli_sanity.feature": "PASS",
    "features/core/srv_docker.feature": "STUCK"
  },
  "stuck_errors": {
    "features/core/srv_docker.feature": "ImportError: cannot import 'click_on' ..."
  }
}
```

- **First run**: enumerate all `.feature` files sorted alphabetically by path, write state
- **Resume**: read state, skip PASS features, continue from `current_index`
- **Reset**: user says "start from scratch" → delete state file, begin anew

### Controller Access

```bash
sshpass -p linux ssh -o StrictHostKeyChecking=no \
  root@maxime-controller.mgr.suse.de \
  "cd /root/uyuni/testsuite && {command}"
```

Credentials: host `maxime-controller.mgr.suse.de`, user `root`, password `linux`.

---

## Run Loop

### Session Start (once per session)

1. Ensure all local changes in `/app` are committed
2. SSH → `git pull origin {branch}`
3. SSH → `pip3.11 install -e .`
4. Load state file (or create if first run)

### Per-Feature Loop

```
for each feature at current_index:

  1. SSH → pytest -v {feature} --tb=short 2>&1
  
  2. Exit 0 → mark PASS, increment index, save state, next feature
  
  3. Exit != 0 (attempt ≤ 3):
     a. Parse error output → classify error type
     b. Fix in /app/testsuite/ (minimal change)
     c. Syntax check: python3 -c "import ast; ast.parse(open(file).read())"
     d. git commit -m "fix(python-migration): {error_summary}"
     e. SSH → git pull
     f. SSH → pytest -v {feature} --tb=short 2>&1
     g. Pass → PASS, next feature
     h. Fail → increment attempt, back to step 3
  
  4. attempt > 3 → mark STUCK, save error, increment index, next feature
```

**Pause condition:** 3 STUCK features in a row → report and stop. Likely signals infrastructure issue (no SUMA server, missing env var) rather than code problem.

---

## Error Classification & Fix Strategies

| Pattern in output | Classification | Fix |
|---|---|---|
| `Step 'X' is not defined` | Missing step | Add `@when`/`@given`/`@then` to appropriate step file |
| `AmbiguousStep` | Duplicate step pattern | Deduplicate: merge into one function with stacked decorators |
| `ImportError: cannot import name 'X'` | Bad import | Fix import path or add `X` to the module |
| `ModuleNotFoundError: No module named 'X'` | Missing module | Fix module path |
| `TypeError: X() got unexpected keyword argument` | Fixture mismatch | Fix function/fixture signature |
| `AssertionError` in step body | Logic error | Fix Playwright locator or assertion in step definition |
| `SyntaxError` | Python syntax | Fix syntax in the affected file |

**Fix discipline:**
- Read the file before editing (required by system rules)
- Make minimal changes — do not refactor surrounding code
- One commit per feature failure cycle

---

## Progress Reporting

### During run (after each feature)
```
[42/263] PASS  features/core/allcli_sanity.feature
[43/263] STUCK features/core/srv_docker.feature (3 attempts)
[44/263] PASS  features/core/srv_first_settings.feature
```

### Session end summary
```
── Validate Python Run ──────────────────────────
Completed : 44 / 263
PASS      : 41
STUCK     : 3
Remaining : 219

STUCK features:
  features/core/srv_docker.feature
    Error: ImportError: cannot import 'click_on' from support...

Resume: next session starts at features/core/srv_organization_credentials.feature
─────────────────────────────────────────────────
```

---

## Trigger Phrases

- `"validate python"` / `"run validate"` / `"validate changes"`
- `"continue validation"` / `"resume validation"` → resume from state
- `"start from scratch"` → reset state file, begin from feature 0

---

## Skill File Location

`/home/claude/.claude/skills/validate-changes-python/SKILL.md`

Must be registered in:
- `/home/claude/.claude/CLAUDE.md` fast-track section
- `/home/claude/.claude/TOOLS.md` (if it exists)

---

## Constraints & Rules

- Never commit with `--no-verify`
- Never force-push
- Always read a file before editing it
- Max 3 fix attempts per feature — mark STUCK and continue, do not loop forever
- SSH is read/write to this controller only (it's the user's dev controller)
- `sshpass` must be available in the environment (check at session start)
- The pytest command must be run from `/root/uyuni/testsuite` on the controller
- State file is the single source of truth — always save after every state change
