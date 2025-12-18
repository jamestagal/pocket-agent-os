"""
Agent OS Custom Nodes for PocketFlow

These nodes extend PocketFlow to provide:
- Session management (start, end, checkpoint)
- Domain expertise loading and self-improvement
- Claude Code subagent delegation
- Smart agent routing
- Progress tracking and guards
"""

from .session import (
    SessionStartNode,
    SessionEndNode,
    CheckpointNode,
)
from .expertise import (
    LoadExpertiseNode,
    ValidateExpertiseNode,
    SelfImproveNode,
)
from .delegation import (
    ClaudeCodeDelegationNode,
    SubagentResultNode,
)
from .routing import (
    AgentSelectorNode,
)
from .progress import (
    ProgressGuardNode,
    TaskSelectorNode,
    MarkTaskCompleteNode,
)

__all__ = [
    # Session
    'SessionStartNode',
    'SessionEndNode',
    'CheckpointNode',
    # Expertise
    'LoadExpertiseNode',
    'ValidateExpertiseNode',
    'SelfImproveNode',
    # Delegation
    'ClaudeCodeDelegationNode',
    'SubagentResultNode',
    # Routing
    'AgentSelectorNode',
    # Progress
    'ProgressGuardNode',
    'TaskSelectorNode',
    'MarkTaskCompleteNode',
]
