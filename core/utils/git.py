"""
Git Utilities

Helper functions for git operations in Agent OS workflows.
"""

import subprocess
from typing import List, Optional, Tuple


def get_git_status(cwd: str = None) -> Optional[str]:
    """
    Get git status (porcelain format).
    
    Returns None if not a git repo or on error.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_recent_commits(
    cwd: str = None,
    count: int = 5,
    format: str = "oneline",
) -> List[str]:
    """
    Get recent git commits.
    
    Args:
        cwd: Working directory
        count: Number of commits to retrieve
        format: Git log format (oneline, short, full)
    
    Returns list of commit strings, or empty list on error.
    """
    try:
        format_arg = f"--format={format}" if format != "oneline" else "--oneline"
        
        result = subprocess.run(
            ["git", "log", format_arg, f"-{count}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            return [line for line in result.stdout.strip().split("\n") if line]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def get_current_branch(cwd: str = None) -> Optional[str]:
    """
    Get current git branch name.
    
    Returns None if not a git repo or on error.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def stage_and_commit(
    message: str,
    cwd: str = None,
    files: List[str] = None,
) -> Tuple[bool, str]:
    """
    Stage files and create a commit.
    
    Args:
        message: Commit message
        cwd: Working directory
        files: Specific files to stage (None = all changes)
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        # Stage files
        if files:
            stage_cmd = ["git", "add"] + files
        else:
            stage_cmd = ["git", "add", "-A"]
        
        stage_result = subprocess.run(
            stage_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if stage_result.returncode != 0:
            return False, f"Stage failed: {stage_result.stderr}"
        
        # Check if there's anything to commit
        status = get_git_status(cwd)
        if not status:
            return True, "Nothing to commit"
        
        # Commit
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if commit_result.returncode == 0:
            return True, commit_result.stdout.strip()
        return False, f"Commit failed: {commit_result.stderr}"
        
    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except FileNotFoundError:
        return False, "Git not found"


def get_changed_files(cwd: str = None, staged_only: bool = False) -> List[str]:
    """
    Get list of changed files.
    
    Args:
        cwd: Working directory
        staged_only: Only return staged files
    
    Returns list of file paths.
    """
    try:
        if staged_only:
            cmd = ["git", "diff", "--cached", "--name-only"]
        else:
            cmd = ["git", "diff", "--name-only", "HEAD"]
        
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def get_file_diff(
    file_path: str,
    cwd: str = None,
    context_lines: int = 3,
) -> Optional[str]:
    """
    Get diff for a specific file.
    
    Returns None on error.
    """
    try:
        result = subprocess.run(
            ["git", "diff", f"-U{context_lines}", "--", file_path],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
