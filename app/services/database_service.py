import json

import asyncpg
from typing import List, Optional, Dict, Any

from dateutil.parser import isoparse

from app.models.facebook_workflow import FacebookWorkflowData, FacebookWorkflowUpdate
from app.configs.settings import settings

class DatabaseService:
    def __init__(self):
        self.connection_string = settings.database_url
    
    async def get_connection(self):
        return await asyncpg.connect(self.connection_string)
    
    async def get_facebook_workflows(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM facebook_workflow_data ORDER BY id DESC LIMIT $1 OFFSET $2",
                limit, offset
            )
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def get_facebook_workflows_count(self) -> int:
        """Get total count of Facebook workflow records"""
        conn = await self.get_connection()
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM facebook_workflow_data")
            return count
        finally:
            await conn.close()
    
    async def get_facebook_workflow_by_id(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM facebook_workflow_data WHERE id = $1",
                workflow_id
            )
            return dict(row) if row else None
        finally:
            await conn.close()
    
    async def create_facebook_workflow(self, workflow_data: FacebookWorkflowData) -> Dict[str, Any]:
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO facebook_workflow_data 
                (user_question, chatbot_intent, vpbank_source, confidence_score, answer, state, sender_id, recipient_id, page_name)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
                """,
                workflow_data.user_question,
                workflow_data.chatbot_intent,
                workflow_data.vpbank_source,
                workflow_data.confidence_score,
                workflow_data.answer,
                workflow_data.state,
                workflow_data.sender_id,
                workflow_data.recipient_id,
                workflow_data.page_name
            )
            return dict(row)
        finally:
            await conn.close()
    
    async def update_facebook_workflow(self, workflow_id: int, update_data: FacebookWorkflowUpdate) -> Optional[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            param_count = 1
            
            for field, value in update_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not update_fields:
                return await self.get_facebook_workflow_by_id(workflow_id)
            
            query = f"""
                UPDATE facebook_workflow_data 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING *
            """
            values.append(workflow_id)
            
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
        finally:
            await conn.close()
    
    # n8n execution methods
    async def save_n8n_execution(self, execution_data: dict) -> None:
        conn = await self.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO n8n_executions (id, workflow_id, status, started_at, finished_at, execution_data)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                int(execution_data["id"]),
                execution_data.get("workflowId"),
                execution_data.get("status"),
                isoparse(execution_data.get("startedAt")).astimezone(tz=None).replace(tzinfo=None),
                isoparse(execution_data.get("stoppedAt")).astimezone(tz=None).replace(tzinfo=None),
                json.dumps(execution_data)
            )
        finally:
            await conn.close()
    
    async def get_unprocessed_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM n8n_executions WHERE processed = false ORDER BY id LIMIT $1",
                limit
            )
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def mark_execution_processed(self, execution_id: int, trace_id: str) -> None:
        conn = await self.get_connection()
        try:
            await conn.execute(
                "UPDATE n8n_executions SET processed = true, langfuse_trace_id = $1 WHERE id = $2",
                trace_id, execution_id
            )
        finally:
            await conn.close()
    
    async def get_max_execution_id(self) -> int:
        conn = await self.get_connection()
        try:
            result = await conn.fetchval("SELECT COALESCE(MAX(id), 0) FROM n8n_executions")
            return result or 0
        finally:
            await conn.close()
    
    async def get_max_execution_id_for_workflow(self, workflow_id: str) -> int:
        conn = await self.get_connection()
        try:
            result = await conn.fetchval(
                "SELECT COALESCE(MAX(id), 0) FROM n8n_executions WHERE workflow_id = $1",
                workflow_id
            )
            return result or 0
        finally:
            await conn.close()
    
    # n8n flow methods
    async def add_n8n_flow(self, flow_data: dict) -> Dict[str, Any]:
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO n8n_flows (flow_id, flow_name, description, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (flow_id) DO UPDATE SET
                    flow_name = EXCLUDED.flow_name,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active,
                    created_at = EXCLUDED.created_at
                RETURNING *
                """,
                flow_data["flow_id"],
                flow_data.get("flow_name"),
                flow_data.get("description"),
                flow_data.get("is_active", True),
                flow_data.get("created_at")
            )
            return dict(row)
        finally:
            await conn.close()
    
    async def get_active_flows(self) -> List[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM n8n_flows WHERE is_active = true ORDER BY id"
            )
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def get_latest_workflow_created_at(self):
        """Get the latest n8n_created_at timestamp from workflows"""
        conn = await self.get_connection()
        try:
            result = await conn.fetchval(
                "SELECT MAX(created_at) FROM n8n_flows"
            )
            # If no records exist, return None to ensure all workflows are added
            return result
        except Exception:
            # Handle any errors by returning None
            return None
        finally:
            await conn.close()

database_service = DatabaseService()