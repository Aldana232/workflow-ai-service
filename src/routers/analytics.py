from fastapi import APIRouter, HTTPException, Request
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
