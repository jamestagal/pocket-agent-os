# Self-Improve Expertise

Update expertise files based on completed work. This captures patterns and learnings automatically.

## When to Self-Improve

- After completing a task group
- When significant patterns are discovered
- When existing expertise is found to be incorrect
- After introducing new architectural patterns

## Self-Improvement Process

### Step 1: Gather Recent Changes

```bash
# Get list of changed files
git diff HEAD~1 --name-only

# Get summary of changes
git diff HEAD~1 --stat

# For detailed changes (optional)
git diff HEAD~1 -- [specific-file]
```

### Step 2: Identify Affected Domains

Map changed files to expertise domains:

| Changed Files Pattern | Affected Domain |
|----------------------|-----------------|
| `src/routes/`, `src/lib/components/` | frontend |
| `src/lib/server/`, `api/`, `routes/+server` | api |
| `prisma/`, `drizzle/`, `**/models/` | database |
| `tests/`, `*.test.*`, `*.spec.*` | testing |
| Custom system paths | {custom domain} |

### Step 3: Read Current Expertise

For each affected domain:

```bash
cat agent-os/expertise/{domain}.yaml
```

### Step 4: Validate Against Code

For each section in the expertise file, verify accuracy:

**Architecture Section:**
- Do the listed entry points still exist?
- Are the file paths correct?
- Are the described patterns still used?

**Data Flow Section:**
- Is the flow description accurate?
- Have any new integration points been added?

**Patterns Section:**
- Are the documented patterns still followed?
- Were new patterns introduced?

### Step 5: Identify Updates Needed

Compare current expertise with observed code:

**Add to expertise:**
- New files/modules created
- New patterns established
- New integration points
- New utilities or helpers

**Update in expertise:**
- Changed file paths
- Modified patterns
- Updated data flows

**Remove from expertise:**
- Deleted files
- Deprecated patterns
- Removed integrations

### Step 6: Update Expertise File

Apply changes to the YAML structure:

```yaml
# Example update
overview:
  last_updated: "[ISO timestamp]"
  
architecture:
  key_files:
    - path: "[new-file-path]"
      purpose: "[description]"

recent_changes:
  - date: "[ISO date]"
    description: "[what changed]"
    task: "[task X.Y]"
```

### Step 7: Commit Expertise Update

```bash
git add agent-os/expertise/
git commit -m "chore(expertise): Update {domain} after Task X.Y

- [Change 1]
- [Change 2]"
```

## Important Guidelines

- **Code is source of truth** - expertise describes code, not the other way around
- **Be specific** - vague descriptions don't help navigation
- **Update timestamps** - always mark when expertise was last verified
- **Keep it focused** - each domain file covers ONE area of the system
