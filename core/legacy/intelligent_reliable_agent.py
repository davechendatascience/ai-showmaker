#!/usr/bin/env python3
"""
Intelligent Reliable MCP Agent with Task Planning

This module provides an intelligent and reliable MCP agent that automatically
uses todo lists for complex multi-step tasks, ensuring systematic execution.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from .reliable_mcp_agent import ReliableLlamaIndexAgent, ReliableMCPToolWrapper
from .intelligent_task_planner import IntelligentTaskPlanner, TaskPlan
from .config import ConfigManager


class IntelligentReliableAgent(ReliableLlamaIndexAgent):
    """
    Intelligent and reliable LlamaIndex agent with automatic task planning.
    
    This agent automatically detects complex tasks and creates todo-based
    execution plans for reliable multi-step task completion.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize the intelligent reliable agent."""
        super().__init__(config)
        self.task_planner = IntelligentTaskPlanner()
        self.active_task_plans: Dict[str, TaskPlan] = {}
        self.logger = logging.getLogger("ai_showmaker.intelligent_reliable_agent")
        
        # Enhanced statistics for task planning
        self.stats.update({
            'complex_tasks_detected': 0,
            'task_plans_created': 0,
            'task_plans_completed': 0,
            'todo_lists_generated': 0
        })
    
    def _build_reliable_system_prompt(self) -> str:
        """Build enhanced system prompt with intelligent task planning."""
        base_prompt = super()._build_reliable_system_prompt()
        return self.task_planner.enhance_system_prompt(base_prompt)
    
    async def query(self, message: str) -> str:
        """Query the agent with intelligent task planning."""
        # Update query statistics
        self.stats['total_queries'] += 1
        
        # First, check if this is a complex task
        if self.task_planner.is_complex_task(message):
            self.logger.info(f"Complex task detected: {message}")
            self.stats['complex_tasks_detected'] += 1
            
            # Generate task plan
            available_tools = self.get_tools_info()
            task_plan = self.task_planner.generate_task_plan(message, available_tools)
            self.active_task_plans[task_plan.task_id] = task_plan
            self.stats['task_plans_created'] += 1
            
            # Execute the task plan
            try:
                result = await self._execute_task_plan(task_plan)
                self.stats['successful_queries'] += 1
                return result
            except Exception as e:
                self.stats['failed_queries'] += 1
                raise e
        else:
            # Simple task, execute normally
            try:
                result = await super().query(message)
                self.stats['successful_queries'] += 1
                return result
            except Exception as e:
                self.stats['failed_queries'] += 1
                raise e
    
    async def _execute_task_plan(self, task_plan: TaskPlan) -> str:
        """Execute a task plan step by step."""
        self.logger.info(f"Executing task plan: {task_plan.task_id}")
        task_plan.status = "in_progress"
        
        results = []
        
        for i, step in enumerate(task_plan.steps):
            try:
                self.logger.info(f"Executing step {i+1}: {step.description}")
                
                # Execute the step
                result = await self._execute_task_step(step)
                step.completed = True
                step.result = result
                results.append(f"Step {i+1} ({step.description}): {result}")
                
                # Update task plan
                task_plan.mark_step_completed(i, result)
                
                # Track todo list generation
                if "create_todos" in step.tool_name:
                    self.stats['todo_lists_generated'] += 1
                
            except Exception as e:
                self.logger.error(f"Step {i+1} failed: {str(e)}")
                step.completed = False
                step.result = f"Error: {str(e)}"
                results.append(f"Step {i+1} ({step.description}): FAILED - {str(e)}")
                
                # Mark task plan as failed
                task_plan.status = "failed"
                break
        
        # Check if task plan is completed
        if task_plan.is_completed():
            task_plan.status = "completed"
            self.stats['task_plans_completed'] += 1
        
        # Generate final response
        return self._generate_task_plan_response(task_plan, results)
    
    async def _execute_task_step(self, step: 'TaskStep') -> str:
        """Execute a single task step."""
        # Find the tool in our registry with better name matching
        tool_func = None
        
        # Try exact match first
        if step.tool_name in self.tool_registry:
            tool_func = self.tool_registry[step.tool_name]
        else:
            # Try various name patterns
            name_variants = [
                step.tool_name,
                f"{step.tool_name}",
                f"calculation_{step.tool_name}",
                f"remote_{step.tool_name}",
                f"development_{step.tool_name}",
                f"monitoring_{step.tool_name}",
                # Also try without prefixes
                step.tool_name.replace("monitoring_", "").replace("calculation_", "").replace("remote_", "").replace("development_", "")
            ]
            
            for name_variant in name_variants:
                if name_variant in self.tool_registry:
                    tool_func = self.tool_registry[name_variant]
                    break
        
        if tool_func is None:
            # Log available tools for debugging
            available_tools = list(self.tool_registry.keys())
            raise Exception(f"Tool '{step.tool_name}' not found. Available tools: {available_tools[:10]}...")
        
        # Update tool call statistics for task planning
        self.stats['total_tool_calls'] += 1
        
        # Execute the tool
        try:
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**step.parameters)
            else:
                result = tool_func(**step.parameters)
            
            self.stats['successful_tool_calls'] += 1
            return str(result)
        except Exception as e:
            self.stats['failed_tool_calls'] += 1
            raise e
    
    def _generate_task_plan_response(self, task_plan: TaskPlan, results: List[str]) -> str:
        """Generate a comprehensive response for task plan execution."""
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "in_progress": "🔄",
            "pending": "⏳"
        }
        
        emoji = status_emoji.get(task_plan.status, "❓")
        
        response = f"{emoji} **Task Plan Execution Results**\n\n"
        response += f"**Task ID:** {task_plan.task_id}\n"
        response += f"**Description:** {task_plan.description}\n"
        response += f"**Status:** {task_plan.status.upper()}\n"
        response += f"**Steps Completed:** {task_plan.current_step}/{len(task_plan.steps)}\n\n"
        
        response += "**Execution Results:**\n"
        for result in results:
            response += f"• {result}\n"
        
        if task_plan.status == "completed":
            response += "\n🎉 **Task completed successfully!** All steps have been executed."
        elif task_plan.status == "failed":
            response += "\n⚠️ **Task failed.** Some steps encountered errors. Please review and retry."
        elif task_plan.status == "in_progress":
            response += "\n🔄 **Task in progress.** Some steps are still pending."
        
        return response
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics including task planning metrics."""
        base_stats = super().get_statistics()
        
        # Merge our task planning statistics with the base agent statistics
        if 'agent_stats' in base_stats:
            base_stats['agent_stats'].update({
                'complex_tasks_detected': self.stats['complex_tasks_detected'],
                'task_plans_created': self.stats['task_plans_created'],
                'task_plans_completed': self.stats['task_plans_completed'],
                'todo_lists_generated': self.stats['todo_lists_generated']
            })
        
        # Add task planning metrics
        base_stats['task_planning_metrics'] = {
            'complex_tasks_detected': self.stats['complex_tasks_detected'],
            'task_plans_created': self.stats['task_plans_created'],
            'task_plans_completed': self.stats['task_plans_completed'],
            'todo_lists_generated': self.stats['todo_lists_generated'],
            'active_task_plans': len(self.active_task_plans),
            'task_success_rate': self.stats['task_plans_completed'] / max(self.stats['task_plans_created'], 1)
        }
        
        return base_stats
    
    def get_active_task_plans(self) -> Dict[str, TaskPlan]:
        """Get all active task plans."""
        return self.active_task_plans.copy()
    
    def get_task_plan(self, task_id: str) -> Optional[TaskPlan]:
        """Get a specific task plan by ID."""
        return self.active_task_plans.get(task_id)
    
    async def continue_task_plan(self, task_id: str) -> str:
        """Continue execution of a specific task plan."""
        task_plan = self.get_task_plan(task_id)
        if not task_plan:
            return f"Task plan {task_id} not found."
        
        if task_plan.status == "completed":
            return f"Task plan {task_id} is already completed."
        
        return await self._execute_task_plan(task_plan)


