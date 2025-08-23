"""
Monitoring MCP Server Implementation

Provides task tracking, progress monitoring, and agent memory management
to help agents maintain context across complex multi-step workflows.
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from ..base.server import AIShowmakerMCPServer, MCPTool


class TaskStatus(Enum):
    """Task status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TodoItem:
    """Individual todo list item."""
    id: str
    content: str
    status: TaskStatus
    active_form: str
    created_at: str
    updated_at: str
    notes: str = ""
    estimated_duration: Optional[int] = None  # seconds
    actual_duration: Optional[int] = None     # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        """Create from dictionary."""
        data['status'] = TaskStatus(data['status'])
        return cls(**data)


class AgentContext:
    """Maintains agent context and session information."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now().isoformat()
        self.last_activity = self.created_at
        self.todo_items: Dict[str, TodoItem] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.metrics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'avg_task_duration': 0.0
        }
    
    def add_todo(self, todo_item: TodoItem) -> None:
        """Add a todo item."""
        self.todo_items[todo_item.id] = todo_item
        self.metrics['total_tasks'] += 1
        self.last_activity = datetime.now().isoformat()
    
    def update_todo(self, todo_id: str, **kwargs) -> bool:
        """Update a todo item."""
        if todo_id not in self.todo_items:
            return False
        
        todo = self.todo_items[todo_id]
        old_status = todo.status
        
        for key, value in kwargs.items():
            if key == 'status' and isinstance(value, str):
                value = TaskStatus(value)
            setattr(todo, key, value)
        
        todo.updated_at = datetime.now().isoformat()
        self.last_activity = todo.updated_at
        
        # Update metrics if status changed
        if old_status != todo.status:
            if todo.status == TaskStatus.COMPLETED:
                self.metrics['completed_tasks'] += 1
            elif todo.status == TaskStatus.FAILED:
                self.metrics['failed_tasks'] += 1
        
        return True
    
    def get_active_todos(self) -> List[TodoItem]:
        """Get all active (non-completed) todo items."""
        return [
            todo for todo in self.todo_items.values() 
            if todo.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get context summary."""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'total_todos': len(self.todo_items),
            'active_todos': len(self.get_active_todos()),
            'metrics': self.metrics
        }


