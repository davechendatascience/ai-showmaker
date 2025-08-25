#!/usr/bin/env python3
"""
Intelligent Task Planner for MCP Agent

This module provides intelligent task planning capabilities that automatically
use todo lists for complex multi-step tasks, ensuring reliable execution.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TaskStep:
    """Represents a single step in a complex task."""
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None
    completed: bool = False
    result: Any = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TaskPlan:
    """Represents a complete task plan with multiple steps."""
    task_id: str
    description: str
    steps: List[TaskStep]
    created_at: datetime
    status: str = "pending"  # pending, in_progress, completed, failed
    current_step: int = 0
    
    def get_next_step(self) -> Optional[TaskStep]:
        """Get the next uncompleted step."""
        for i, step in enumerate(self.steps):
            if not step.completed:
                return step
        return None
    
    def mark_step_completed(self, step_index: int, result: Any = None):
        """Mark a step as completed."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index].completed = True
            self.steps[step_index].result = result
            self.current_step = step_index + 1
    
    def is_completed(self) -> bool:
        """Check if all steps are completed."""
        return all(step.completed for step in self.steps)


class IntelligentTaskPlanner:
    """
    Intelligent task planner that automatically detects complex tasks
    and creates todo-based execution plans.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ai_showmaker.task_planner")
        self.task_patterns = self._initialize_task_patterns()
        self.complex_task_indicators = [
            "deploy", "setup", "configure", "install", "build", "test framework", "monitor",
            "migrate", "backup", "restore", "optimize", "analyze", "generate",
            "create a project", "create an application", "create a website", "create a service",
            "set up", "build a", "deploy the", "configure the",
            "multiple", "several", "various", "different", "steps", "process"
        ]
    
    def _initialize_task_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for different types of complex tasks."""
        return {
            "deployment": [
                r"deploy.*app", r"deploy.*service", r"deploy.*website",
                r"set up.*server", r"configure.*deployment", r"build.*deploy"
            ],
            "development": [
                r"create.*project", r"set up.*development", r"build.*application",
                r"configure.*environment", r"install.*dependencies", r"setup.*dev"
            ],
            "monitoring": [
                r"set up.*monitoring", r"configure.*logging", r"monitor.*performance",
                r"track.*metrics", r"analyze.*logs", r"check.*status"
            ],
            "data_processing": [
                r"process.*data", r"analyze.*dataset", r"generate.*report",
                r"backup.*data", r"migrate.*database", r"export.*data"
            ],
            "system_administration": [
                r"configure.*system", r"set up.*server", r"install.*software",
                r"update.*system", r"backup.*system", r"optimize.*performance"
            ]
        }
    
    def is_complex_task(self, query: str) -> bool:
        """Determine if a query represents a complex multi-step task."""
        query_lower = query.lower()
        
        # Check for explicit multi-step indicators
        if any(indicator in query_lower for indicator in self.complex_task_indicators):
            return True
        
        # Check for task patterns
        for task_type, patterns in self.task_patterns.items():
            if any(re.search(pattern, query_lower) for pattern in patterns):
                return True
        
        # Check for natural language indicators of complexity, but be more selective
        # Only trigger if there are multiple step indicators AND project-level keywords
        step_indicators = [
            "first", "then", "next", "after", "before", "finally",
            "step by step", "step 1", "step 2", "phase", "stage"
        ]
        
        project_keywords = [
            "project", "application", "website", "service", "system", "environment",
            "deployment", "development", "setup", "configuration", "framework"
        ]
        
        # Count step indicators
        step_count = sum(1 for indicator in step_indicators if indicator in query_lower)
        
        # Check if this is a project-level task with multiple steps
        has_project_keywords = any(keyword in query_lower for keyword in project_keywords)
        
        # Only classify as complex if there are multiple step indicators AND project keywords
        if step_count >= 2 and has_project_keywords:
            return True
        
        # Also check for explicit multi-step commands (like numbered lists)
        if re.search(r'\d+\.\s', query_lower) and len(re.findall(r'\d+\.\s', query_lower)) >= 3:
            return True
        
        return False
    
    def generate_task_plan(self, query: str, available_tools: List[Dict[str, Any]]) -> TaskPlan:
        """Generate a task plan for a complex query."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Analyze the query to determine task type
        task_type = self._classify_task(query)
        
        # Generate steps based on task type
        steps = self._generate_steps_for_task(query, task_type, available_tools)
        
        return TaskPlan(
            task_id=task_id,
            description=query,
            steps=steps,
            created_at=datetime.now()
        )
    
    def _classify_task(self, query: str) -> str:
        """Classify the type of task based on the query."""
        query_lower = query.lower()
        
        for task_type, patterns in self.task_patterns.items():
            if any(re.search(pattern, query_lower) for pattern in patterns):
                return task_type
        
        # Default classification based on keywords
        if any(word in query_lower for word in ["deploy", "deployment"]):
            return "deployment"
        elif any(word in query_lower for word in ["create", "build", "develop"]):
            return "development"
        elif any(word in query_lower for word in ["monitor", "track", "analyze"]):
            return "monitoring"
        elif any(word in query_lower for word in ["data", "process", "analyze"]):
            return "data_processing"
        elif any(word in query_lower for word in ["system", "server", "configure"]):
            return "system_administration"
        
        return "general"
    
    def _generate_steps_for_task(self, query: str, task_type: str, available_tools: List[Dict[str, Any]]) -> List[TaskStep]:
        """Generate specific steps for a given task type."""
        steps = []
        
        # Create a mapping of tool names to tool info
        tool_map = {tool['name']: tool for tool in available_tools}
        
        if task_type == "deployment":
            steps = self._generate_deployment_steps(query, tool_map)
        elif task_type == "development":
            steps = self._generate_development_steps(query, tool_map)
        elif task_type == "monitoring":
            steps = self._generate_monitoring_steps(query, tool_map)
        elif task_type == "data_processing":
            steps = self._generate_data_processing_steps(query, tool_map)
        elif task_type == "system_administration":
            steps = self._generate_system_admin_steps(query, tool_map)
        else:
            steps = self._generate_general_steps(query, tool_map)
        
        return steps
    
    def _generate_deployment_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate steps for deployment tasks."""
        steps = []
        
        # Step 1: Check system information
        if "remote_execute_command" in tool_map:
            steps.append(TaskStep(
                description="Check system information and available resources",
                tool_name="remote_execute_command",
                parameters={"command": "uname -a && df -h && free -h"}
            ))
        
        # Step 2: Check current directory structure
        if "remote_list_directory" in tool_map:
            steps.append(TaskStep(
                description="Analyze current directory structure",
                tool_name="remote_list_directory",
                parameters={"path": "."}
            ))
        
        # Step 3: Create deployment todos
        if "monitoring_create_todos" in tool_map:
            deployment_todos = [
                "Prepare deployment environment",
                "Build application if needed",
                "Configure deployment settings",
                "Deploy application",
                "Verify deployment success",
                "Set up monitoring and logging"
            ]
            steps.append(TaskStep(
                description="Create comprehensive deployment todo list",
                tool_name="monitoring_create_todos",
                parameters={"todos": deployment_todos}
            ))
        
        return steps
    
    def _generate_development_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate steps for development tasks."""
        steps = []
        
        # Check if this is a Flask application creation task
        query_lower = query.lower()
        is_flask_task = any(keyword in query_lower for keyword in ["flask", "web application", "web app", "app.py"])
        
        if is_flask_task:
            # Generate specific Flask application steps
            steps = self._generate_flask_application_steps(query, tool_map)
        else:
            # Generate generic development steps
            steps = self._generate_generic_development_steps(query, tool_map)
        
        return steps
    
    def _generate_flask_application_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate specific steps for Flask application creation."""
        steps = []
        
        # Step 1: Check if Python and pip are available
        if "remote_execute_command" in tool_map:
            steps.append(TaskStep(
                description="Check Python and pip availability",
                tool_name="remote_execute_command",
                parameters={"command": "python3 --version && pip3 --version"}
            ))
        
        # Step 2: Create project directory
        if "remote_execute_command" in tool_map:
            steps.append(TaskStep(
                description="Create Flask project directory",
                tool_name="remote_execute_command",
                parameters={"command": "mkdir -p hello_flask && cd hello_flask && pwd"}
            ))
        
        # Step 3: Create requirements.txt
        if "remote_write_file" in tool_map:
            steps.append(TaskStep(
                description="Create requirements.txt with Flask dependency",
                tool_name="remote_write_file",
                parameters={"filename": "hello_flask/requirements.txt", "content": "Flask==2.3.3\n"}
            ))
        
        # Step 4: Create Flask app.py
        if "remote_write_file" in tool_map:
            flask_app_content = '''from flask import Flask
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return f"Hello Flask! Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
'''
            steps.append(TaskStep(
                description="Create Flask application file",
                tool_name="remote_write_file",
                parameters={"filename": "hello_flask/app.py", "content": flask_app_content}
            ))
        
        # Step 5: Create startup script
        if "remote_write_file" in tool_map:
            run_script_content = '''#!/bin/bash
cd hello_flask
pip3 install -r requirements.txt
python3 app.py
'''
            steps.append(TaskStep(
                description="Create startup script",
                tool_name="remote_write_file",
                parameters={"filename": "hello_flask/run.py", "content": run_script_content}
            ))
        
        # Step 6: Test Flask application startup
        if "remote_execute_command" in tool_map:
            steps.append(TaskStep(
                description="Test Flask application startup (timeout after 5 seconds)",
                tool_name="remote_execute_command",
                parameters={"command": "cd hello_flask && timeout 5 python3 app.py || echo 'Flask app test completed'"}
            ))
        
        return steps
    
    def _generate_generic_development_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate generic development steps."""
        steps = []
        
        # Step 1: Check current project structure
        if "remote_list_directory" in tool_map:
            steps.append(TaskStep(
                description="Analyze current project structure",
                tool_name="remote_list_directory",
                parameters={"path": "."}
            ))
        
        # Step 2: Create development todos
        if "monitoring_create_todos" in tool_map:
            dev_todos = [
                "Set up development environment",
                "Install required dependencies",
                "Configure development tools",
                "Create initial project structure",
                "Set up version control",
                "Configure testing framework",
                "Set up development database"
            ]
            steps.append(TaskStep(
                description="Create development setup todo list",
                tool_name="monitoring_create_todos",
                parameters={"todos": dev_todos}
            ))
        
        return steps
    
    def _generate_monitoring_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate steps for monitoring tasks."""
        steps = []
        
        # Step 1: Check system status
        if "remote_execute_command" in tool_map:
            steps.append(TaskStep(
                description="Check current system status and performance",
                tool_name="remote_execute_command",
                parameters={"command": "top -bn1 && ps aux | head -10"}
            ))
        
        # Step 2: Create monitoring todos
        if "monitoring_create_todos" in tool_map:
            monitoring_todos = [
                "Set up system monitoring tools",
                "Configure performance metrics collection",
                "Set up alerting and notifications",
                "Configure log aggregation",
                "Set up dashboard for monitoring",
                "Create monitoring documentation"
            ]
            steps.append(TaskStep(
                description="Create monitoring setup todo list",
                tool_name="monitoring_create_todos",
                parameters={"todos": monitoring_todos}
            ))
        
        return steps
    
    def _generate_data_processing_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate steps for data processing tasks."""
        steps = []
        
        # Step 1: Check data directory
        if "remote_list_directory" in tool_map:
            steps.append(TaskStep(
                description="Analyze data directory structure",
                tool_name="remote_list_directory",
                parameters={"path": "."}
            ))
        
        # Step 2: Create data processing todos
        if "monitoring_create_todos" in tool_map:
            data_todos = [
                "Analyze data structure and format",
                "Set up data processing pipeline",
                "Configure data validation rules",
                "Set up data transformation processes",
                "Configure data storage and backup",
                "Set up data quality monitoring",
                "Create data processing documentation"
            ]
            steps.append(TaskStep(
                description="Create data processing todo list",
                tool_name="monitoring_create_todos",
                parameters={"todos": data_todos}
            ))
        
        return steps
    
    def _generate_system_admin_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate steps for system administration tasks."""
        steps = []
        
        # Step 1: Check system information
        if "execute_command" in tool_map:
            steps.append(TaskStep(
                description="Gather system information and status",
                tool_name="execute_command",
                parameters={"command": "uname -a && cat /etc/os-release && systemctl status"}
            ))
        
        # Step 2: Create system admin todos
        if "create_todos" in tool_map:
            admin_todos = [
                "Analyze current system configuration",
                "Identify system requirements",
                "Plan system changes and updates",
                "Backup current system state",
                "Implement system changes",
                "Verify system functionality",
                "Update system documentation"
            ]
            steps.append(TaskStep(
                description="Create system administration todo list",
                tool_name="create_todos",
                parameters={"todos": admin_todos}
            ))
        
        return steps
    
    def _generate_general_steps(self, query: str, tool_map: Dict[str, Any]) -> List[TaskStep]:
        """Generate general steps for complex tasks."""
        steps = []
        
        # Step 1: Analyze current state
        if "remote_list_directory" in tool_map:
            steps.append(TaskStep(
                description="Analyze current environment and context",
                tool_name="remote_list_directory",
                parameters={"path": ".", "recursive": False}
            ))
        
        # Step 2: Create general planning todos
        if "monitoring_create_todos" in tool_map:
            general_todos = [
                "Analyze task requirements",
                "Plan task execution steps",
                "Identify required resources",
                "Set up task execution environment",
                "Execute task steps",
                "Verify task completion",
                "Document task results"
            ]
            steps.append(TaskStep(
                description="Create task planning todo list",
                tool_name="monitoring_create_todos",
                parameters={"todos": general_todos}
            ))
        
        return steps
    
    def enhance_system_prompt(self, base_prompt: str) -> str:
        """Enhance the system prompt with intelligent task planning instructions."""
        planning_instructions = """

INTELLIGENT TASK PLANNING:
For complex tasks involving multiple steps (deployment, development, monitoring, data processing, system administration), you MUST:

1. AUTOMATICALLY DETECT complex tasks that require multiple steps
2. USE the create_todos tool to create a comprehensive plan
3. BREAK DOWN complex tasks into manageable steps
4. PROVIDE clear execution guidance

COMPLEX TASK INDICATORS:
- Tasks with words like: deploy, setup, configure, install, build, test, monitor
- Tasks mentioning multiple steps, phases, or stages
- Tasks involving system administration, development, or data processing
- Tasks that require planning or coordination

EXECUTION STRATEGY:
1. For complex tasks: First create a todo list with all required steps
2. For simple tasks: Execute directly with appropriate tools
3. Always provide clear next steps and guidance

EXAMPLE COMPLEX TASK HANDLING:
User: "Deploy a web application"
Response: 
FUNCTION_CALL: create_todos(todos=["Check system requirements", "Set up deployment environment", "Build application", "Configure web server", "Deploy application", "Verify deployment", "Set up monitoring"])

Then provide guidance on executing each step.
"""
        
        return base_prompt + planning_instructions
