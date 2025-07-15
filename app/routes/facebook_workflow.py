from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.models.facebook_workflow import FacebookWorkflowData, FacebookWorkflowUpdate
from app.services.database_service import database_service
from app.services.webhook_service import webhook_service

router = APIRouter(prefix="/api/v1/facebook-workflow", tags=["Facebook Workflow"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_facebook_workflows(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get Facebook workflow data records"""
    return await database_service.get_facebook_workflows(limit, offset)

@router.get("/{workflow_id}", response_model=Dict[str, Any])
async def get_facebook_workflow(workflow_id: int):
    """Get specific Facebook workflow record by ID"""
    workflow = await database_service.get_facebook_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.post("/", response_model=Dict[str, Any], status_code=201)
async def create_facebook_workflow(workflow_data: FacebookWorkflowData):
    """Create new Facebook workflow record"""
    return await database_service.create_facebook_workflow(workflow_data)

@router.put("/{workflow_id}", response_model=Dict[str, Any])
async def update_facebook_workflow(workflow_id: int, update_data: FacebookWorkflowUpdate):
    """Update Facebook workflow record"""
    workflow = await database_service.update_facebook_workflow(workflow_id, update_data)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Send webhook if answer, sender_id, and recipient_id are present
    if (workflow.get("answer") and 
        workflow.get("sender_id") and 
        workflow.get("recipient_id")):
        await webhook_service.send_facebook_webhook(
            answer=workflow["answer"],
            sender_id=workflow["sender_id"],
            recipient_id=workflow["recipient_id"]
        )
    
    return workflow