class MonitoringMCPServer(AIShowmakerMCPServer):
    """MCP Server for task monitoring and agent context management."""
    
    def __init__(self):
        super().__init__(
            name="monitoring",
            version="2.0.0",
            description="Task tracking and agent context management server"
        )
        self.contexts: Dict[str, AgentContext] = {}
        self.current_session_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """Initialize the monitoring server and register tools."""
        
        # Session Management
        create_session_tool = MCPTool(
            name="create_session",
            description="Create a new agent session for task tracking",
            parameters={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name for the session",
                        "default": "default"
                    }
                }
            },
            execute_func=self._create_session,
            category="session",
            timeout=5
        )
        self.register_tool(create_session_tool)
        
        # Todo Management
        create_todos_tool = MCPTool(
            name="create_todos",
            description="CRITICAL: ALWAYS use this for ANY multi-step task (2+ steps). Create todo list to track progress and ensure nothing is missed. Required for: building apps, creating scripts, deploying services, setting up environments. Input: JSON with 'todos' array or simple string array.",
            parameters={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "List of todo items. Can be strings or objects with content/status/activeForm",
                        "items": {
                            "oneOf": [
                                {"type": "string", "description": "Simple task description"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string", "description": "Task description"},
                                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"], "description": "Task status", "default": "pending"},
                                        "activeForm": {"type": "string", "description": "Present continuous form of the task"}
                                    },
                                    "required": ["content"]
                                }
                            ]
                        }
                    }
                },
                "required": ["todos"]
            },
            execute_func=self._create_todos,
            category="todos",
            timeout=10
        )
        self.register_tool(create_todos_tool)
        
        update_todo_tool = MCPTool(
            name="update_todo_status", 
            description="REQUIRED: Update todo item status as you complete each step. ALWAYS call this when finishing a todo item to track progress properly.",
            parameters={
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "string",
                        "description": "ID of the todo item to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "failed"],
                        "description": "New status for the todo item"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the status change",
                        "default": ""
                    }
                },
                "required": ["todo_id", "status"]
            },
            execute_func=self._update_todo_status,
            category="todos",
            timeout=5
        )
        self.register_tool(update_todo_tool)
        
        get_todos_tool = MCPTool(
            name="get_current_todos",
            description="Get current todo list to check progress. Use this when user asks about status or when you need to see what's left to do.",
            parameters={
                "type": "object",
                "properties": {
                    "include_completed": {
                        "type": "boolean",
                        "description": "Include completed tasks in the list",
                        "default": False
                    }
                }
            },
            execute_func=self._get_current_todos,
            category="todos",
            timeout=5
        )
        self.register_tool(get_todos_tool)
        
        clear_todos_tool = MCPTool(
            name="clear_todos",
            description="Clear all todo items (use when starting a new task)",
            parameters={
                "type": "object",
                "properties": {}
            },
            execute_func=self._clear_todos,
            category="todos",
            timeout=5
        )
        self.register_tool(clear_todos_tool)
        
        # Progress Reporting
        get_progress_tool = MCPTool(
            name="get_progress_summary",
            description="Get overall progress summary for current session",
            parameters={
                "type": "object",
                "properties": {}
            },
            execute_func=self._get_progress_summary,
            category="progress",
            timeout=5
        )
        self.register_tool(get_progress_tool)
        
        self.logger.info(f"Monitoring MCP Server initialized with {len(self.tools)} tools")
    
    def _get_current_context(self) -> AgentContext:
        """Get or create current agent context."""
        if not self.current_session_id:
            # Create default session
            session_id = f"session_{int(time.time())}"
            self.contexts[session_id] = AgentContext(session_id)
            self.current_session_id = session_id
        
        return self.contexts[self.current_session_id]
    
    async def _create_session(self, session_name: str = "default") -> str:
        """Create a new agent session."""
        session_id = f"{session_name}_{int(time.time())}"
        self.contexts[session_id] = AgentContext(session_id)
        self.current_session_id = session_id
        
        self.logger.info(f"Created new session: {session_id}")
        return f"Created session '{session_id}'. Agent will now track progress and maintain context."
    
    async def _create_todos(self, todos: List[Any]) -> str:
        """Create todo list from provided items."""
        context = self._get_current_context()
        
        # Clear existing todos
        context.todo_items.clear()
        
        created_todos = []
        for i, todo_item_input in enumerate(todos):
            todo_id = f"todo_{i+1}"
            
            # Handle different input formats
            if isinstance(todo_item_input, str):
                # Simple string input
                content = todo_item_input
                status = TaskStatus.PENDING
                active_form = f"Working on {content.lower()}"
            elif isinstance(todo_item_input, dict):
                # Dictionary input
                content = todo_item_input.get('content', '')
                if not content:
                    self.logger.warning(f"Skipping todo item {i+1}: missing content")
                    continue
                    
                status_str = todo_item_input.get('status', 'pending')
                try:
                    status = TaskStatus(status_str)
                except ValueError:
                    self.logger.warning(f"Invalid status '{status_str}' for todo {i+1}, using 'pending'")
                    status = TaskStatus.PENDING
                
                active_form = todo_item_input.get('activeForm', f"Working on {content.lower()}")
            else:
                self.logger.warning(f"Skipping todo item {i+1}: unsupported format {type(todo_item_input)}")
                continue
            
            todo_item = TodoItem(
                id=todo_id,
                content=content,
                status=status,
                active_form=active_form,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            context.add_todo(todo_item)
            created_todos.append(f"{todo_id}: {todo_item.content} [{todo_item.status.value}]")
        
        if not created_todos:
            return "No valid todo items were created. Please provide todos as strings or objects with 'content' field."
        
        result = f"Created {len(created_todos)} todo items:\n" + "\n".join(created_todos)
        self.logger.info(f"Created {len(created_todos)} todos for session {context.session_id}")
        
        return result
    
    async def _update_todo_status(self, todo_id: str, status: str, notes: str = "") -> str:
        """Update todo item status."""
        context = self._get_current_context()
        
        if context.update_todo(todo_id, status=status, notes=notes):
            todo = context.todo_items[todo_id]
            result = f"Updated {todo_id}: {todo.content} -> {status}"
            if notes:
                result += f" (Notes: {notes})"
            
            self.logger.info(f"Updated todo {todo_id} to {status}")
            return result
        else:
            return f"Todo item '{todo_id}' not found"
    
    async def _get_current_todos(self, include_completed: bool = False) -> str:
        """Get current todo list."""
        context = self._get_current_context()
        
        if not context.todo_items:
            return "No todo items in current session. Use create_todos to start tracking tasks."
        
        todos = list(context.todo_items.values())
        if not include_completed:
            todos = [t for t in todos if t.status != TaskStatus.COMPLETED]
        
        if not todos:
            return "All tasks completed! 🎉"
        
        todo_lines = []
        for todo in todos:
            status_emoji = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄", 
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫"
            }
            
            emoji = status_emoji.get(todo.status, "❓")
            line = f"{emoji} {todo.id}: {todo.content}"
            if todo.notes:
                line += f" (Notes: {todo.notes})"
            todo_lines.append(line)
        
        return "Current Todo List:\n" + "\n".join(todo_lines)
    
    async def _clear_todos(self) -> str:
        """Clear all todo items."""
        context = self._get_current_context()
        count = len(context.todo_items)
        context.todo_items.clear()
        context.metrics['total_tasks'] = 0
        context.metrics['completed_tasks'] = 0
        context.metrics['failed_tasks'] = 0
        
        return f"Cleared {count} todo items. Ready for new tasks."
    
    async def _get_progress_summary(self) -> str:
        """Get progress summary for current session."""
        context = self._get_current_context()
        summary = context.get_summary()
        
        active_todos = context.get_active_todos()
        completed = context.metrics['completed_tasks']
        total = context.metrics['total_tasks']
        
        if total == 0:
            return "No tasks tracked yet. Create todos to start tracking progress."
        
        progress_pct = (completed / total * 100) if total > 0 else 0
        
        result = f"""Progress Summary:
📊 Overall Progress: {completed}/{total} tasks ({progress_pct:.1f}%)
🔄 Active Tasks: {len(active_todos)}
⏱️  Session Duration: {self._format_duration(summary['created_at'])}
📈 Success Rate: {((completed / total) * 100):.1f}%"""

        if active_todos:
            result += "\n\n🎯 Next Active Tasks:"
            for todo in active_todos[:3]:  # Show next 3 tasks
                result += f"\n  • {todo.content}"
        
        return result
    
    def _format_duration(self, start_time: str) -> str:
        """Format duration since start time."""
        start = datetime.fromisoformat(start_time)
        duration = datetime.now() - start
        
        if duration.days > 0:
            return f"{duration.days}d {duration.seconds//3600}h"
        elif duration.seconds > 3600:
            return f"{duration.seconds//3600}h {(duration.seconds%3600)//60}m"
        else:
            return f"{duration.seconds//60}m {duration.seconds%60}s"
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring server."""
        self.logger.info(f"Monitoring MCP Server shutting down. Tracked {len(self.contexts)} sessions.")