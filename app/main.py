from fastapi import FastAPI
from app.logging_config import setup_logging
from app.api.routes_tasks import router as tasks_router
from app.api.routes_health import router as health_router
from app.api.routes_metrics import router as metrics_router

setup_logging()

app = FastAPI(title="distributed-task-orchestrator")

app.include_router(tasks_router)
app.include_router(health_router)
app.include_router(metrics_router)