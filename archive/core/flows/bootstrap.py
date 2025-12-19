"""
Bootstrap Workflow Flow

Expertise initialization workflow:
1. Analyze project structure
2. Detect tech stack
3. Generate domain expertise files
4. Create routing configuration
"""

import os
import json
import yaml
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocketflow import Node, Flow


class AnalyzeProjectNode(Node):
    """
    Analyze project structure and detect patterns.
    
    Shared Store Inputs:
    - project_root: Path to project
    
    Shared Store Outputs:
    - project_structure: Directory structure
    - detected_patterns: File patterns found
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_root": shared.get("project_root", os.getcwd()),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Scan project structure."""
        project_root = inputs["project_root"]
        result = {
            "directories": [],
            "file_extensions": {},
            "config_files": [],
            "patterns": {},
        }
        
        # Walk project directory (limit depth)
        max_depth = 4
        for root, dirs, files in os.walk(project_root):
            # Calculate depth
            depth = root.replace(project_root, '').count(os.sep)
            if depth > max_depth:
                dirs.clear()
                continue
            
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if d not in [
                'node_modules', '.git', '__pycache__', 'venv', 
                '.venv', 'dist', 'build', '.next', 'coverage'
            ]]
            
            rel_root = os.path.relpath(root, project_root)
            if rel_root != '.':
                result["directories"].append(rel_root)
            
            for file in files:
                ext = os.path.splitext(file)[1]
                result["file_extensions"][ext] = result["file_extensions"].get(ext, 0) + 1
                
                # Detect config files
                if file in ['package.json', 'tsconfig.json', 'pyproject.toml', 
                           'Cargo.toml', 'go.mod', 'Gemfile', 'requirements.txt',
                           'docker-compose.yml', 'Dockerfile', '.env.example']:
                    result["config_files"].append(os.path.join(rel_root, file))
        
        # Detect patterns
        patterns = result["patterns"]
        
        # Frontend detection
        if any(ext in result["file_extensions"] for ext in ['.tsx', '.jsx', '.vue']):
            patterns["frontend"] = True
            if '.tsx' in result["file_extensions"]:
                patterns["typescript"] = True
            if any('components' in d for d in result["directories"]):
                patterns["component_based"] = True
        
        # Backend detection
        if any(ext in result["file_extensions"] for ext in ['.py', '.go', '.rs', '.java']):
            patterns["backend"] = True
        
        # API detection
        if any('api' in d.lower() or 'routes' in d.lower() for d in result["directories"]):
            patterns["api"] = True
        
        # Database detection
        if any('migrations' in d or 'models' in d for d in result["directories"]):
            patterns["database"] = True
        
        return result
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["project_structure"] = exec_res
        shared["detected_patterns"] = exec_res["patterns"]
        return "analyzed"


