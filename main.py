from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.routers import analytics, predictions, anomalies, recommendations
from src.services.mongodb_service import MongoDBService

mongodb_service = MongoDBService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongodb_service.connect()
    app.state.mongodb = mongodb_service
    yield
    await mongodb_service.close()


app = FastAPI(title="Workflow AI Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)
app.include_router(predictions.router)
app.include_router(anomalies.router)
app.include_router(recommendations.router)


@app.get("/")
async def root():
    return {"status": "running", "service": "Workflow AI Service"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
