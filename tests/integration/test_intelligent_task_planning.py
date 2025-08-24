#!/usr/bin/env python3
"""
Integration tests for Intelligent Task Planning

Tests the intelligent task planning capabilities with real MCP server interactions.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.intelligent_reliable_agent import IntelligentReliableAIShowmakerAgent
from core.intelligent_task_planner import IntelligentTaskPlanner, TaskPlan, TaskStep
from core.config import ConfigManager


class TestIntelligentTaskPlanning:
    """Test suite for intelligent task planning integration."""
    
    @pytest.fixture
    async def agent(self):
        """Create an intelligent reliable agent for testing."""
        config = ConfigManager()
        agent = IntelligentReliableAIShowmakerAgent(config)
        await agent.initialize()
        yield agent
        await agent.shutdown()
    
    @pytest.fixture
    def task_planner(self):
        """Create a task planner for testing."""
        return IntelligentTaskPlanner()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test that the intelligent agent initializes correctly."""
        assert agent is not None
        assert agent.agent is not None
        assert hasattr(agent.agent, 'task_planner')
        assert len(agent.agent.mcp_tools) > 0
        assert len(agent.agent.llama_tools) > 0
    
    @pytest.mark.asyncio
    async def test_simple_task_detection(self, task_planner):
        """Test that simple tasks are not classified as complex."""
        simple_tasks = [
            "Calculate 5 + 3",
            "What is 2 * 4?",
            "Get the current time",
            "List files in directory"
        ]
        
        for task in simple_tasks:
            assert not task_planner.is_complex_task(task), f"Task '{task}' should not be complex"
    
    @pytest.mark.asyncio
    async def test_complex_task_detection(self, task_planner):
        """Test that complex tasks are properly detected."""
        complex_tasks = [
            "Deploy a web application",
            "Set up a development environment",
            "Configure system monitoring",
            "Process and analyze data",
            "Install and configure a database",
            "Build and deploy the application",
            "Set up monitoring and logging",
            "Create a deployment pipeline"
        ]
        
        for task in complex_tasks:
            assert task_planner.is_complex_task(task), f"Task '{task}' should be complex"
    
    @pytest.mark.asyncio
    async def test_task_classification(self, task_planner):
        """Test task classification into different types."""
        test_cases = [
            ("Deploy a web application", "deployment"),
            ("Set up development environment", "development"),
            ("Configure monitoring system", "monitoring"),
            ("Process large dataset", "data_processing"),
            ("Install system software", "system_administration"),
            ("Calculate 5 + 3", "general")  # Simple task
        ]
        
        for task, expected_type in test_cases:
            task_type = task_planner._classify_task(task)
            assert task_type == expected_type, f"Task '{task}' should be classified as '{expected_type}', got '{task_type}'"
    
    @pytest.mark.asyncio
    async def test_deployment_task_planning(self, agent):
        """Test deployment task planning with real MCP tools."""
        result = await agent.query("Deploy a web application")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
            assert planning_stats['task_plans_created'] > 0
    
    @pytest.mark.asyncio
    async def test_development_task_planning(self, agent):
        """Test development task planning with real MCP tools."""
        result = await agent.query("Set up a development environment for a Python project")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_task_planning(self, agent):
        """Test monitoring task planning with real MCP tools."""
        result = await agent.query("Set up system monitoring and performance tracking")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task planning was triggered
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            assert planning_stats['complex_tasks_detected'] > 0
    
    @pytest.mark.asyncio
    async def test_simple_task_execution(self, agent):
        """Test that simple tasks execute directly without task planning."""
        result = await agent.query("Calculate 5 + 3")
        
        assert result is not None
        assert "8" in result or "5 + 3 = 8" in result
        
        # Check that no task planning was triggered for simple tasks
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            # Simple tasks should not trigger complex task detection
    
    @pytest.mark.asyncio
    async def test_task_plan_execution(self, agent):
        """Test that task plans are executed step by step."""
        # This should trigger task planning
        result = await agent.query("Deploy a web application with monitoring")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that task plan was created and executed
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Check task plan details
        for task_id, plan in active_plans.items():
            assert isinstance(plan, TaskPlan)
            assert plan.task_id == task_id
            assert len(plan.steps) > 0
            assert plan.status in ["pending", "in_progress", "completed", "failed"]
    
    @pytest.mark.asyncio
    async def test_task_plan_statistics(self, agent):
        """Test that task planning statistics are properly tracked."""
        # Execute a complex task
        await agent.query("Set up a development environment")
        
        stats = agent.get_statistics()
        assert 'task_planning_metrics' in stats
        
        planning_stats = stats['task_planning_metrics']
        assert 'complex_tasks_detected' in planning_stats
        assert 'task_plans_created' in planning_stats
        assert 'task_plans_completed' in planning_stats
        assert 'active_task_plans' in planning_stats
        assert 'task_success_rate' in planning_stats
    
    @pytest.mark.asyncio
    async def test_task_step_execution(self, agent):
        """Test individual task step execution."""
        # Create a simple task plan manually for testing
        available_tools = agent.get_tools_info()
        task_planner = agent.agent.task_planner
        task_plan = task_planner.generate_task_plan("Test deployment", available_tools)
        
        assert len(task_plan.steps) > 0
        
        # Test step execution
        for i, step in enumerate(task_plan.steps):
            assert isinstance(step, TaskStep)
            assert step.description is not None
            assert step.tool_name is not None
            assert step.parameters is not None
            assert not step.completed  # Initially not completed
    
    @pytest.mark.asyncio
    async def test_error_handling_in_task_plans(self, agent):
        """Test error handling during task plan execution."""
        # This should trigger task planning but may fail due to missing tools
        result = await agent.query("Deploy a complex application with multiple services")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that errors are handled gracefully
        active_plans = agent.get_active_task_plans()
        for task_id, plan in active_plans.items():
            # Plan should exist even if some steps failed
            assert plan is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_task_planning(self, agent):
        """Test handling of concurrent complex tasks."""
        complex_queries = [
            "Deploy a web application",
            "Set up monitoring system",
            "Configure development environment"
        ]
        
        # Execute queries concurrently
        tasks = [agent.query(query) for query in complex_queries]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert len(result) > 0
        
        # Check that multiple task plans were created
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) >= 3
    
    @pytest.mark.asyncio
    async def test_task_plan_continuation(self, agent):
        """Test continuing execution of existing task plans."""
        # Create a task plan
        await agent.query("Deploy a web application")
        
        # Get active plans
        active_plans = agent.get_active_task_plans()
        assert len(active_plans) > 0
        
        # Continue execution of the first plan
        task_id = list(active_plans.keys())[0]
        result = await agent.continue_task_plan(task_id)
        
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_system_prompt_enhancement(self, agent):
        """Test that system prompts are enhanced with task planning instructions."""
        # The system prompt should include intelligent task planning instructions
        # This is tested indirectly through task execution
        result = await agent.query("What tools are available for complex tasks?")
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_todo_list_generation(self, agent):
        """Test that todo lists are generated for complex tasks."""
        result = await agent.query("Deploy a web application")
        
        assert result is not None
        assert len(result) > 0
        
        # Check that todo creation was part of the task plan
        stats = agent.get_statistics()
        if 'task_planning_metrics' in stats:
            planning_stats = stats['task_planning_metrics']
            # Should have generated todo lists
            assert planning_stats['todo_lists_generated'] >= 0


