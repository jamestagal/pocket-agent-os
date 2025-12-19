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


def format_product_context(product_files: Dict[str, str]) -> str:
    """
    Format product files into readable context for delegation.
    
    Prioritizes key files: mission.md, roadmap.md, tech-stack.md
    """
    if not product_files:
        return ""
    
    sections = []
    
    # Priority order for product files
    priority_files = ["mission.md", "roadmap.md", "tech-stack.md"]
    
    # Add priority files first
    for filename in priority_files:
        if filename in product_files:
            content = product_files[filename]
            sections.append(f"### {filename}\n\n{content}")
    
    # Add other product files
    other_files = [f for f in product_files.keys() if f not in priority_files]
    for filename in sorted(other_files):
        content = product_files[filename]
        if filename.endswith(('.yaml', '.yml')):
            sections.append(f"### {filename}\n\n```yaml\n{content}\n```")
        else:
            sections.append(f"### {filename}\n\n{content}")
    
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
    1. Printed for human to execute manually (batch or single)
    2. Written to a pending delegations file
    3. Executed via claude CLI (if available)
    
    Delegation Modes:
    - "print": Print ONE delegation and exit (legacy behavior)
    - "batch": Print ALL delegations, then exit with summary
    - "file": Write delegations to file
    - "cli": Execute via claude CLI
    
    Shared Store Inputs:
    - current_task: Task to delegate
    - target_agent: Name of subagent to use
    - spec_path: Path to spec folder
    - spec_files: Dict of all spec file contents (from SessionStartNode)
    - spec_visuals: List of visual file paths
    - expertise: Domain expertise to pass (optional)
    - delegation_mode: "print" | "batch" | "file" | "cli" (default: "print")
    
    Shared Store Outputs:
    - delegation: Dict with instruction, agent, context
    - delegation_history: Accumulated delegations
    - printed_tasks: Set of task IDs that have been printed (batch mode)
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
        
        # Get product context files (mission.md, roadmap.md, tech-stack.md)
        product_files = shared.get("product_files", {})
        
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
            "product_files": product_files,
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
        
        # Product context (mission, roadmap, tech-stack)
        product_files = inputs.get("product_files", {})
        if product_files:
            product_context = format_product_context(product_files)
            instruction_parts.append(f"\n## Product Context\n\nThe following product documentation provides broader context:\n\n{product_context}")
        
        # Expertise hints
        if inputs["relevant_expertise"]:
            expertise_parts = []
            for domain, expertise in inputs["relevant_expertise"].items():
                expertise_parts.append(f"- **{domain}**: {expertise}")
            instruction_parts.append(f"\n## Expertise Hints\n\n" + "\n".join(expertise_parts))
        
        # After implementation note
        if spec_path:
            instruction_parts.append(f"\n## After Implementation\n\nUpdate `{spec_path}/tasks.md` to mark this task as complete: `- [x]`")
        
        instruction = "\n".join(instruction_parts)
        
        # Build result
        result = {
            "instruction": instruction,
            "agent": agent,
            "task_id": inputs["task_id"],
            "task_description": task,
            "context": {
                "spec_path": spec_path,
                "files_count": len(spec_files),
                "has_visuals": len(spec_visuals) > 0,
                "has_expertise": len(inputs["relevant_expertise"]) > 0,
            },
            "delegated_at": datetime.now().isoformat(),
            "mode": inputs["delegation_mode"],
            "executed": False,
            "output": None,
            "error": None,
        }
        
        mode = inputs["delegation_mode"]
        
        if mode == "file":
            # Write delegation to a single file for Claude Code to read
            delegation_path = os.path.join(inputs["project_root"], "agent-os", "current-delegation.md")
            os.makedirs(os.path.dirname(delegation_path), exist_ok=True)
            
            with open(delegation_path, "w") as f:
                f.write(instruction)
            
            # Print confirmation message
            print(f"\n{'=' * 70}")
            print(f"📄 DELEGATION WRITTEN TO FILE")
            print(f"{'=' * 70}")
            print(f"   Task: {inputs['task_id']} - {task[:50]}...")
            print(f"   Agent: {agent}")
            print(f"   File: {delegation_path}")
            print(f"\n   In Claude Code, use: /agent-os pocketflow-implement")
            print(f"   Or read the file directly: agent-os/current-delegation.md")
            print(f"{'=' * 70}\n")
            
            result["output"] = f"Delegation written to {delegation_path}"
            result["executed"] = False
            
            # Also append to history
            history_path = os.path.join(inputs["project_root"], "agent-os", "delegation-history.md")
            with open(history_path, "a") as f:
                f.write(f"\n\n{'=' * 70}\n")
                f.write(f"Task: {inputs['task_id']} - {task[:50]}...\n")
                f.write(f"Agent: {agent}\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"{'=' * 70}\n\n")
                f.write(instruction)
                f.write("\n")
        
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
        
        # For "print" and "batch" modes, output is handled in post()
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store delegation and update history."""
        # Store current delegation
        shared["delegation"] = {
            "instruction": exec_res["instruction"],
            "agent": exec_res["agent"],
            "task_id": exec_res["task_id"],
            "task_description": exec_res["task_description"],
            "context": exec_res["context"],
            "delegated_at": exec_res["delegated_at"],
            "output": exec_res.get("output"),
            "executed": exec_res["executed"],
        }
        
        # Update delegation history
        if "delegation_history" not in shared:
            shared["delegation_history"] = []
        shared["delegation_history"].append(shared["delegation"])
        
        # Track printed tasks (for batch mode) - use list for JSON serialization
        if "printed_tasks" not in shared:
            shared["printed_tasks"] = []
        if exec_res["task_id"] not in shared["printed_tasks"]:
            shared["printed_tasks"].append(exec_res["task_id"])
        
        mode = exec_res.get("mode", "print")
        
        if mode == "print":
            # Legacy behavior: Print ONE delegation and exit
            print("\n" + "=" * 70)
            print("DELEGATION INSTRUCTION")
            print("=" * 70)
            print(exec_res["instruction"])
            print("=" * 70 + "\n")
            return "print_complete"
        
        elif mode == "file":
            # File mode: Write ONE delegation to file and exit (like print)
            return "file_complete"
        
        elif mode == "batch":
            # Batch mode: Print delegation and continue to next task
            task_num = len(shared["delegation_history"])
            print(f"\n{'=' * 70}")
            print(f"📋 DELEGATION {task_num}: {exec_res['task_id']}")
            print(f"   Agent: {exec_res['agent']}")
            print(f"   Task: {exec_res['task_description'][:60]}...")
            print(f"{'=' * 70}")
            print(exec_res["instruction"])
            print(f"{'=' * 70}\n")
            
            # Return "printed" to continue to next task (not mark as complete)
            return "printed"
        
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
            result["summary"] = f"Task {inputs['task_id']} completed successfully"
            if inputs["files_modified"]:
                result["summary"] += f", modified {len(inputs['files_modified'])} files"
        else:
            result["summary"] = f"Task {inputs['task_id']} failed"
            if inputs["error"]:
                result["summary"] += f": {inputs['error']}"
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store result and update progress."""
        shared["task_result"] = exec_res
        
        # Add to results history
        if "results_history" not in shared:
            shared["results_history"] = []
        shared["results_history"].append(exec_res)
        
        if exec_res["success"]:
            return "success"
        else:
            return "failed"
