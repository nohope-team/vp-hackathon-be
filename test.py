import asyncio
import json

from app.services.database_service import database_service
from app.services.langfuse_service import langfuse_service
from app.services.n8n_service import N8nService, n8n_service


async def main():
    unprocessed = await database_service.get_unprocessed_executions()

    for execution in unprocessed:
        try:
            # Create Langfuse trace
            trace_id = langfuse_service.create_trace_from_execution(json.loads(execution["execution_data"]))

            if trace_id:
                # Mark as processed
                await database_service.mark_execution_processed(execution["id"], trace_id)
                # app_logger.info(f"Processed execution {execution['id']} to Langfuse trace {trace_id}")

        except Exception as e:
            # app_logger.error(f"Error processing execution {execution['id']}: {e}")
            print(e)

asyncio.run(main())