"""
Session Management Nodes

Handles session lifecycle:
- SessionStartNode: Initialize session, load previous state, orient
- SessionEndNode: Save state, cleanup, summarize
- CheckpointNode: Mid-session progress persistence
"""

import os
import json
import time
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


def parse_tasks_from_markdown(tasks_content: str) -> List[Dict[str, Any]]:
    """
    Parse tasks from tasks.md content.
    
    Extracts task items in formats like:
    - [ ] 1.1 Task description
    - [x] 1.2 Completed task
    - [ ] Task without number
    
    Returns list of task objects with:
    - id: Task identifier (e.g., "1.1" or generated)
    - description: Task text
    - status: "pending" or "completed"
    - phase: Extracted from section header if available
    """
    import re
    
    tasks = []
    current_phase = "default"
    current_group = None
    
    lines = tasks_content.split('\n')
    
    for line in lines:
        # Track section headers for phase/group context
        if line.startswith('### '):
            # Task Group header like "### Task Group 1: Database Layer"
            header = line[4:].strip()
            if 'Task Group' in header:
                current_group = header
                # Extract phase from header (e.g., "Database Layer")
                if ':' in header:
                    current_phase = header.split(':', 1)[1].strip()
        elif line.startswith('## '):
            # Section header like "## Database Layer"
            current_phase = line[3:].strip()
        
        # Parse task items
        # Match patterns like: - [ ] 1.1 Description or - [x] Description
        task_match = re.match(r'^[-*]\s*\[([ xX])\]\s*(.+)$', line.strip())
        if task_match:
            checkbox = task_match.group(1)
            task_text = task_match.group(2).strip()
            
            # Try to extract task ID (e.g., "1.1", "2.3")
            id_match = re.match(r'^(\d+\.?\d*)\s+(.+)$', task_text)
            if id_match:
                task_id = id_match.group(1)
                description = id_match.group(2)
            else:
                # Generate ID from description
                task_id = task_text[:20].replace(' ', '_').lower()
                description = task_text
            
            task = {
                "id": task_id,
                "description": description,
                "full_text": task_text,
                "status": "completed" if checkbox.lower() == 'x' else "pending",
                "phase": current_phase,
                "group": current_group,
            }
            tasks.append(task)
    
    return tasks


