# Bootstrap Project Expertise

Initialize or rebuild domain expertise files for this project by analyzing the codebase structure and product context.

## When to Use

Run this command:
- **After `/plan-product`** - To set up expertise for a new project
- **When adding Agent OS to an existing codebase** - To create expertise from existing code
- **To rebuild stale expertise** - When expertise files have drifted from reality

## Process

{{IF use_claude_code_subagents}}
Delegate to the **meta-expert** subagent to bootstrap expertise:

Provide to the subagent:
- Path to product folder: `agent-os/product/`
- The current project root directory

The subagent will:
1. Read product context (mission.md, tech-stack.md, roadmap.md)
2. Analyze the existing codebase structure
3. Identify domains that need expertise files based on tech stack
4. Create `agent-os/expertise/_index.yaml`
5. Create expertise files for each identified domain
6. Validate all file paths and patterns exist
{{ENDIF use_claude_code_subagents}}

{{UNLESS use_claude_code_subagents}}
### Step 1: Read Product Context

```bash
cat agent-os/product/mission.md
cat agent-os/product/tech-stack.md
cat agent-os/product/roadmap.md 2>/dev/null || echo "No roadmap yet"
```

Extract the product purpose, technology choices, and architectural patterns.

### Step 2: Analyze Codebase Structure

```bash
# Get directory structure
find . -type d -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" | head -50

# Find key file types
find . -name "*.ts" -o -name "*.svelte" -o -name "*.py" | grep -v node_modules | head -30

# Check for common framework indicators
ls -la prisma/ 2>/dev/null
ls -la src/routes/ 2>/dev/null
cat package.json 2>/dev/null | head -50
```

### Step 3: Identify Domains

Based on tech-stack.md and codebase analysis, determine which domains need expertise:

| Tech Stack Component | Domain | Expertise File |
|---------------------|--------|----------------|
| SvelteKit, React, Vue | frontend | frontend.yaml |
| Flask, FastAPI, Express | api | api.yaml |
| Prisma, Drizzle, SQLAlchemy | database | database.yaml |
| Jest, Pytest, Vitest | testing | testing.yaml |
| Custom system | {system-name} | {system-name}.yaml |

### Step 4: Create Expertise Directory

```bash
mkdir -p agent-os/expertise
```

### Step 5: Create Expertise Index

Create `agent-os/expertise/_index.yaml` with:
- Project name and description (from mission.md)
- List of domains with their key paths
- Tech stack summary (from tech-stack.md)
- Specialist agent mappings (optional)

Use the template in `agent-os/expertise/_templates/_index.yaml.template` as a starting point.

### Step 6: Create Domain Expertise Files

For each identified domain, create `agent-os/expertise/{domain}.yaml` using the templates in `agent-os/expertise/_templates/` as starting points.

Each domain file should include:
- **overview**: Purpose, framework, status
- **architecture**: Entry points, directories, structure patterns
- **data_flow**: How information moves through the system
- **patterns**: Established conventions to follow
- **key_files**: Critical files frequently referenced
- **recent_changes**: Empty initially (populated by self-improver)

### Step 7: Validate Created Expertise

For each expertise file created, verify:
1. All listed file paths actually exist
2. Patterns match observed code
3. Data flow descriptions are accurate

```bash
# Example validation
for path in $(grep "path:" agent-os/expertise/frontend.yaml | awk '{print $2}' | tr -d '"'); do
    [ -e "$path" ] && echo "✓ $path" || echo "✗ MISSING: $path"
done
```
{{ENDUNLESS use_claude_code_subagents}}

## Output

After completion, output:

```
═══════════════════════════════════════════
EXPERTISE BOOTSTRAP COMPLETE
═══════════════════════════════════════════

Project: [name]
Domains Created: [count]

✓ agent-os/expertise/_index.yaml
✓ agent-os/expertise/frontend.yaml
✓ agent-os/expertise/api.yaml
✓ agent-os/expertise/database.yaml

Next Steps:
1. Review generated expertise for accuracy
2. Configure specialist agents in _index.yaml (optional)
3. Customize routing in agent-os/routing.yaml (optional)
═══════════════════════════════════════════
```

## Tips

- **Start simple** - You can always add more domains later
- **Validate paths** - Expertise is only useful if it points to real code
- **Keep it focused** - Each domain file should cover ONE area of the system
- **Commit the expertise** - It should be version controlled with your project
