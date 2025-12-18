# Session End Protocol

Execute these steps IN ORDER before ending a work session:

## Step 1: Clean Up Code

Before committing, ensure code is clean:

```bash
# Check for debug statements that should be removed
grep -rn "console.log\|print(\|debugger\|TODO: REMOVE" --include="*.ts" --include="*.js" --include="*.py" --include="*.svelte" . 2>/dev/null | grep -v node_modules | grep -v ".git" | head -20
```

Remove any:
- Debug print/log statements (unless intentional logging)
- Commented-out code blocks
- TODO markers for temporary code
- Hardcoded test values

## Step 2: Update Task Status

Update `agent-os/specs/[this-spec]/tasks.md`:
- Mark completed tasks with `- [x]`
- Add notes for partially completed tasks
- Document any blockers discovered

## Step 3: Update Progress File

Update or create `agent-os/specs/[this-spec]/progress.json`:

```json
{
  "spec_name": "[spec-name]",
  "status": "in_progress",
  "current_task_group": [N],
  "last_completed_task": "[X.Y]",
  "last_updated": "[ISO timestamp]",
  "last_session_summary": "[Brief description of what was accomplished]",
  "blocking_issues": [],
  "next_task": "[X.Y] - [description]",
  "session_count": [N]
}
```

Write a clear, actionable `last_session_summary` that future sessions can use to quickly understand context.

## Step 4: Git Commit

Commit changes with a descriptive message:

```bash
# Stage implementation changes
git add -A

# Commit with descriptive message
git commit -m "[spec-name] Task X.Y: [brief description]

- [Key change 1]
- [Key change 2]
- [Key change 3]

Progress: [X/Y] tasks in group [N] complete"
```

**Commit message guidelines:**
- Start with spec name for easy filtering
- Include task number for traceability
- List key changes made
- Note progress status

## Step 5: Trigger Self-Improvement (Optional)

If significant patterns or learnings emerged, delegate to the **self-improver** subagent:

```
Use the self-improver subagent to update expertise based on:
- Files modified: [list]
- Patterns discovered: [brief description]
- Domain affected: [frontend/backend/etc]
```

## Step 6: Run Final Verification

```bash
# Verify the codebase is in good state
if [ -f "agent-os/specs/[this-spec]/verifications/verify.sh" ]; then
    ./agent-os/specs/[this-spec]/verifications/verify.sh
fi

# Run relevant tests if available
npm test 2>/dev/null || python -m pytest 2>/dev/null || echo "No test runner found"
```

## Step 7: Session Summary Output

Output a clear session summary:

```
═══════════════════════════════════════════
SESSION COMPLETE
═══════════════════════════════════════════

✅ Completed: Task [X.Y] - [description]
📁 Files Modified: [count] files
📝 Commit: [commit hash - first 7 chars]

📊 Progress: [X/Y] tasks in group [N]
👉 Next: Task [X.Y] - [description]

⚠️  Notes: [Any blockers or concerns for next session]
═══════════════════════════════════════════
```

This summary provides quick context for the next session or human review.
