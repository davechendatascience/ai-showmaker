import os
import subprocess
import json

# Set your Gemini (Google) API key
with open('secrets.json', 'r') as f:
    secrets = json.load(f)
os.environ["GOOGLE_API_KEY"] = secrets["GOOGLE_API_KEY"]

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import initialize_agent, AgentType
import paramiko

# AWS EC2 SSH access configuration
AWS_HOST = 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com'  # Replace with EC2 PUBLIC DNS/IP
AWS_USER = 'ec2-user'  # or 'ec2-user' for Amazon Linux
PEM_PATH = 'ai-showmaker.pem'  # Local path to your .pem file

# Example calculator tool
def calculator_tool(input: str) -> str:
    try:
        return str(eval(input))
    except Exception:
        return "Error"

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
    
def human_in_the_loop(task_description, agent, max_retries=3):
    current_task = task_description
    for attempt in range(max_retries):
        response = agent.run(current_task)
        print(f"\nAgent Output:\n{response}")
        confirm = input("Is the task completed as expected? (y/n): ").strip().lower()
        if confirm == "y":
            print("Task confirmed and marked as complete!\n")
            return response
        else:
            print("Task NOT confirmed.")
            feedback = input("Describe what's missing or what should be changed for the next attempt: ")
            # Chain feedback to the next agent prompt as explicit guidance
            current_task = (
                f"Your previous attempt: {response}\n"
                f"The user says: {feedback}\n"
                f"Please try again, taking the feedback into account."
            )
    print("Max retries reached or user declined final confirmation.\n")
    return None

tools = [
    Tool(name="Calculator", func=calculator_tool, description="Calculates mathematical expressions."),
    Tool(
        name="RemoteCommand",
        func=remote_command_tool,
        description="Runs a shell command on the remote Amazon Linux with ssh."
    ),
    # Add other tools here if needed
]

system_message = "You are an expert assistant that tackles complex problems stepwise, calling tools when appropriate."

prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    ("human", "{input}")
])

# Set up Gemini chat agent
chat = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)  # Use "gemini-pro"; adjust as per docs

agent = initialize_agent(
    tools,
    chat,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# --- Usage Example ---
query2 = "can you create a demo website and make sure that outside traffic can reach it, not just within the server?"
final_response2 = human_in_the_loop(query2, agent)