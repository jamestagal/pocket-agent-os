# Session Start Protocol

Execute these steps IN ORDER before beginning implementation work:

## Step 1: Orient (Quick Context Gathering)

```bash
# Confirm working directory
pwd

# Check git status for any uncommitted changes
git status --short

# Review recent commits for context
git log --oneline -5
```

**If there are uncommitted changes:** Decide whether to commit them or stash them before proceeding.

## Step 2: Load Progress State

Check if progress tracking exists for this spec:

```bash
# Check for progress.json
if [ -f "agent-os/specs/[this-spec]/progress.json" ]; then
    cat agent-os/specs/[this-spec]/progress.json
fi
```

If `progress.json` exists, note:
- `last_session_summary` - What was accomplished last time
- `current_task_group` - Where we left off
- `blocking_issues` - Any unresolved problems
- `last_completed_task` - The most recent completed task

## Step 3: Load Domain Expertise

Check for relevant expertise files:

```bash
# List available expertise
if [ -d "agent-os/expertise" ]; then
    ls -la agent-os/expertise/
fi
```

Based on the current task's domain, read the relevant expertise file(s):
- Frontend tasks → Read `agent-os/expertise/frontend.yaml`
- Backend/API tasks → Read `agent-os/expertise/api.yaml`
- Database tasks → Read `agent-os/expertise/database.yaml`
- Custom domain tasks → Read `agent-os/expertise/{domain}.yaml`

## Step 4: Verify System State

If a verification script exists, run it:

```bash
# Run verification if available
if [ -f "agent-os/specs/[this-spec]/verifications/verify.sh" ]; then
    chmod +x agent-os/specs/[this-spec]/verifications/verify.sh
    ./agent-os/specs/[this-spec]/verifications/verify.sh
fi
```

**CRITICAL:** If verification fails, diagnose and fix issues BEFORE starting new work. Do not pile new code on top of broken code.

## Step 5: Select ONE Task

From `tasks.md`, identify the next incomplete task:
1. Find the current task group (from progress.json or by scanning checkboxes)
2. Within that group, find the first unchecked `- [ ]` task
3. Work on ONLY that task - do not attempt multiple tasks at once

## Step 6: Announce Intent

Before starting implementation, clearly state:
```
Starting work on Task [X.Y]: [task description]
Domain: [frontend/backend/database/etc]
Expected files to modify: [list key files]
```

This creates a clear record of what this session will accomplish.
