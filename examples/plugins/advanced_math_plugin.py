"""Advanced Math Plugin for MCP-Zero

This plugin provides advanced mathematical capabilities including:
- Complex mathematical operations
- Statistical functions
- Matrix operations
- Symbolic computation
- Mathematical constants and utilities
"""

import math
import statistics
import numpy as np
from typing import Dict, Any, List, Union, Optional
from mcp_servers.base.server import AIShowmakerMCPServer, MCPTool


class AdvancedMathPluginServer(AIShowmakerMCPServer):
    """
    Advanced mathematics plugin server with comprehensive mathematical tools.
    
    This server provides advanced mathematical capabilities that can be
    discovered and used dynamically by the MCP-Zero system.
    """
    
    def __init__(self):
        super().__init__(
            name="advanced_math",
            version="1.0.0",
            description="Advanced mathematics plugin with complex operations, statistics, and matrix functions"
        )
        
    async def initialize(self) -> None:
        """Initialize the advanced math plugin server."""
        # Register mathematical operation tools
        self.register_tool(MCPTool(
            name="math_advanced_calc",
            description="Advanced mathematical calculations with support for complex operations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to calculate (e.g., '2^3 + sqrt(16)', 'sin(pi/2)', 'log(100, 10)')"
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Decimal precision for the result",
                        "default": 6
                    }
                },
                "required": ["expression"]
            },
            execute_func=self.advanced_calculator,
            category="mathematics",
            version="1.0.0"
        ))
        
        # Statistical analysis tools
        self.register_tool(MCPTool(
            name="math_statistics",
            description="Comprehensive statistical analysis of numerical data",
            parameters={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Array of numerical data for statistical analysis"
                    },
                    "include_advanced": {
                        "type": "boolean",
                        "description": "Include advanced statistics (percentiles, skewness, kurtosis)",
                        "default": False
                    }
                },
                "required": ["data"]
            },
            execute_func=self.statistical_analysis,
            category="statistics",
            version="1.0.0"
        ))
        
        # Matrix operations
        self.register_tool(MCPTool(
            name="math_matrix_ops",
            description="Matrix operations including multiplication, determinant, inverse, and eigenvalues",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Matrix operation to perform",
                        "enum": ["multiply", "determinant", "inverse", "eigenvalues", "transpose", "rank"]
                    },
                    "matrix_a": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "First matrix (2D array of numbers)"
                    },
                    "matrix_b": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "Second matrix for binary operations (2D array of numbers)"
                    }
                },
                "required": ["operation", "matrix_a"]
            },
            execute_func=self.matrix_operations,
            category="linear_algebra",
            version="1.0.0"
        ))
        
        # Mathematical constants and utilities
        self.register_tool(MCPTool(
            name="math_constants",
            description="Get mathematical constants and their properties",
            parameters={
                "type": "object",
                "properties": {
                    "constant": {
                        "type": "string",
                        "description": "Mathematical constant to retrieve",
                        "enum": ["pi", "e", "golden_ratio", "euler_mascheroni", "catalan", "all"]
                    }
                },
                "required": ["constant"]
            },
            execute_func=self.get_mathematical_constants,
            category="mathematics",
            version="1.0.0"
        ))
        
        # Numerical integration
        self.register_tool(MCPTool(
            name="math_integrate",
            description="Numerical integration of mathematical functions",
            parameters={
                "type": "object",
                "properties": {
                    "function": {
                        "type": "string",
                        "description": "Mathematical function to integrate (e.g., 'x^2', 'sin(x)', 'exp(-x^2)')"
                    },
                    "lower_bound": {
                        "type": "number",
                        "description": "Lower bound of integration"
                    },
                    "upper_bound": {
                        "type": "number",
                        "description": "Upper bound of integration"
                    },
                    "method": {
                        "type": "string",
                        "description": "Integration method",
                        "enum": ["trapezoidal", "simpson", "adaptive"],
                        "default": "adaptive"
                    }
                },
                "required": ["function", "lower_bound", "upper_bound"]
            },
            execute_func=self.numerical_integration,
            category="calculus",
            version="1.0.0"
        ))
        
        # Prime number utilities
        self.register_tool(MCPTool(
            name="math_prime_utils",
            description="Prime number utilities including factorization, primality testing, and prime generation",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Prime number operation to perform",
                        "enum": ["is_prime", "factorize", "next_prime", "prime_factors", "prime_count"]
                    },
                    "number": {
                        "type": "integer",
                        "description": "Number to operate on"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit for operations like prime counting (optional)"
                    }
                },
                "required": ["operation", "number"]
            },
            execute_func=self.prime_number_utilities,
            category="number_theory",
            version="1.0.0"
        ))
        
        self.logger.info(f"Advanced math plugin initialized with {len(self.tools)} mathematical tools")
        
    async def shutdown(self) -> None:
        """Clean shutdown of the advanced math plugin server."""
        self.logger.info(f"Advanced math plugin server shutting down")
        # Clean up any resources if needed
        # For this plugin, no special cleanup is required
        
    async def advanced_calculator(self, expression: str, precision: int = 6) -> str:
        """Advanced mathematical expression calculator."""
        try:
            # Replace common mathematical notations
            expression = expression.replace('^', '**')
            expression = expression.replace('pi', str(math.pi))
            expression = expression.replace('e', str(math.e))
            expression = expression.replace('sqrt', 'math.sqrt')
            expression = expression.replace('sin', 'math.sin')
            expression = expression.replace('cos', 'math.cos')
            expression = expression.replace('tan', 'math.tan')
            expression = expression.replace('log', 'math.log')
            expression = expression.replace('ln', 'math.log')
            expression = expression.replace('exp', 'math.exp')
            
            # Use the safe expression calculator
            result = self._safe_calculate_expression(expression)
            
            if isinstance(result, (int, float)):
                return f"Result: {round(result, precision)}"
            else:
                return f"Result: {result}"
                
        except Exception as e:
            return f"Error calculating expression: {str(e)}"
            
    async def statistical_analysis(self, data: List[float], include_advanced: bool = False) -> str:
        """Comprehensive statistical analysis of numerical data."""
        try:
            if not data:
                return "Error: No data provided"
                
            n = len(data)
            mean = statistics.mean(data)
            median = statistics.median(data)
            mode = statistics.mode(data) if len(set(data)) < len(data) else "No mode"
            std_dev = statistics.stdev(data) if n > 1 else 0
            variance = statistics.variance(data) if n > 1 else 0
            
            result = f"""Statistical Analysis Results:
Sample size: {n}
Mean: {mean:.6f}
Median: {median:.6f}
Mode: {mode}
Standard Deviation: {std_dev:.6f}
Variance: {variance:.6f}
Min: {min(data):.6f}
Max: {max(data):.6f}
Range: {max(data) - min(data):.6f}"""
            
            if include_advanced and n > 2:
                # Calculate percentiles
                sorted_data = sorted(data)
                p25 = np.percentile(sorted_data, 25)
                p75 = np.percentile(sorted_data, 75)
                iqr = p75 - p25
                
                # Calculate skewness and kurtosis
                skewness = self._calculate_skewness(data, mean, std_dev)
                kurtosis = self._calculate_kurtosis(data, mean, std_dev)
                
                result += f"""
25th Percentile: {p25:.6f}
75th Percentile: {p75:.6f}
Interquartile Range: {iqr:.6f}
Skewness: {skewness:.6f}
Kurtosis: {kurtosis:.6f}"""
                
            return result
            
        except Exception as e:
            return f"Error in statistical analysis: {str(e)}"
            
    async def matrix_operations(self, operation: str, matrix_a: List[List[float]], 
                               matrix_b: Optional[List[List[float]]] = None) -> str:
        """Perform matrix operations."""
        try:
            if not matrix_a:
                return "Error: Matrix A is empty"
                
            # Convert to numpy arrays
            A = np.array(matrix_a)
            
            if operation == "determinant":
                if A.shape[0] != A.shape[1]:
                    return "Error: Determinant requires a square matrix"
                det = np.linalg.det(A)
                return f"Determinant: {det:.6f}"
                
            elif operation == "inverse":
                if A.shape[0] != A.shape[1]:
                    return "Error: Inverse requires a square matrix"
                try:
                    inv = np.linalg.inv(A)
                    return f"Inverse matrix:\n{inv.tolist()}"
                except np.linalg.LinAlgError:
                    return "Error: Matrix is not invertible (singular)"
                    
            elif operation == "eigenvalues":
                if A.shape[0] != A.shape[1]:
                    return "Error: Eigenvalues require a square matrix"
                eigenvals = np.linalg.eigvals(A)
                return f"Eigenvalues: {eigenvals.tolist()}"
                
            elif operation == "transpose":
                transposed = A.T
                return f"Transposed matrix:\n{transposed.tolist()}"
                
            elif operation == "rank":
                rank = np.linalg.matrix_rank(A)
                return f"Matrix rank: {rank}"
                
            elif operation == "multiply":
                if matrix_b is None:
                    return "Error: Matrix B is required for multiplication"
                B = np.array(matrix_b)
                if A.shape[1] != B.shape[0]:
                    return f"Error: Matrix dimensions incompatible for multiplication ({A.shape} × {B.shape})"
                product = np.dot(A, B)
                return f"Matrix product:\n{product.tolist()}"
                
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error in matrix operation: {str(e)}"
            
    async def get_mathematical_constants(self, constant: str) -> str:
        """Get mathematical constants and their properties."""
        constants = {
            "pi": {
                "value": math.pi,
                "description": "Pi (π) - ratio of circle circumference to diameter",
                "approximation": "3.141592653589793",
                "history": "Known since ancient times, first calculated by Archimedes"
            },
            "e": {
                "value": math.e,
                "description": "Euler's number - base of natural logarithm",
                "approximation": "2.718281828459045",
                "history": "Discovered by Jacob Bernoulli in 1683"
            },
            "golden_ratio": {
                "value": (1 + math.sqrt(5)) / 2,
                "description": "Golden ratio (φ) - approximately 1.618",
                "approximation": "1.618033988749895",
                "history": "Known since ancient Greece, appears in art and architecture"
            },
            "euler_mascheroni": {
                "value": 0.5772156649015329,
                "description": "Euler-Mascheroni constant (γ)",
                "approximation": "0.5772156649015329",
                "history": "First calculated by Leonhard Euler in 1734"
            },
            "catalan": {
                "value": 0.9159655941772190,
                "description": "Catalan's constant (G)",
                "approximation": "0.9159655941772190",
                "history": "Named after Eugène Charles Catalan"
            }
        }
        
        if constant == "all":
            result = "Mathematical Constants:\n" + "=" * 50 + "\n"
            for name, info in constants.items():
                result += f"\n{name.upper()}:\n"
                result += f"  Value: {info['value']:.15f}\n"
                result += f"  Description: {info['description']}\n"
                result += f"  History: {info['history']}\n"
            return result
        elif constant in constants:
            info = constants[constant]
            return f"""{constant.upper()}:
Value: {info['value']:.15f}
Description: {info['description']}
History: {info['history']}"""
        else:
            return f"Unknown constant: {constant}. Available: {', '.join(constants.keys())}, all"
            
    async def numerical_integration(self, function: str, lower_bound: float, 
                                   upper_bound: float, method: str = "adaptive") -> str:
        """Numerical integration of mathematical functions."""
        try:
            # Simple numerical integration methods
            if method == "trapezoidal":
                result = self._trapezoidal_integration(function, lower_bound, upper_bound)
            elif method == "simpson":
                result = self._simpson_integration(function, lower_bound, upper_bound)
            elif method == "adaptive":
                result = self._adaptive_integration(function, lower_bound, upper_bound)
            else:
                return f"Unknown integration method: {method}"
                
            return f"Integration result ({method} method): {result:.8f}"
            
        except Exception as e:
            return f"Error in numerical integration: {str(e)}"
            
    async def prime_number_utilities(self, operation: str, number: int, limit: Optional[int] = None) -> str:
        """Prime number utilities and operations."""
        try:
            if operation == "is_prime":
                result = self._is_prime(number)
                return f"{number} is {'prime' if result else 'not prime'}"
                
            elif operation == "factorize":
                factors = self._prime_factorization(number)
                return f"Prime factorization of {number}: {factors}"
                
            elif operation == "next_prime":
                next_prime = self._find_next_prime(number)
                return f"Next prime after {number}: {next_prime}"
                
            elif operation == "prime_factors":
                factors = self._get_prime_factors(number)
                return f"Prime factors of {number}: {factors}"
                
            elif operation == "prime_count":
                if limit is None:
                    limit = number
                count = self._count_primes_up_to(limit)
                return f"Number of primes up to {limit}: {count}"
                
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error in prime number operation: {str(e)}"
            
    # Helper methods for advanced calculations
    def _calculate_skewness(self, data: List[float], mean: float, std_dev: float) -> float:
        """Calculate skewness of the data."""
        if std_dev == 0:
            return 0
        n = len(data)
        skewness = sum(((x - mean) / std_dev) ** 3 for x in data) / n
        return skewness
        
    def _calculate_kurtosis(self, data: List[float], mean: float, std_dev: float) -> float:
        """Calculate kurtosis of the data."""
        if std_dev == 0:
            return 0
        n = len(data)
        kurtosis = sum(((x - mean) / std_dev) ** 4 for x in data) / n - 3
        return kurtosis
        
    def _trapezoidal_integration(self, function: str, a: float, b: float, n: int = 1000) -> float:
        """Trapezoidal rule for numerical integration."""
        h = (b - a) / n
        x = np.linspace(a, b, n + 1)
        
        # Safe calculation of function values
        y = [self._safe_calculate_function(function, x_val) for x_val in x]
        
        return h * (0.5 * y[0] + sum(y[1:-1]) + 0.5 * y[-1])
        
    def _simpson_integration(self, function: str, a: float, b: float, n: int = 1000) -> float:
        """Simpson's rule for numerical integration."""
        if n % 2 == 1:
            n += 1
        h = (b - a) / n
        x = np.linspace(a, b, n + 1)
        
        y = [self._safe_calculate_function(function, x_val) for x_val in x]
        
        return h/3 * (y[0] + 4*sum(y[1:-1:2]) + 2*sum(y[2:-1:2]) + y[-1])
        
    def _adaptive_integration(self, function: str, a: float, b: float) -> float:
        """Adaptive integration using both trapezoidal and Simpson's methods."""
        # Use Simpson's method with higher precision
        return self._simpson_integration(function, a, b, 2000)
        
    def _is_prime(self, n: int) -> bool:
        """Check if a number is prime."""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True
        
    def _prime_factorization(self, n: int) -> List[int]:
        """Get prime factorization of a number."""
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        return factors
        
    def _find_next_prime(self, n: int) -> int:
        """Find the next prime number after n."""
        if n < 2:
            return 2
        candidate = n + 1
        while not self._is_prime(candidate):
            candidate += 1
        return candidate
        
    def _get_prime_factors(self, n: int) -> List[int]:
        """Get unique prime factors of a number."""
        factors = self._prime_factorization(n)
        return sorted(list(set(factors)))
        
    def _count_primes_up_to(self, limit: int) -> int:
        """Count prime numbers up to a limit using Sieve of Eratosthenes."""
        if limit < 2:
            return 0
            
        sieve = [True] * (limit + 1)
        sieve[0] = sieve[1] = False
        
        for i in range(2, int(math.sqrt(limit)) + 1):
            if sieve[i]:
                for j in range(i * i, limit + 1, i):
                    sieve[j] = False
                    
        return sum(sieve)
        
    def _safe_calculate_expression(self, expression: str) -> float:
        """Safely calculate mathematical expressions without using unsafe methods."""
        try:
            # Clean up the expression
            expression = expression.strip()
            
            # Handle parentheses first (innermost to outermost)
            while '(' in expression and ')' in expression:
                # Find the innermost parentheses
                start = expression.rfind('(')
                end = expression.find(')', start)
                if start == -1 or end == -1:
                    break
                    
                # Extract the content inside parentheses
                inner_expr = expression[start+1:end]
                # Calculate the inner expression
                inner_result = self._safe_calculate_expression(inner_expr)
                # Replace the parentheses with the result
                expression = expression[:start] + str(inner_result) + expression[end+1:]
            
            # Handle functions (now that parentheses are resolved)
            if expression.startswith('math.sqrt'):
                # Extract the number after math.sqrt
                number_str = expression.replace('math.sqrt', '').strip()
                try:
                    number = float(number_str)
                    return math.sqrt(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for sqrt: {number_str}")
            elif expression.startswith('math.sin'):
                number_str = expression.replace('math.sin', '').strip()
                try:
                    number = float(number_str)
                    return math.sin(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for sin: {number_str}")
            elif expression.startswith('math.cos'):
                number_str = expression.replace('math.cos', '').strip()
                try:
                    number = float(number_str)
                    return math.cos(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for cos: {number_str}")
            elif expression.startswith('math.tan'):
                number_str = expression.replace('math.tan', '').strip()
                try:
                    number = float(number_str)
                    return math.tan(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for tan: {number_str}")
            elif expression.startswith('math.log'):
                number_str = expression.replace('math.log', '').strip()
                try:
                    number = float(number_str)
                    return math.log(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for log: {number_str}")
            elif expression.startswith('math.exp'):
                number_str = expression.replace('math.exp', '').strip()
                try:
                    number = float(number_str)
                    return math.exp(number)
                except ValueError:
                    raise ValueError(f"Invalid argument for exp: {number_str}")
            
            # Handle basic arithmetic operations (order of operations)
            # Handle exponentiation first
            if '**' in expression:
                parts = expression.split('**', 1)
                return self._safe_calculate_expression(parts[0]) ** self._safe_calculate_expression(parts[1])
            
            # Handle multiplication and division
            if '*' in expression:
                parts = expression.split('*', 1)
                return self._safe_calculate_expression(parts[0]) * self._safe_calculate_expression(parts[1])
            elif '/' in expression:
                parts = expression.split('/', 1)
                return self._safe_calculate_expression(parts[0]) / self._safe_calculate_expression(parts[1])
            
            # Handle addition and subtraction
            if '+' in expression and not expression.startswith('+'):
                parts = expression.split('+', 1)
                return self._safe_calculate_expression(parts[0]) + self._safe_calculate_expression(parts[1])
            elif '-' in expression and not expression.startswith('-'):
                parts = expression.split('-', 1)
                return self._safe_calculate_expression(parts[0]) - self._safe_calculate_expression(parts[1])
            
            # Handle numbers
            try:
                return float(expression)
            except ValueError:
                raise ValueError(f"Cannot calculate expression: {expression}")
                
        except Exception as e:
            raise ValueError(f"Error calculating expression '{expression}': {str(e)}")
            
    def _safe_calculate_function(self, function: str, x_val: float) -> float:
        """Safely calculate a mathematical function at a specific x value."""
        try:
            # Replace 'x' with the actual value
            function_with_x = function.replace('x', str(x_val))
            return self._safe_calculate_expression(function_with_x)
        except Exception as e:
            raise ValueError(f"Error calculating function '{function}' at x={x_val}: {str(e)}")
