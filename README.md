# Pocket Agent OS

A Claude Code native orchestration system that automates spec-driven development with domain-specialist routing.

## What It Does

Run a single command in Claude Code:
```
/agent-os pocketflow-implement-all wishlist
```

And it automatically:
1. **Parses** your `tasks.md` into task groups by `### ` headers
2. **Routes** each group to the right specialist (database → database-specialist, API → api-specialist, etc.)
3. **Delegates** sequentially with full context
4. **Verifies** completion before moving to next group
5. **Reports** progress throughout

## Key Components

### Specialist Agents (`profiles/default/agents/`)

| Agent | Expertise |
|-------|-----------|
| `database-specialist` | Drizzle ORM, SQLite/D1, schema design, migrations |
| `api-specialist` | SvelteKit server routes, form actions, load functions |
| `frontend-specialist` | Svelte 5 runes, components, TailwindCSS, shadcn-svelte |
| `implementer` | General implementation, testing, integration |

### Slash Commands (`profiles/default/commands/`)

| Command | Purpose |
|---------|---------|
| `pocketflow-implement-all` | Automated implementation with specialist routing |
| `implement-tasks` | Original Agent OS implementation flow |
| `create-tasks` | Generate tasks.md from spec |
| `write-spec` | Write specification from requirements |
| `shape-spec` | Refine and improve a spec |

## Installation

### 1. Clone the repo
```bash
git clone https://github.com/jamestagal/pocket-agent-os.git ~/pocket-agent-os
```

### 2. Install to your project
```bash
cd /path/to/your/project
~/pocket-agent-os/scripts/project-install.sh
```

This creates:
- `.claude/agents/agent-os/` - Specialist agents
- `.claude/commands/agent-os/` - Slash commands
- `agent-os/` - Spec storage, product docs, workflows

### 3. Use in Claude Code
```
/agent-os pocketflow-implement-all your-feature-name
```

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  /agent-os pocketflow-implement-all wishlist                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Preview execution plan, get confirmation                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Parse tasks.md → identify ### headers                       │
│     ### Database Layer    → database-specialist                 │
│     ### API Layer         → api-specialist                      │
│     ### Frontend          → frontend-specialist                 │
│     ### Testing           → implementer                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Sequential delegation with verification                     │
│     Task Group 1 → wait for [x] → Task Group 2 → ...           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Final verification report                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Routing

The system routes task groups to specialists based on `### ` header text:

| Header Contains | Routes To |
|-----------------|-----------|
| "Database" | database-specialist |
| "API" | api-specialist |
| "Frontend", "UI", "Component" | frontend-specialist |
| "Testing", "Integration" | implementer |
| (default) | implementer |

## Project Structure

```
pocket-agent-os/
├── profiles/default/
│   ├── agents/           # Specialist agent definitions
│   ├── commands/         # Slash command prompts
│   ├── workflows/        # Reusable workflow templates
│   ├── standards/        # Coding standards by domain
│   └── routing/          # Routing configuration
├── scripts/
│   └── project-install.sh
└── archive/              # Archived CLI implementation
```

## License

MIT
