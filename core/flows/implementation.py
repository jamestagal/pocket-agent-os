"""
Implementation Workflow Flow

Complete implementation workflow:
1. Start session
2. Load expertise
3. Select task
4. Route to agent
5. Delegate to subagent
6. Process result
7. Self-improve
8. Checkpoint
9. Loop or end session
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pocketflow import Flow
from nodes.session import SessionStartNode, SessionEndNode, CheckpointNode
from nodes.expertise import LoadExpertiseNode, SelfImproveNode
from nodes.delegation import ClaudeCodeDelegationNode, SubagentResultNode
from nodes.routing import AgentSelectorNode
from nodes.progress import TaskSelectorNode, MarkTaskCompleteNode, ProgressGuardNode


def create_implementation_flow(
    delegation_mode: str = "print",
    auto_checkpoint: bool = True,
    self_improve: bool = True,
) -> Flow:
    """
    Create a complete implementation workflow flow.
    
    Args:
        delegation_mode: How to delegate tasks:
            - "print": Print ONE delegation and exit (legacy)
            - "batch": Print ALL delegations, then exit with summary
            - "file": Write delegations to file
            - "cli": Execute via claude CLI
        auto_checkpoint: Whether to checkpoint after each task
        self_improve: Whether to update expertise after tasks
    
    Returns:
        Flow ready to execute
    
    Usage:
        flow = create_implementation_flow(delegation_mode="batch")
        shared = {
            "project_root": "/path/to/project",
            "spec_name": "my-feature",
        }
        flow.run(shared)
    """
    
    # Create nodes
    session_start = SessionStartNode()
    load_expertise = LoadExpertiseNode()
    task_selector = TaskSelectorNode()
    progress_guard = ProgressGuardNode()
    agent_router = AgentSelectorNode()
    delegation = ClaudeCodeDelegationNode(delegation_mode=delegation_mode)
    result_processor = SubagentResultNode()
    mark_complete = MarkTaskCompleteNode()
    self_improver = SelfImproveNode()
    checkpoint = CheckpointNode()
    session_end = SessionEndNode()
    
    # Build flow graph
    #
    # BATCH MODE FLOW:
    # session_start → load_expertise → task_selector
    #                                      ↓
    #                    [all_complete] → session_end
    #                    [all_printed] → session_end (batch summary)
    #                    [task_selected] ↓
    #                               progress_guard
    #                                      ↓
    #                    [blocked] → task_selector (skip blocked)
    #                    [valid] ↓
    #                               agent_router
    #                                      ↓
    #                               delegation
    #                                      ↓
    #                    [printed] → task_selector (continue batch)
    #                    [delegated] → result_processor
    #                                      ↓
    #                    [failed] → task_selector (retry next)
    #                    [success] ↓
    #                               mark_complete → ... → task_selector (loop)
    
    # Session start connections
    session_start - "fresh" >> load_expertise
    session_start - "resumed" >> load_expertise
    
    # Load expertise → task selection
    load_expertise - "loaded" >> task_selector
    load_expertise - "empty" >> task_selector
    load_expertise - "partial" >> task_selector
    
    # Task selection branching
    task_selector - "all_complete" >> session_end
    task_selector - "all_blocked" >> session_end
    task_selector - "all_printed" >> session_end  # Batch mode: all tasks printed
    task_selector - "task_selected" >> progress_guard
    
    # Progress guard
    progress_guard - "valid" >> agent_router
    progress_guard - "blocked" >> task_selector  # Skip blocked tasks, try next
    
    # Agent routing → delegation
    agent_router - "high" >> delegation
    agent_router - "medium" >> delegation
    agent_router - "low" >> delegation
    
    # Delegation branching
    delegation - "delegated" >> result_processor  # CLI/file mode: process result
    delegation - "error" >> task_selector  # Skip to next task on error
    delegation - "print_complete" >> session_end  # Legacy print mode: exit after one
    delegation - "printed" >> task_selector  # Batch mode: continue to next task
    
    # Result processing branching
    result_processor - "failed" >> task_selector  # Try next task
    result_processor - "success" >> mark_complete
    
    # After marking complete
    if self_improve:
        mark_complete - "completed" >> self_improver
        self_improver - "improved" >> checkpoint if auto_checkpoint else task_selector
        self_improver - "no_changes" >> checkpoint if auto_checkpoint else task_selector
    else:
        mark_complete - "completed" >> checkpoint if auto_checkpoint else task_selector
    
    # Checkpoint loops back to task selection
    if auto_checkpoint:
        checkpoint - "checkpointed" >> task_selector
        checkpoint - "error" >> task_selector
    
    # Session end
    session_end - "saved" >> None  # Terminal
    session_end - "error" >> None  # Terminal
    
    return Flow(start=session_start)


class ImplementationFlow(Flow):
    """
    Pre-configured implementation workflow.
    
    A class-based flow for more control over configuration.
    
    Usage:
        flow = ImplementationFlow(delegation_mode="batch")
        shared = {
            "project_root": "/path/to/project",
            "spec_name": "my-feature",
        }
        flow.run(shared)
    """
    
    def __init__(
        self,
        delegation_mode: str = "print",
        auto_checkpoint: bool = True,
        self_improve: bool = True,
    ):
        # Build the flow
        inner_flow = create_implementation_flow(
            delegation_mode=delegation_mode,
            auto_checkpoint=auto_checkpoint,
            self_improve=self_improve,
        )
        
        # Initialize with the start node from inner flow
        super().__init__(start=inner_flow.start_node)
        
        # Copy successors
        self.start_node = inner_flow.start_node
