import paramiko

AWS_HOST = 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com'
AWS_USER = 'ec2-user'
PEM_PATH = 'ai-showmaker.pem'

def remote_command_tool(command: str) -> str:
    try:
        key = paramiko.Ed25519Key.from_private_key_file(PEM_PATH)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=AWS_HOST, username=AWS_USER, pkey=key)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode() + stderr.read().decode()
        ssh.close()
        return output
    except Exception as error:
        return f"SSH Error: {error}"

print(remote_command_tool("ls"))