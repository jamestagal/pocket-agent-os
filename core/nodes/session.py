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
from typing import Any, Dict, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


class SessionStartNode(Node):
    """
    Initialize a new session or resume an existing one.
    
    Performs:
    1. Orient (pwd, git status, recent commits)
    2. Load previous session state if exists
    3. Load progress.json from active spec
    4. Set up session context in shared store
    
    Shared Store Inputs:
    - project_root: Path to project root (required)
    - spec_name: Active spec name (optional)
    - session_id: Explicit session ID (optional, auto-generated if missing)
    
    Shared Store Outputs:
    - session: Dict with id, started_at, resumed
    - orientation: Dict with cwd, git_status, recent_commits
    - progress: Dict loaded from progress.json (if exists)
    """
    
    def __init__(self, sessions_dir: str = "agent-os/sessions", **kwargs):
        super().__init__(**kwargs)
        self.sessions_dir = sessions_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather session initialization context."""
        project_root = shared.get("project_root", os.getcwd())
        spec_name = shared.get("spec_name")
        session_id = shared.get("session_id") or f"session_{int(time.time())}"
        
        return {
            "project_root": project_root,
            "spec_name": spec_name,
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
        
        # 4. Load progress.json from spec
        if inputs["spec_name"]:
            progress_path = os.path.join(
                project_root,
                "agent-os/specs",
                inputs["spec_name"],
                "progress.json"
            )
            if os.path.exists(progress_path):
                try:
                    with open(progress_path, 'r') as f:
                        result["progress"] = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass
        
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
