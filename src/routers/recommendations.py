from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.services.ml_service import MLService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
ml = MLService()


class ProcessRequest(BaseModel):
    description: str
    company_id: str


@router.post("/process")
async def recommend_process(body: ProcessRequest, request: Request):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_tramites(body.company_id)
        process_ids = list({t.get("processId") for t in tramites if t.get("processId")})
        available_processes = []
        for pid in process_ids:
            nodes = await mongodb.get_process_nodes(pid)
            available_processes.append({
                "id": pid,
                "name": pid,
                "description": " ".join([n.get("label", "") for n in nodes if n.get("label")]),
            })
        result = ml.recommend_policy(body.description, available_processes)
        return {"recommendation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/next-action/{tramite_id}")
async def get_next_action(tramite_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        history = await mongodb.get_tramite_history(tramite_id)

        if not history:
            return {
                "tramiteId": tramite_id,
                "status": "insufficient_data",
                "message": "Se necesitan más datos para el análisis",
            }

        completed_nodes = {h.get("nodeId") for h in history if h.get("status") == "COMPLETED"}
        pending = [h for h in history if h.get("status") != "COMPLETED"]

        if not pending:
            return {
                "tramiteId": tramite_id,
                "nextAction": "Trámite completado",
                "completedNodes": list(completed_nodes),
                "recommendation": "Todos los nodos han sido procesados exitosamente.",
            }

        next_node = pending[0]
        avg_durations = [float(h.get("durationMinutes", 0)) for h in history if h.get("durationMinutes")]
        avg = round(sum(avg_durations) / len(avg_durations), 2) if avg_durations else None

        return {
            "tramiteId": tramite_id,
            "nextAction": f"Procesar nodo: {next_node.get('nodeId', 'desconocido')}",
            "nextNodeId": next_node.get("nodeId"),
            "completedNodes": list(completed_nodes),
            "estimatedDurationMinutes": avg,
            "recommendation": "Continuar con el siguiente nodo pendiente para mantener el flujo del trámite.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
