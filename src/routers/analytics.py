from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query, Request
from src.services.ml_service import MLService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
ml = MLService()


@router.get("/bottlenecks/{process_id}")
async def get_bottlenecks(process_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        submissions = await mongodb.get_task_submissions(process_id)
        result = ml.detect_bottlenecks(submissions)
        return {"processId": process_id, "bottlenecks": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/{company_id}")
async def get_active_tramites(company_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_active_tramites(company_id)
        prioritized = ml.prioritize_tramites(tramites)
        return {"companyId": company_id, "tramites": prioritized}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/completion-time/{tramite_id}")
async def get_completion_time(tramite_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        history = await mongodb.get_tramite_history(tramite_id)
        tramite_data = {"tramiteId": tramite_id, "history": history}
        result = ml.predict_completion_time(tramite_data)
        return {"tramiteId": tramite_id, "prediction": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-date")
async def get_tramites_by_date(
    request: Request,
    from_date: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    to_date: str = Query(..., description="Fecha fin YYYY-MM-DD"),
):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_tramites_by_date(from_date, to_date)
        result = []
        for t in tramites:
            created = t.get("createdAt")
            result.append({
                "code": t.get("code", ""),
                "status": t.get("status", ""),
                "processId": t.get("processId", ""),
                "createdAt": created.isoformat() if created else None,
                "nombre": t.get("clienteInfo", {}).get("nombre", ""),
            })
        completed = sum(1 for t in tramites if t.get("status") == "COMPLETED")
        active = sum(1 for t in tramites if t.get("status") == "ACTIVE")
        return {
            "from_date": from_date,
            "to_date": to_date,
            "total": len(tramites),
            "completed": completed,
            "active": active,
            "tramites": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Formato de fecha invalido: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-client")
async def get_tramites_by_client(
    request: Request,
    name: str = Query(..., description="Nombre o fragmento del cliente"),
):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_tramites_by_client(name)
        result = []
        for t in tramites:
            created = t.get("createdAt")
            result.append({
                "code": t.get("code", ""),
                "status": t.get("status", ""),
                "processId": t.get("processId", ""),
                "createdAt": created.isoformat() if created else None,
                "clienteInfo": t.get("clienteInfo", {}),
            })
        return {
            "name": name,
            "total": len(tramites),
            "tramites": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary-by-process")
async def get_summary_by_process(request: Request):
    try:
        mongodb = request.app.state.mongodb
        tramites, submissions = await mongodb.get_all_tramites_with_submissions()

        # Index submissions by processId for fast lookup
        subs_by_process = defaultdict(list)
        for s in submissions:
            pid = s.get("processId", "")
            if pid:
                subs_by_process[pid].append(s.get("durationMinutes") or 0)

        stats_by_process = defaultdict(lambda: {"total": 0, "completed": 0, "active": 0})
        for t in tramites:
            pid = t.get("processId", "unknown")
            stats_by_process[pid]["total"] += 1
            if t.get("status") == "COMPLETED":
                stats_by_process[pid]["completed"] += 1
            elif t.get("status") == "ACTIVE":
                stats_by_process[pid]["active"] += 1

        summary = []
        for pid, counts in stats_by_process.items():
            durations = subs_by_process.get(pid, [])
            avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
            summary.append({
                "processId": pid,
                "total": counts["total"],
                "completed": counts["completed"],
                "active": counts["active"],
                "avgDurationMinutes": avg_duration,
            })

        summary.sort(key=lambda x: x["total"], reverse=True)
        return {"processes": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
