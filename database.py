"""
Database Module
===============
SQLite-based persistence for Maestro V3.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import threading


class Database:
    """
    SQLite database for persistent storage.
    Thread-safe with connection pooling.
    """
    
    _local = threading.local()
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path(__file__).parent / "maestro.db"
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic commit/rollback"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database tables"""
        with self.get_cursor() as cursor:
            # Projects table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT,
                    objective TEXT,
                    status TEXT DEFAULT 'new',
                    created_at TEXT,
                    updated_at TEXT,
                    config TEXT
                )
            ''')
            
            # Workflows table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    name TEXT,
                    objective TEXT,
                    status TEXT DEFAULT 'created',
                    created_at TEXT,
                    completed_at TEXT,
                    task_data TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            # Agent executions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT,
                    agent_name TEXT,
                    task TEXT,
                    result TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    tokens_used INTEGER,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            ''')
            
            # Memory entries table (for vector-like search)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    agent_name TEXT,
                    entry_type TEXT,
                    content TEXT,
                    context TEXT,
                    keywords TEXT,
                    created_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    event_data TEXT,
                    created_at TEXT
                )
            ''')
    
    # Project methods
    def save_project(self, project_id: str, name: str, path: str, 
                     objective: str = "", status: str = "new", 
                     config: Dict = None):
        """Save or update a project"""
        now = datetime.now().isoformat()
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT OR REPLACE INTO projects 
                (id, name, path, objective, status, created_at, updated_at, config)
                VALUES (?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM projects WHERE id = ?), ?),
                    ?, ?)
            ''', (project_id, name, path, objective, status, 
                  project_id, now, now, json.dumps(config or {})))
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a project by ID"""
        with self.get_cursor() as cursor:
            cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_all_projects(self, limit: int = 50) -> List[Dict]:
        """Get all projects, ordered by updated_at"""
        with self.get_cursor() as cursor:
            cursor.execute(
                'SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?', 
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_project(self, project_id: str):
        """Delete a project and related data"""
        with self.get_cursor() as cursor:
            cursor.execute('DELETE FROM memory_entries WHERE project_id = ?', (project_id,))
            cursor.execute('DELETE FROM agent_executions WHERE workflow_id IN (SELECT id FROM workflows WHERE project_id = ?)', (project_id,))
            cursor.execute('DELETE FROM workflows WHERE project_id = ?', (project_id,))
            cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    
    # Workflow methods
    def save_workflow(self, workflow_id: str, project_id: str, name: str,
                      objective: str, status: str = "created", 
                      task_data: List = None):
        """Save or update a workflow"""
        now = datetime.now().isoformat()
        completed = now if status in ["completed", "failed", "cancelled"] else None
        
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT OR REPLACE INTO workflows
                (id, project_id, name, objective, status, created_at, completed_at, task_data)
                VALUES (?, ?, ?, ?, ?,
                    COALESCE((SELECT created_at FROM workflows WHERE id = ?), ?),
                    ?, ?)
            ''', (workflow_id, project_id, name, objective, status,
                  workflow_id, now, completed, json.dumps(task_data or [])))
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Get a workflow by ID"""
        with self.get_cursor() as cursor:
            cursor.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['task_data'] = json.loads(result.get('task_data') or '[]')
                return result
        return None
    
    # Agent execution methods
    def log_agent_execution(self, workflow_id: str, agent_name: str,
                           task: str, result: str, status: str,
                           started_at: str, completed_at: str,
                           duration_ms: int = 0, tokens_used: int = 0):
        """Log an agent execution"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO agent_executions
                (workflow_id, agent_name, task, result, status, 
                 started_at, completed_at, duration_ms, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (workflow_id, agent_name, task, result, status,
                  started_at, completed_at, duration_ms, tokens_used))
    
    def get_agent_stats(self, agent_name: str = None) -> Dict:
        """Get statistics for agent(s)"""
        with self.get_cursor() as cursor:
            if agent_name:
                cursor.execute('''
                    SELECT 
                        agent_name,
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                        AVG(duration_ms) as avg_duration,
                        SUM(tokens_used) as total_tokens
                    FROM agent_executions
                    WHERE agent_name = ?
                    GROUP BY agent_name
                ''', (agent_name,))
            else:
                cursor.execute('''
                    SELECT 
                        agent_name,
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                        AVG(duration_ms) as avg_duration,
                        SUM(tokens_used) as total_tokens
                    FROM agent_executions
                    GROUP BY agent_name
                ''')
            return [dict(row) for row in cursor.fetchall()]
    
    # Memory methods
    def save_memory_entry(self, project_id: str, agent_name: str,
                          entry_type: str, content: str, 
                          context: str = None, keywords: List[str] = None):
        """Save a memory entry"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO memory_entries
                (project_id, agent_name, entry_type, content, context, keywords, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, agent_name, entry_type, content, context,
                  json.dumps(keywords or []), datetime.now().isoformat()))
    
    def search_memory(self, project_id: str = None, query: str = None,
                      agent_name: str = None, limit: int = 10) -> List[Dict]:
        """Search memory entries (simple keyword search)"""
        with self.get_cursor() as cursor:
            sql = 'SELECT * FROM memory_entries WHERE 1=1'
            params = []
            
            if project_id:
                sql += ' AND project_id = ?'
                params.append(project_id)
            if agent_name:
                sql += ' AND agent_name = ?'
                params.append(agent_name)
            if query:
                sql += ' AND (content LIKE ? OR keywords LIKE ?)'
                params.extend([f'%{query}%', f'%{query}%'])
            
            sql += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Settings methods
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        with self.get_cursor() as cursor:
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except:
                    return row['value']
        return default
    
    def set_setting(self, key: str, value: Any):
        """Set a setting value"""
        with self.get_cursor() as cursor:
            cursor.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, json.dumps(value))
            )
    
    # Analytics methods
    def log_event(self, event_type: str, event_data: Dict = None):
        """Log an analytics event"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO analytics (event_type, event_data, created_at)
                VALUES (?, ?, ?)
            ''', (event_type, json.dumps(event_data or {}), datetime.now().isoformat()))
    
    def get_analytics(self, event_type: str = None, 
                      since: str = None, limit: int = 100) -> List[Dict]:
        """Get analytics events"""
        with self.get_cursor() as cursor:
            sql = 'SELECT * FROM analytics WHERE 1=1'
            params = []
            
            if event_type:
                sql += ' AND event_type = ?'
                params.append(event_type)
            if since:
                sql += ' AND created_at >= ?'
                params.append(since)
            
            sql += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


# Global database instance
db = Database()
