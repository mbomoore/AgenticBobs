"""Storage utilities for process automation data.

Handles persistence of scenarios, logs, and results using DuckDB and Parquet.
"""
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
from datetime import datetime

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class StorageProvider:
    """Storage provider for process automation data."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = None
        
        if DUCKDB_AVAILABLE:
            self.conn = duckdb.connect(db_path)
            self._setup_tables()
    
    def _setup_tables(self):
        """Setup database tables."""
        if not self.conn:
            return
        
        # Events table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP,
                event_type VARCHAR,
                case_id VARCHAR,
                activity VARCHAR,
                resource VARCHAR,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Scenarios table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE,
                config JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Simulation results table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation_results (
                id INTEGER PRIMARY KEY,
                scenario_name VARCHAR,
                run_id VARCHAR,
                metrics JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def store_events(self, events: List[Dict[str, Any]]):
        """Store events in the database."""
        if not self.conn:
            raise RuntimeError("Database connection not available")
        
        for event in events:
            self.conn.execute("""
                INSERT INTO events (timestamp, event_type, case_id, activity, resource, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                event.get("timestamp"),
                event.get("event_type"),
                event.get("case_id"),
                event.get("activity"),
                event.get("resource"),
                json.dumps(event.get("data", {}))
            ])
    
    def store_scenario(self, name: str, config: Dict[str, Any]):
        """Store scenario configuration."""
        if not self.conn:
            raise RuntimeError("Database connection not available")
        
        self.conn.execute("""
            INSERT OR REPLACE INTO scenarios (name, config, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, [name, json.dumps(config)])
    
    def get_scenario(self, name: str) -> Optional[Dict[str, Any]]:
        """Get scenario configuration by name."""
        if not self.conn:
            return None
        
        result = self.conn.execute("""
            SELECT config FROM scenarios WHERE name = ?
        """, [name]).fetchone()
        
        if result:
            return json.loads(result[0])
        return None
    
    def store_simulation_results(self, scenario_name: str, run_id: str, metrics: Dict[str, Any]):
        """Store simulation results."""
        if not self.conn:
            raise RuntimeError("Database connection not available")
        
        self.conn.execute("""
            INSERT INTO simulation_results (scenario_name, run_id, metrics)
            VALUES (?, ?, ?)
        """, [scenario_name, run_id, json.dumps(metrics)])
    
    def export_to_parquet(self, table_name: str, output_path: str):
        """Export table to Parquet format."""
        if not self.conn:
            raise RuntimeError("Database connection not available")
        
        self.conn.execute(f"""
            COPY {table_name} TO '{output_path}' (FORMAT PARQUET)
        """)
    
    def query(self, sql: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        if not self.conn:
            raise RuntimeError("Database connection not available")
        
        if params:
            result = self.conn.execute(sql, params)
        else:
            result = self.conn.execute(sql)
        
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


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
    
    def store_simulation_results(self, scenario_name: str, run_id: str, metrics: Dict[str, Any]):
        """Store simulation results as JSON file."""
        filename = self.base_path / f"results_{scenario_name}_{run_id}.json"
        
        with open(filename, "w") as f:
            json.dump(metrics, f, indent=2, default=str)


def create_storage_provider(db_path: str = ":memory:") -> Union[StorageProvider, FileStorageProvider]:
    """Create appropriate storage provider based on available dependencies."""
    if DUCKDB_AVAILABLE:
        return StorageProvider(db_path)
    else:
        return FileStorageProvider()