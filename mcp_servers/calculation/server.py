"""
Calculation MCP Server Implementation

Provides secure mathematical computation tools using AST-based evaluation
instead of unsafe eval() operations.
"""

import math
import ast
import operator
import re
from typing import Any, Dict, Union
from pathlib import Path

from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool


class SafeCalculator:
    """A safe calculator that supports mathematical operations without eval()."""
    
    def __init__(self):
        # Allowed operators
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        # Mathematical functions from math module
        self.functions = {
            'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan, 'atan2': math.atan2,
            'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
            'exp': math.exp, 'log': math.log, 'log10': math.log10, 'log2': math.log2,
            'sqrt': math.sqrt, 'pow': pow, 'ceil': math.ceil, 'floor': math.floor,
            'factorial': math.factorial, 'gcd': math.gcd, 'lcm': math.lcm,
            'degrees': math.degrees, 'radians': math.radians,
            'fabs': math.fabs, 'fmod': math.fmod, 'frexp': math.frexp,
            'ldexp': math.ldexp, 'modf': math.modf, 'trunc': math.trunc,
        }
        
        # Mathematical constants
        self.constants = {
            'pi': math.pi, 'e': math.e, 'tau': math.tau, 'inf': math.inf, 'nan': math.nan
        }
        
        # Variables storage for multi-step calculations
        self.variables = {}
    
    def _safe_eval(self, node: ast.AST) -> Any:
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):  # Numbers, strings
            return node.value
        elif isinstance(node, ast.Name):  # Variables or constants
            if node.id in self.constants:
                return self.constants[node.id]
            elif node.id in self.variables:
                return self.variables[node.id]
            else:
                raise ValueError(f"Undefined variable: {node.id}")
        elif isinstance(node, ast.BinOp):  # Binary operations
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            op = self.operators.get(type(node.op))
            if op:
                return op(left, right)
            else:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):  # Unary operations
            operand = self._safe_eval(node.operand)
            op = self.operators.get(type(node.op))
            if op:
                return op(operand)
            else:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        elif isinstance(node, ast.Call):  # Function calls
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name in self.functions:
                args = [self._safe_eval(arg) for arg in node.args]
                return self.functions[func_name](*args)
            else:
                raise ValueError(f"Unsupported function: {func_name}")
        elif isinstance(node, ast.List):  # Lists for functions like min, max, sum
            return [self._safe_eval(item) for item in node.elts]
        elif isinstance(node, ast.Compare):  # Comparisons (for conditional logic)
            left = self._safe_eval(node.left)
            results = []
            for i, (op, right) in enumerate(zip(node.ops, node.comparators)):
                right_val = self._safe_eval(right)
                if isinstance(op, ast.Eq):
                    results.append(left == right_val)
                elif isinstance(op, ast.NotEq):
                    results.append(left != right_val)
                elif isinstance(op, ast.Lt):
                    results.append(left < right_val)
                elif isinstance(op, ast.LtE):
                    results.append(left <= right_val)
                elif isinstance(op, ast.Gt):
                    results.append(left > right_val)
                elif isinstance(op, ast.GtE):
                    results.append(left >= right_val)
                else:
                    raise ValueError(f"Unsupported comparison: {type(op)}")
                left = right_val  # For chained comparisons
            return all(results)
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")
    
    def calculate(self, expression: str) -> str:
        """Calculate the result of a mathematical expression."""
        try:
            # Handle variable assignments (e.g., "x = 5")
            if '=' in expression and not any(op in expression for op in ['==', '!=', '<=', '>=']):
                var_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)', expression.strip())
                if var_match:
                    var_name, var_expr = var_match.groups()
                    result = self.calculate(var_expr)
                    self.variables[var_name] = float(result) if '.' in result else int(result)
                    return f"{var_name} = {result}"
            
            # Parse the expression into an AST
            tree = ast.parse(expression, mode='eval')
            result = self._safe_eval(tree.body)
            
            # Format the result
            if isinstance(result, float):
                if result.is_integer():
                    return str(int(result))
                else:
                    return f"{result:.10g}"  # Remove trailing zeros
            elif isinstance(result, bool):
                return str(result).lower()
            else:
                return str(result)
                
        except ZeroDivisionError:
            return "Error: Division by zero"
        except ValueError as e:
            return f"Error: {str(e)}"
        except SyntaxError:
            return "Error: Invalid mathematical expression"
        except Exception as e:
            return f"Error: {str(e)}"


class CalculationMCPServer(AIShowmakerMCPServer):
    """MCP Server for mathematical calculations and computations."""
    
    def __init__(self):
        super().__init__(
            name="calculation",
            version="2.0.0",
            description="Advanced mathematical computation server with secure evaluation"
        )
        self.calculator = SafeCalculator()
    
    async def initialize(self) -> None:
        """Initialize the calculation server and register tools."""
        # Register the main calculation tool
        calculate_tool = MCPTool(
            name="calculate",
            description="Perform safe mathematical calculations including arithmetic, trigonometry, logarithms, factorials, variables, and complex expressions",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sin(pi/2)', 'x = 5')"
                    }
                },
                "required": ["expression"]
            },
            execute_func=self._calculate,
            category="mathematics",
            timeout=10
        )
        self.register_tool(calculate_tool)
        
        # Register variable management tools
        set_variable_tool = MCPTool(
            name="set_variable",
            description="Set a variable for use in calculations",
            parameters={
                "type": "object", 
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Variable name"
                    },
                    "value": {
                        "type": "number", 
                        "description": "Variable value"
                    }
                },
                "required": ["name", "value"]
            },
            execute_func=self._set_variable,
            category="variables",
            timeout=5
        )
        self.register_tool(set_variable_tool)
        
        get_variables_tool = MCPTool(
            name="get_variables",
            description="Get all currently defined variables",
            parameters={
                "type": "object",
                "properties": {}
            },
            execute_func=self._get_variables,
            category="variables", 
            timeout=5
        )
        self.register_tool(get_variables_tool)
        
        clear_variables_tool = MCPTool(
            name="clear_variables",
            description="Clear all variables from memory",
            parameters={
                "type": "object",
                "properties": {}
            },
            execute_func=self._clear_variables,
            category="variables",
            timeout=5
        )
        self.register_tool(clear_variables_tool)
        
        self.logger.info(f"Calculation MCP Server initialized with {len(self.tools)} tools")
    
    async def _calculate(self, expression: str) -> str:
        """Execute a mathematical calculation."""
        result = self.calculator.calculate(expression)
        self.logger.info(f"Calculated: {expression} = {result}")
        return result
    
    async def _set_variable(self, name: str, value: float) -> str:
        """Set a variable value."""
        self.calculator.variables[name] = value
        return f"Variable '{name}' set to {value}"
    
    async def _get_variables(self) -> Dict[str, float]:
        """Get all currently defined variables."""
        return self.calculator.variables.copy()
    
    async def _clear_variables(self) -> str:
        """Clear all variables."""
        count = len(self.calculator.variables)
        self.calculator.variables.clear()
        return f"Cleared {count} variables"
    
    async def shutdown(self) -> None:
        """Shutdown the calculation server."""
        self.logger.info("Calculation MCP Server shutting down")
        self.calculator.variables.clear()