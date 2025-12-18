"""
File-based Store for Shared State

Provides persistence utilities for saving and loading
the PocketFlow shared store to/from JSON files.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, Optional


class FileStore:
    """
    File-based persistence for PocketFlow shared store.
    
    Features:
    - Auto-save after operations
    - Checkpoint history
    - JSON serialization with datetime support
    
    Usage:
        store = FileStore("/path/to/sessions", "my-session")
        
        # Load existing or create new
        shared = store.load()
        
        # Use in flow
        flow.run(shared)
        
        # Save after flow
        store.save(shared)
    """
    
    def __init__(
        self,
        base_path: str,
        session_id: str,
        auto_backup: bool = True,
        max_backups: int = 5,
    ):
        self.base_path = base_path
        self.session_id = session_id
        self.auto_backup = auto_backup
        self.max_backups = max_backups
        
        self.file_path = os.path.join(base_path, f"{session_id}.json")
        self.backup_dir = os.path.join(base_path, "backups")
    
    def load(self) -> Dict[str, Any]:
        """Load shared store from file, or return empty dict."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {self.file_path}: {e}")
        
        return {}
    
    def save(self, shared: Dict[str, Any]) -> bool:
        """
        Save shared store to file.
        
        Returns True on success, False on failure.
        """
        try:
            # Ensure directory exists
            os.makedirs(self.base_path, exist_ok=True)
            
            # Create backup if file exists and auto_backup enabled
            if self.auto_backup and os.path.exists(self.file_path):
                self._create_backup()
            
            # Add metadata
            shared["_store_metadata"] = {
                "saved_at": datetime.now().isoformat(),
                "session_id": self.session_id,
            }
            
            # Write with custom serializer
            with open(self.file_path, 'w') as f:
                json.dump(shared, f, indent=2, default=self._json_serializer)
            
            return True
            
        except IOError as e:
            print(f"Error saving store: {e}")
            return False
    
    def _create_backup(self) -> None:
        """Create a timestamped backup of current file."""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.session_id}_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Copy current file to backup
            with open(self.file_path, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # Cleanup old backups
            self._cleanup_backups()
            
        except IOError:
            pass  # Backup failure shouldn't block save
    
    def _cleanup_backups(self) -> None:
        """Remove old backups beyond max_backups limit."""
        try:
            backups = []
            prefix = f"{self.session_id}_"
            
            for f in os.listdir(self.backup_dir):
                if f.startswith(prefix) and f.endswith('.json'):
                    full_path = os.path.join(self.backup_dir, f)
                    backups.append((os.path.getmtime(full_path), full_path))
            
            # Sort by modification time (oldest first)
            backups.sort()
            
            # Remove oldest backups
            while len(backups) > self.max_backups:
                _, path = backups.pop(0)
                os.remove(path)
                
        except IOError:
            pass
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def checkpoint(self, shared: Dict[str, Any], label: str = None) -> bool:
        """
        Create a named checkpoint.
        
        Unlike regular save, checkpoints are never overwritten.
        """
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            label_part = f"_{label}" if label else ""
            checkpoint_name = f"{self.session_id}_checkpoint{label_part}_{timestamp}.json"
            checkpoint_path = os.path.join(self.backup_dir, checkpoint_name)
            
            with open(checkpoint_path, 'w') as f:
                json.dump(shared, f, indent=2, default=self._json_serializer)
            
            return True
            
        except IOError as e:
            print(f"Error creating checkpoint: {e}")
            return False
    
    def list_checkpoints(self) -> list:
        """List all checkpoints for this session."""
        checkpoints = []
        
        if os.path.exists(self.backup_dir):
            prefix = f"{self.session_id}_checkpoint"
            
            for f in os.listdir(self.backup_dir):
                if f.startswith(prefix) and f.endswith('.json'):
                    full_path = os.path.join(self.backup_dir, f)
                    checkpoints.append({
                        "name": f,
                        "path": full_path,
                        "modified": datetime.fromtimestamp(
                            os.path.getmtime(full_path)
                        ).isoformat(),
                    })
        
        return sorted(checkpoints, key=lambda x: x["modified"], reverse=True)
    
    def load_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """Load a specific checkpoint."""
        checkpoint_path = os.path.join(self.backup_dir, checkpoint_name)
        
        if os.path.exists(checkpoint_path):
            try:
                with open(checkpoint_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return None


# Convenience functions

def load_shared(
    base_path: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Load shared store from file.
    
    Convenience function for simple use cases.
    
    Usage:
        shared = load_shared("agent-os/sessions", "my-session")
    """
    store = FileStore(base_path, session_id)
    return store.load()


def save_shared(
    shared: Dict[str, Any],
    base_path: str,
    session_id: str,
) -> bool:
    """
    Save shared store to file.
    
    Convenience function for simple use cases.
    
    Usage:
        save_shared(shared, "agent-os/sessions", "my-session")
    """
    store = FileStore(base_path, session_id)
    return store.save(shared)
