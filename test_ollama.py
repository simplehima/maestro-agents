import requests
from config import OLLAMA_API_URL, DEFAULT_MODEL

def test_connection():
    print(f"Testing connection to Ollama at {OLLAMA_API_URL}...")
    try:
        # Simple test to check if Ollama is running and has the model
        payload = {
            "model": DEFAULT_MODEL,
            "prompt": "hi",
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print("Successfully connected to Ollama!")
            print(f"Model '{DEFAULT_MODEL}' is ready.")
        else:
            print(f"Failed to connect. Status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure Ollama is installed and running!")
        print("You can download it from https://ollama.com")

if __name__ == "__main__":
    test_connection()
