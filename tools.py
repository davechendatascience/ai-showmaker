import paramiko
import os
import json
import time
from pathlib import Path
from typing import Optional
import threading
from contextlib import contextmanager

class SSHConnectionPool:
    """Thread-safe SSH connection pool for reusing connections."""
    
    def __init__(self, max_connections: int = 5, connection_timeout: int = 300):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.connections = {}
        self.lock = threading.Lock()
    
    def _create_connection(self) -> paramiko.SSHClient:
        """Create a new SSH connection."""
        key = paramiko.Ed25519Key.from_private_key_file(os.environ["PEM_PATH"])
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=os.environ["AWS_HOST"],
            username=os.environ["AWS_USER"],
            pkey=key,
            timeout=30
        )
        return ssh
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)."""
        connection_key = f"{os.environ['AWS_HOST']}:{os.environ['AWS_USER']}"
        
        with self.lock:
            if connection_key not in self.connections:
                self.connections[connection_key] = {
                    'client': self._create_connection(),
                    'last_used': time.time(),
                    'in_use': False
                }
        
        conn_info = self.connections[connection_key]
        
        # Check if connection is still alive
        try:
            transport = conn_info['client'].get_transport()
            if not transport or not transport.is_active():
                conn_info['client'] = self._create_connection()
        except:
            conn_info['client'] = self._create_connection()
        
        conn_info['in_use'] = True
        conn_info['last_used'] = time.time()
        
        try:
            yield conn_info['client']
        finally:
            conn_info['in_use'] = False
    
    def cleanup_old_connections(self):
        """Clean up old unused connections."""
        current_time = time.time()
        with self.lock:
            keys_to_remove = []
            for key, conn_info in self.connections.items():
                if (not conn_info['in_use'] and 
                    current_time - conn_info['last_used'] > self.connection_timeout):
                    try:
                        conn_info['client'].close()
                    except:
                        pass
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.connections[key]

# Global connection pool
_ssh_pool = SSHConnectionPool()

def validate_filename(filename: str) -> str:
    """Validate filename to prevent path traversal attacks."""
    # Convert to Path object for better handling
    path = Path(filename)
    
    # Check for path traversal attempts
    if '..' in filename or filename.startswith('/'):
        raise ValueError(f"Security violation: Path traversal detected in '{filename}'")
    
    # Check for absolute paths on Windows
    if path.is_absolute():
        raise ValueError(f"Security violation: Absolute paths not allowed '{filename}'")
    
    # Restrict to reasonable file extensions
    allowed_extensions = {'.py', '.txt', '.js', '.html', '.css', '.json', '.md', '.yml', '.yaml', '.sh', '.conf'}
    if path.suffix and path.suffix.lower() not in allowed_extensions:
        raise ValueError(f"File extension '{path.suffix}' not allowed. Allowed: {sorted(allowed_extensions)}")
    
    return filename

def remote_sftp_write_file_tool(input_str: str) -> str:
    """
    Securely writes files to remote server via SFTP.
    Expects input_str to be a JSON string: 
    '{"filename": "somefile.py", "code": "print(123)"}'
    
    Security features:
    - Path traversal protection
    - File extension validation
    - Directory auto-creation
    """
    try:
        args = json.loads(input_str)
        filename = args['filename']
        code = args['code']
        
        # Validate filename for security
        filename = validate_filename(filename)
        
        # Connect to server using connection pool
        with _ssh_pool.get_connection() as ssh:
            sftp = ssh.open_sftp()
        
        # Create directory if it doesn't exist
        file_path = Path(filename)
        if file_path.parent != Path('.'):
            try:
                sftp.mkdir(str(file_path.parent))
            except FileExistsError:
                pass  # Directory already exists
            except Exception as e:
                # Try to create parent directories recursively
                try:
                    ssh.exec_command(f"mkdir -p {file_path.parent}")
                except:
                    pass  # Continue anyway, might still work
        
        # Write file
        with sftp.open(filename, 'w') as f:
            f.write(code)
        
            # Get file size for confirmation
            stat = sftp.stat(filename)
            file_size = stat.st_size
            
            sftp.close()
            return f"File '{filename}' written successfully ({file_size} bytes)."
        
    except json.JSONDecodeError:
        return "Error: Invalid JSON input. Expected format: {'filename': 'file.py', 'code': 'content'}"
    except ValueError as e:
        return f"Validation Error: {str(e)}"
    except paramiko.AuthenticationException:
        return "Error: SSH authentication failed. Check your key file and permissions."
    except paramiko.SSHException as e:
        return f"SSH Connection Error: {str(e)}"
    except FileNotFoundError:
        return f"Error: SSH key file not found at {os.environ.get('PEM_PATH', 'undefined path')}"
    except Exception as error:
        return f"SFTP Error: {str(error)}"

import math
import ast
import operator
import re
from typing import Any, Dict, Union

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

# Create global calculator instance
_calculator = SafeCalculator()

def calculator_tool(input: str) -> str:
    """
    Advanced mathematical calculator tool that safely evaluates mathematical expressions.
    
    Supports:
    - Basic arithmetic: +, -, *, /, //, %, **
    - Mathematical functions: sin, cos, tan, log, sqrt, factorial, etc.
    - Constants: pi, e, tau, inf, nan
    - Variable assignments: x = 5, then use x in calculations
    - Complex expressions: sin(pi/4) * sqrt(2), factorial(5) + log(e)
    - List operations: min([1,2,3]), max([4,5,6]), sum([1,2,3])
    - Comparisons: 5 > 3, 10 == 2*5
    
    Examples:
    - "2 + 3 * 4" → "14"
    - "sqrt(16) + sin(pi/2)" → "5"
    - "x = 10" then "x * 2" → "20"
    - "factorial(5)" → "120"
    - "log(e) + cos(0)" → "2"
    """
    return _calculator.calculate(input)

def remote_command_tool(command: str) -> str:
    """
    Execute commands on remote server via SSH with improved error handling and timeout.
    
    Features:
    - 30-second timeout for commands
    - Exit code reporting
    - Separate stdout/stderr handling
    - Better error messages
    
    Note: Does not handle interactive commands that require user input.
    Use remote_interactive_command_tool for scripts that need stdin input.
    """
    try:
        # Connect using connection pool
        with _ssh_pool.get_connection() as ssh:
            # Execute command with timeout
            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
            
            # Wait for command completion and get exit code
            exit_code = stdout.channel.recv_exit_status()
            
            # Read output with proper decoding
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
        
        # Format output with exit code
        result = f"Exit Code: {exit_code}\n"
        if stdout_text:
            result += f"STDOUT:\n{stdout_text}"
        if stderr_text:
            result += f"STDERR:\n{stderr_text}"
        if not stdout_text and not stderr_text:
            result += "No output"
        
        return result
        
    except paramiko.AuthenticationException:
        return "Error: SSH authentication failed. Check your key file and permissions."
    except paramiko.SSHException as e:
        return f"SSH Connection Error: {str(e)}"
    except FileNotFoundError:
        return f"Error: SSH key file not found at {os.environ.get('PEM_PATH', 'undefined path')}"
    except TimeoutError:
        return "Error: Command timed out after 30 seconds"
    except Exception as error:
        return f"SSH Error: {str(error)}"

def remote_interactive_command_tool(input_str: str) -> str:
    """
    Execute interactive commands on remote server that require stdin input.
    
    Input: JSON string with 'command' and 'inputs' fields
    Example: '{"command": "python greet.py", "inputs": ["John", "25"]}'
    
    Features:
    - Handles programs that prompt for user input
    - Sends predefined inputs via stdin
    - 60-second timeout for interactive programs
    - Captures all output including prompts
    """
    try:
        args = json.loads(input_str)
        command = args['command']
        inputs = args.get('inputs', [])
        
        # Connect using connection pool
        with _ssh_pool.get_connection() as ssh:
            # Use invoke_shell for interactive commands
            shell = ssh.invoke_shell()
            shell.settimeout(60)
            
            # Send the command
            shell.send(command + '\n')
            time.sleep(0.5)  # Wait for command to start
            
            # Send inputs if program prompts for them
            for user_input in inputs:
                # Read any prompts first
                time.sleep(1)
                try:
                    output = shell.recv(1024).decode('utf-8', errors='replace')
                except:
                    pass
                
                # Send the input
                shell.send(str(user_input) + '\n')
                time.sleep(0.5)
            
            # Wait for program to complete and collect all output
            time.sleep(2)
            all_output = ""
            
            # Collect all available output
            while True:
                try:
                    shell.settimeout(2)  # Short timeout for final output
                    chunk = shell.recv(1024).decode('utf-8', errors='replace')
                    if chunk:
                        all_output += chunk
                    else:
                        break
                except:
                    break
            
            # Send exit to close shell
            shell.send('exit\n')
            shell.close()
            
            # Clean up the output (remove shell prompts, etc.)
            lines = all_output.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Skip shell prompt lines and command echo
                line = line.strip()
                if (line and 
                    not line.startswith('[') and  # Skip user@host prompts
                    not line.endswith('$') and   # Skip shell prompts
                    not line == command and      # Skip command echo
                    not line.startswith('exit')):  # Skip exit command
                    cleaned_lines.append(line)
            
            result = '\n'.join(cleaned_lines).strip()
            return result if result else "Interactive command completed (no output captured)"
            
    except json.JSONDecodeError:
        return "Error: Invalid JSON input. Expected format: {'command': 'python script.py', 'inputs': ['input1', 'input2']}"
    except Exception as error:
        return f"Interactive SSH Error: {str(error)}"

def smart_remote_command_tool(input_str: str) -> str:
    """
    Unified remote command tool that handles both interactive and non-interactive commands.
    
    Input: JSON string with 'command' and optional 'input_data' fields
    Examples: 
    - Non-interactive: '{"command": "ls -la"}'
    - Interactive: '{"command": "python3 greet.py", "input_data": "John\\n25"}'
    
    Features:
    - Automatically handles interactive programs with input_data
    - Runs regular commands when no input_data provided
    - Uses shell piping for interactive programs
    - 30-second timeout and proper error handling
    """
    try:
        args = json.loads(input_str)
        command = args['command']
        input_data = args.get('input_data', '')
        
        # Create a command that pipes input to the program if needed
        if input_data:
            # Use printf to handle newlines properly for interactive programs
            piped_command = f"printf '{input_data}\\n' | {command}"
        else:
            # Regular command execution
            piped_command = command
        
        # Use the existing remote_command_tool logic with connection pooling
        try:
            # Connect using connection pool
            with _ssh_pool.get_connection() as ssh:
                # Execute command with timeout
                stdin, stdout, stderr = ssh.exec_command(piped_command, timeout=30)
                
                # Wait for command completion and get exit code
                exit_code = stdout.channel.recv_exit_status()
                
                # Read output with proper decoding
                stdout_text = stdout.read().decode('utf-8', errors='replace')
                stderr_text = stderr.read().decode('utf-8', errors='replace')
                
                # Format output with exit code
                result = f"Exit Code: {exit_code}\\n"
                if stdout_text:
                    result += f"STDOUT:\\n{stdout_text}"
                if stderr_text:
                    result += f"STDERR:\\n{stderr_text}"
                if not stdout_text and not stderr_text:
                    result += "No output"
                
                return result
                
        except paramiko.AuthenticationException:
            return "Error: SSH authentication failed. Check your key file and permissions."
        except paramiko.SSHException as e:
            return f"SSH Connection Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: SSH key file not found at {os.environ.get('PEM_PATH', 'undefined path')}"
        except TimeoutError:
            return "Error: Command timed out after 30 seconds"
        except Exception as error:
            return f"SSH Error: {str(error)}"
        
    except json.JSONDecodeError:
        return "Error: Invalid JSON input. Expected format: {'command': 'ls -la'} or {'command': 'python3 script.py', 'input_data': 'input_text'}"
    except Exception as error:
        return f"Command Error: {str(error)}"
