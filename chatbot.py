import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# Settings
# -----------------------------
MODEL = "gpt-4o-mini"
MAX_TURNS_TO_KEEP = 12  # 12 turns = 24 messages (user+assistant). Adjust as you like.

SYSTEM = (
    "You are a helpful assistant. "
    "If the user asks for anything that may be time-sensitive or needs verification, "
    "use web_search to look it up. "
    "When you use web_search, cite sources by listing URLs."
)

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

# -----------------------------
# Tool implementation
# -----------------------------
def web_search(query: str, max_results: int = 5) -> list[dict]:
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

# -----------------------------
# Memory helpers
# -----------------------------
def trim_history(history: list[dict]) -> list[dict]:
    """
    Keep system + last MAX_TURNS_TO_KEEP turns.
    A 'turn' = (user + assistant). So keep 2*MAX_TURNS_TO_KEEP messages.
    """
    # history[0] is system
    if len(history) <= 1:
        return history

    max_msgs = 1 + (MAX_TURNS_TO_KEEP * 2)
    if len(history) > max_msgs:
        # Keep system + last messages
        return [history[0]] + history[-(max_msgs - 1):]
    return history

# -----------------------------
# Chat with tools + memory
# -----------------------------
def chat_with_tools(history: list[dict], user_input: str) -> str:
    """
    Uses conversation history as memory.
    If the model calls web_search, we execute it and do a second call.
    """
    # Add user message to memory
    history.append({"role": "user", "content": user_input})
    history[:] = trim_history(history)

    # First call: model may request tool(s)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=history,
        tools=TOOLS,
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    # If no tool calls, finalize
    if not msg.tool_calls:
        assistant_text = (msg.content or "").strip()
        history.append({"role": "assistant", "content": assistant_text})
        history[:] = trim_history(history)
        return assistant_text

    # If tool calls exist, append the assistant tool-call message
    history.append(msg)

    # Execute each tool call and append tool outputs
    for tool_call in msg.tool_calls:
        if tool_call.function.name == "web_search":
            args = json.loads(tool_call.function.arguments)
            results = web_search(args["query"], args.get("max_results", 5))

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(results),
                }
            )

    # Second call: model uses tool results + memory to answer
    final = client.chat.completions.create(
        model=MODEL,
        messages=history,
    )

    assistant_text = final.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": assistant_text})
    history[:] = trim_history(history)
    return assistant_text

def main():
    print("Web-enabled chatbot with memory started. Type 'quit', 'exit', 'bye' to stop.")
    print("Type '/reset' to clear memory.\n")

    # Memory starts with system message
    history = [{"role": "system", "content": SYSTEM}]

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Chatbot: Bye.")
            break

        if user_input.strip().lower() == "/reset":
            history = [{"role": "system", "content": SYSTEM}]
            print("Chatbot: Memory cleared.\n")
            continue

        try:
            reply = chat_with_tools(history, user_input)
            print(f"Chatbot: {reply}\n")
        except Exception as e:
            print(f"Chatbot error: {e}\n")

if __name__ == "__main__":
    main()
