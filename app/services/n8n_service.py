import httpx
import os
from typing import List, Dict, Any, Optional

from app.configs.settings import settings
from app.utils.logger import app_logger

class N8nService:
    def __init__(self):
        self.base_url = settings.n8n_base_url
        self.api_key = settings.n8n_api_key
        self.workflow_id = settings.n8n_workflow_id
        print(f"n8n_base_url: {self.base_url}, n8n_api_key: {self.api_key}, n8n_workflow_id: {self.workflow_id}")
        if not all([self.base_url, self.api_key, self.workflow_id]):
            app_logger.warning("n8n configuration missing - service disabled")
            self.enabled = False
        else:
            self.enabled = True
            self.headers = {"X-N8N-API-KEY": self.api_key}
    
    async def get_executions(self, workflow_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get list of executions from n8n"""
        if not self.enabled:
            return []
        
        workflow_id = workflow_id or self.workflow_id
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/executions",
                headers=self.headers,
                params={"workflowId": workflow_id, "limit": limit}
            )
            response.raise_for_status()
            return response.json().get("data", [])
    
    async def get_execution_detail(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed execution data from n8n"""
        if not self.enabled:
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/executions/{execution_id}",
                    headers=self.headers,
                    params={"includeData": "true"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            app_logger.error(f"Failed to get execution {execution_id}: {e}")
            return None
    
    async def get_active_workflows(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of active workflows from n8n"""
        if not self.enabled:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/workflows",
                    headers=self.headers,
                    params={
                        "active": "true",
                        "excludePinnedData": "false",
                        "limit": limit
                    }
                )
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            app_logger.error(f"Failed to get active workflows: {e}")
            return []

n8n_service = N8nService()