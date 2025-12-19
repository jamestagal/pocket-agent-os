#!/usr/bin/env python3
"""
Agent OS Flow Runner

CLI for executing PocketFlow workflows in Agent OS.

Usage:
    python run-flow.py bootstrap --project /path/to/project
    python run-flow.py implement --project /path/to/project --spec my-feature
    python run-flow.py spec --project /path/to/project --name my-feature --requirements "Build X"
"""

import os
import sys
import argparse
import json
from datetime import datetime

# Add core to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "core")
sys.path.insert(0, CORE_DIR)

from pocketflow import Flow
from flows import (
    ImplementationFlow,
    SpecificationFlow,
    BootstrapFlow,
    create_implementation_flow,
    create_bootstrap_flow,
)
from store import FileStore


def run_bootstrap(args):
    """Run the bootstrap flow to initialize expertise."""
    print(f"🚀 Bootstrapping expertise for: {args.project}")
    print("-" * 50)
    
    flow = BootstrapFlow()
    shared = {
        "project_root": os.path.abspath(args.project),
    }
    
    flow.run(shared)
    
    # Report results
    print("\n✅ Bootstrap complete!")
    print(f"   Project structure analyzed")
    print(f"   Tech stack: {shared.get('tech_stack', {})}")
    print(f"   Detected patterns: {list(shared.get('detected_patterns', {}).keys())}")
    print(f"   Generated files: {shared.get('expertise_generated', [])}")
    
    if shared.get("routing_generated"):
        print(f"   Routing config created")
    
    return shared


def run_implementation(args):
    """Run the implementation workflow."""
    print(f"🔧 Starting implementation workflow")
    print(f"   Project: {args.project}")
    print(f"   Spec: {args.spec}")
    print(f"   Mode: {args.mode}")
    print("-" * 50)
    
    # Create flow with options
    flow = create_implementation_flow(
        delegation_mode=args.mode,
        auto_checkpoint=not args.no_checkpoint,
        self_improve=not args.no_improve,
    )
    
    # Initialize shared store
    project_root = os.path.abspath(args.project)
    session_id = args.session or f"impl_{int(datetime.now().timestamp())}"
    
    # Try to load existing session
    store = FileStore(
        os.path.join(project_root, "agent-os/sessions"),
        session_id
    )
    shared = store.load()
    
    # Set up initial state
    shared.update({
        "project_root": project_root,
        "spec_name": args.spec,
        "session_id": session_id,
        "delegation_mode": args.mode,
    })
    
    try:
        # Run the flow
        flow.run(shared)
        
        # Save final state
        store.save(shared)
        
        # Report results
        print("\n" + "=" * 50)
        print("📊 Session Summary")
        print("=" * 50)
        print(f"   Session ID: {session_id}")
        print(f"   Status: {shared.get('session_summary', 'Completed')}")
        
        progress = shared.get("progress", {})
        completed = len(progress.get("completed", []))
        total = len(progress.get("tasks", []))
        print(f"   Tasks: {completed}/{total} completed")
        
        if shared.get("delegation_history"):
            print(f"   Delegations: {len(shared['delegation_history'])}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted! Saving state...")
        store.save(shared)
        print(f"   Session saved: {session_id}")
        print("   Resume with: --session", session_id)
    
    return shared


def run_spec(args):
    """Run the specification creation workflow."""
    print(f"📝 Creating specification: {args.name}")
    print("-" * 50)
    
    flow = SpecificationFlow()
    shared = {
        "project_root": os.path.abspath(args.project),
        "spec_name": args.name,
        "requirements": args.requirements,
    }
    
    flow.run(shared)
    
    # Report results
    if shared.get("spec_saved"):
        print("\n✅ Specification created!")
        print(f"   Path: {shared.get('spec_path')}")
        print(f"   Tasks: {len(shared.get('tasks', []))}")
    else:
        print("\n❌ Specification creation failed")
        if shared.get("spec_errors"):
            for error in shared["spec_errors"]:
                print(f"   Error: {error}")
    
    return shared