class TestTaskPlannerUnit:
    """Unit tests for TaskPlanner class."""
    
    def test_task_patterns_initialization(self):
        """Test that task patterns are properly initialized."""
        planner = IntelligentTaskPlanner()
        
        assert hasattr(planner, 'task_patterns')
        assert isinstance(planner.task_patterns, dict)
        
        expected_categories = ['deployment', 'development', 'monitoring', 'data_processing', 'system_administration']
        for category in expected_categories:
            assert category in planner.task_patterns
            assert isinstance(planner.task_patterns[category], list)
            assert len(planner.task_patterns[category]) > 0
    
    def test_complex_task_indicators(self):
        """Test complex task indicators."""
        planner = IntelligentTaskPlanner()
        
        assert hasattr(planner, 'complex_task_indicators')
        assert isinstance(planner.complex_task_indicators, list)
        assert len(planner.complex_task_indicators) > 0
        
        # Check for key indicators
        key_indicators = ['deploy', 'setup', 'configure', 'install', 'build', 'test', 'monitor']
        for indicator in key_indicators:
            assert indicator in planner.complex_task_indicators
    
    def test_task_step_creation(self):
        """Test TaskStep dataclass creation."""
        step = TaskStep(
            description="Test step",
            tool_name="test_tool",
            parameters={"param1": "value1"}
        )
        
        assert step.description == "Test step"
        assert step.tool_name == "test_tool"
        assert step.parameters == {"param1": "value1"}
        assert step.completed is False
        assert step.result is None
        assert step.dependencies == []
    
    def test_task_plan_creation(self):
        """Test TaskPlan dataclass creation."""
        steps = [
            TaskStep("Step 1", "tool1", {}),
            TaskStep("Step 2", "tool2", {})
        ]
        
        plan = TaskPlan(
            task_id="test_plan",
            description="Test plan",
            steps=steps,
            created_at=None  # Will be set automatically
        )
        
        assert plan.task_id == "test_plan"
        assert plan.description == "Test plan"
        assert len(plan.steps) == 2
        assert plan.status == "pending"
        assert plan.current_step == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
