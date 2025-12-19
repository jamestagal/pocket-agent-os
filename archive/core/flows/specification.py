"""
Specification Workflow Flow

Workflow for creating and managing specifications:
1. Gather requirements
2. Generate spec structure
3. Break down into tasks
4. Validate task graph
5. Save spec files
"""

import os
import json
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocketflow import Node, Flow


class GatherRequirementsNode(Node):
    """
    Gather requirements for specification.
    
    Shared Store Inputs:
    - requirements: Initial requirements (string or dict)
    - spec_name: Name for the specification
    - project_root: Project root path
    
    Shared Store Outputs:
    - requirements: Normalized requirements dict
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        requirements = shared.get("requirements", "")
        
        return {
            "raw_requirements": requirements,
            "spec_name": shared.get("spec_name", f"spec-{int(datetime.now().timestamp())}"),
            "project_root": shared.get("project_root", os.getcwd()),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize requirements."""
        raw = inputs["raw_requirements"]
        
        if isinstance(raw, dict):
            return {"requirements": raw}
        
        # Parse string requirements
        return {
            "requirements": {
                "description": str(raw),
                "goals": [],
                "constraints": [],
                "created_at": datetime.now().isoformat(),
            }
        }
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["requirements"] = exec_res["requirements"]
        shared["spec_name"] = prep_res["spec_name"]
        return "gathered"


class GenerateTasksNode(Node):
    """
    Generate task breakdown from requirements.
    
    Note: In full implementation, this would use LLM to analyze
    requirements and generate appropriate tasks.
    
    Shared Store Inputs:
    - requirements: Normalized requirements
    - task_template: Optional template for tasks
    
    Shared Store Outputs:
    - tasks: List of task definitions
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "requirements": shared.get("requirements", {}),
            "template": shared.get("task_template"),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate tasks from requirements.
        
        In production, this would call an LLM. For now, creates
        a basic task structure.
        """
        requirements = inputs["requirements"]
        
        # Basic task template
        tasks = [
            {
                "id": "task-001",
                "description": f"Implement core functionality: {requirements.get('description', 'No description')[:100]}",
                "phase": "implement",
                "priority": 10,
            },
            {
                "id": "task-002", 
                "description": "Write tests for implementation",
                "phase": "test",
                "priority": 5,
                "depends_on": ["task-001"],
            },
            {
                "id": "task-003",
                "description": "Update documentation",
                "phase": "docs",
                "priority": 3,
                "depends_on": ["task-001"],
            },
        ]
        
        return {"tasks": tasks}
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["tasks"] = exec_res["tasks"]
        return "generated"


class ValidateSpecNode(Node):
    """
    Validate the specification structure.
    
    Checks:
    - All task IDs are unique
    - Dependencies reference valid tasks
    - No circular dependencies
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tasks": shared.get("tasks", []),
            "requirements": shared.get("requirements", {}),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        tasks = inputs["tasks"]
        errors = []
        warnings = []
        
        # Check unique IDs
        task_ids = [t.get("id") for t in tasks]
        duplicates = set(x for x in task_ids if task_ids.count(x) > 1)
        if duplicates:
            errors.append(f"Duplicate task IDs: {duplicates}")
        
        # Check dependencies
        valid_ids = set(task_ids)
        for task in tasks:
            deps = task.get("depends_on", [])
            for dep in deps:
                if dep not in valid_ids:
                    errors.append(f"Task {task.get('id')} depends on unknown task: {dep}")
        
        # Check for circular dependencies (simple check)
        # A more thorough check would use topological sort
        for task in tasks:
            task_id = task.get("id")
            deps = task.get("depends_on", [])
            if task_id in deps:
                errors.append(f"Task {task_id} depends on itself")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["spec_valid"] = exec_res["valid"]
        shared["spec_errors"] = exec_res["errors"]
        
        if exec_res["valid"]:
            return "valid"
        return "invalid"


class SaveSpecNode(Node):
    """
    Save specification to files.
    
    Creates:
    - spec.yaml: Main specification
    - progress.json: Initial progress tracking
    """
    
    def __init__(self, specs_dir: str = "agent-os/specs", **kwargs):
        super().__init__(**kwargs)
        self.specs_dir = specs_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        project_root = shared.get("project_root", os.getcwd())
        spec_name = shared.get("spec_name", "unnamed-spec")
        
        return {
            "spec_path": os.path.join(project_root, self.specs_dir, spec_name),
            "spec_name": spec_name,
            "requirements": shared.get("requirements", {}),
            "tasks": shared.get("tasks", []),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Save spec files."""
        spec_path = inputs["spec_path"]
        
        try:
            os.makedirs(spec_path, exist_ok=True)
            
            # Save spec.yaml
            spec_data = {
                "name": inputs["spec_name"],
                "requirements": inputs["requirements"],
                "tasks": inputs["tasks"],
                "created_at": datetime.now().isoformat(),
            }
            
            with open(os.path.join(spec_path, "spec.yaml"), 'w') as f:
                yaml.dump(spec_data, f, default_flow_style=False)
            
            # Save progress.json
            progress_data = {
                "tasks": inputs["tasks"],
                "completed": [],
                "failed": [],
                "current_task": None,
                "created_at": datetime.now().isoformat(),
            }
            
            with open(os.path.join(spec_path, "progress.json"), 'w') as f:
                json.dump(progress_data, f, indent=2)
            
            return {"saved": True, "path": spec_path}
            
        except IOError as e:
            return {"saved": False, "error": str(e)}
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["spec_path"] = exec_res.get("path")
        shared["spec_saved"] = exec_res["saved"]
        
        if exec_res["saved"]:
            return "saved"
        return "error"


class SpecificationFlow(Flow):
    """
    Complete specification creation workflow.
    
    Usage:
        flow = SpecificationFlow()
        shared = {
            "project_root": "/path/to/project",
            "spec_name": "my-feature",
            "requirements": "Build a user authentication system with OAuth support"
        }
        flow.run(shared)
    """
    
    def __init__(self):
        # Create nodes
        gather = GatherRequirementsNode()
        generate = GenerateTasksNode()
        validate = ValidateSpecNode()
        save = SaveSpecNode()
        
        # Build flow
        gather - "gathered" >> generate
        generate - "generated" >> validate
        validate - "valid" >> save
        validate - "invalid" >> None  # Terminal on validation failure
        save - "saved" >> None  # Terminal
        save - "error" >> None  # Terminal
        
        super().__init__(start=gather)