def run_status(args):
    """Show current session/progress status."""
    project_root = os.path.abspath(args.project)
    sessions_dir = os.path.join(project_root, "agent-os/sessions")
    
    print(f"📊 Status for: {project_root}")
    print("-" * 50)
    
    # List sessions
    # Session files match patterns: impl_*, session_*, bootstrap_*
    # Exclude utility files like pending_delegations.json
    SESSION_PREFIXES = ('impl_', 'session_', 'bootstrap_', 'spec_')
    
    if os.path.exists(sessions_dir):
        sessions = [
            f for f in os.listdir(sessions_dir) 
            if f.endswith('.json') and any(f.startswith(p) for p in SESSION_PREFIXES)
        ]
        if sessions:
            print(f"\nSessions ({len(sessions)}):")
            for session_file in sorted(sessions)[-5:]:  # Last 5
                session_path = os.path.join(sessions_dir, session_file)
                try:
                    with open(session_path) as f:
                        data = json.load(f)
                    
                    session_id = session_file[:-5]
                    progress = data.get("progress", {})
                    completed = len(progress.get("completed", []))
                    total = len(progress.get("tasks", []))
                    
                    print(f"   {session_id}: {completed}/{total} tasks")
                except:
                    print(f"   {session_file}: (unable to read)")
        else:
            print("\nNo sessions found.")
    
    # Check for specs
    specs_dir = os.path.join(project_root, "agent-os/specs")
    if os.path.exists(specs_dir):
        specs = [d for d in os.listdir(specs_dir) 
                if os.path.isdir(os.path.join(specs_dir, d))]
        if specs:
            print(f"\nSpecs ({len(specs)}):")
            for spec in sorted(specs):
                progress_path = os.path.join(specs_dir, spec, "progress.json")
                if os.path.exists(progress_path):
                    try:
                        with open(progress_path) as f:
                            progress = json.load(f)
                        completed = len(progress.get("completed", []))
                        total = len(progress.get("tasks", []))
                        print(f"   {spec}: {completed}/{total} tasks")
                    except:
                        print(f"   {spec}: (unable to read progress)")
                else:
                    print(f"   {spec}: (no progress file)")
    
    # Check expertise
    expertise_dir = os.path.join(project_root, "agent-os/expertise")
    if os.path.exists(expertise_dir):
        domains = [f[:-5] for f in os.listdir(expertise_dir) 
                  if f.endswith('.yaml') and not f.startswith('_')]
        if domains:
            print(f"\nExpertise domains: {', '.join(domains)}")


def main():
    parser = argparse.ArgumentParser(
        description="Agent OS Flow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bootstrap expertise for a project
  python run-flow.py bootstrap --project /path/to/project
  
  # Create a new specification
  python run-flow.py spec --project . --name my-feature --requirements "Build feature X"
  
  # Run implementation workflow
  python run-flow.py implement --project . --spec my-feature
  
  # Check status
  python run-flow.py status --project .
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Bootstrap command
    bootstrap_parser = subparsers.add_parser("bootstrap", help="Initialize expertise")
    bootstrap_parser.add_argument("--project", "-p", required=True, help="Project root path")
    
    # Spec command
    spec_parser = subparsers.add_parser("spec", help="Create specification")
    spec_parser.add_argument("--project", "-p", required=True, help="Project root path")
    spec_parser.add_argument("--name", "-n", required=True, help="Specification name")
    spec_parser.add_argument("--requirements", "-r", required=True, help="Requirements description")
    
    # Implement command
    impl_parser = subparsers.add_parser("implement", help="Run implementation workflow")
    impl_parser.add_argument("--project", "-p", required=True, help="Project root path")
    impl_parser.add_argument("--spec", "-s", required=True, help="Specification name")
    impl_parser.add_argument("--session", help="Resume specific session")
    impl_parser.add_argument("--mode", "-m", default="batch",
                            choices=["batch", "print", "file", "cli"],
                            help="Delegation mode: batch (all tasks), print (one task), file, cli")
    impl_parser.add_argument("--no-checkpoint", action="store_true",
                            help="Disable auto-checkpointing")
    impl_parser.add_argument("--no-improve", action="store_true",
                            help="Disable self-improvement")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show status")
    status_parser.add_argument("--project", "-p", required=True, help="Project root path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to appropriate handler
    if args.command == "bootstrap":
        run_bootstrap(args)
    elif args.command == "spec":
        run_spec(args)
    elif args.command == "implement":
        run_implementation(args)
    elif args.command == "status":
        run_status(args)


if __name__ == "__main__":
    main()