def load_product_files(project_root: str) -> Dict[str, str]:
    """
    Load product context files from agent-os/product/.
    
    These files provide broader product context:
    - mission.md: Product mission, purpose, target users
    - roadmap.md: Features completed, current state, where new features fit
    - tech-stack.md: Technologies, frameworks, constraints
    - Any other .md files in the product folder
    
    Returns dict with filename -> content mapping.
    """
    product_dir = Path(project_root) / "agent-os" / "product"
    result = {}
    
    if not product_dir.exists():
        return result
    
    # Load all markdown files in product folder
    for md_file in product_dir.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                result[md_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            result[md_file.name] = f"[Error reading {md_file.name}]"
    
    # Also load any yaml/yml files
    for yaml_file in product_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                result[yaml_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            pass
    
    for yml_file in product_dir.glob("*.yml"):
        try:
            with open(yml_file, 'r', encoding='utf-8') as f:
                result[yml_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            pass
    
    return result


def load_spec_files(spec_path: str) -> Dict[str, Any]:
    """
    Load all files from a spec directory.
    
    Reads:
    - spec.md, tasks.md, requirements.md (main files)
    - Any other .md files in spec root
    - planning/*.md (planning documents)
    - planning/visuals/* (image paths only, not content)
    - progress.json
    
    Returns dict with:
    - files: Dict[filename, content] for text files
    - visuals: List of visual file paths
    - progress: Dict from progress.json
    """
    result = {
        "files": {},
        "visuals": [],
        "progress": None,
        "spec_path": spec_path,
    }
    
    if not os.path.exists(spec_path):
        return result
    
    spec_dir = Path(spec_path)
    
    # Load all markdown files in spec root
    for md_file in spec_dir.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                result["files"][md_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            result["files"][md_file.name] = f"[Error reading {md_file.name}]"
    
    # Load progress.json
    progress_file = spec_dir / "progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                result["progress"] = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Load planning folder if exists
    planning_dir = spec_dir / "planning"
    if planning_dir.exists() and planning_dir.is_dir():
        # Load planning markdown files
        for md_file in planning_dir.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    result["files"][f"planning/{md_file.name}"] = f.read()
            except (IOError, UnicodeDecodeError):
                result["files"][f"planning/{md_file.name}"] = f"[Error reading {md_file.name}]"
        
        # Collect visual file paths (don't load binary content)
        visuals_dir = planning_dir / "visuals"
        if visuals_dir.exists() and visuals_dir.is_dir():
            for visual_file in visuals_dir.iterdir():
                if visual_file.is_file():
                    result["visuals"].append(str(visual_file.relative_to(spec_dir)))
    
    # Load any yaml/yml config files
    for yaml_file in spec_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                result["files"][yaml_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            pass
    
    for yml_file in spec_dir.glob("*.yml"):
        try:
            with open(yml_file, 'r', encoding='utf-8') as f:
                result["files"][yml_file.name] = f.read()
        except (IOError, UnicodeDecodeError):
            pass
    
    return result


class SessionStartNode(Node):
    """
    Initialize a new session or resume an existing one.
    
    Performs:
    1. Orient (pwd, git status, recent commits)
    2. Load previous session state if exists
    3. Load ALL spec files (spec.md, tasks.md, requirements.md, planning/*, etc.)
    4. Set up session context in shared store
    
    Shared Store Inputs:
    - project_root: Path to project root (required)
    - spec_name: Active spec name (optional)
    - session_id: Explicit session ID (optional, auto-generated if missing)
    
    Shared Store Outputs:
    - session: Dict with id, started_at, resumed
    - orientation: Dict with cwd, git_status, recent_commits
    - progress: Dict loaded from progress.json (if exists)
    - spec_files: Dict with all spec file contents
    - spec_visuals: List of visual file paths
    """
    
    def __init__(self, sessions_dir: str = "agent-os/sessions", **kwargs):
        super().__init__(**kwargs)
        self.sessions_dir = sessions_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather session initialization context."""
        project_root = shared.get("project_root", os.getcwd())
        spec_name = shared.get("spec_name")
        session_id = shared.get("session_id") or f"session_{int(time.time())}"
        
        # Build spec path
        spec_path = None
        if spec_name:
            spec_path = os.path.join(project_root, "agent-os/specs", spec_name)
        
        return {
            "project_root": project_root,
            "spec_name": spec_name,
            "spec_path": spec_path,
            "session_id": session_id,
            "sessions_path": os.path.join(project_root, self.sessions_dir),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute orientation and load existing state.
        This is pure compute - no shared store access.
        """
        result = {
            "session_id": inputs["session_id"],
            "orientation": {},
            "previous_state": None,
            "progress": None,
            "spec_files": {},
            "spec_visuals": [],
            "product_files": {},
            "parsed_tasks": [],
            "spec_path": inputs["spec_path"],
            "resumed": False,
        }
        
        project_root = inputs["project_root"]
        
        # 1. Orient: Get current working directory
        result["orientation"]["cwd"] = project_root
        
        # 2. Orient: Git status (if git repo)
        try:
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            result["orientation"]["git_status"] = git_status.stdout.strip()
            
            # Recent commits
            git_log = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            result["orientation"]["recent_commits"] = git_log.stdout.strip().split("\n")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result["orientation"]["git_status"] = None
            result["orientation"]["recent_commits"] = []
        
        # 3. Load previous session state
        session_file = os.path.join(
            inputs["sessions_path"], 
            f"{inputs['session_id']}.json"
        )
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    result["previous_state"] = json.load(f)
                    result["resumed"] = True
            except (json.JSONDecodeError, IOError):
                pass
        
        # 4. Load ALL spec files (not just progress.json)
        if inputs["spec_path"]:
            spec_data = load_spec_files(inputs["spec_path"])
            result["spec_files"] = spec_data["files"]
            result["spec_visuals"] = spec_data["visuals"]
            result["progress"] = spec_data["progress"]
            
            # 4b. Parse tasks from tasks.md
            if "tasks.md" in result["spec_files"]:
                parsed_tasks = parse_tasks_from_markdown(result["spec_files"]["tasks.md"])
                result["parsed_tasks"] = parsed_tasks
        
        # 5. Load product context files (mission.md, roadmap.md, tech-stack.md, etc.)
        result["product_files"] = load_product_files(inputs["project_root"])
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Write session context to shared store."""
        # Session metadata
        shared["session"] = {
            "id": exec_res["session_id"],
            "started_at": datetime.now().isoformat(),
            "resumed": exec_res["resumed"],
            "project_root": prep_res["project_root"],
            "spec_name": prep_res["spec_name"],
        }
        
        # Orientation results
        shared["orientation"] = exec_res["orientation"]
        
        # Store spec path for delegation
        shared["spec_path"] = exec_res["spec_path"]
        
        # Store ALL spec files for delegation context
        shared["spec_files"] = exec_res["spec_files"]
        shared["spec_visuals"] = exec_res["spec_visuals"]
        
        # Store product context files
        shared["product_files"] = exec_res["product_files"]
        
        # Log what was loaded
        if exec_res["spec_files"]:
            file_list = list(exec_res["spec_files"].keys())
            print(f"   Loaded spec files: {', '.join(file_list)}")
        if exec_res["spec_visuals"]:
            print(f"   Found {len(exec_res['spec_visuals'])} visual files")
        if exec_res["product_files"]:
            product_list = list(exec_res["product_files"].keys())
            print(f"   Loaded product files: {', '.join(product_list)}")
        
        # Restore previous state if resuming
        if exec_res["previous_state"]:
            shared["previous_session"] = exec_res["previous_state"]
            # Optionally restore specific fields
            if "learnings" in exec_res["previous_state"]:
                shared["learnings"] = exec_res["previous_state"]["learnings"]
        
        # Progress from spec
        if exec_res["progress"]:
            shared["progress"] = exec_res["progress"]
        else:
            shared["progress"] = {
                "tasks": [],
                "current_task": None,
                "completed": [],
            }
        
        # Merge parsed tasks into progress
        if exec_res.get("parsed_tasks"):
            parsed = exec_res["parsed_tasks"]
            # Get pending tasks only (not already completed in tasks.md)
            pending_tasks = [t for t in parsed if t["status"] == "pending"]
            completed_from_md = [t["id"] for t in parsed if t["status"] == "completed"]
            
            # Set tasks list from parsed tasks
            shared["progress"]["tasks"] = pending_tasks
            
            # Merge completed tasks (from progress.json and tasks.md)
            existing_completed = set(shared["progress"].get("completed", []))
            existing_completed.update(completed_from_md)
            # Also check completed_tasks field (alternative format)
            if shared["progress"].get("completed_tasks"):
                existing_completed.update(shared["progress"]["completed_tasks"])
            shared["progress"]["completed"] = list(existing_completed)
            
            # Log task stats
            print(f"   Parsed {len(parsed)} tasks: {len(pending_tasks)} pending, {len(completed_from_md)} completed")
        
        # Route based on whether we're resuming
        if exec_res["resumed"]:
            return "resumed"
        return "fresh"


class SessionEndNode(Node):
    """
    End a session gracefully.
    
    Performs:
    1. Save current state to session file
    2. Commit any pending changes (if configured)
    3. Generate session summary
    
    Shared Store Inputs:
    - session: Session metadata (from SessionStartNode)
    - progress: Current progress state
    - learnings: Session learnings (optional)
    - auto_commit: Whether to auto-commit (default: False)
    
    Shared Store Outputs:
    - session_summary: Summary of what was accomplished
    """
    
    def __init__(self, sessions_dir: str = "agent-os/sessions", **kwargs):
        super().__init__(**kwargs)
        self.sessions_dir = sessions_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather state to persist."""
        session = shared.get("session", {})
        project_root = session.get("project_root", os.getcwd())
        
        return {
            "session_id": session.get("id", f"session_{int(time.time())}"),
            "project_root": project_root,
            "sessions_path": os.path.join(project_root, self.sessions_dir),
            "state_to_save": {
                "session": session,
                "progress": shared.get("progress", {}),
                "learnings": shared.get("learnings", []),
                "ended_at": datetime.now().isoformat(),
            },
            "auto_commit": shared.get("auto_commit", False),
            "spec_name": session.get("spec_name"),
            "delegation_history": shared.get("delegation_history", []),
            "delegation_mode": shared.get("delegation_mode", "print"),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Save state and optionally commit."""
        result = {
            "saved": False,
            "committed": False,
            "summary": "",
        }
        
        # Ensure sessions directory exists
        os.makedirs(inputs["sessions_path"], exist_ok=True)
        
        # Save session state
        session_file = os.path.join(
            inputs["sessions_path"],
            f"{inputs['session_id']}.json"
        )
        try:
            with open(session_file, 'w') as f:
                json.dump(inputs["state_to_save"], f, indent=2)
            result["saved"] = True
        except IOError as e:
            result["save_error"] = str(e)
        
        # Save progress.json back to spec
        if inputs["spec_name"]:
            progress_path = os.path.join(
                inputs["project_root"],
                "agent-os/specs",
                inputs["spec_name"],
                "progress.json"
            )
            try:
                os.makedirs(os.path.dirname(progress_path), exist_ok=True)
                with open(progress_path, 'w') as f:
                    json.dump(inputs["state_to_save"]["progress"], f, indent=2)
            except IOError:
                pass
        
        # Auto-commit if configured
        if inputs["auto_commit"]:
            try:
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=inputs["project_root"],
                    timeout=30
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Session {inputs['session_id']} checkpoint"],
                    cwd=inputs["project_root"],
                    timeout=30
                )
                result["committed"] = True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # Generate summary
        progress = inputs["state_to_save"].get("progress", {})
        completed = progress.get("completed", [])
        result["summary"] = f"Session ended. Completed {len(completed)} tasks."
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store summary and return."""
        shared["session_summary"] = exec_res["summary"]
        shared["session"]["ended_at"] = datetime.now().isoformat()
        
        # Print batch summary if we have delegation history
        delegation_history = prep_res.get("delegation_history", [])
        delegation_mode = prep_res.get("delegation_mode", "print")
        
        if delegation_mode == "batch" and delegation_history:
            print("\n" + "=" * 70)
            print("📋 BATCH DELEGATION SUMMARY")
            print("=" * 70)
            print(f"\n✅ Generated {len(delegation_history)} delegation(s):\n")
            
            # Group by agent
            by_agent = {}
            for d in delegation_history:
                agent = d.get("agent", "unknown")
                if agent not in by_agent:
                    by_agent[agent] = []
                by_agent[agent].append(d)
            
            for agent, delegations in by_agent.items():
                print(f"\n🤖 {agent}:")
                for d in delegations:
                    task_id = d.get("task_id", "?")
                    task_desc = d.get("task_description", "")[:50]
                    print(f"   • Task {task_id}: {task_desc}...")
            
            print("\n" + "-" * 70)
            print("📝 HOW TO USE THESE DELEGATIONS:")
            print("-" * 70)
            print("""
Copy any delegation above and paste into Claude Code with:

    Use the [agent-name] subagent to implement this task:
    
    [paste delegation instruction]

Work through tasks in order (1.0 → 2.0 → 3.0 → 4.0) or pick based on priority.
Each specialist agent has domain-specific expertise for optimal results.
""")
            print("=" * 70 + "\n")
        
        if exec_res["saved"]:
            return "saved"
        return "error"


class CheckpointNode(Node):
    """
    Mid-session checkpoint - persist current state without ending session.
    
    Use this between major operations to enable recovery.
    
    Shared Store Inputs:
    - session: Session metadata
    - progress: Current progress
    - Any other state to checkpoint
    
    Shared Store Outputs:
    - last_checkpoint: Timestamp of checkpoint
    """
    
    def __init__(self, sessions_dir: str = "agent-os/sessions", **kwargs):
        super().__init__(**kwargs)
        self.sessions_dir = sessions_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather state for checkpoint."""
        session = shared.get("session", {})
        project_root = session.get("project_root", os.getcwd())
        
        # Collect all relevant state
        checkpoint_state = {
            "session": session,
            "progress": shared.get("progress", {}),
            "learnings": shared.get("learnings", []),
            "expertise": shared.get("expertise", {}),
            "checkpoint_at": datetime.now().isoformat(),
        }
        
        return {
            "session_id": session.get("id", "unknown"),
            "sessions_path": os.path.join(project_root, self.sessions_dir),
            "checkpoint_state": checkpoint_state,
            "spec_name": session.get("spec_name"),
            "project_root": project_root,
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Write checkpoint to disk."""
        result = {"success": False, "checkpoint_at": inputs["checkpoint_state"]["checkpoint_at"]}
        
        os.makedirs(inputs["sessions_path"], exist_ok=True)
        
        # Save to session file
        session_file = os.path.join(
            inputs["sessions_path"],
            f"{inputs['session_id']}.json"
        )
        try:
            with open(session_file, 'w') as f:
                json.dump(inputs["checkpoint_state"], f, indent=2)
            result["success"] = True
        except IOError as e:
            result["error"] = str(e)
        
        # Also update progress.json in spec
        if inputs["spec_name"]:
            progress_path = os.path.join(
                inputs["project_root"],
                "agent-os/specs",
                inputs["spec_name"],
                "progress.json"
            )
            try:
                with open(progress_path, 'w') as f:
                    json.dump(inputs["checkpoint_state"]["progress"], f, indent=2)
            except IOError:
                pass
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Update shared with checkpoint timestamp."""
        shared["last_checkpoint"] = exec_res["checkpoint_at"]
        
        if exec_res["success"]:
            return "checkpointed"
        return "error"
