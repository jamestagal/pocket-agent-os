# Progress Checkpoint

Create a checkpoint of current progress. Use this workflow:
- After completing each task (before moving to next)
- When switching between task groups
- Before any risky operation
- At natural breakpoints in implementation

## Checkpoint Process

### Step 1: Update tasks.md

Mark the just-completed task as done:

```markdown
- [x] Task X.Y: Description (← change [ ] to [x])
```

### Step 2: Update progress.json

Read the current progress file and update it:

```bash
cat agent-os/specs/[this-spec]/progress.json
```

Update these fields:
- `last_completed_task`: The task just finished
- `last_updated`: Current ISO timestamp
- `last_session_summary`: Brief note on what was done

If the task group is now complete, also update:
- `current_task_group`: Increment to next group
- `status`: Update if all groups done

### Step 3: Quick Commit (Optional but Recommended)

For significant checkpoints, create a commit:

```bash
git add -A
git commit -m "checkpoint: Task X.Y complete - [brief note]"
```

This creates restore points if something goes wrong later.

### Step 4: Verify Before Continuing

Quick sanity check before moving to next task:

```bash
# Ensure no syntax errors in recently modified files
# (This will vary by language/framework)

# For TypeScript/JavaScript
npx tsc --noEmit 2>/dev/null || true

# For Python
python -m py_compile [modified-file.py] 2>/dev/null || true
```

### Step 5: Log Checkpoint

Output checkpoint confirmation:

```
✓ CHECKPOINT: Task [X.Y] complete
  Time: [timestamp]
  Next: Task [X.Y] - [description]
```
