import os
from langfuse import Langfuse
from typing import Dict, Any
from datetime import datetime

from app.configs.settings import settings
from app.utils.logger import app_logger

class LangfuseService:
    def __init__(self):
        self.langfuse = Langfuse(
            secret_key='sk-lf-40484669-8a8e-4fdf-8f70-296c2deef06a',
            public_key='pk-lf-e2285dc1-130f-46a0-a4ec-309e7cf3be98',
            host=settings.langfuse_host
        )
    
    def create_trace_from_execution(self, execution_data: Dict[str, Any]) -> str:
        """Convert n8n execution to Langfuse trace"""
        try:
            trace = self.langfuse.trace(
                name=f"n8n-execution-{execution_data['id']}",
                input=execution_data.get("data", {}).get("startData", {}),
                output=execution_data.get("data", {}).get("resultData", {}),
                metadata={
                    "workflow_id": execution_data.get("workflowId"),
                    "status": execution_data.get("status"),
                    "mode": execution_data.get("mode"),
                    "n8n_execution_id": execution_data["id"]
                },
                start_time=self._parse_datetime(execution_data.get("startedAt")),
                end_time=self._parse_datetime(execution_data.get("stoppedAt")),
                tags=["n8n", "workflow", execution_data.get("status", "unknown")]
            )
            
            # Add spans for each node execution
            if execution_data.get("data", {}).get("resultData", {}).get("runData"):
                self._add_node_spans(trace, execution_data["data"]["resultData"]["runData"])
            print(trace.id)
            # Flush to ensure trace is sent immediately
            self.langfuse.flush()
            
            return trace.id
        except Exception as e:
            app_logger.error(f"Failed to create Langfuse trace: {e}")
            return None
    
    def _add_node_spans(self, trace, run_data: Dict[str, Any]):
        """Add spans for each node execution"""
        for node_name, node_runs in run_data.items():
            for i, run in enumerate(node_runs):
                trace.span(
                    name=f"{node_name}-{i}",
                    input=run.get("data", {}).get("main", [{}])[0] if run.get("data", {}).get("main") else {},
                    output=run.get("data", {}).get("main", [{}])[-1] if run.get("data", {}).get("main") else {},
                    start_time=self._parse_datetime(run.get("startTime")),
                    end_time=self._parse_datetime(run.get("executionTime")),
                    metadata={
                        "node_type": run.get("node", {}).get("type"),
                        "execution_status": run.get("executionStatus")
                    }
                )
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string to datetime object"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

langfuse_service = LangfuseService()