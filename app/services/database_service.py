import asyncpg
import os
from typing import List, Optional, Dict, Any
from app.models.facebook_workflow import FacebookWorkflowData, FacebookWorkflowUpdate

class DatabaseService:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL", "postgresql://vpbank:vpbanksummer2025@103.69.97.133:5432/vpbank_hackathon")
    
    async def get_connection(self):
        return await asyncpg.connect(self.connection_string)
    
    async def get_facebook_workflows(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = await self.get_connection()
        try:
            rows = await conn.fetch(
                "SELECT * FROM facebook_workflow_data ORDER BY id LIMIT $1 OFFSET $2",
                limit, offset
            )
            return [dict(row) for row in rows]
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

database_service = DatabaseService()