import os
from tools import *
from config import get_config

# Load configuration
config = get_config()
os.environ["GOOGLE_API_KEY"] = config['google_api_key']

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import initialize_agent, AgentType
import paramiko

# AWS EC2 SSH access configuration
os.environ["AWS_HOST"] = config['aws_host']
os.environ["AWS_USER"] = config['aws_user']
os.environ["PEM_PATH"] = config['pem_path']

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
    Tool(name="Calculator", func=calculator_tool, description="Advanced mathematical calculator supporting arithmetic, trigonometry, logarithms, factorials, variables, and complex expressions. Use for any mathematical computation including scientific functions."),
    Tool(
        name="RemoteCommand",
        func=smart_remote_command_tool,
        description="Execute commands on the remote server. Input: JSON string. For regular commands: '{{\"command\": \"ls -la\"}}'. For interactive programs that need user input: '{{\"command\": \"python3 script.py\", \"input_data\": \"input1\\\\ninput2\"}}'. Automatically handles both types."
    ),
    Tool(
        name="RemoteWriteFile",
        func=remote_sftp_write_file_tool,
        description="Write code to a file on the remote server via SFTP. Input: JSON string '{{\"filename\": \"file.py\", \"code\": \"YOUR CODE\"}}'"
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
query = "can you take the 3 to the power of 2?"
response = human_in_the_loop(query, agent)

query = "can you create an art gallary and publish it through the web?"
response = human_in_the_loop(query, agent)