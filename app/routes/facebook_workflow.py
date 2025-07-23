from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.models.facebook_workflow import FacebookWorkflowData, FacebookWorkflowUpdate
from app.services.database_service import database_service
from app.services.webhook_service import webhook_service
from math import ceil

router = APIRouter(prefix="/api/v1/facebook-workflow", tags=["Facebook Workflow"])

@router.get("/")
async def get_facebook_workflows(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """Get Facebook workflow data records with pagination"""
    # Calculate offset from page and page_size
    offset = (page - 1) * page_size
    
    # Get total count
    total_count = await database_service.get_facebook_workflows_count()
    
    # Get data for current page
    data = await database_service.get_facebook_workflows(limit=page_size, offset=offset)
    
    # Calculate pagination metadata
    total_pages = ceil(total_count / page_size) if total_count > 0 else 1
    
    # Return data with metadata
    return {
        "data": data,
        "metadata": {
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size
        }
    }

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