class DetectTechStackNode(Node):
    """
    Detect technology stack from config files.
    
    Shared Store Inputs:
    - project_root: Project path
    - project_structure: From AnalyzeProjectNode
    
    Shared Store Outputs:
    - tech_stack: Detected technologies
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_root": shared.get("project_root", os.getcwd()),
            "config_files": shared.get("project_structure", {}).get("config_files", []),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze config files for tech stack."""
        project_root = inputs["project_root"]
        tech_stack = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
        }
        
        for config_file in inputs["config_files"]:
            full_path = os.path.join(project_root, config_file)
            filename = os.path.basename(config_file)
            
            try:
                if filename == "package.json":
                    with open(full_path, 'r') as f:
                        pkg = json.load(f)
                    
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    if "react" in deps:
                        tech_stack["frameworks"].append("React")
                    if "vue" in deps:
                        tech_stack["frameworks"].append("Vue")
                    if "next" in deps:
                        tech_stack["frameworks"].append("Next.js")
                    if "express" in deps:
                        tech_stack["frameworks"].append("Express")
                    if "prisma" in deps:
                        tech_stack["tools"].append("Prisma")
                    if "typescript" in deps:
                        tech_stack["languages"].append("TypeScript")
                    
                    tech_stack["languages"].append("JavaScript")
                
                elif filename == "pyproject.toml":
                    tech_stack["languages"].append("Python")
                    # Could parse for frameworks
                
                elif filename == "requirements.txt":
                    tech_stack["languages"].append("Python")
                    with open(full_path, 'r') as f:
                        reqs = f.read().lower()
                    if "django" in reqs:
                        tech_stack["frameworks"].append("Django")
                    if "flask" in reqs:
                        tech_stack["frameworks"].append("Flask")
                    if "fastapi" in reqs:
                        tech_stack["frameworks"].append("FastAPI")
                
                elif filename == "go.mod":
                    tech_stack["languages"].append("Go")
                
                elif filename == "Cargo.toml":
                    tech_stack["languages"].append("Rust")
                
                elif filename in ["docker-compose.yml", "docker-compose.yaml"]:
                    tech_stack["tools"].append("Docker")
                    # Could parse for database services
                    
            except (IOError, json.JSONDecodeError):
                pass
        
        # Deduplicate
        for key in tech_stack:
            tech_stack[key] = list(set(tech_stack[key]))
        
        return tech_stack
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["tech_stack"] = exec_res
        return "detected"


