# Show Spec Progress

Display the current progress state for a spec, including completed tasks, blocking issues, and next steps.

## When to Use

Run this command:
- **At session start** - To quickly understand where you left off
- **During implementation** - To check overall progress
- **After interruptions** - To regain context on a spec

## Process

### Step 1: Identify Target Spec

**If a spec name was provided:** Use that spec.

**If no spec was provided:** Find the most recent spec:

```bash
# Get most recent spec by folder date
ls -t agent-os/specs/ | head -1
```

### Step 2: Verify Spec Exists

```bash
SPEC_PATH="agent-os/specs/[spec-name]"

if [ ! -d "$SPEC_PATH" ]; then
    echo "❌ Spec not found: $SPEC_PATH"
    echo ""
    echo "Available specs:"
    ls agent-os/specs/
    exit 1
fi
```

### Step 3: Load Progress Data

Check for progress.json:

```bash
if [ -f "$SPEC_PATH/progress.json" ]; then
    cat "$SPEC_PATH/progress.json"
else
    echo "No progress.json found - this spec may not have progress tracking enabled."
fi
```

### Step 4: Load Tasks Status

Read tasks.md and count completion:

```bash
# Count completed vs total tasks
COMPLETED=$(grep -c "^\s*- \[x\]" "$SPEC_PATH/tasks.md" 2>/dev/null || echo "0")
TOTAL=$(grep -c "^\s*- \[" "$SPEC_PATH/tasks.md" 2>/dev/null || echo "0")
```

### Step 5: Display Progress Summary

Output the progress report:

```
═══════════════════════════════════════════════════════════════
📊 PROGRESS: [spec-name]
═══════════════════════════════════════════════════════════════

Status: [status from progress.json or "unknown"]
Overall: [COMPLETED]/[TOTAL] tasks complete ([percentage]%)

┌─────────────────────────────────────────────────────────────┐
│ Current Focus                                                │
├─────────────────────────────────────────────────────────────┤
│ Task Group: [N] - [group name]                              │
│ Next Task:  [X.Y] - [task description]                      │
│ Last Done:  [X.Y] - [task description]                      │
└─────────────────────────────────────────────────────────────┘

📝 Last Session Summary:
   [last_session_summary from progress.json]

⚠️  Blocking Issues:
   [blocking_issues from progress.json or "None"]

📋 Task Groups Overview:
   [1] Setup & Scaffolding      ████████░░ 4/5 tasks
   [2] Core Implementation      ██░░░░░░░░ 1/5 tasks  ← CURRENT
   [3] Testing & Verification   ░░░░░░░░░░ 0/4 tasks

═══════════════════════════════════════════════════════════════
```

### Step 6: Suggest Next Action

Based on the progress state:

**If blocking issues exist:**
```
⚠️  ACTION NEEDED: Resolve blocking issues before continuing
    → [description of blocker]
```

**If all tasks complete:**
```
✅ ALL TASKS COMPLETE
    → Run /implement-tasks to trigger final verification
```

**Otherwise:**
```
👉 CONTINUE WITH: Task [X.Y] - [description]
    → Run /implement-tasks to continue implementation
```

## Output Formats

### Minimal (for quick checks)

```
[spec-name]: 12/20 tasks (60%) | Current: Task 2.3 | No blockers
```

### Full (default)

The full progress report as shown above.

### JSON (for automation)

```json
{
  "spec_name": "[name]",
  "status": "[status]",
  "progress": {
    "completed": 12,
    "total": 20,
    "percentage": 60
  },
  "current_task": {
    "group": 2,
    "task": "2.3",
    "description": "[description]"
  },
  "blocking_issues": [],
  "last_session": "[summary]"
}
```

## Tips

- **Run at session start** - Get context quickly before diving in
- **Check for blockers** - Address issues before starting new work
- **Use with /implement-tasks** - Progress tracking works best when using the full workflow
