
import sqlite3
import json
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .approvals import PendingRequest

class SentinelDB:
    def __init__(self, db_path: str = None):
        # REDIRECTION: Added support for isolated pilot runs via environment variable
        env_db = os.getenv("SENTINEL_DB_PATH")
        self.db_path = Path(env_db) if env_db else Path(db_path or "data/sentinel.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            # Approvals Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    wallet_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    project_id TEXT DEFAULT 'default',
                    command TEXT NOT NULL,
                    estimated_cost_jul REAL DEFAULT 0.0,
                    risk_score INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    rule_name TEXT,
                    reason TEXT,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    resolved_at REAL,
                    actor_id TEXT,
                    resolution_reason TEXT,
                    hold_id TEXT
                )
            """)
            
            # Add hold_id column if it doesn't exist (Migrate existing DB)
            try:
                conn.execute("ALTER TABLE approvals ADD COLUMN hold_id TEXT")
            except sqlite3.OperationalError:
                pass # Already exists
            
            # Audit Logs Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    command TEXT NOT NULL,
                    allowed BOOLEAN NOT NULL,
                    risk_score INTEGER,
                    reason TEXT,
                    details JSON
                )
            """)
            conn.commit()

            # Holds Table (State Machine Cache)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holds (
                    id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    wallet_id TEXT NOT NULL,
                    project_id TEXT,
                    org_id TEXT,
                    amount_jul REAL NOT NULL,
                    status TEXT NOT NULL,
                    status_reason TEXT,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    resolved_at REAL,
                    actual_amount_jul REAL,
                    surplus_released_jul REAL,
                    FOREIGN KEY(request_id) REFERENCES approvals(id)
                )
            """)
            
            # Migration check for new columns
            new_columns = [
                ("project_id", "TEXT"),
                ("org_id", "TEXT"),
                ("status_reason", "TEXT"),
                ("expires_at", "REAL"),
                ("resolved_at", "REAL"),
                ("actual_amount_jul", "REAL"),
                ("surplus_released_jul", "REAL")
            ]
            for col_name, col_type in new_columns:
                try:
                    conn.execute(f"ALTER TABLE holds ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass # Already exists
            
            conn.commit()

    def insert_hold(self, hold_id: str, request_id: str, wallet_id: str, amount_jul: float, 
                    project_id: str = None, org_id: str = None, expires_at: float = None):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO holds (id, request_id, wallet_id, project_id, org_id, amount_jul, status, created_at, expires_at) 
                   VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                (hold_id, request_id, wallet_id, project_id, org_id, amount_jul, time.time(), expires_at)
            )
            conn.commit()

    def update_hold_status(self, hold_id: str, status: str, resolved_at: float = None, 
                           actual_amount_jul: float = None, surplus_released_jul: float = None,
                           status_reason: str = None):
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE holds SET status = ?, resolved_at = ?, actual_amount_jul = ?, 
                   surplus_released_jul = ?, status_reason = ? WHERE id = ?""",
                (status, resolved_at, actual_amount_jul, surplus_released_jul, status_reason, hold_id)
            )
            conn.commit()

    def get_holds_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, request_id, wallet_id, amount_jul, status, created_at, 
                          project_id, org_id, expires_at, resolved_at, actual_amount_jul, 
                          surplus_released_jul, status_reason 
                   FROM holds WHERE status = ? ORDER BY created_at DESC LIMIT ?""",
                (status, limit)
            )
            holds = []
            for row in cursor.fetchall():
                holds.append({
                    "id": row[0],
                    "request_id": row[1],
                    "wallet_id": row[2],
                    "amount_jul": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "project_id": row[6],
                    "org_id": row[7],
                    "expires_at": row[8],
                    "resolved_at": row[9],
                    "actual_amount_jul": row[10],
                    "surplus_released_jul": row[11],
                    "status_reason": row[12]
                })
            return holds

    def get_hold(self, hold_id: str) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, request_id, wallet_id, amount_jul, status, created_at,
                          project_id, org_id, expires_at, resolved_at, actual_amount_jul, 
                          surplus_released_jul, status_reason
                   FROM holds WHERE id = ?""",
                (hold_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "request_id": row[1],
                    "wallet_id": row[2],
                    "amount_jul": row[3],
                    "status": row[4],
                    "created_at": row[5],
                    "project_id": row[6],
                    "org_id": row[7],
                    "expires_at": row[8],
                    "resolved_at": row[9],
                    "actual_amount_jul": row[10],
                    "surplus_released_jul": row[11],
                    "status_reason": row[12]
                }
            return None

    def get_all_holds(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, request_id, wallet_id, amount_jul, status, created_at FROM holds ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            holds = []
            for row in cursor.fetchall():
                holds.append({
                    "id": row[0],
                    "request_id": row[1],
                    "wallet_id": row[2],
                    "amount_jul": row[3],
                    "status": row[4],
                    "created_at": row[5]
                })
            return holds

    def insert_approval(self, request: PendingRequest):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO approvals (
                    id, wallet_id, agent_id, project_id, command, estimated_cost_jul, 
                    risk_score, status, rule_name, reason, expires_at, created_at, hold_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.id, request.wallet_id, request.agent_id, request.project_id, 
                    request.command, request.estimated_cost_jul, request.risk_score, 
                    request.status, request.rule_name, request.reason, 
                    request.expires_at, request.created_at, request.hold_id
                )
            )
            conn.commit()

    def _row_to_request(self, row) -> PendingRequest:
        return PendingRequest(
            id=row[0],
            wallet_id=row[1],
            agent_id=row[2],
            project_id=row[3],
            command=row[4],
            estimated_cost_jul=row[5],
            risk_score=row[6],
            status=row[7],
            rule_name=row[8],
            reason=row[9],
            expires_at=row[10],
            created_at=row[11],
            resolved_at=row[12],
            actor_id=row[13],
            resolution_reason=row[14],
            hold_id=row[15]
        )

    def get_pending_approvals(self) -> Dict[str, PendingRequest]:
        query = """
            SELECT id, wallet_id, agent_id, project_id, command, estimated_cost_jul, 
                   risk_score, status, rule_name, reason, expires_at, created_at,
                   resolved_at, actor_id, resolution_reason, hold_id
            FROM approvals WHERE status = 'pending'
        """
        with self._get_conn() as conn:
            cursor = conn.execute(query)
            results = {}
            for row in cursor.fetchall():
                req = self._row_to_request(row)
                results[req.id] = req
            return results

    def get_all_approvals(self, limit: int = 100) -> List[PendingRequest]:
        """Fetch full history of approval requests, including processed and expired."""
        query = """
            SELECT id, wallet_id, agent_id, project_id, command, estimated_cost_jul, 
                   risk_score, status, rule_name, reason, expires_at, created_at,
                   resolved_at, actor_id, resolution_reason, hold_id
            FROM approvals ORDER BY created_at DESC LIMIT ?
        """
        with self._get_conn() as conn:
            cursor = conn.execute(query, (limit,))
            return [self._row_to_request(row) for row in cursor.fetchall()]

    def get_approval(self, request_id: str) -> Optional[PendingRequest]:
        query = """
            SELECT id, wallet_id, agent_id, project_id, command, estimated_cost_jul, 
                   risk_score, status, rule_name, reason, expires_at, created_at,
                   resolved_at, actor_id, resolution_reason, hold_id
            FROM approvals WHERE id = ?
        """
        with self._get_conn() as conn:
            cursor = conn.execute(query, (request_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_request(row)
            return None

    def update_approval_status(self, request_id: str, status: str, actor_id: str, resolution_reason: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE approvals SET status = ?, resolved_at = ?, actor_id = ?, resolution_reason = ? WHERE id = ?",
                (status, time.time(), actor_id, resolution_reason, request_id)
            )
            conn.commit()

    def get_expired_ids(self, current_time: float) -> List[str]:
        """Fetch IDs of requests ready for automatic expiration."""
        query = "SELECT id FROM approvals WHERE status = 'pending' AND expires_at < ?"
        with self._get_conn() as conn:
            cursor = conn.execute(query, (current_time,))
            return [row[0] for row in cursor.fetchall()]

    def purge_expired_requests(self, current_time: float):
        """Finalise expired requests as 'expired' rather than leaving them in limbo."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE approvals SET status = 'expired', resolved_at = ? WHERE status = 'pending' AND expires_at < ?",
                (current_time, current_time)
            )
            conn.commit()

    def log_audit(self, command: str, result: Dict[str, Any]):
        allowed = result.get("allowed", False)
        risk_score = result.get("risk_score", 0)
        reason = result.get("reason", "")
        details = json.dumps(result)
        
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, command, allowed, risk_score, reason, details) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), command, allowed, risk_score, reason, details)
            )
            conn.commit()

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, command, allowed, risk_score, reason, details FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "command": row[2],
                    "allowed": bool(row[3]),
                    "risk_score": row[4],
                    "reason": row[5],
                    "details": json.loads(row[6]) if row[6] else {}
                })
            return logs
