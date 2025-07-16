import os
from langfuse import Langfuse
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

from app.configs.settings import settings
from app.utils.logger import app_logger

class LangfuseService:
    def __init__(self):
        self.langfuse = Langfuse(
            secret_key=settings.langfuse_secret_key,#'sk-lf-40484669-8a8e-4fdf-8f70-296c2deef06a',
            public_key=settings.langfuse_public_key,#'pk-lf-e2285dc1-130f-46a0-a4ec-309e7cf3be98',
            host=settings.langfuse_host
        )
    
    def create_trace_from_execution(self, execution_data: Dict[str, Any]) -> str:
        """Convert n8n execution to Langfuse trace"""
        try:
            # Get workflow data for better context
            workflow_data = execution_data.get("workflowData", {})
            workflow_name = workflow_data.get("name", "Unknown Workflow")
            
            # Extract initial input from trigger node
            initial_input = self._extract_initial_input(execution_data)
            
            # Extract final output from last executed node
            final_output = self._extract_final_output(execution_data)
            
            total_latency, total_tokens = self._calculate_totals(execution_data)

            trace = self.langfuse.trace(
                name=f"{workflow_name}-{execution_data['id']}",
                input=initial_input,
                output=final_output,
                metadata={
                    "workflow_id": execution_data.get("workflowId"),
                    "workflow_name": workflow_name,
                    "status": execution_data.get("status"),
                    "mode": execution_data.get("mode"),
                    "n8n_execution_id": execution_data["id"],
                    "last_node_executed": execution_data.get("data", {}).get("resultData", {}).get("lastNodeExecuted"),
                    "total_latency_ms": total_latency
                },
                tokens=total_tokens,
                start_time=self._parse_datetime(execution_data.get("startedAt")),
                end_time=self._parse_datetime(execution_data.get("stoppedAt")),
                tags=["n8n", "workflow", execution_data.get("status", "unknown")]
            )
            
            # Add spans for each node execution
            if execution_data.get("data", {}).get("resultData", {}).get("runData"):
                self._add_node_spans(trace, execution_data["data"]["resultData"]["runData"])
            
            # Flush to ensure trace is sent immediately
            self.langfuse.flush()
            
            return trace.id
        except Exception as e:
            app_logger.error(f"Failed to create Langfuse trace: {e}")
            return None

    def _extract_initial_input(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract initial input from trigger node or first node"""
        run_data = execution_data.get("data", {}).get("resultData", {}).get("runData", {})
        
        # Look for trigger node first
        trigger_nodes = ["When Executed by Another Workflow", "Webhook", "Manual Trigger"]
        for trigger_node in trigger_nodes:
            if trigger_node in run_data and run_data[trigger_node]:
                first_run = run_data[trigger_node][0]
                if first_run.get("data", {}).get("main"):
                    return first_run["data"]["main"][0][0].get("json", {}) if first_run["data"]["main"][0] else {}
        
        # Fallback to startData
        return execution_data.get("data", {}).get("startData", {})

    def _extract_final_output(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract final output from last executed node"""
        last_node = execution_data.get("data", {}).get("resultData", {}).get("lastNodeExecuted")
        run_data = execution_data.get("data", {}).get("resultData", {}).get("runData", {})
        
        if last_node and last_node in run_data and run_data[last_node]:
            last_run = run_data[last_node][-1]  # Get the last run of the last node
            if last_run.get("data", {}).get("main"):
                main_data = last_run["data"]["main"]
                if main_data and main_data[0]:  # Check if there's output data
                    return main_data[0][0].get("json", {}) if main_data[0] else {}
        
        # Fallback to resultData
        return execution_data.get("data", {}).get("resultData", {})

    def _add_node_spans(self, trace, run_data: Dict[str, Any]):
        """Add spans for each node execution"""
        for node_name, node_runs in run_data.items():
            for i, run in enumerate(node_runs):
                # Calculate proper end time
                start_time = self._parse_datetime_from_timestamp(run.get("startTime"))
                execution_time_ms = run.get("executionTime", 0)
                end_time = None
                if start_time and execution_time_ms:
                    end_time = start_time + timedelta(milliseconds=execution_time_ms)
                
                # Extract input data - prioritize inputOverride for AI nodes
                input_data = {}
                if run.get("inputOverride"):
                    # For AI nodes, inputOverride contains the actual prompt/messages
                    input_data = run["inputOverride"]
                elif run.get("source"):
                    # This node has input from previous nodes
                    input_data = {"from_nodes": [src.get("previousNode") for src in run["source"] if src is not None]}
                
                # Extract output data - check different data types
                output_data = {}
                
                # For AI language model nodes
                if run.get("data", {}).get("ai_languageModel"):
                    ai_data = run["data"]["ai_languageModel"]
                    if ai_data and ai_data[0] and ai_data[0][0].get("json"):
                        ai_json = ai_data[0][0]["json"]
                        if "response" in ai_json:
                            output_data = {"response": ai_json["response"]}
                        else:
                            output_data = ai_json
                
                # For regular nodes with main data
                elif run.get("data", {}).get("main"):
                    main_data = run["data"]["main"]
                    if main_data and main_data[0]:
                        output_data = main_data[0][0].get("json", {}) if main_data[0] else {}
                
                # Extract token usage for AI nodes
                token_usage = self._extract_token_usage(run)
                
                span_metadata = {
                    "node_name": node_name,
                    "execution_status": run.get("executionStatus"),
                    "execution_index": run.get("executionIndex"),
                    "execution_time_ms": execution_time_ms
                }
                
                # Add parent execution info if available
                if run.get("metadata", {}).get("parentExecution"):
                    span_metadata["parent_execution"] = run["metadata"]["parentExecution"]
                
                span = trace.span(
                    name=f"{node_name}" if i == 0 else f"{node_name}-{i}",
                    input=input_data,
                    output=output_data,
                    start_time=start_time,
                    end_time=end_time,
                    metadata=span_metadata
                )
                
                # Add generation for AI model nodes to track costs and tokens
                if run.get("data", {}).get("ai_languageModel") and token_usage:
                    model_name = self._extract_model_name(run)
                    prompt = self._extract_prompt(run)
                    completion = self._extract_completion(run)
                    
                    if model_name:
                        span.generation(
                            model=model_name,
                            input=prompt or input_data,
                            output=completion or output_data,
                            usage=token_usage,
                            start_time=start_time,
                            end_time=end_time
                        )
    def _calculate_totals(self, execution_data: Dict[str, Any]) -> tuple:
        """Calculate total latency and token usage across all nodes"""
        total_latency = 0
        total_tokens = {"input": 0, "output": 0, "total": 0}
        
        run_data = execution_data.get("data", {}).get("resultData", {}).get("runData", {})
        
        for node_name, node_runs in run_data.items():
            for run in node_runs:
                # Add execution time
                execution_time = run.get("executionTime", 0)
                total_latency += execution_time
                
                # Add token usage
                token_usage = self._extract_token_usage(run)
                if token_usage:
                    total_tokens["input"] += token_usage.get("input", 0)
                    total_tokens["output"] += token_usage.get("output", 0)
                    total_tokens["total"] += token_usage.get("total", 0)
        
        return total_latency, total_tokens if total_tokens["total"] > 0 else None


    def _extract_token_usage(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Extract token usage from AI model nodes"""
        # Check in ai_languageModel data first
        if run.get("data", {}).get("ai_languageModel"):
            ai_data = run["data"]["ai_languageModel"]
            if ai_data and ai_data[0] and ai_data[0][0].get("json", {}).get("tokenUsage"):
                token_usage = ai_data[0][0]["json"]["tokenUsage"]
                return {
                    "input": token_usage.get("promptTokens", 0),
                    "output": token_usage.get("completionTokens", 0),
                    "total": token_usage.get("totalTokens", 0)
                }
        
        # Check in response data for nested token usage
        if run.get("data", {}).get("ai_languageModel"):
            ai_data = run["data"]["ai_languageModel"]
            if ai_data and ai_data[0] and ai_data[0][0].get("json", {}).get("response", {}).get("tokenUsage"):
                token_usage = ai_data[0][0]["json"]["response"]["tokenUsage"]
                return {
                    "input": token_usage.get("promptTokens", 0),
                    "output": token_usage.get("completionTokens", 0),
                    "total": token_usage.get("totalTokens", 0)
                }
        
        return None

    def _extract_model_name(self, run: Dict[str, Any]) -> str:
        """Extract model name from AI node run data"""
        try:
            # For Google Gemini
            if run.get("inputOverride", {}).get("ai_languageModel"):
                options = run["inputOverride"]["ai_languageModel"][0][0].get("json", {}).get("options", {})
                return options.get("model_name", "unknown-model")
            
            # For OpenAI
            if run.get("data", {}).get("ai_languageModel"):
                ai_data = run["data"]["ai_languageModel"]
                if ai_data and ai_data[0] and ai_data[0][0].get("json"):
                    return ai_data[0][0].get("json", {}).get("model", "unknown-model")
            
            # Default fallback
            return "unknown-model"
        except Exception:
            return "unknown-model"
    
    def _extract_prompt(self, run: Dict[str, Any]) -> str:
        """Extract prompt text from AI node run data"""
        try:
            # For nodes with messages array
            if run.get("inputOverride", {}).get("ai_languageModel"):
                messages = run["inputOverride"]["ai_languageModel"][0][0].get("json", {}).get("messages", [])
                if isinstance(messages, list) and messages:
                    return str(messages[0]) if messages else ""
                return str(messages)
            
            # For nodes with direct prompt
            if run.get("inputOverride", {}).get("prompt"):
                return str(run["inputOverride"]["prompt"])
            
            # Return JSON representation of input as fallback
            return str(run.get("inputOverride", {}))
        except Exception:
            return ""
    
    def _extract_completion(self, run: Dict[str, Any]) -> str:
        """Extract completion text from AI node run data"""
        try:
            # For Google Gemini
            if run.get("data", {}).get("ai_languageModel"):
                ai_data = run["data"]["ai_languageModel"]
                if ai_data and ai_data[0] and ai_data[0][0].get("json"):
                    response = ai_data[0][0]["json"].get("response", {})
                    
                    # Handle different response formats
                    if isinstance(response, str):
                        return response
                    
                    # Handle Gemini format
                    if response.get("generations"):
                        generations = response["generations"]
                        if generations and generations[0] and generations[0][0]:
                            return generations[0][0].get("text", "")
                    
                    # Handle OpenAI format
                    if response.get("choices"):
                        choices = response["choices"]
                        if choices and choices[0]:
                            return choices[0].get("message", {}).get("content", "")
            
            # Return string representation of output as fallback
            return str(run.get("data", {}).get("main", [{}])[0][0].get("json", {}))
        except Exception:
            return ""

    def _parse_datetime_from_timestamp(self, timestamp: int) -> datetime:
        """Parse timestamp to datetime object"""
        if not timestamp:
            return None
        try:
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        except:
            return None

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string to datetime object"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

        if run.get("data", {}).get("ai_languageModel"):
            ai_data = run["data"]["ai_languageModel"]
            if ai_data and ai_data[0] and ai_data[0][0].get("json", {}).get("tokenUsage"):
                token_usage = ai_data[0][0]["json"]["tokenUsage"]
                return {
                    "input": token_usage.get("promptTokens", 0),
                    "output": token_usage.get("completionTokens", 0),
                    "total": token_usage.get("totalTokens", 0)
                }
        # Check in response data for nested token usage
        if run.get("data", {}).get("ai_languageModel"):
            ai_data = run["data"]["ai_languageModel"]
            if ai_data and ai_data[0] and ai_data[0][0].get("json", {}).get("response", {}).get("tokenUsage"):
                token_usage = ai_data[0][0]["json"]["response"]["tokenUsage"]
                return {
                    "input": token_usage.get("promptTokens", 0),
                    "output": token_usage.get("completionTokens", 0),
                    "total": token_usage.get("totalTokens", 0)
                }
        return None

    def _parse_datetime_from_timestamp(self, timestamp: int) -> datetime:
        """Parse timestamp to datetime object"""
        if not timestamp:
            return None
        try:
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        except:
            return None

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string to datetime object"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

langfuse_service = LangfuseService()