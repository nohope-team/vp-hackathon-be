import asyncio
import json

from app.services.database_service import database_service
from app.services.langfuse_service import langfuse_service
from app.services.n8n_service import N8nService, n8n_service
from app.services.scheduler_service import scheduler_service


async def main():
    await scheduler_service.collect_n8n_executions()

asyncio.run(main())