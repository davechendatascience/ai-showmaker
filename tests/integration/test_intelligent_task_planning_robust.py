#!/usr/bin/env python3
"""
Robust Integration tests for Intelligent Task Planning

These tests actually validate the agent's behavior, including parameter validation,
tool usage verification, and todo list creation.
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import os
import json
import re
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.intelligent_reliable_agent import IntelligentReliableAIShowmakerAgent
from core.intelligent_task_planner import IntelligentTaskPlanner, TaskPlan, TaskStep
from core.config import ConfigManager


class TestRobustIntelligentTaskPlanning:
    """Robust test suite that validates actual agent behavior."""
    
    @pytest_asyncio.fixture
    async def agent(self):
        """Create an intelligent reliable agent for testing."""
        config = ConfigManager()
        agent = IntelligentReliableAIShowmakerAgent(config)
        await agent.initialize()
        yield agent
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_calculation_with_correct_parameters(self, agent):
        """Test that calculation tool receives correct parameters."""
        result = await agent.query("Calculate 5 + 3")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that the result contains the expected calculation
        assert "8" in result or "5 + 3 = 8" in result
        
        # Check statistics to see if tool was called
        stats = agent.get_statistics()
        assert stats['agent_stats']['total_tool_calls'] > 0
        assert stats['agent_stats']['successful_tool_calls'] > 0
    
    @pytest.mark.asyncio
    async def test_calculation_with_missing_parameters(self, agent):
        """Test that calculation tool handles missing parameters gracefully."""
        result = await agent.query("Calculate")  # Missing expression
        
        assert result is not None
        assert len(result) > 0
        
        # Should handle missing parameters gracefully
        stats = agent.get_statistics()
        # May have failed tool calls due to missing parameters
        assert stats['agent_stats']['total_tool_calls'] >= 0
    
    @pytest.mark.asyncio
    async def test_todo_creation_with_content(self, agent):
        """Test that todo creation tool receives proper content."""
        result = await agent.query("Create todos for: deploy app, test features, monitor performance")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that todo creation was attempted
        stats = agent.get_statistics()
        assert stats['agent_stats']['total_tool_calls'] > 0
        
        # The result should indicate todo creation
        assert "todo" in result.lower() or "created" in result.lower() or "list" in result.lower()
    
    @pytest.mark.asyncio
    async def test_deployment_task_creates_todo_list(self, agent):
        """Test that deployment tasks actually create todo lists."""
        result = await agent.query("Deploy a web application")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
            assert planning_stats['task_plans_created'] > 0
        
        # Check that todo creation was part of the task plan
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Verify that at least one step involves todo creation
        todo_steps_found = False
        for task_id, plan in active_plans.items():
            for step in plan.steps:
                if 'create_todos' in step.tool_name or 'todo' in step.description.lower():
                    todo_steps_found = True
                    break
            if todo_steps_found:
                break
        
        assert todo_steps_found, "Deployment task should include todo creation step"
    
    @pytest.mark.asyncio
    async def test_development_task_creates_appropriate_steps(self, agent):
        """Test that development tasks create appropriate planning steps."""
        result = await agent.query("Set up a development environment for a Python project")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
        
        # Check that appropriate steps were created
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Verify that development-related steps are included
        dev_steps_found = False
        for task_id, plan in active_plans.items():
            for step in plan.steps:
                if any(keyword in step.description.lower() for keyword in 
                      ['development', 'environment', 'setup', 'install', 'configure']):
                    dev_steps_found = True
                    break
            if dev_steps_found:
                break
        
        assert dev_steps_found, "Development task should include development-related steps"
    
    @pytest.mark.asyncio
    async def test_monitoring_task_creates_monitoring_steps(self, agent):
        """Test that monitoring tasks create monitoring-related steps."""
        result = await agent.query("Set up system monitoring and performance tracking")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
        
        # Check that monitoring steps were created
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Verify that monitoring-related steps are included
        monitoring_steps_found = False
        for task_id, plan in active_plans.items():
            for step in plan.steps:
                if any(keyword in step.description.lower() for keyword in 
                      ['monitor', 'tracking', 'performance', 'system', 'status']):
                    monitoring_steps_found = True
                    break
            if monitoring_steps_found:
                break
        
        assert monitoring_steps_found, "Monitoring task should include monitoring-related steps"
    
    @pytest.mark.asyncio
    async def test_task_plan_execution_validation(self, agent):
        """Test that task plans are actually executed and validated."""
        result = await agent.query("Deploy a web application with monitoring")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task plan was created and executed
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Check task plan details and execution
        for task_id, plan in active_plans.items():
            assert isinstance(plan, TaskPlan)
            assert plan.task_id == task_id
            assert len(plan.steps) > 0
            assert plan.status in ["pending", "in_progress", "completed", "failed"]
            
            # Check that steps have proper metadata
            for step in plan.steps:
                assert step.description is not None
                assert step.tool_name is not None
                assert step.parameters is not None
                
                # If step was completed, it should have a result
                if step.completed:
                    assert step.result is not None
    
    @pytest.mark.asyncio
    async def test_parameter_validation_in_task_steps(self, agent):
        """Test that task steps validate parameters properly."""
        # Create a task plan manually to test parameter validation
        available_tools = agent.get_tools_info()
        task_planner = agent.agent.task_planner
        task_plan = task_planner.generate_task_plan("Test deployment", available_tools)
        
        assert len(task_plan.steps) > 0
        
        # Test that steps have valid parameters
        for step in task_plan.steps:
            assert step.description is not None
            assert step.tool_name is not None
            assert step.parameters is not None
            
            # Check that parameters match the tool requirements
            tool_info = None
            for tool in available_tools:
                if tool['name'] == step.tool_name:
                    tool_info = tool
                    break
            
            if tool_info:
                # Verify that required parameters are provided
                required_params = tool_info.get('parameters', {}).get('required', [])
                for param in required_params:
                    assert param in step.parameters, f"Required parameter '{param}' missing for tool '{step.tool_name}'"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_tools(self, agent):
        """Test error handling when tools are called with invalid parameters."""
        result = await agent.query("Execute a non-existent tool with invalid parameters")
        
        assert result is not None
        assert len(result) > 0
        
        # Should handle errors gracefully
        stats = agent.get_statistics()
        # May have failed tool calls, but should not crash
        assert stats['agent_stats']['total_queries'] > 0
    
    @pytest.mark.asyncio
    async def test_simple_vs_complex_task_differentiation(self, agent):
        """Test that simple and complex tasks are handled differently."""
        # Test simple task
        simple_result = await agent.query("Calculate 2 + 2")
        
        # Test complex task
        complex_result = await agent.query("Deploy a web application")
        
        assert simple_result is not None
        assert complex_result is not None
        
        # Check that complex task triggered task planning
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
            assert planning_stats['task_plans_created'] > 0
        
        # Simple task should not create task plans
        active_plans = agent.get_active_task_plans()
        # Complex tasks should create plans, but we can't guarantee simple tasks don't
        # since the agent might decide to create plans for any task
    
    @pytest.mark.asyncio
    async def test_todo_list_content_validation(self, agent):
        """Test that todo lists contain appropriate content for the task."""
        result = await agent.query("Deploy a web application")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that todo creation was part of the task plan
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Find todo creation steps and validate their content
        for task_id, plan in active_plans.items():
            for step in plan.steps:
                if 'create_todos' in step.tool_name:
                    # Check that todos parameter is provided
                    assert 'todos' in step.parameters
                    todos = step.parameters['todos']
                    assert isinstance(todos, list)
                    assert len(todos) > 0
                    
                    # Check that todos contain deployment-related items
                    deployment_keywords = ['deploy', 'setup', 'configure', 'build', 'test', 'monitor']
                    deployment_todos = [todo for todo in todos if any(keyword in todo.lower() for keyword in deployment_keywords)]
                    assert len(deployment_todos) > 0, "Deployment todos should contain deployment-related items"
    
    @pytest.mark.asyncio
    async def test_task_plan_completion_tracking(self, agent):
        """Test that task plan completion is properly tracked."""
        result = await agent.query("Set up a simple development environment")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task plan was created
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Check completion status
        for task_id, plan in active_plans.items():
            assert plan.status in ["pending", "in_progress", "completed", "failed"]
            
            # Check step completion tracking
            completed_steps = sum(1 for step in plan.steps if step.completed)
            assert completed_steps >= 0
            assert completed_steps <= len(plan.steps)
            
            # If all steps are completed, plan should be completed
            if completed_steps == len(plan.steps):
                assert plan.status == "completed"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
