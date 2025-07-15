import asyncio
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.services.n8n_service import n8n_service
from app.services.database_service import database_service
from app.services.langfuse_service import langfuse_service
from app.utils.logger import app_logger

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Start the scheduler with jobs"""
        # Job 1: Sync n8n workflows every 5 minutes
        self.scheduler.add_job(
            self.sync_workflows,
            trigger=IntervalTrigger(minutes=1),
            id="sync_workflows",
            name="Sync n8n Workflows"
        )
        
        # Job 2: Collect n8n executions every minute
        self.scheduler.add_job(
            self.collect_n8n_executions,
            trigger=IntervalTrigger(minutes=1),
            id="collect_n8n_executions",
            name="Collect n8n Executions"
        )
        
        # Job 3: Process executions to Langfuse every minute
        self.scheduler.add_job(
            self.process_executions_to_langfuse,
            trigger=IntervalTrigger(minutes=1),
            id="process_to_langfuse",
            name="Process Executions to Langfuse"
        )
        
        self.scheduler.start()
        app_logger.info("Scheduler started with n8n collection and Langfuse processing jobs")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        app_logger.info("Scheduler stopped")
    
    async def sync_workflows(self):
        """Sync active workflows from n8n to database"""
        try:
            app_logger.info("Starting workflow sync from n8n")
            
            # Get active workflows from n8n
            active_workflows = await n8n_service.get_active_workflows()
            
            # Get existing workflow IDs and creation times from database
            existing_flows = await database_service.get_active_flows()
            existing_flow_ids = {flow["flow_id"] for flow in existing_flows}
            
            # Get latest creation timestamp from database
            latest_created_at = await database_service.get_latest_workflow_created_at()
            
            # Track stats
            stats = {
                "total": len(active_workflows),
                "new": 0,
                "existing": 0,
                "error": 0
            }
            
            # Process each workflow
            for workflow in active_workflows:
                try:
                    flow_id = workflow.get("id")
                    if not flow_id:
                        continue
                    
                    # Parse n8n creation timestamp
                    n8n_created_at = self._parse_datetime(workflow.get("createdAt"))
                    
                    # Skip if workflow exists and creation time is not newer
                    # If latest_created_at is None (empty table), don't skip any workflows
                    if flow_id in existing_flow_ids and latest_created_at and (not n8n_created_at or n8n_created_at <= latest_created_at):
                        stats["existing"] += 1
                        continue
                    
                    # Add new workflow to database
                    flow_data = {
                        "flow_id": flow_id,
                        "flow_name": workflow.get("name", "Unnamed Workflow"),
                        "description": workflow.get("description", ""),
                        "is_active": True,
                        "created_at": n8n_created_at
                    }
                    
                    await database_service.add_n8n_flow(flow_data)
                    stats["new"] += 1
                    app_logger.info(f"Added new workflow: {flow_id} - {flow_data['flow_name']}")
                    
                except Exception as e:
                    stats["error"] += 1
                    app_logger.error(f"Error processing workflow {workflow.get('id')}: {e}")
            
            app_logger.info(f"Workflow sync completed: {stats}")
            return stats
            
        except Exception as e:
            app_logger.error(f"Failed to sync workflows: {e}")
            return {"error": str(e)}
    
    def _parse_datetime(self, dt_str):
        """Parse datetime string to datetime object without timezone info"""
        if not dt_str:
            return None
        try:
            from datetime import datetime
            # Parse with timezone, then remove timezone info
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        except Exception as e:
            app_logger.error(f"Error parsing datetime {dt_str}: {e}")
            return None
    
    async def collect_n8n_executions(self):
        """Collect new executions from n8n for all active flows"""
        try:
            app_logger.info("Starting n8n execution collection")
            
            # Get all active flows from database
            active_flows = await database_service.get_active_flows()
            total_new_executions = 0
            
            for flow in active_flows:
                flow_id = flow["flow_id"]
                
                # Get latest executions for this flow
                executions = await n8n_service.get_executions(workflow_id=flow_id, limit=100)
                
                # Get max execution ID for this specific workflow
                max_id = await database_service.get_max_execution_id_for_workflow(flow_id)
                new_executions = [ex for ex in executions if int(ex["id"]) > max_id]
                
                for execution in new_executions:
                    # Get detailed execution data
                    detailed_execution = await n8n_service.get_execution_detail(execution["id"])
                    if detailed_execution:
                        await database_service.save_n8n_execution(detailed_execution)
                        app_logger.info(f"Saved execution {execution['id']} for flow {flow_id}")
                
                total_new_executions += len(new_executions)
            
            app_logger.info(f"Collected {total_new_executions} new executions from {len(active_flows)} flows")
            
        except Exception as e:
            app_logger.error(f"Error collecting n8n executions: {e}")
    
    async def process_executions_to_langfuse(self):
        """Process unprocessed executions to Langfuse"""
        try:
            app_logger.info("Starting Langfuse processing")
            
            # Get unprocessed executions
            unprocessed = await database_service.get_unprocessed_executions()
            
            for execution in unprocessed:
                try:
                    # Create Langfuse trace
                    trace_id = langfuse_service.create_trace_from_execution(json.loads(execution["execution_data"]))
                    
                    if trace_id:
                        # Mark as processed
                        await database_service.mark_execution_processed(execution["id"], trace_id)
                        app_logger.info(f"Processed execution {execution['id']} to Langfuse trace {trace_id}")
                    
                    # Add delay between traces to ensure proper ingestion
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    app_logger.error(f"Error processing execution {execution['id']}: {e}")
            
            app_logger.info(f"Processed {len(unprocessed)} executions to Langfuse")
            
        except Exception as e:
            app_logger.error(f"Error processing executions to Langfuse: {e}")

scheduler_service = SchedulerService()