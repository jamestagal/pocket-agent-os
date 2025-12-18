# Load Domain Expertise

Load relevant expertise files based on the current task's domain.

## When to Load Expertise

- At session start (via session-start protocol)
- When switching to a task in a different domain
- When working with unfamiliar code areas

## Load Process

### Step 1: Identify Required Domains

Based on the current task, determine which domains are relevant:

| Task Involves | Domain | Expertise File |
|---------------|--------|----------------|
| UI components, pages, routes | frontend | `expertise/frontend.yaml` |
| API endpoints, server logic | api | `expertise/api.yaml` |
| Database queries, models, migrations | database | `expertise/database.yaml` |
| Tests, testing utilities | testing | `expertise/testing.yaml` |
| Project-specific system | {custom} | `expertise/{system}.yaml` |

A single task may span multiple domains (e.g., a full-stack feature).

### Step 2: Check Expertise Index

```bash
# Read the expertise index to understand available domains
cat agent-os/expertise/_index.yaml 2>/dev/null || echo "No expertise index found"
```

The index maps domains to their key paths and provides overview.

### Step 3: Load Domain Files

For each relevant domain:

```bash
cat agent-os/expertise/{domain}.yaml
```

### Step 4: Validate Key Paths

For critical operations, validate that key paths in expertise still exist:

```bash
# Example: Validate frontend entry points
for path in $(grep "entry_point:" agent-os/expertise/frontend.yaml | awk '{print $2}'); do
    [ -f "$path" ] && echo "✓ $path" || echo "✗ $path (MISSING)"
done
```

If paths are invalid, the expertise file may be stale and need updating.

### Step 5: Apply Expertise

Use the loaded expertise to:
- Navigate directly to relevant files (no blind searching)
- Follow established patterns for the domain
- Understand data flow before making changes
- Avoid reinventing existing utilities

## Expertise File Not Found

If no expertise exists for a domain:
1. Check if `meta-expert` has been run for this project
2. Consider running `/bootstrap-expertise` command
3. Fall back to standard codebase exploration
