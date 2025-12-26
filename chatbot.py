import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# DuckDuckGo search (no API key)
from ddgs import DDGS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Return a small list of web results."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                }
            )
    return results

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Number of results", "default": 5},
                },
                "required": ["query"],
            },
        },
    }
]

SYSTEM = (
    "You are a helpful assistant. "
    "If the user asks for anything that may be time-sensitive or needs verification, "
    "use web_search to look it up. "
    "When you use web_search, cite sources by listing URLs."
)

def chat_with_tools(user_input: str) -> str:
    # First model call: it may decide to call the web_search tool
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_input},
    ]

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    # If no tool call, just return the assistant text
    if not msg.tool_calls:
        return (msg.content or "").strip()

    # Execute tool calls and append tool results
    for tool_call in msg.tool_calls:
        if tool_call.function.name == "web_search":
            args = json.loads(tool_call.function.arguments)
            results = web_search(args["query"], args.get("max_results", 5))

            messages.append(msg)  # assistant message that requested the tool
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(results),
                }
            )

    # Second model call: now it has the web results
    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    return final.choices[0].message.content.strip()

def main():
    print("Web-enabled chatbot started. Type 'quit', 'exit', or 'bye' to stop.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Chatbot: Bye.")
            break

        try:
            reply = chat_with_tools(user_input)
            print(f"Chatbot: {reply}\n")
        except Exception as e:
            print(f"Chatbot error: {e}\n")

if __name__ == "__main__":
    main()
