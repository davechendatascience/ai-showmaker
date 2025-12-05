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
import os
from pathlib import Path


class TaskStatus(Enum):
    """Task status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NOT_APPLICABLE = "not_applicable"


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
        self.error_log: List[Dict[str, Any]] = []
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
            if todo.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.NOT_APPLICABLE]
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get context summary."""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'total_todos': len(self.todo_items),
            'active_todos': len(self.get_active_todos()),
            'error_count': len(self.error_log),
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
        # Simple on-disk persistence so todos can survive process restarts (opt-in)
        self.state_path = Path(os.environ.get("MONITORING_STATE_PATH", "monitoring_state.json"))
        self.persist = str(os.environ.get("MONITORING_PERSIST", "0")).lower() in ("1", "true", "yes")
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
            description="Create todo list. Call as: create_todos(todos=['Plan project', 'Write code', 'Test app']) - always use a simple array of strings",
            parameters={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "Array of task strings like ['Plan architecture', 'Write code', 'Deploy app']",
                        "items": {
                            "type": "string",
                            "description": "Task description as simple string"
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
            description="Update todo status. Call as: update_todo_status(todo_id='todo_1', status='completed') or update_todo_status(todo_id='todo_2', status='in_progress')",
            parameters={
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "string",
                        "description": "Todo ID like 'todo_1', 'todo_2', 'todo_3'"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "failed", "cancelled", "not_applicable"],
                        "description": "Status: 'pending', 'in_progress', 'completed', 'failed', 'cancelled', or 'not_applicable'"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes (not required)",
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

        # Todo management extensions: add/update/remove
        add_todo_tool = MCPTool(
            name="add_todo",
            description="Append a new todo item (agent-designed). Provide 'content' and optional 'status' and 'notes'",
            parameters={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Todo content"},
                    "status": {"type": "string", "description": "pending|in_progress|completed|failed", "default": "pending"},
                    "notes": {"type": "string", "description": "Optional notes", "default": ""}
                },
                "required": ["content"]
            },
            execute_func=self._add_todo,
            category="todos",
            timeout=5
        )
        self.register_tool(add_todo_tool)

        update_todo_tool2 = MCPTool(
            name="update_todo",
            description="Update a todo's content/status/notes by id",
            parameters={
                "type": "object",
                "properties": {
                    "todo_id": {"type": "string", "description": "Todo id like 'todo_2'"},
                    "content": {"type": "string", "description": "New content", "default": None},
                    "status": {"type": "string", "description": "pending|in_progress|completed|failed|cancelled|not_applicable", "default": None},
                    "notes": {"type": "string", "description": "Notes", "default": None}
                },
                "required": ["todo_id"]
            },
            execute_func=self._update_todo,
            category="todos",
            timeout=5
        )
        self.register_tool(update_todo_tool2)

        # Advanced todo tools: reorder, bulk update, reset state
        reorder_tool = MCPTool(
            name="reorder_todos",
            description="Reorder todos by providing an array of todo IDs. Unlisted items keep their relative order after listed ones.",
            parameters={
                "type": "object",
                "properties": {
                    "order": {"type": "array", "items": {"type": "string"}, "description": "Desired order of todo IDs"}
                },
                "required": ["order"]
            },
            execute_func=self._reorder_todos,
            category="todos",
            timeout=5
        )
        self.register_tool(reorder_tool)

        bulk_update_tool = MCPTool(
            name="bulk_update_todos",
            description="Bulk update todos. Provide items: [{todo_id, status?, content?, notes?}]",
            parameters={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "todo_id": {"type": "string"},
                                "status": {"type": "string"},
                                "content": {"type": "string"},
                                "notes": {"type": "string"}
                            },
                            "required": ["todo_id"]
                        }
                    }
                },
                "required": ["items"]
            },
            execute_func=self._bulk_update_todos,
            category="todos",
            timeout=10
        )
        self.register_tool(bulk_update_tool)

        reset_state_tool = MCPTool(
            name="reset_monitoring_state",
            description="Reset monitoring: clear all sessions and delete persisted state.",
            parameters={"type": "object", "properties": {}},
            execute_func=self._reset_monitoring_state,
            category="maintenance",
            timeout=5
        )
        self.register_tool(reset_state_tool)

        remove_todo_tool = MCPTool(
            name="remove_todo",
            description="Remove a todo by id",
            parameters={
                "type": "object",
                "properties": {
                    "todo_id": {"type": "string", "description": "Todo id like 'todo_3'"}
                },
                "required": ["todo_id"]
            },
            execute_func=self._remove_todo,
            category="todos",
            timeout=5
        )
        self.register_tool(remove_todo_tool)

        # Error log tools
        append_error_tool = MCPTool(
            name="append_error_log",
            description="Append an entry to the session error log (non-blocking)",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Error message"},
                    "tool": {"type": "string", "description": "Related tool name", "default": ""}
                },
                "required": ["message"]
            },
            execute_func=self._append_error_log,
            category="errors",
            timeout=3
        )
        self.register_tool(append_error_tool)

        get_errors_tool = MCPTool(
            name="get_error_log",
            description="Get recent error log entries",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max entries", "default": 20}
                }
            },
            execute_func=self._get_error_log,
            category="errors",
            timeout=3
        )
        self.register_tool(get_errors_tool)

        clear_errors_tool = MCPTool(
            name="clear_error_log",
            description="Clear all error log entries for the current session",
            parameters={"type": "object", "properties": {}},
            execute_func=self._clear_error_log,
            category="errors",
            timeout=3
        )
        self.register_tool(clear_errors_tool)

        # Load persisted state only if persistence is enabled
        if self.persist:
            try:
                self._load_state()
            except Exception as e:
                self.logger.warning(f"Monitoring state load failed: {e}")
        else:
            # If persistence is disabled, ensure prior state file does not leak old todos
            try:
                if self.state_path.exists():
                    self.state_path.unlink()
            except Exception:
                pass

        self.logger.info(f"Monitoring MCP Server initialized with {len(self.tools)} tools")

    # --- Persistence helpers ---
    def _save_state(self) -> None:
        if not getattr(self, 'persist', False):
            return
        try:
            data = {
                'current_session_id': getattr(self, 'current_session_id', None),
                'contexts': {}
            }
            for sid, ctx in self.contexts.items():
                data['contexts'][sid] = {
                    'session_id': ctx.session_id,
                    'created_at': ctx.created_at,
                    'last_activity': ctx.last_activity,
                    'todo_items': { tid: item.to_dict() for tid, item in ctx.todo_items.items() },
                    'task_history': ctx.task_history,
                    'error_log': ctx.error_log,
                    'metrics': ctx.metrics
                }
            self.state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            self.logger.warning(f"Monitoring state save failed: {e}")

    def _load_state(self) -> None:
        try:
            if not self.state_path.exists():
                return
            raw = self.state_path.read_text(encoding='utf-8')
            parsed = json.loads(raw)
            self.current_session_id = parsed.get('current_session_id')
            self.contexts = {}
            for sid, c in parsed.get('contexts', {}).items():
                ctx = AgentContext(sid)
                ctx.created_at = c.get('created_at', ctx.created_at)
                ctx.last_activity = c.get('last_activity', ctx.last_activity)
                # Restore todo items
                todo_items = {}
                for tid, item in (c.get('todo_items') or {}).items():
                    try:
                        todo_items[tid] = TodoItem.from_dict(item)
                    except Exception:
                        continue
                ctx.todo_items = todo_items
                ctx.task_history = c.get('task_history', [])
                ctx.error_log = c.get('error_log', [])
                ctx.metrics = c.get('metrics', ctx.metrics)
                self.contexts[sid] = ctx
        except Exception as e:
            raise Exception(f"Failed to load state: {e}")
    
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
        # Persist creation
        try:
            self._save_state()
        except Exception:
            pass
        
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
        # Persist
        try:
            self._save_state()
        except Exception:
            pass
        
        return result

    async def _add_todo(self, content: str, status: str = "pending", notes: str = "") -> str:
        context = self._get_current_context()
        new_id = f"todo_{len(context.todo_items) + 1}"
        try:
            st = TaskStatus(status) if isinstance(status, str) else TaskStatus.PENDING
        except Exception:
            st = TaskStatus.PENDING
        todo_item = TodoItem(
            id=new_id,
            content=content,
            status=st,
            active_form=f"Working on {content.lower()}",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            notes=notes
        )
        context.add_todo(todo_item)
        try:
            self._save_state()
        except Exception:
            pass
        return f"Added {new_id}: {content} [{todo_item.status.value}]"

    async def _update_todo(self, todo_id: str, content: Optional[str] = None, status: Optional[str] = None, notes: Optional[str] = None) -> str:
        context = self._get_current_context()
        kwargs: Dict[str, Any] = {}
        if content is not None:
            kwargs['content'] = content
        if status is not None:
            # Accept known statuses plus aliases
            try:
                if status == 'not_applicable':
                    kwargs['status'] = TaskStatus.NOT_APPLICABLE.value
                else:
                    TaskStatus(status)  # validate
                    kwargs['status'] = status
            except Exception:
                pass
        if notes is not None:
            kwargs['notes'] = notes
        ok = context.update_todo(todo_id, **kwargs)
        if ok:
            try:
                self._save_state()
            except Exception:
                pass
        return f"Updated {todo_id}" if ok else f"Todo {todo_id} not found"

    async def _remove_todo(self, todo_id: str) -> str:
        context = self._get_current_context()
        if todo_id in context.todo_items:
            del context.todo_items[todo_id]
            try:
                self._save_state()
            except Exception:
                pass
            return f"Removed {todo_id}"
        return f"Todo {todo_id} not found"
    
    async def _update_todo_status(self, todo_id: str, status: str, notes: str = "") -> str:
        """Update todo item status."""
        context = self._get_current_context()
        
        # Map not_applicable alias
        if status == 'not_applicable':
            status = TaskStatus.NOT_APPLICABLE.value

        if context.update_todo(todo_id, status=status, notes=notes):
            todo = context.todo_items[todo_id]
            result = f"Updated {todo_id}: {todo.content} -> {status}"
            if notes:
                result += f" (Notes: {notes})"
            
            self.logger.info(f"Updated todo {todo_id} to {status}")
            try:
                self._save_state()
            except Exception:
                pass
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
            return "All tasks completed! ✅"
        
        todo_lines = []
        for todo in todos:
            status_emoji = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔧", 
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫"
            }
            
            emoji = status_emoji.get(todo.status, "•")
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
        try:
            self._save_state()
        except Exception:
            pass
        
        return f"Cleared {count} todo items. Ready for new tasks."

    async def _reorder_todos(self, order: List[str]) -> str:
        """Reorder todos by new id list, preserving any unlisted items after in original order."""
        context = self._get_current_context()
        current = context.todo_items
        new_map: Dict[str, TodoItem] = {}
        # Add listed ones in given order
        for tid in order:
            if tid in current and tid not in new_map:
                new_map[tid] = current[tid]
        # Append remaining in existing order
        for tid, item in current.items():
            if tid not in new_map:
                new_map[tid] = item
        context.todo_items = new_map
        try:
            self._save_state()
        except Exception:
            pass
        return "Reordered todos: " + ", ".join(new_map.keys())

    async def _bulk_update_todos(self, items: List[Dict[str, Any]]) -> str:
        """Bulk update todos with optional content/status/notes."""
        context = self._get_current_context()
        updated = 0
        for it in items or []:
            tid = it.get('todo_id')
            if not tid or tid not in context.todo_items:
                continue
            kwargs: Dict[str, Any] = {}
            if 'content' in it and it['content'] is not None:
                kwargs['content'] = str(it['content'])
            if 'status' in it and it['status'] is not None:
                s = str(it['status'])
                if s == 'not_applicable':
                    kwargs['status'] = TaskStatus.NOT_APPLICABLE.value
                else:
                    try:
                        TaskStatus(s)
                        kwargs['status'] = s
                    except Exception:
                        pass
            if 'notes' in it and it['notes'] is not None:
                kwargs['notes'] = str(it['notes'])
            if kwargs:
                if context.update_todo(tid, **kwargs):
                    updated += 1
        try:
            if updated:
                self._save_state()
        except Exception:
            pass
        return f"Bulk updated {updated} todos"

    async def _reset_monitoring_state(self) -> str:
        """Clear sessions and delete persisted monitoring state file."""
        self.contexts.clear()
        self.current_session_id = None
        try:
            if self.state_path.exists():
                self.state_path.unlink()
        except Exception:
            pass
        return "Monitoring state reset"

    async def _append_error_log(self, message: str, tool: str = "") -> str:
        context = self._get_current_context()
        entry = {
            'timestamp': datetime.now().isoformat(),
            'tool': tool,
            'message': message,
        }
        context.error_log.append(entry)
        context.last_activity = entry['timestamp']
        return f"Logged error: {message[:120]}"

    async def _get_error_log(self, limit: int = 20) -> str:
        context = self._get_current_context()
        items = context.error_log[-max(1, int(limit)):] if context.error_log else []
        if not items:
            return "No errors logged"
        lines = [f"[{e['timestamp']}] {e.get('tool') or 'tool'}: {e['message']}" for e in items]
        return "\n".join(lines)

    async def _clear_error_log(self) -> str:
        context = self._get_current_context()
        n = len(context.error_log)
        context.error_log.clear()
        return f"Cleared {n} error log entries"
    
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
?? Overall Progress: {completed}/{total} tasks ({progress_pct:.1f}%)
?? Active Tasks: {len(active_todos)}
?梧?  Session Duration: {self._format_duration(summary['created_at'])}
?? Success Rate: {((completed / total) * 100):.1f}%"""

        if active_todos:
            result += "\n\n? Next Active Tasks:"
            for todo in active_todos[:3]:  # Show next 3 tasks
                result += f"\n  ??{todo.content}"
        
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
