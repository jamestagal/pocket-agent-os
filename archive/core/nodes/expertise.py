"""
Domain Expertise Management Nodes

Handles domain knowledge:
- LoadExpertiseNode: Load expertise from YAML files
- ValidateExpertiseNode: Check if required expertise exists
- SelfImproveNode: Update expertise after task completion
"""

import os
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


class LoadExpertiseNode(Node):
    """
    Load domain expertise from YAML files into shared store.
    
    Reads:
    - _index.yaml: Domain registry and project overview
    - Individual domain files (frontend.yaml, api.yaml, etc.)
    
    Shared Store Inputs:
    - project_root: Path to project root
    - expertise_path: Custom expertise directory (optional)
    - domains_to_load: List of specific domains (optional, loads all if not specified)
    
    Shared Store Outputs:
    - expertise: Dict containing all loaded domain knowledge
    - expertise_domains: List of available domains
    """
    
    def __init__(self, expertise_dir: str = "agent-os/expertise", **kwargs):
        super().__init__(**kwargs)
        self.expertise_dir = expertise_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare paths for expertise loading."""
        project_root = shared.get("project_root") or shared.get("session", {}).get("project_root", os.getcwd())
        expertise_path = shared.get("expertise_path") or os.path.join(project_root, self.expertise_dir)
        
        return {
            "expertise_path": expertise_path,
            "domains_to_load": shared.get("domains_to_load"),  # None = load all
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load expertise files."""
        result = {
            "index": {},
            "domains": {},
            "available_domains": [],
            "errors": [],
        }
        
        expertise_path = inputs["expertise_path"]
        
        if not os.path.exists(expertise_path):
            result["errors"].append(f"Expertise directory not found: {expertise_path}")
            return result
        
        # Load _index.yaml
        index_path = os.path.join(expertise_path, "_index.yaml")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    result["index"] = yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError) as e:
                result["errors"].append(f"Error loading _index.yaml: {e}")
        
        # Find available domain files
        domains_to_load = inputs["domains_to_load"]
        
        for filename in os.listdir(expertise_path):
            if filename.startswith("_") or not filename.endswith(".yaml"):
                continue
            
            domain_name = filename[:-5]  # Remove .yaml
            result["available_domains"].append(domain_name)
            
            # Skip if specific domains requested and this isn't one
            if domains_to_load and domain_name not in domains_to_load:
                continue
            
            # Load domain file
            domain_path = os.path.join(expertise_path, filename)
            try:
                with open(domain_path, 'r') as f:
                    result["domains"][domain_name] = yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError) as e:
                result["errors"].append(f"Error loading {filename}: {e}")
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store expertise in shared store."""
        shared["expertise"] = {
            "index": exec_res["index"],
            "domains": exec_res["domains"],
        }
        shared["expertise_domains"] = exec_res["available_domains"]
        
        if exec_res["errors"]:
            shared["expertise_errors"] = exec_res["errors"]
            return "partial"
        
        if not exec_res["domains"]:
            return "empty"
        
        return "loaded"


class ValidateExpertiseNode(Node):
    """
    Validate that required domain expertise is available.
    
    Shared Store Inputs:
    - expertise: Loaded expertise (from LoadExpertiseNode)
    - required_domains: List of domains needed for current task
    - current_task: Task being worked on (optional, for context)
    
    Shared Store Outputs:
    - expertise_valid: Boolean
    - missing_domains: List of missing required domains
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather expertise and requirements."""
        expertise = shared.get("expertise", {})
        
        # Try to infer required domains from task if not explicit
        required = shared.get("required_domains", [])
        
        if not required and shared.get("current_task"):
            # Simple heuristic: look for domain keywords in task
            task = shared["current_task"]
            if isinstance(task, dict):
                task_text = str(task.get("description", "")) + str(task.get("file_patterns", []))
            else:
                task_text = str(task)
            
            # Check for domain hints
            domain_hints = {
                "frontend": ["react", "vue", "component", "css", "html", "ui", "ux"],
                "api": ["endpoint", "rest", "graphql", "controller", "route", "http"],
                "database": ["sql", "query", "migration", "schema", "model", "orm"],
                "devops": ["docker", "kubernetes", "ci", "cd", "deploy", "pipeline"],
            }
            
            task_lower = task_text.lower()
            for domain, hints in domain_hints.items():
                if any(hint in task_lower for hint in hints):
                    required.append(domain)
        
        return {
            "available_domains": list(expertise.get("domains", {}).keys()),
            "required_domains": required,
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Check for missing domains."""
        available = set(inputs["available_domains"])
        required = set(inputs["required_domains"])
        
        missing = required - available
        
        return {
            "valid": len(missing) == 0,
            "missing": list(missing),
            "matched": list(required & available),
        }
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Update shared with validation results."""
        shared["expertise_valid"] = exec_res["valid"]
        shared["missing_domains"] = exec_res["missing"]
        
        if exec_res["valid"]:
            return "valid"
        return "missing"


class SelfImproveNode(Node):
    """
    Update expertise based on completed work.
    
    After task completion, analyzes what was learned and updates
    the relevant domain expertise files.
    
    Shared Store Inputs:
    - expertise: Current expertise
    - task_result: Result of completed task
    - session: Session metadata (for project_root)
    - learnings: Accumulated learnings this session
    
    Shared Store Outputs:
    - expertise: Updated expertise
    - improvement_summary: What was improved
    """
    
    def __init__(self, expertise_dir: str = "agent-os/expertise", **kwargs):
        super().__init__(**kwargs)
        self.expertise_dir = expertise_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather context for improvement."""
        session = shared.get("session", {})
        project_root = session.get("project_root", os.getcwd())
        
        return {
            "project_root": project_root,
            "expertise_path": os.path.join(project_root, self.expertise_dir),
            "current_expertise": shared.get("expertise", {}),
            "task_result": shared.get("task_result", {}),
            "learnings": shared.get("learnings", []),
            "affected_domain": shared.get("affected_domain"),  # Hint for which domain
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze task result and generate improvements.
        
        Note: In a full implementation, this would call an LLM to analyze
        the task result and generate expertise updates. For now, we
        provide a structural framework.
        """
        result = {
            "updates": {},
            "new_patterns": [],
            "summary": "",
        }
        
        task_result = inputs["task_result"]
        learnings = inputs["learnings"]
        
        if not task_result and not learnings:
            result["summary"] = "No task results or learnings to process"
            return result
        
        # Determine affected domain
        affected_domain = inputs.get("affected_domain")
        
        if not affected_domain:
            # Try to infer from task result
            if isinstance(task_result, dict):
                files = task_result.get("files_modified", [])
                if any(".tsx" in f or ".jsx" in f or ".css" in f for f in files):
                    affected_domain = "frontend"
                elif any("api" in f or "controller" in f or "route" in f for f in files):
                    affected_domain = "api"
                elif any("migration" in f or "model" in f or "schema" in f for f in files):
                    affected_domain = "database"
        
        if affected_domain:
            # Load current domain expertise
            domain_path = os.path.join(inputs["expertise_path"], f"{affected_domain}.yaml")
            current_domain = {}
            
            if os.path.exists(domain_path):
                try:
                    with open(domain_path, 'r') as f:
                        current_domain = yaml.safe_load(f) or {}
                except (yaml.YAMLError, IOError):
                    pass
            
            # Add new learnings
            if "learnings" not in current_domain:
                current_domain["learnings"] = []
            
            timestamp = datetime.now().isoformat()
            for learning in learnings:
                current_domain["learnings"].append({
                    "content": learning,
                    "added_at": timestamp,
                })
            
            # Keep only last 50 learnings
            current_domain["learnings"] = current_domain["learnings"][-50:]
            
            result["updates"][affected_domain] = current_domain
            result["new_patterns"] = learnings
        
        result["summary"] = f"Added {len(learnings)} learnings to {affected_domain or 'general'}"
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Write updates to files and shared store."""
        # Write updated domain files
        for domain_name, domain_data in exec_res["updates"].items():
            domain_path = os.path.join(prep_res["expertise_path"], f"{domain_name}.yaml")
            try:
                os.makedirs(os.path.dirname(domain_path), exist_ok=True)
                with open(domain_path, 'w') as f:
                    yaml.dump(domain_data, f, default_flow_style=False)
            except IOError:
                pass
        
        # Update shared expertise
        if shared.get("expertise") and "domains" in shared["expertise"]:
            shared["expertise"]["domains"].update(exec_res["updates"])
        
        shared["improvement_summary"] = exec_res["summary"]
        shared["learnings"] = []  # Clear processed learnings
        
        if exec_res["updates"]:
            return "improved"
        return "no_changes"
