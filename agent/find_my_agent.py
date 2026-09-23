import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
if not endpoint:
    raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is missing from the environment")

client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

print("Fetching agents from Azure...")
agents = client.agents.list()

for agent in agents:
    print(f"Name: {agent.name} -> ID: {agent.id}")
