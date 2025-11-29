from google import genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


def get_response(prompt):
    API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key = API_KEY)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents= prompt
    )

    return response.text

if __name__ == "__main__":

    prompt= "hi can you hear"
    response= get_response(prompt)
    print(response)
