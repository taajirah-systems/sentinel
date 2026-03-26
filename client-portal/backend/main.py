from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sqlite3
import os
import json
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Sovereign Client Portal API")

# Security: Allow specific origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/Users/taajirah_systems/sentinel/data/sentinel.db"
REPORTS_DIR = "/Users/taajirah_systems/sentinel/data/reports"

class AuditLog(BaseModel):
    id: int
    timestamp: float
    command: str
    allowed: bool
    risk_score: Optional[int]
    reason: Optional[str]
    details: Optional[dict]

class SystemStats(BaseModel):
    total_actions: int
    high_risk_actions: int
    system_status: str

@app.get("/stats", response_model=SystemStats)
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE risk_score >= 8")
    high_risk = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_actions": total,
        "high_risk_actions": high_risk,
        "system_status": "Operational"
    }

@app.get("/logs", response_model=List[AuditLog])
def get_logs(limit: int = 50, offset: int = 0):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    
    logs = []
    for row in rows:
        log = dict(row)
        if log['details']:
            try:
                log['details'] = json.loads(log['details'])
            except:
                log['details'] = {}
        logs.append(log)
        
    conn.close()
    return logs

@app.get("/reports")
def list_reports():
    if not os.path.exists(REPORTS_DIR):
        return []
    
    reports = []
    for f in os.listdir(REPORTS_DIR):
        if f.endswith(".md"):
            stats = os.stat(os.path.join(REPORTS_DIR, f))
            reports.append({
                "filename": f,
                "created_at": datetime.datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "size": stats.st_size
            })
    return sorted(reports, key=lambda x: x['created_at'], reverse=True)

import datetime # Need this for list_reports

@app.get("/reports/{filename}")
def download_report(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(file_path, media_type="text/markdown", filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
