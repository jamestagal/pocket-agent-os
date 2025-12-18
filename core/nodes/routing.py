"""
Agent Routing Node

Smart routing to select the best agent for a task.
- AgentSelectorNode: Analyze task and select appropriate agent
"""

import os
import re
import yaml
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pocketflow import Node


class AgentSelectorNode(Node):
    """
    Select the best agent for a given task.
    
    Routes tasks to specialist agents based on:
    1. Explicit override in task: [use:agent-name]
    2. File patterns in task
    3. Keywords in task description
    4. Domain detection from context
    5. Routing rules from routing.yaml
    
    Shared Store Inputs:
    - current_task: Task to route
    - expertise: Domain expertise (optional, for context)
    - available_agents: List of available agents (optional)
    
    Shared Store Outputs:
    - target_agent: Selected agent name
    - routing_confidence: Confidence level (high/medium/low)
    - detected_domains: Domains detected in task
    - routing_reason: Why this agent was selected
    """
    
    def __init__(
        self,
        routing_file: str = "agent-os/routing.yaml",
        default_agent: str = "implementer",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.routing_file = routing_file
        self.default_agent = default_agent
        
        # Built-in routing rules (can be overridden by routing.yaml)
        self.default_rules = {
            "agents": {
                "frontend-specialist": {
                    "file_patterns": [r"\.tsx$", r"\.jsx$", r"\.css$", r"\.scss$", r"components/", r"pages/"],
                    "keywords": ["react", "vue", "component", "ui", "ux", "style", "layout", "responsive"],
                    "domains": ["frontend"],
                },
                "api-specialist": {
                    "file_patterns": [r"api/", r"routes/", r"controllers/", r"\.controller\.", r"endpoint"],
                    "keywords": ["endpoint", "rest", "graphql", "api", "http", "request", "response"],
                    "domains": ["api", "backend"],
                },
                "database-specialist": {
                    "file_patterns": [r"migrations/", r"models/", r"schema", r"\.sql$", r"prisma/"],
                    "keywords": ["database", "sql", "query", "migration", "schema", "model", "orm"],
                    "domains": ["database"],
                },
                "test-specialist": {
                    "file_patterns": [r"\.test\.", r"\.spec\.", r"__tests__/", r"tests/"],
                    "keywords": ["test", "spec", "coverage", "assertion", "mock", "fixture"],
                    "domains": ["testing"],
                },
                "devops-specialist": {
                    "file_patterns": [r"docker", r"\.ya?ml$", r"ci/", r"\.github/", r"kubernetes/"],
                    "keywords": ["deploy", "docker", "kubernetes", "ci", "cd", "pipeline", "infrastructure"],
                    "domains": ["devops"],
                },
            },
            "default_agent": "implementer",
            "fallback_confidence": "low",
        }
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        """Gather routing context."""
        task = shared.get("current_task", {})
        
        # Normalize task
        if isinstance(task, str):
            task = {"description": task}
        
        task_description = task.get("description", "")
        task_files = task.get("file_patterns", [])
        task_id = task.get("id", "unknown")
        
        # Get project root for routing file
        project_root = shared.get("session", {}).get("project_root", os.getcwd())
        
        return {
            "task_id": task_id,
            "task_description": task_description,
            "task_files": task_files,
            "full_task": task,
            "project_root": project_root,
            "routing_file": os.path.join(project_root, self.routing_file),
            "available_agents": shared.get("available_agents"),
            "expertise_domains": list(shared.get("expertise", {}).get("domains", {}).keys()),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task and select agent."""
        result = {
            "agent": self.default_agent,
            "confidence": "low",
            "detected_domains": [],
            "reason": "Default fallback",
            "scores": {},
        }
        
        description = inputs["task_description"].lower()
        files = inputs["task_files"]
        
        # 1. Check for explicit override: [use:agent-name]
        override_match = re.search(r'\[use:([a-z-]+)\]', inputs["task_description"], re.IGNORECASE)
        if override_match:
            result["agent"] = override_match.group(1)
            result["confidence"] = "high"
            result["reason"] = f"Explicit override: [use:{result['agent']}]"
            return result
        
        # 2. Load routing rules
        rules = self.default_rules.copy()
        
        if os.path.exists(inputs["routing_file"]):
            try:
                with open(inputs["routing_file"], 'r') as f:
                    custom_rules = yaml.safe_load(f) or {}
                    # Merge custom rules (custom takes precedence)
                    if "agents" in custom_rules:
                        rules["agents"].update(custom_rules["agents"])
                    if "default_agent" in custom_rules:
                        rules["default_agent"] = custom_rules["default_agent"]
            except (yaml.YAMLError, IOError):
                pass
        
        # 3. Score each agent
        available = inputs["available_agents"]
        
        for agent_name, agent_rules in rules["agents"].items():
            # Skip if not in available agents (when specified)
            if available and agent_name not in available:
                continue
            
            score = 0
            matches = []
            
            # Check file patterns
            file_patterns = agent_rules.get("file_patterns", [])
            for pattern in file_patterns:
                for file_path in files:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        score += 10
                        matches.append(f"file:{pattern}")
                
                # Also check in description
                if re.search(pattern, description, re.IGNORECASE):
                    score += 5
                    matches.append(f"desc_file:{pattern}")
            
            # Check keywords
            keywords = agent_rules.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in description:
                    score += 3
                    matches.append(f"keyword:{keyword}")
            
            # Check domains
            domains = agent_rules.get("domains", [])
            for domain in domains:
                if domain in inputs["expertise_domains"]:
                    score += 2
                    matches.append(f"domain:{domain}")
                    result["detected_domains"].append(domain)
            
            result["scores"][agent_name] = {
                "score": score,
                "matches": matches,
            }
        
        # 4. Select best agent
        if result["scores"]:
            best_agent = max(result["scores"].keys(), key=lambda a: result["scores"][a]["score"])
            best_score = result["scores"][best_agent]["score"]
            
            if best_score >= 10:
                result["agent"] = best_agent
                result["confidence"] = "high"
                result["reason"] = f"Strong match: {result['scores'][best_agent]['matches'][:3]}"
            elif best_score >= 5:
                result["agent"] = best_agent
                result["confidence"] = "medium"
                result["reason"] = f"Moderate match: {result['scores'][best_agent]['matches'][:3]}"
            elif best_score > 0:
                result["agent"] = best_agent
                result["confidence"] = "low"
                result["reason"] = f"Weak match: {result['scores'][best_agent]['matches']}"
            else:
                result["agent"] = rules.get("default_agent", self.default_agent)
                result["confidence"] = "low"
                result["reason"] = "No patterns matched, using default"
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        """Store routing decision."""
        shared["target_agent"] = exec_res["agent"]
        shared["routing_confidence"] = exec_res["confidence"]
        shared["detected_domains"] = list(set(exec_res["detected_domains"]))
        shared["routing_reason"] = exec_res["reason"]
        shared["routing_scores"] = exec_res["scores"]
        
        # Return confidence level as action for flow control
        return exec_res["confidence"]