class GenerateExpertiseNode(Node):
    """
    Generate domain expertise files based on analysis.
    
    Shared Store Inputs:
    - project_root: Project path
    - detected_patterns: From AnalyzeProjectNode
    - tech_stack: From DetectTechStackNode
    
    Shared Store Outputs:
    - expertise_generated: List of generated files
    """
    
    def __init__(self, expertise_dir: str = "agent-os/expertise", **kwargs):
        super().__init__(**kwargs)
        self.expertise_dir = expertise_dir
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_root": shared.get("project_root", os.getcwd()),
            "expertise_path": os.path.join(
                shared.get("project_root", os.getcwd()),
                self.expertise_dir
            ),
            "patterns": shared.get("detected_patterns", {}),
            "tech_stack": shared.get("tech_stack", {}),
            "structure": shared.get("project_structure", {}),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate expertise files."""
        expertise_path = inputs["expertise_path"]
        generated = []
        
        try:
            os.makedirs(expertise_path, exist_ok=True)
            
            # Generate _index.yaml
            index = {
                "project_name": os.path.basename(inputs["project_root"]),
                "tech_stack": inputs["tech_stack"],
                "domains": [],
                "generated_at": datetime.now().isoformat(),
            }
            
            patterns = inputs["patterns"]
            
            # Generate domain files based on patterns
            if patterns.get("frontend"):
                index["domains"].append("frontend")
                frontend_expertise = {
                    "domain": "frontend",
                    "frameworks": [f for f in inputs["tech_stack"].get("frameworks", [])
                                 if f in ["React", "Vue", "Next.js", "Angular"]],
                    "patterns": {
                        "component_based": patterns.get("component_based", False),
                        "typescript": patterns.get("typescript", False),
                    },
                    "conventions": {
                        "component_location": "src/components",
                        "style_approach": "css-modules",  # Could detect
                    },
                    "learnings": [],
                }
                with open(os.path.join(expertise_path, "frontend.yaml"), 'w') as f:
                    yaml.dump(frontend_expertise, f, default_flow_style=False)
                generated.append("frontend.yaml")
            
            if patterns.get("api") or patterns.get("backend"):
                index["domains"].append("api")
                api_expertise = {
                    "domain": "api",
                    "frameworks": [f for f in inputs["tech_stack"].get("frameworks", [])
                                 if f in ["Express", "FastAPI", "Django", "Flask"]],
                    "patterns": {
                        "rest": True,  # Could detect GraphQL
                    },
                    "conventions": {
                        "route_location": "src/api or routes/",
                    },
                    "learnings": [],
                }
                with open(os.path.join(expertise_path, "api.yaml"), 'w') as f:
                    yaml.dump(api_expertise, f, default_flow_style=False)
                generated.append("api.yaml")
            
            if patterns.get("database"):
                index["domains"].append("database")
                db_expertise = {
                    "domain": "database",
                    "tools": [t for t in inputs["tech_stack"].get("tools", [])
                            if t in ["Prisma", "SQLAlchemy", "TypeORM"]],
                    "patterns": {
                        "migrations": True,
                        "models": True,
                    },
                    "learnings": [],
                }
                with open(os.path.join(expertise_path, "database.yaml"), 'w') as f:
                    yaml.dump(db_expertise, f, default_flow_style=False)
                generated.append("database.yaml")
            
            # Save index
            with open(os.path.join(expertise_path, "_index.yaml"), 'w') as f:
                yaml.dump(index, f, default_flow_style=False)
            generated.append("_index.yaml")
            
            return {"success": True, "generated": generated}
            
        except IOError as e:
            return {"success": False, "error": str(e), "generated": generated}
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["expertise_generated"] = exec_res["generated"]
        
        if exec_res["success"]:
            return "generated"
        return "error"


class GenerateRoutingNode(Node):
    """
    Generate routing configuration based on expertise.
    
    Shared Store Inputs:
    - project_root: Project path
    - detected_patterns: Patterns found
    - expertise_generated: Generated expertise files
    
    Shared Store Outputs:
    - routing_generated: Boolean
    """
    
    def prep(self, shared: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_root": shared.get("project_root", os.getcwd()),
            "patterns": shared.get("detected_patterns", {}),
        }
    
    def exec(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate routing.yaml."""
        project_root = inputs["project_root"]
        patterns = inputs["patterns"]
        
        routing = {
            "agents": {},
            "default_agent": "implementer",
        }
        
        if patterns.get("frontend"):
            routing["agents"]["frontend-specialist"] = {
                "file_patterns": [r"\.tsx$", r"\.jsx$", r"components/"],
                "keywords": ["component", "ui", "style"],
                "domains": ["frontend"],
            }
        
        if patterns.get("api"):
            routing["agents"]["api-specialist"] = {
                "file_patterns": [r"api/", r"routes/"],
                "keywords": ["endpoint", "api", "route"],
                "domains": ["api"],
            }
        
        if patterns.get("database"):
            routing["agents"]["database-specialist"] = {
                "file_patterns": [r"migrations/", r"models/"],
                "keywords": ["database", "migration", "schema"],
                "domains": ["database"],
            }
        
        try:
            routing_path = os.path.join(project_root, "agent-os/routing.yaml")
            os.makedirs(os.path.dirname(routing_path), exist_ok=True)
            
            with open(routing_path, 'w') as f:
                yaml.dump(routing, f, default_flow_style=False)
            
            return {"success": True, "path": routing_path}
            
        except IOError as e:
            return {"success": False, "error": str(e)}
    
    def post(self, shared: Dict[str, Any], prep_res: Dict[str, Any], exec_res: Dict[str, Any]) -> Optional[str]:
        shared["routing_generated"] = exec_res["success"]
        
        if exec_res["success"]:
            return "generated"
        return "error"


def create_bootstrap_flow() -> Flow:
    """Create the bootstrap workflow."""
    analyze = AnalyzeProjectNode()
    detect_stack = DetectTechStackNode()
    generate_expertise = GenerateExpertiseNode()
    generate_routing = GenerateRoutingNode()
    
    analyze - "analyzed" >> detect_stack
    detect_stack - "detected" >> generate_expertise
    generate_expertise - "generated" >> generate_routing
    generate_expertise - "error" >> None
    generate_routing - "generated" >> None
    generate_routing - "error" >> None
    
    return Flow(start=analyze)


class BootstrapFlow(Flow):
    """
    Pre-configured bootstrap workflow.
    
    Usage:
        flow = BootstrapFlow()
        shared = {"project_root": "/path/to/project"}
        flow.run(shared)
        
        print(shared["expertise_generated"])
    """
    
    def __init__(self):
        inner = create_bootstrap_flow()
        super().__init__(start=inner.start_node)
