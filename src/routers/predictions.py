from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.services.ml_service import MLService

router = APIRouter(prefix="/api/predictions", tags=["predictions"])
ml = MLService()


class PolicyRequest(BaseModel):
    description: str
    company_id: str


@router.post("/policy")
async def recommend_policy(body: PolicyRequest, request: Request):
    try:
        mongodb = request.app.state.mongodb

        # Obtener procesos directamente de la colección con nombre real
        processes = await mongodb.get_processes_by_company(body.company_id)

        available_processes = []
        for p in processes:
            pid  = str(p.get("_id", ""))
            name = p.get("name") or pid

            # Construir descripción desde los nodos del proceso
            nodes = p.get("nodes") or p.get("elements") or []
            labels = []
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                label = (
                    n.get("label")
                    or n.get("name")
                    or (n.get("data") or {}).get("label", "")
                )
                if label and str(label).strip():
                    labels.append(str(label).strip())

            description = " ".join(labels) if labels else name
            available_processes.append({"id": pid, "name": name, "description": description})

        result = ml.recommend_policy(body.description, available_processes)

        # Aplanar el campo recommendedProcess para que el cliente lea el ID directamente
        if isinstance(result.get("recommendedProcess"), dict):
            rec = result["recommendedProcess"]
            result["recommendedProcess"] = rec.get("id", "")
            result["processName"]        = rec.get("name", "")
        result["confidence"] = result.pop("confidenceScore", result.get("confidence", 0))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/priority/{company_id}")
async def get_priority_tramites(company_id: str, request: Request):
    try:
        mongodb = request.app.state.mongodb
        tramites = await mongodb.get_active_tramites()
        prioritized = ml.prioritize_tramites(tramites)
        return {"companyId": company_id, "tramites": prioritized}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
