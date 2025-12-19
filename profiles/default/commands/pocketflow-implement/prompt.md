# PocketFlow Task Implementation

Execute the next task from the PocketFlow orchestration system.

## Workflow

### Step 1: Check for Current Delegation

Read the current delegation file:

```
agent-os/current-delegation.md
```

If this file exists, it contains the next task to implement with full context.

### Step 2: Parse the Delegation

The delegation file has this structure:
- **Header**: `# Delegation to [specialist-name] subagent` - tells you which specialist to use
- **Task**: The specific task to implement
- **Spec Context**: Full spec.md, tasks.md, requirements.md content
- **Product Context**: mission.md, roadmap.md, tech-stack.md for broader context
- **Expertise Hints**: Domain-specific patterns and conventions

### Step 3: Execute with Specialist

Delegate to the specialist agent named in the header. For example:
- `database-specialist` → Database schema, migrations, models
- `api-specialist` → Server routes, form actions, API endpoints
- `frontend-specialist` → UI components, pages, Svelte files
- `implementer` → Testing, integration, general tasks

Pass the ENTIRE delegation content to the specialist.

### Step 4: After Completion

After the specialist completes the task:

1. Verify tasks.md has been updated with `[x]` marks for completed tasks
2. Delete or clear `agent-os/current-delegation.md` to indicate completion
3. The user can then run `./agent-os/run-flow implement --spec [name] --mode file` in terminal to generate the next delegation

## Generating New Delegations

If no `current-delegation.md` exists, instruct the user to run in their terminal:

```bash
./agent-os/run-flow implement --spec [spec-name] --mode file
```

This generates the next task delegation based on what's pending in tasks.md.

## Quick Reference

| Mode | Command | Purpose |
|------|---------|---------|
| File | `--mode file` | Write delegation to `current-delegation.md` |
| Print | `--mode print` | Print to terminal (for copy/paste) |
| Batch | `--mode batch` | Show all tasks summary |
