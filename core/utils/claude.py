"""
Claude Code Integration Utilities

Helper functions for building prompts and formatting context
for Claude Code subagent delegation.
"""

from typing import Any, Dict, List, Optional


def build_delegation_prompt(
    agent_name: str,
    task: Dict[str, Any],
    expertise: Dict[str, Any] = None,
    spec_context: Dict[str, Any] = None,
    include_expertise: bool = True,
) -> str:
    """
    Build a complete delegation prompt for Claude Code.
    
    Args:
        agent_name: Name of the subagent to invoke
        task: Task dictionary with description, files, etc.
        expertise: Domain expertise to include as context
        spec_context: Specification context
        include_expertise: Whether to include expertise in prompt
    
    Returns:
        Formatted prompt string for delegation
    """
    parts = []
    
    # Main instruction
    task_desc = task.get("description", str(task))
    parts.append(f"Use the {agent_name} subagent to: {task_desc}")
    
    # Task details
    if task.get("file_patterns"):
        files = task["file_patterns"]
        if isinstance(files, list):
            files = ", ".join(files)
        parts.append(f"\nFiles to focus on: {files}")
    
    if task.get("acceptance_criteria"):
        criteria = task["acceptance_criteria"]
        if isinstance(criteria, list):
            criteria = "\n- ".join([""] + criteria)
        parts.append(f"\nAcceptance criteria:{criteria}")
    
    # Spec context
    if spec_context:
        parts.append(f"\nSpecification: {spec_context.get('name', 'Unknown')}")
        if spec_context.get("path"):
            parts.append(f"Spec location: {spec_context['path']}")
    
    # Expertise context
    if include_expertise and expertise:
        expertise_str = format_expertise_context(expertise)
        if expertise_str:
            parts.append(f"\nDomain knowledge:\n{expertise_str}")
    
    return "\n".join(parts)


def format_expertise_context(
    expertise: Dict[str, Any],
    max_items: int = 5,
    include_learnings: bool = True,
) -> str:
    """
    Format expertise for inclusion in prompts.
    
    Args:
        expertise: Expertise dictionary (index + domains)
        max_items: Max items per section
        include_learnings: Include recent learnings
    
    Returns:
        Formatted expertise string
    """
    parts = []
    
    # Index information
    index = expertise.get("index", {})
    if index.get("tech_stack"):
        tech = index["tech_stack"]
        if tech.get("frameworks"):
            parts.append(f"Frameworks: {', '.join(tech['frameworks'][:max_items])}")
        if tech.get("languages"):
            parts.append(f"Languages: {', '.join(tech['languages'][:max_items])}")
    
    # Domain-specific expertise
    domains = expertise.get("domains", {})
    for domain_name, domain_data in domains.items():
        domain_parts = [f"\n[{domain_name.upper()}]"]
        
        # Conventions
        conventions = domain_data.get("conventions", {})
        if conventions:
            for key, value in list(conventions.items())[:max_items]:
                domain_parts.append(f"  {key}: {value}")
        
        # Patterns
        patterns = domain_data.get("patterns", {})
        active_patterns = [k for k, v in patterns.items() if v]
        if active_patterns:
            domain_parts.append(f"  Patterns: {', '.join(active_patterns[:max_items])}")
        
        # Recent learnings
        if include_learnings:
            learnings = domain_data.get("learnings", [])
            recent = learnings[-max_items:] if learnings else []
            for learning in recent:
                content = learning.get("content", learning) if isinstance(learning, dict) else learning
                domain_parts.append(f"  • {content[:100]}")
        
        if len(domain_parts) > 1:  # More than just the header
            parts.extend(domain_parts)
    
    return "\n".join(parts)


def build_verification_prompt(
    task: Dict[str, Any],
    implementation: Dict[str, Any],
    spec: Dict[str, Any] = None,
) -> str:
    """
    Build a prompt for verifying task completion.
    
    Args:
        task: Original task
        implementation: Implementation details
        spec: Specification for context
    
    Returns:
        Verification prompt
    """
    parts = ["Verify the following implementation:"]
    
    # Task
    parts.append(f"\nTask: {task.get('description', str(task))}")
    
    # What was done
    if implementation.get("files_modified"):
        parts.append(f"\nFiles modified: {', '.join(implementation['files_modified'])}")
    
    if implementation.get("summary"):
        parts.append(f"\nImplementation summary: {implementation['summary']}")
    
    # Acceptance criteria
    criteria = task.get("acceptance_criteria", [])
    if criteria:
        parts.append("\nAcceptance criteria to verify:")
        for c in criteria:
            parts.append(f"  [ ] {c}")
    
    # Verification instructions
    parts.append("\nPlease verify:")
    parts.append("1. All acceptance criteria are met")
    parts.append("2. Code follows project conventions")
    parts.append("3. No obvious bugs or issues")
    parts.append("4. Tests pass (if applicable)")
    
    return "\n".join(parts)


def format_task_for_display(task: Dict[str, Any]) -> str:
    """
    Format a task for display to user.
    
    Args:
        task: Task dictionary
    
    Returns:
        Human-readable task description
    """
    if isinstance(task, str):
        return task
    
    parts = []
    
    # ID and description
    task_id = task.get("id", "unknown")
    desc = task.get("description", "No description")
    parts.append(f"[{task_id}] {desc}")
    
    # Priority
    if task.get("priority"):
        parts.append(f"  Priority: {task['priority']}")
    
    # Files
    if task.get("file_patterns"):
        files = task["file_patterns"]
        if isinstance(files, list):
            files = ", ".join(files[:5])
            if len(task["file_patterns"]) > 5:
                files += f" (+{len(task['file_patterns']) - 5} more)"
        parts.append(f"  Files: {files}")
    
    # Dependencies
    if task.get("depends_on"):
        deps = task["depends_on"]
        if isinstance(deps, list):
            deps = ", ".join(deps)
        parts.append(f"  Depends on: {deps}")
    
    return "\n".join(parts)


def format_progress_summary(progress: Dict[str, Any]) -> str:
    """
    Format progress state for display.
    
    Args:
        progress: Progress dictionary
    
    Returns:
        Human-readable progress summary
    """
    parts = ["Progress Summary:"]
    
    tasks = progress.get("tasks", [])
    completed = progress.get("completed", [])
    failed = progress.get("failed", [])
    current = progress.get("current_task")
    
    total = len(tasks)
    done = len(completed)
    fail = len(failed)
    remaining = total - done - fail
    
    parts.append(f"  Total tasks: {total}")
    parts.append(f"  Completed: {done}")
    parts.append(f"  Failed: {fail}")
    parts.append(f"  Remaining: {remaining}")
    
    if current:
        parts.append(f"  Current: {current}")
    
    # Completion percentage
    if total > 0:
        pct = (done / total) * 100
        parts.append(f"  Progress: {pct:.1f}%")
    
    return "\n".join(parts)
