from fastapi import APIRouter
from typing import Dict, Any
from app.models.n8n_flow import N8nFlow
from app.services.database_service import database_service

router = APIRouter(prefix="/api/v1/n8n-flow", tags=["n8n Flow"])

@router.post("/", response_model=Dict[str, Any], status_code=201)
async def add_n8n_flow(flow_data: N8nFlow):
    """Add n8n flow ID to database"""
    return await database_service.add_n8n_flow(flow_data.model_dump())