"""
Progress Tracking Nodes

Handles task progress:
- ProgressGuardNode: Prevent premature completion
- TaskSelectorNode: Select next task to work on
- MarkTaskCompleteNode: Mark a task as done
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


class ProgressGuardNode(Node):
    """
    Guard against premature completion and one-shotting.
    
    Validates that required phases have been completed before
    allowing the workflow to proceed.
    
    Shared Store Inputs:
    - progress: Current progress state
    - required_phases: List of phases that must be complete
    - current_phase: Phase being entered
    
    Shared Store Outputs:
    - phase_valid: Boolean
    - missing_phases: List of phases not yet completed
    """
    
    def __init__(self, required_phases: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.required_phases = required_phases or ["spec", "implement", "verify"]
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather progress state."""
        progress = shared.get("progress", {})
        
        return {
            "completed_phases": progress.get("completed_phases", []),
            "current_phase": shared.get("current_phase", progress.get("current_phase")),
            "required_phases": shared.get("required_phases", self.required_phases),
            "completed_tasks": progress.get("completed", []),
            "total_tasks": len(progress.get("tasks", [])),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate phase progression."""
        result = {
            "valid": True,
            "missing_phases": [],
            "warnings": [],
        }
        
        current = inputs["current_phase"]
        completed = set(inputs["completed_phases"])
        required = inputs["required_phases"]
        
        # Check if trying to skip phases
        if current in required:
            current_idx = required.index(current)
            
            # All previous phases should be complete
            for i in range(current_idx):
                phase = required[i]
                if phase not in completed:
                    result["missing_phases"].append(phase)
        
        if result["missing_phases"]:
            result["valid"] = False
            result["warnings"].append(
                f"Cannot enter '{current}' phase without completing: {result['missing_phases']}"
            )
        
        # Check for premature completion
        if current == "complete":
            if inputs["completed_tasks"] < inputs["total_tasks"]:
                result["warnings"].append(
                    f"Only {inputs['completed_tasks']}/{inputs['total_tasks']} tasks completed"
                )
                # Allow but warn
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Update progress and route."""
        shared["phase_valid"] = exec_res["valid"]
        shared["missing_phases"] = exec_res["missing_phases"]
        
        if exec_res["warnings"]:
            shared["progress_warnings"] = exec_res["warnings"]
        
        if exec_res["valid"]:
            # Update current phase in progress
            progress = shared.get("progress", {})
            progress["current_phase"] = prep_res["current_phase"]
            shared["progress"] = progress
            return "valid"
        
        return "blocked"


class TaskSelectorNode(Node):
    """
    Select the next task to work on.
    
    Prioritizes tasks based on:
    1. Dependencies (blocked tasks come later)
    2. Priority field
    3. Order in task list
    
    Handles batch mode by tracking printed tasks separately from completed tasks.
    
    Shared Store Inputs:
    - progress: Progress state with tasks list
    - task_filter: Optional filter criteria
    - printed_tasks: Set of task IDs already printed (batch mode)
    - delegation_mode: Current delegation mode
    
    Shared Store Outputs:
    - current_task: Selected task
    - remaining_tasks: Count of remaining tasks
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather task list."""
        progress = shared.get("progress", {})
        
        # printed_tasks can be a set or list depending on source
        printed_raw = shared.get("printed_tasks", [])
        printed_tasks = set(printed_raw) if isinstance(printed_raw, list) else printed_raw
        
        return {
            "tasks": progress.get("tasks", []),
            "completed": set(progress.get("completed", [])),
            "failed": [f.get("task_id") for f in progress.get("failed", [])],
            "printed_tasks": printed_tasks,
            "delegation_mode": shared.get("delegation_mode", "print"),
            "task_filter": shared.get("task_filter"),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Select next task."""
        result = {
            "selected_task": None,
            "remaining_count": 0,
            "blocked_count": 0,
            "printed_count": 0,
            "all_printed": False,
        }
        
        tasks = inputs["tasks"]
        completed = inputs["completed"]
        failed_ids = set(inputs["failed"])
        printed_tasks = inputs["printed_tasks"]
        delegation_mode = inputs["delegation_mode"]
        task_filter = inputs["task_filter"]
        
        available_tasks = []
        blocked_tasks = []
        printed_but_not_complete = []
        
        for task in tasks:
            # Normalize task
            if isinstance(task, str):
                task = {"id": task, "description": task}
            
            task_id = task.get("id", task.get("description", "unknown"))
            
            # Skip completed tasks
            if task_id in completed:
                continue
            
            # In batch mode, track printed tasks separately
            if delegation_mode == "batch" and task_id in printed_tasks:
                printed_but_not_complete.append(task)
                continue
            
            # Skip failed tasks (unless retry requested)
            if task_id in failed_ids and not task.get("retry"):
                continue
            
            # Apply filter if provided
            if task_filter:
                if isinstance(task_filter, str):
                    if task_filter.lower() not in str(task).lower():
                        continue
                elif callable(task_filter):
                    if not task_filter(task):
                        continue
            
            # Check dependencies
            dependencies = task.get("depends_on", [])
            if dependencies:
                unmet = [dep for dep in dependencies if dep not in completed]
                if unmet:
                    blocked_tasks.append(task)
                    continue
            
            available_tasks.append(task)
        
        result["remaining_count"] = len(available_tasks) + len(blocked_tasks)
        result["blocked_count"] = len(blocked_tasks)
        result["printed_count"] = len(printed_but_not_complete)
        
        # In batch mode, check if all tasks have been printed
        if delegation_mode == "batch":
            total_pending = len(available_tasks) + len(blocked_tasks) + len(printed_but_not_complete)
            if len(printed_but_not_complete) > 0 and len(available_tasks) == 0:
                result["all_printed"] = True
        
        if available_tasks:
            # Sort by priority (higher first), then by order
            available_tasks.sort(
                key=lambda t: (-t.get("priority", 0), tasks.index(t) if t in tasks else 999)
            )
            result["selected_task"] = available_tasks[0]
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store selected task."""
        shared["current_task"] = exec_res["selected_task"]
        shared["remaining_tasks"] = exec_res["remaining_count"]
        shared["blocked_tasks"] = exec_res["blocked_count"]
        
        # Update progress
        progress = shared.get("progress", {})
        if exec_res["selected_task"]:
            task_id = exec_res["selected_task"].get("id", "unknown")
            progress["current_task"] = task_id
        shared["progress"] = progress
        
        if exec_res["selected_task"]:
            return "task_selected"
        
        # In batch mode, return "all_printed" when all tasks have been printed
        if exec_res["all_printed"]:
            return "all_printed"
        
        if exec_res["blocked_count"] > 0:
            return "all_blocked"
        
        return "all_complete"


class MarkTaskCompleteNode(Node):
    """
    Mark a task as complete.
    
    Shared Store Inputs:
    - current_task: Task to mark complete (or task_id)
    - progress: Progress state
    - task_notes: Optional notes about completion
    
    Shared Store Outputs:
    - progress: Updated with task in completed list
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Get task to complete."""
        task = shared.get("current_task", {})
        
        if isinstance(task, str):
            task_id = task
        else:
            task_id = task.get("id", task.get("description", "unknown"))
        
        return {
            "task_id": task_id,
            "task_notes": shared.get("task_notes"),
            "progress": shared.get("progress", {}),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Update progress."""
        progress = inputs["progress"].copy()
        
        # Add to completed list
        if "completed" not in progress:
            progress["completed"] = []
        
        if inputs["task_id"] not in progress["completed"]:
            progress["completed"].append(inputs["task_id"])
        
        # Add to completed phases if this represents a phase
        if "completed_phases" not in progress:
            progress["completed_phases"] = []
        
        # Record completion time
        if "completion_log" not in progress:
            progress["completion_log"] = []
        
        progress["completion_log"].append({
            "task_id": inputs["task_id"],
            "completed_at": datetime.now().isoformat(),
            "notes": inputs["task_notes"],
        })
        
        # Clear current task
        progress["current_task"] = None
        
        return {"progress": progress}
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Update shared progress."""
        shared["progress"] = exec_res["progress"]
        
        # Clear current task
        shared["current_task"] = None
        
        return "completed"
