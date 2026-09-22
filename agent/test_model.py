import os
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import UserMessage

load_dotenv()

client = ChatCompletionsClient(
    endpoint=os.environ["FOUNDRY_MODEL_ENDPOINT"],
    credential=AzureKeyCredential(os.environ["FOUNDRY_MODEL_KEY"])
)

response = client.complete(
    messages=[UserMessage(content="Reply with 'Ready' if online.")],
    model=os.environ.get("FOUNDRY_DEPLOYMENT_NAME", "gpt-5-mini-2")
)

print(response.choices[0].message.content)