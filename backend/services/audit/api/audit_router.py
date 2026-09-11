from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Query, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
import csv
import io
import json

from backend.common.security import RoleChecker, get_current_user
from backend.common.schemas.response import APIResponse
from backend.database.connection import get_db_connection

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])

def fetch_audit_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
        
    logs = []
    try:
        with conn.cursor() as cur:
            query = "SELECT log_id, employee_id, action, details, ip_address, created_at FROM audit_logs WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date)
            if end_date:
                query += " AND created_at <= %s"
                params.append(end_date)
                
            if search:
                # Search across action, employee_id, or stringified details
                query += " AND (action ILIKE %s OR employee_id ILIKE %s OR details::text ILIKE %s)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])
                
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
            for row in rows:
                logs.append({
                    "log_id": str(row[0]),
                    "employee_id": row[1],
                    "action": row[2],
                    "details": row[3], # Dict from JSONB
                    "ip_address": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                })
    finally:
        conn.close()
        
    return logs


@router.get("/logs", dependencies=[Depends(RoleChecker(["admin"]))])
def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    search: Optional[str] = Query(None, description="Search term for actions, employee, or details"),
    user: dict = Depends(get_current_user)
):
    """Retrieves immutable audit logs based on filters."""
    logs = fetch_audit_logs(start_date, end_date, search)
    return APIResponse.ok(data=logs, message="Audit logs retrieved successfully")


@router.get("/logs/export", dependencies=[Depends(RoleChecker(["admin"]))])
def export_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    search: Optional[str] = Query(None, description="Search term"),
    user: dict = Depends(get_current_user)
):
    """Exports audit logs as a CSV file."""
    logs = fetch_audit_logs(start_date, end_date, search)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Timestamp", "Log ID", "Employee ID", "Action", "IP Address", "Details"])
    
    # Write data
    for log in logs:
        writer.writerow([
            log["created_at"],
            log["log_id"],
            log["employee_id"],
            log["action"],
            log["ip_address"] or "N/A",
            json.dumps(log["details"])
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )
