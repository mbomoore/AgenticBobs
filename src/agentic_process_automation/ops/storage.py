"""Storage utilities for process automation data.

Handles persistence of scenarios, logs, and results.
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False


class FileStorageProvider:
    """File-based storage provider for when DuckDB is not available."""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def store_events(self, events: List[Dict[str, Any]]):
        """Store events as JSON files."""
        timestamp = datetime.now().isoformat().replace(":", "_")
        filename = self.base_path / f"events_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(events, f, indent=2, default=str)
    
    def store_scenario(self, name: str, config: Dict[str, Any]):
        """Store scenario as JSON file."""
        filename = self.base_path / f"scenario_{name}.json"
        
        with open(filename, "w") as f:
            json.dump(config, f, indent=2)
    
    def get_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Get scenario from JSON file."""
        filename = self.base_path / f"scenario_{name}.json"
        
        if filename.exists():
            with open(filename, "r") as f:
                return json.load(f)
        return None


def create_storage_provider(db_path: str = ":memory:"):
    """Create appropriate storage provider based on available dependencies."""
    if DUCKDB_AVAILABLE:
        # Return a DuckDB provider when available
        pass  # TODO: Implement DuckDB provider
    
    return FileStorageProvider()
