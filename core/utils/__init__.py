"""
Utilities for Agent OS PocketFlow Integration
"""

from .git import (
    get_git_status,
    get_recent_commits,
    stage_and_commit,
    get_current_branch,
)
from .claude import (
    build_delegation_prompt,
    format_expertise_context,
)

__all__ = [
    # Git
    'get_git_status',
    'get_recent_commits', 
    'stage_and_commit',
    'get_current_branch',
    # Claude
    'build_delegation_prompt',
    'format_expertise_context',
]