# Enhanced compatibility wrapper
class IntelligentReliableAIShowmakerAgent:
    """
    Intelligent reliable compatibility wrapper with automatic task planning.
    """
    
    def __init__(self, config: ConfigManager):
        """Initialize with intelligent reliable backend."""
        self.config = config
        self.logger = logging.getLogger("ai_showmaker.intelligent_reliable_agent")
        self.manager = None
        self.agent = None
        self.start_time = datetime.now()
        
    async def initialize(self) -> None:
        """Initialize the agent and MCP servers."""
        from core.enhanced_mcp_agent import EnhancedMCPServerManager
        
        self.manager = EnhancedMCPServerManager()
        await self.manager.initialize_servers()
        self.agent = IntelligentReliableAgent(self.config)
        self.agent.set_mcp_servers(self.manager.servers)
        self.logger.info("IntelligentReliableAIShowmakerAgent initialized with task planning capabilities")
    
    async def query(self, message: str) -> str:
        """Query the agent with intelligent task planning."""
        if not self.agent:
            await self.initialize()
        return await self.agent.query(message)
    
    def get_tools_info(self) -> List[Dict[str, Any]]:
        """Get available tools information."""
        if not self.agent:
            return []
        return self.agent.get_tools_info()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics."""
        if not self.agent:
            return {'error': 'Agent not initialized'}
        
        stats = self.agent.get_statistics()
        stats['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        return stats
    
    def get_active_task_plans(self) -> Dict[str, TaskPlan]:
        """Get all active task plans."""
        if not self.agent:
            return {}
        return self.agent.get_active_task_plans()
    
    def get_task_plan(self, task_id: str) -> Optional[TaskPlan]:
        """Get a specific task plan by ID."""
        if not self.agent:
            return None
        return self.agent.get_task_plan(task_id)
    
    async def continue_task_plan(self, task_id: str) -> str:
        """Continue execution of a specific task plan."""
        if not self.agent:
            await self.initialize()
        return await self.agent.continue_task_plan(task_id)
    
    async def _get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        if not self.manager:
            return {}
        return self.manager.get_server_stats()
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        if self.manager:
            await self.manager.shutdown()
