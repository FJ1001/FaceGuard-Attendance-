"""Optional FastAPI + WebSocket layer for passive attendance dashboards."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from services.passive_attendance_service import PassiveAttendanceService

app = FastAPI(title="EyeAmHere Passive Attendance API", version="1.0.0")
service = PassiveAttendanceService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "passive-attendance", "time": datetime.now().isoformat()}


@app.get("/passive/sessions")
def list_sessions() -> List[Dict[str, Any]]:
    return service.list_sessions(limit=100)


@app.get("/passive/sessions/active")
def active_session() -> Dict[str, Any]:
    session = service.get_active_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    return session


@app.get("/passive/sessions/{session_id}/dashboard")
def session_dashboard(session_id: int) -> Dict[str, Any]:
    return service.get_live_dashboard(session_id=session_id)


@app.post("/passive/sessions/start")
def start_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    ok, message, session_id = service.create_session(
        class_name=str(payload.get("class_name", "Active Class")),
        course=str(payload.get("course", "")),
        camera_source=str(payload.get("camera_source", "webcam")),
        created_by=str(payload.get("created_by", "api")),
        start_time=str(payload.get("start_time", datetime.now().isoformat(timespec="seconds"))),
        student_ids=[int(v) for v in payload.get("student_ids", [])],
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": ok, "message": message, "session_id": session_id}


@app.post("/passive/sessions/stop")
def stop_session() -> Dict[str, Any]:
    ok, message = service.stop_active_session()
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": ok, "message": message}


@app.websocket("/ws/passive/{session_id}")
async def passive_ws(websocket: WebSocket, session_id: int) -> None:
    await websocket.accept()
    try:
        while True:
            payload = service.get_live_dashboard(session_id=session_id)
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
