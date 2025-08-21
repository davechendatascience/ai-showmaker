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

# Replace with your GCP instance name and zone
INSTANCE_NAME = "instance-20250821-144622"
ZONE = "us-central1-c"

# Example calculator tool
def calculator_tool(input: str) -> str:
    try:
        return str(eval(input))
    except Exception:
        return "Error"

# Tool to run commands on the GCP Debian VM
def remote_command_tool(command: str) -> str:
    safe_command = '"' + command + '"'
    gcloud_cmd = f'gcloud compute ssh {INSTANCE_NAME} --zone={ZONE} --command={safe_command}'
    print(gcloud_cmd)
    try:
        result = subprocess.run(gcloud_cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr
    except Exception as error:
        return str(error)

tools = [
    Tool(name="Calculator", func=calculator_tool, description="Calculates mathematical expressions."),
    Tool(
        name="RemoteCommand",
        func=remote_command_tool,
        description="Runs a shell command on the remote GCP Debian VM via gcloud ssh."
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

# EXAMPLES
query1 = "Calculate the average of 12, 45, and 22, then tell me the square root of that value."
response1 = agent.run(query1)
print(response1)

query2 = "can you create a ollama rag app"
response2 = agent.run(query2)
print(response2)