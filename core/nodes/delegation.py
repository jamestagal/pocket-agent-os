"""
Claude Code Delegation Nodes

Handles delegation to Claude Code subagents:
- ClaudeCodeDelegationNode: Delegate tasks to subagents with full spec context
- SubagentResultNode: Process results from subagent execution
"""

import os
import json
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


def format_spec_context(spec_files: Dict[str, str], spec_visuals: List[str], spec_path: str) -> str:
    """
    Format spec files into readable context for delegation.
    
    Prioritizes key files and includes all available context.
    """
    sections = []
    
    # Priority order for main files
    priority_files = ["spec.md", "tasks.md", "requirements.md"]
    
    # Add priority files first
    for filename in priority_files:
        if filename in spec_files:
            content = spec_files[filename]
            sections.append(f"### {filename}\n\n{content}")
    
    # Add other root-level markdown files
    other_md_files = [f for f in spec_files.keys() 
                      if f.endswith('.md') 
                      and f not in priority_files 
                      and not f.startswith('planning/')]
    for filename in sorted(other_md_files):
        content = spec_files[filename]
        sections.append(f"### {filename}\n\n{content}")
    
    # Add planning files
    planning_files = [f for f in spec_files.keys() if f.startswith('planning/')]
    if planning_files:
        sections.append("### Planning Documents\n")
        for filename in sorted(planning_files):
            content = spec_files[filename]
            sections.append(f"#### {filename}\n\n{content}")
    
    # Add yaml/yml config files
    config_files = [f for f in spec_files.keys() 
                    if f.endswith('.yaml') or f.endswith('.yml')]
    for filename in sorted(config_files):
        content = spec_files[filename]
        sections.append(f"### {filename}\n\n```yaml\n{content}\n```")
    
    # Note about visuals
    if spec_visuals:
        visual_list = "\n".join(f"- {v}" for v in spec_visuals)
        sections.append(f"### Visual References\n\nThe following visual files are available in `{spec_path}/planning/visuals/`:\n{visual_list}")
    
    return "\n\n---\n\n".join(sections)


def extract_current_task_context(spec_files: Dict[str, str], task_description: str) -> str:
    """
    Extract the specific task context from tasks.md if available.
    """
    tasks_content = spec_files.get("tasks.md", "")
    if not tasks_content:
        return ""
    
    # Try to find the task in the tasks.md content
    lines = tasks_content.split('\n')
    for i, line in enumerate(lines):
        if task_description.lower() in line.lower():
            # Get some context around the task (5 lines before and after)
            start = max(0, i - 5)
            end = min(len(lines), i + 10)
            context = '\n'.join(lines[start:end])
            return f"\n\n### Current Task Context (from tasks.md)\n\n```\n{context}\n```"
    
    return ""


