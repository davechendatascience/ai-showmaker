"""
Plugin Security Validator

Provides security validation for MCP server plugins before they are loaded.
"""

import ast
import logging
from typing import List, Set, Tuple
from pathlib import Path


class PluginValidator:
    """
    Validates MCP server plugins for security and compatibility.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("mcp_zero.validator")
        
        # Dangerous imports that are not allowed
        self.dangerous_imports = {
            'os', 'subprocess', 'sys', 'eval', 'exec', 'compile',
            'open', 'file', 'input', 'raw_input', 'globals', 'locals',
            'vars', 'dir', 'getattr', 'setattr', 'delattr'
        }
        
        # Dangerous AST nodes that are truly dangerous
        self.dangerous_nodes = {
            'Exec', 'Lambda', 'Yield', 'YieldFrom'
            # Removed: 'AsyncFunctionDef', 'AsyncFor', 'AsyncWith', 'Call'
            # These are legitimate for MCP servers
        }
        
        # Allowed patterns for MCP servers
        self.allowed_patterns = {
            'async def', 'await', 'class', 'def', 'self.',
            'register_tool', 'AIShowmakerMCPServer', 'MCPTool'
        }
        
    async def validate_plugin(self, plugin_path) -> Tuple[bool, List[str]]:
        """
        Validate a plugin file for security and compatibility.
        
        Args:
            plugin_path: Path to the plugin file (string or Path object)
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # Convert to Path object if it's a string
            if isinstance(plugin_path, str):
                plugin_path = Path(plugin_path)
            elif not isinstance(plugin_path, Path):
                return False, [f"Invalid plugin_path type: {type(plugin_path)}"]
                
            # Read the plugin code
            with open(plugin_path, 'r', encoding='utf-8') as f:
                plugin_code = f.read()
                
            errors = []
            
            # 1. Basic syntax validation
            if not await self._validate_syntax(plugin_code):
                errors.append("Invalid Python syntax")
                
            # 2. Import validation
            import_errors = await self._validate_imports(plugin_code)
            errors.extend(import_errors)
            
            # 3. AST validation (less restrictive)
            ast_errors = await self._validate_ast(plugin_code)
            errors.extend(ast_errors)
            
            # 4. Content validation
            content_errors = await self._validate_content(plugin_code)
            errors.extend(content_errors)
            
            # 5. MCP server pattern validation
            mcp_errors = await self._validate_mcp_patterns(plugin_code)
            errors.extend(mcp_errors)
            
            is_valid = len(errors) == 0
            
            if is_valid:
                self.logger.info(f"Plugin {plugin_path.name} passed validation")
            else:
                self.logger.warning(f"Plugin {plugin_path.name} failed validation: {errors}")
                
            return is_valid, errors
            
        except Exception as e:
            self.logger.error(f"Error validating plugin {plugin_path}: {e}")
            return False, [f"Validation error: {str(e)}"]
            
    async def _validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
            
    async def _validate_imports(self, code: str) -> List[str]:
        """Validate imports for dangerous modules."""
        errors = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.dangerous_imports:
                            errors.append(f"Dangerous import: {alias.name}")
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.dangerous_imports:
                        errors.append(f"Dangerous import from: {node.module}")
                        
        except Exception as e:
            errors.append(f"Import validation error: {str(e)}")
            
        return errors
        
    async def _validate_ast(self, code: str) -> List[str]:
        """Validate AST for dangerous patterns (less restrictive)."""
        errors = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                node_type = type(node).__name__
                
                # Only block truly dangerous nodes
                if node_type in self.dangerous_nodes:
                    errors.append(f"Dangerous AST node: {node_type}")
                    
                # Check for dangerous function calls to blocked imports
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.dangerous_imports:
                            errors.append(f"Dangerous function call: {node.func.id}")
                            
        except Exception as e:
            errors.append(f"AST validation error: {str(e)}")
            
        return errors
        
    async def _validate_content(self, code: str) -> List[str]:
        """Validate content for suspicious patterns."""
        errors = []
        
        # Check for suspicious strings
        suspicious_patterns = [
            'eval(', 'exec(', 'compile(', 'os.system(',
            'subprocess.call(', 'subprocess.Popen(',
            '__import__', 'globals()', 'locals()'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in code:
                errors.append(f"Suspicious pattern found: {pattern}")
                
        return errors
        
    async def _validate_mcp_patterns(self, code: str) -> List[str]:
        """Validate that the plugin follows MCP server patterns."""
        errors = []
        
        # Check for required MCP server patterns
        has_mcp_server = False
        has_register_tool = False
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check for class definitions
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits from AIShowmakerMCPServer
                    for base in node.bases:
                        if isinstance(base, ast.Name) and 'MCPServer' in base.id:
                            has_mcp_server = True
                        elif isinstance(base, ast.Attribute) and 'MCPServer' in base.attr:
                            has_mcp_server = True
                            
                # Check for register_tool calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == 'register_tool':
                            has_register_tool = True
                            
        except Exception as e:
            # If we can't parse, just check for string patterns
            if 'AIShowmakerMCPServer' in code:
                has_mcp_server = True
            if 'register_tool' in code:
                has_register_tool = True
                
        # Warn if missing required patterns (but don't fail validation)
        if not has_mcp_server:
            self.logger.warning("Plugin doesn't appear to inherit from AIShowmakerMCPServer")
            
        if not has_register_tool:
            self.logger.warning("Plugin doesn't appear to register tools")
            
        return errors
        
    def get_validation_info(self) -> dict:
        """Get information about the validation system."""
        return {
            'dangerous_imports': list(self.dangerous_imports),
            'dangerous_nodes': list(self.dangerous_nodes),
            'allowed_patterns': list(self.allowed_patterns),
            'validation_methods': [
                'syntax_validation',
                'import_validation', 
                'ast_validation',
                'content_validation',
                'mcp_pattern_validation'
            ]
        }
