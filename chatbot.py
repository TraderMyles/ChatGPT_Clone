import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Create OpenAI client using API key from .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chat_with_gpt(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content.strip()

def main():
    print("Chatbot started. Type 'quit', 'exit', or 'bye' to stop.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Chatbot: Bye.")
            break

        try:
            reply = chat_with_gpt(user_input)
            print(f"Chatbot: {reply}\n")
        except Exception as e:
            print(f"Chatbot error: {e}\n")

if __name__ == "__main__":
    main()
