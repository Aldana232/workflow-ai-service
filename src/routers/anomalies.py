from fastapi import APIRouter, HTTPException, Request
from src.services.ml_service import MLService

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])
ml = MLService()


@router.get("/detect/{company_id}")
async def detect_anomalies(company_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_active_tramites()
        anomalies = ml.detect_anomalies(tramites)
        return {"companyId": company_id, "anomalies": anomalies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tramite/{tramite_id}")
async def analyze_tramite(tramite_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        history = await mongodb.get_tramite_history(tramite_id)
        anomalies = ml.detect_anomalies(history)
        is_anomalous = (
            isinstance(anomalies, list)
            and len(anomalies) > 0
            and anomalies[0].get("status") != "insufficient_data"
        )
        return {
            "tramiteId": tramite_id,
            "isAnomalous": is_anomalous,
            "details": anomalies,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
