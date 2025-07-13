import httpx
import os
from typing import List, Dict, Any, Optional
from app.utils.logger import app_logger

class N8nService:
    def __init__(self):
        self.base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.api_key = os.getenv("N8N_API_KEY",'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTc5MzA5ZC0xNTA1LTQ4NjctYjYyNC0yNGU2MWVmNDNkNzIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUyMzMzODkwfQ.KkEtxUkZXt5WdF3TSrbThtHpnjC5AEItLPJbMcAD0b0')
        self.workflow_id = os.getenv("N8N_WORKFLOW_ID",'Lacf09MYPwmGRVY0')
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

n8n_service = N8nService()