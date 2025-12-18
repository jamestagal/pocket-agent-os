# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent OS is a framework for spec-driven agentic development. It provides structured workflows that give AI coding agents the specs they need to ship quality code. Works with Claude Code, Cursor, or any AI coding tool.

## Common Commands

### Installation Scripts

```bash
# Install Agent OS into a project (run from project directory)
~/pocket-agent-os/scripts/project-install.sh

# With options
~/pocket-agent-os/scripts/project-install.sh --profile default --claude-code-commands true --use-claude-code-subagents true

# Update existing installation
~/pocket-agent-os/scripts/project-update.sh

# Re-install (deletes and reinstalls)
~/pocket-agent-os/scripts/project-install.sh --re-install

# Dry run (show what would be created)
~/pocket-agent-os/scripts/project-install.sh --dry-run

# Create a custom profile
~/pocket-agent-os/scripts/create-profile.sh --name my-profile
```

### PocketFlow CLI (Python workflows)

```bash
# Run from a project with Agent OS installed
./agent-os/run-flow status              # Show session/progress status
./agent-os/run-flow bootstrap           # Initialize expertise for project
./agent-os/run-flow spec --name my-feature --requirements "Build X"
./agent-os/run-flow implement --spec my-feature
./agent-os/run-flow implement --spec my-feature --session <session-id>  # Resume
```

## Architecture

### Core Framework (`core/`)

- **pocketflow/**: Minimalist LLM framework (~100 lines, vendored from PocketFlow). Core concepts:
  - `Node`: Executes tasks via `prep → exec → post` lifecycle
  - `Flow`: Orchestrates nodes via action-based transitions
  - Shared Store: Python dict for inter-node communication
  - Supports batch processing and async/await

- **nodes/**: PocketFlow nodes for Agent OS features
  - `session.py`: Session lifecycle management (start/end, checkpoints)
  - `expertise.py`: Domain knowledge loading and caching
  - `routing.py`: Smart agent selection based on task analysis
  - `delegation.py`: Task delegation to subagents
  - `progress.py`: Task state tracking and persistence

- **flows/**: Pre-built workflow compositions
  - `ImplementationFlow`: Full implementation workflow
  - `SpecificationFlow`: Spec creation workflow
  - `BootstrapFlow`: Expertise initialization

- **store/**: Persistence layer (`FileStore` for JSON-based session/state storage)

- **utils/**: Helpers for git operations and Claude API integration

### Profiles (`profiles/`)

Template system for different project types. Each profile contains:
- `agents/`: Claude Code subagent definitions
- `commands/`: Slash command templates (multi-agent and single-agent variants)
- `standards/`: Code standards (backend, frontend, global, testing)
- `workflows/`: Reusable workflow snippets (planning, specification, implementation)
- `expertise/`: Domain expertise templates
- `routing/`: Agent routing configuration templates

### Scripts (`scripts/`)

- `project-install.sh`: Main installation script - compiles templates from profiles into project
- `project-update.sh`: Updates existing installations preserving customizations
- `create-profile.sh`: Creates new profiles from default template
- `common-functions.sh`: Shared bash utilities (config parsing, file copying, template compilation)
- `run-flow.py`: Python CLI for PocketFlow execution

### Configuration (`config.yml`)

Root configuration controlling installation behavior:
- `claude_code_commands`: Install `.claude/commands/agent-os/`
- `use_claude_code_subagents`: Enable multi-agent delegation
- `agent_os_commands`: Install `agent-os/commands/` for non-Claude tools
- `standards_as_claude_code_skills`: Use Claude Code Skills for standards
- PocketFlow v3.0 enhancements: `session_management`, `expertise_tracking`, `progress_tracking`, `smart_routing`, `self_improvement`

## Template Compilation

Commands and agents use conditional compilation via template markers:
- `{{IF flag}}...{{ENDIF flag}}`: Include block if flag is true
- `{{UNLESS flag}}...{{ENDUNLESS flag}}`: Include block if flag is false
- `{{workflows/path/to/workflow}}`: Inline workflow content

These are processed by `compile_command()` and `compile_agent()` in `common-functions.sh`.

## Installed Project Structure

When Agent OS is installed into a project, it creates:
```
project/
├── agent-os/
│   ├── config.yml           # Project-specific config
│   ├── standards/           # Code standards
│   ├── expertise/           # Domain expertise files
│   ├── sessions/            # Session state persistence
│   ├── specs/               # Feature specifications
│   │   └── <spec-name>/
│   │       ├── spec.md
│   │       ├── tasks.md
│   │       └── progress.json
│   └── run-flow             # PocketFlow CLI wrapper
└── .claude/
    ├── commands/agent-os/   # Claude Code slash commands
    └── agents/agent-os/     # Claude Code subagents
```
