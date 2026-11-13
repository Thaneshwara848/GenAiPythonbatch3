
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env file
load_dotenv()

# Create OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

text = "Python is a programming language"

# Convert text into embedding
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)

vector = response.data[0].embedding

print("Original Text:", text)
print("First 5 Vector Values:", vector[:1536])
print("Total Dimensions:", len(vector))
