from fastapi import APIRouter
from app.api.v1 import ingest, alerts, cases, users, risk, reports, audit

api_router = APIRouter()
api_router.include_router(ingest.router)
api_router.include_router(alerts.router)
api_router.include_router(cases.router)
api_router.include_router(users.router)
api_router.include_router(risk.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
