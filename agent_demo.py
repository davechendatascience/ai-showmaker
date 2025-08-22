import os
import json
from tools import *

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
os.environ["AWS_HOST"] = 'ec2-54-206-17-243.ap-southeast-2.compute.amazonaws.com'  # Replace with EC2 PUBLIC DNS/IP
os.environ["AWS_USER"] = 'ec2-user'  # or 'ec2-user' for Amazon Linux
os.environ["PEM_PATH"] = 'ai-showmaker.pem'  # Local path to your .pem file

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
                f"task description: {task_description}\n"
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
        description="Runs a shell command on the remote Amazon Linux with ssh. You are only ssh to the server, not actually in the server."
    ),
    Tool(
        name="RemoteWriteFile",
        func=remote_sftp_write_file_tool,
        description="Write code to a file on the remote server. Input: JSON string '{{\"filename\": \"file.py\", \"code\": \"YOUR CODE\"}}'"
    )
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
query = "can you create a stock analysis website and publish it through the web?"
final_response = human_in_the_loop(query, agent)