import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBService:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB", "workflow_platform")
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def close(self):
        if self.client:
            self.client.close()

    async def get_tramites(self, company_id: str = None) -> list:
        cursor = self.db.tramites.find({}).limit(100)
        return await cursor.to_list(length=None)

    async def get_task_submissions(self, process_id: str) -> list:
        cursor = self.db.task_submissions.find({"processId": process_id})
        return await cursor.to_list(length=None)

    async def get_active_tramites(self, company_id: str = None) -> list:
        cursor = self.db.tramites.find({"status": "ACTIVE"})
        return await cursor.to_list(length=None)

    async def get_tramite_history(self, tramite_id: str) -> list:
        cursor = self.db.task_submissions.find({"tramiteId": tramite_id})
        return await cursor.to_list(length=None)

    async def get_process_nodes(self, process_id: str) -> list:
        try:
            process = await self.db.processes.find_one({"_id": ObjectId(process_id)})
        except Exception:
            process = await self.db.processes.find_one({"_id": process_id})
        if process and "nodes" in process:
            return process["nodes"]
        return []

    async def get_tramites_by_process(self, process_id: str) -> list:
        cursor = self.db.tramites.find({"processId": process_id, "status": "ACTIVE"})
        return await cursor.to_list(length=None)

    async def get_processes_by_company(self, company_id: str) -> list:
        cursor = self.db.processes.find({
            "companyId": company_id,
            "status": {"$in": ["ACTIVE", "PUBLISHED"]},
        })
        return await cursor.to_list(length=None)
