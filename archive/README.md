# PocketFlow CLI (Archived)

This directory contains the original Python CLI implementation that was replaced by Claude Code native slash commands.

## Why Archived?

The slash command approach (`/agent-os pocketflow-implement-all`) achieves the same orchestration entirely within Claude Code without requiring:
- External Python scripts
- CLI execution
- JSON progress tracking

The concepts from this code (nodes, flows, routing) informed the design but the implementation wasn't needed.

## Contents

- `core/` - PocketFlow framework (nodes, flows, store)
- `run-flow.py` - CLI entry point

## If You Need CLI Features

The CLI still works if you want:
- Batch previews outside Claude Code
- JSON progress tracking
- Integration with other tools

To use:
```bash
cd /path/to/project
python3 ~/pocket-agent-os/archive/run-flow.py implement --spec feature-name --mode batch
```

Requires: `pip3 install pyyaml`
