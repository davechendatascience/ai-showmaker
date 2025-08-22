import paramiko
import os

import json
import paramiko

def remote_sftp_write_file_tool(input_str: str) -> str:
    """
    Expects input_str to be a JSON string: 
    '{"filename": "somefile.py", "code": "print(123)"}'
    """
    try:
        args = json.loads(input_str)
        filename = args['filename']
        code = args['code']
        key = paramiko.Ed25519Key.from_private_key_file(os.environ["PEM_PATH"])
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=os.environ["AWS_HOST"], username=os.environ["AWS_USER"], pkey=key)
        sftp = ssh.open_sftp()
        with sftp.open(filename, 'w') as f:
            f.write(code)
        sftp.close()
        ssh.close()
        return f"File {filename} written successfully."
    except Exception as error:
        return f"SFTP Error: {error}"

# Example calculator tool
def calculator_tool(input: str) -> str:
    try:
        return str(eval(input))
    except Exception:
        return "Error"

def remote_command_tool(command: str) -> str:
    try:
        key = paramiko.Ed25519Key.from_private_key_file(os.environ["PEM_PATH"])
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=os.environ["AWS_HOST"], username=os.environ["AWS_USER"], pkey=key)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()
        ssh.close()
        return output
    except Exception as error:
        return f"SSH Error: {error}"
    