class ClaudeCodeDelegationNode(Node):
    """
    Delegate a task to a Claude Code subagent with full spec context.
    
    This node prepares a delegation instruction that includes:
    1. Target agent and task description
    2. ALL spec files (spec.md, tasks.md, requirements.md, planning/*, etc.)
    3. Visual file references
    4. Relevant expertise hints
    
    The instruction can be:
    1. Printed for human to execute manually
    2. Written to a pending delegations file
    3. Executed via claude CLI (if available)
    
    Shared Store Inputs:
    - current_task: Task to delegate
    - target_agent: Name of subagent to use
    - spec_path: Path to spec folder
    - spec_files: Dict of all spec file contents (from SessionStartNode)
    - spec_visuals: List of visual file paths
    - expertise: Domain expertise to pass (optional)
    - delegation_mode: "print" | "file" | "cli" (default: "print")
    
    Shared Store Outputs:
    - delegation: Dict with instruction, agent, context
    - delegation_history: Accumulated delegations
    """
    
    def __init__(
        self, 
        default_agent: str = "implementer",
        delegation_mode: str = "print",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.default_agent = default_agent
        self.delegation_mode = delegation_mode
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare delegation context with full spec files."""
        task = shared.get("current_task", {})
        target_agent = shared.get("target_agent", self.default_agent)
        
        # Build task description
        if isinstance(task, dict):
            task_description = task.get("description", str(task))
            task_files = task.get("file_patterns", [])
            task_id = task.get("id", "unknown")
            task_phase = task.get("phase", "implement")
        else:
            task_description = str(task)
            task_files = []
            task_id = "unknown"
            task_phase = "implement"
        
        # Get ALL spec files loaded by SessionStartNode
        spec_files = shared.get("spec_files", {})
        spec_visuals = shared.get("spec_visuals", [])
        spec_path = shared.get("spec_path", "")
        
        # Get relevant expertise
        expertise = shared.get("expertise", {})
        relevant_expertise = {}
        
        # Extract domain-specific expertise if available
        if expertise.get("domains"):
            domains = expertise["domains"]
            for domain in shared.get("detected_domains", []):
                if domain in domains:
                    relevant_expertise[domain] = domains[domain]
        
        return {
            "target_agent": target_agent,
            "task_description": task_description,
            "task_files": task_files,
            "task_id": task_id,
            "task_phase": task_phase,
            "spec_path": spec_path,
            "spec_files": spec_files,
            "spec_visuals": spec_visuals,
            "relevant_expertise": relevant_expertise,
            "delegation_mode": shared.get("delegation_mode", self.delegation_mode),
            "project_root": shared.get("session", {}).get("project_root", os.getcwd()),
            "spec_name": shared.get("session", {}).get("spec_name", ""),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build delegation instruction with full spec context."""
        agent = inputs["target_agent"]
        task = inputs["task_description"]
        spec_path = inputs["spec_path"]
        spec_files = inputs["spec_files"]
        spec_visuals = inputs["spec_visuals"]
        
        # Build the main instruction header
        instruction_parts = []
        
        # Header
        instruction_parts.append(f"# Delegation to {agent} subagent")
        instruction_parts.append(f"\n## Task\n\n{task}")
        instruction_parts.append(f"\n**Task ID:** {inputs['task_id']}")
        instruction_parts.append(f"**Phase:** {inputs['task_phase']}")
        
        # Spec location
        if spec_path:
            instruction_parts.append(f"\n## Spec Location\n\n`{spec_path}`")
        
        # Files to focus on (if specified in task)
        if inputs["task_files"]:
            files_list = "\n".join(f"- `{f}`" for f in inputs["task_files"])
            instruction_parts.append(f"\n## Files to Focus On\n\n{files_list}")
        
        # Full spec context
        if spec_files:
            spec_context = format_spec_context(spec_files, spec_visuals, spec_path)
            instruction_parts.append(f"\n## Spec Context\n\n{spec_context}")
            
            # Add specific task context if found in tasks.md
            task_context = extract_current_task_context(spec_files, task)
            if task_context:
                instruction_parts.append(task_context)
        
        # Expertise hints
        if inputs["relevant_expertise"]:
            expertise_notes = []
            for domain, info in inputs["relevant_expertise"].items():
                if isinstance(info, dict):
                    notes = info.get("notes", str(info))
                else:
                    notes = str(info)
                expertise_notes.append(f"- **{domain}**: {notes}")
            if expertise_notes:
                instruction_parts.append(f"\n## Expertise Hints\n\n" + "\n".join(expertise_notes))
        
        # Reminder about task completion
        instruction_parts.append(f"\n## After Implementation\n\nUpdate `{spec_path}/tasks.md` to mark this task as complete: `- [x]`")
        
        instruction = "\n".join(instruction_parts)
        
        result = {
            "instruction": instruction,
            "agent": agent,
            "task_id": inputs["task_id"],
            "context": {
                "task": inputs["task_description"],
                "files": inputs["task_files"],
                "spec": inputs["spec_path"],
                "spec_files_count": len(spec_files),
                "visuals_count": len(spec_visuals),
                "expertise_domains": list(inputs["relevant_expertise"].keys()),
            },
            "delegated_at": datetime.now().isoformat(),
            "mode": inputs["delegation_mode"],
            "executed": False,
        }
        
        # Execute based on mode
        mode = inputs["delegation_mode"]
        
        if mode == "print":
            # Just prepare the instruction (will be printed in post)
            result["output"] = instruction
            
        elif mode == "file":
            # Write to pending delegations file
            delegations_file = os.path.join(
                inputs["project_root"],
                "agent-os/pending_delegations.json"
            )
            try:
                os.makedirs(os.path.dirname(delegations_file), exist_ok=True)
                
                # Load existing delegations
                existing = []
                if os.path.exists(delegations_file):
                    with open(delegations_file, 'r') as f:
                        existing = json.load(f)
                
                # Add new delegation
                existing.append({
                    "instruction": instruction,
                    "agent": agent,
                    "task_id": inputs["task_id"],
                    "spec_name": inputs["spec_name"],
                    "created_at": result["delegated_at"],
                    "status": "pending",
                })
                
                with open(delegations_file, 'w') as f:
                    json.dump(existing, f, indent=2)
                
                result["output"] = f"Delegation written to {delegations_file}"
                result["executed"] = True
            except IOError as e:
                result["output"] = f"Failed to write delegation: {e}"
                result["error"] = str(e)
                
        elif mode == "cli":
            # Try to execute via claude CLI
            try:
                cmd_result = subprocess.run(
                    ["claude", "--print", instruction],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=inputs["project_root"],
                )
                result["output"] = cmd_result.stdout
                result["error"] = cmd_result.stderr if cmd_result.returncode != 0 else None
                result["executed"] = cmd_result.returncode == 0
            except FileNotFoundError:
                result["output"] = "Claude CLI not found. Install claude CLI or use 'print' mode."
                result["error"] = "claude CLI not available"
            except subprocess.TimeoutExpired:
                result["output"] = "Delegation timed out"
                result["error"] = "timeout"
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store delegation and update history."""
        # Store current delegation
        shared["delegation"] = {
            "instruction": exec_res["instruction"],
            "agent": exec_res["agent"],
            "task_id": exec_res["task_id"],
            "context": exec_res["context"],
            "delegated_at": exec_res["delegated_at"],
            "output": exec_res.get("output"),
            "executed": exec_res["executed"],
        }
        
        # Update delegation history
        if "delegation_history" not in shared:
            shared["delegation_history"] = []
        shared["delegation_history"].append(shared["delegation"])
        
        # Print instruction if in print mode
        if exec_res["mode"] == "print":
            print("\n" + "=" * 70)
            print("DELEGATION INSTRUCTION")
            print("=" * 70)
            print(exec_res["instruction"])
            print("=" * 70 + "\n")
        
        if exec_res.get("error"):
            return "error"
        
        return "delegated"


class SubagentResultNode(Node):
    """
    Process the result of a subagent execution.
    
    This node is called after a subagent completes its work.
    It validates the result and updates progress.
    
    Shared Store Inputs:
    - delegation: The delegation that was executed
    - subagent_output: Raw output from subagent (optional)
    - files_modified: List of files that were modified
    - success: Boolean indicating success
    - error: Error message if failed
    
    Shared Store Outputs:
    - task_result: Processed result of the task
    - progress: Updated progress (task marked complete or failed)
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather result context."""
        delegation = shared.get("delegation", {})
        
        return {
            "delegation": delegation,
            "subagent_output": shared.get("subagent_output"),
            "files_modified": shared.get("files_modified", []),
            "success": shared.get("success", True),
            "error": shared.get("error"),
            "task_id": delegation.get("task_id"),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate the result."""
        result = {
            "task_id": inputs["task_id"],
            "success": inputs["success"],
            "files_modified": inputs["files_modified"],
            "completed_at": datetime.now().isoformat(),
            "summary": "",
        }
        
        if inputs["success"]:
            result["summary"] = f"Task {inputs['task_id']} completed successfully. "
            if inputs["files_modified"]:
                result["summary"] += f"Modified {len(inputs['files_modified'])} files."
        else:
            result["summary"] = f"Task {inputs['task_id']} failed: {inputs.get('error', 'Unknown error')}"
            result["error"] = inputs.get("error")
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Update progress and store result."""
        # Store task result
        shared["task_result"] = exec_res
        
        # Update progress
        progress = shared.get("progress", {"tasks": [], "completed": [], "failed": []})
        
        if exec_res["success"]:
            if exec_res["task_id"] not in progress.get("completed", []):
                if "completed" not in progress:
                    progress["completed"] = []
                progress["completed"].append(exec_res["task_id"])
            
            # Record files modified for learning
            if exec_res["files_modified"]:
                if "files_modified_this_session" not in shared:
                    shared["files_modified_this_session"] = []
                shared["files_modified_this_session"].extend(exec_res["files_modified"])
        else:
            if "failed" not in progress:
                progress["failed"] = []
            progress["failed"].append({
                "task_id": exec_res["task_id"],
                "error": exec_res.get("error"),
                "at": exec_res["completed_at"],
            })
        
        shared["progress"] = progress
        
        if exec_res["success"]:
            return "success"
        return "failed"
