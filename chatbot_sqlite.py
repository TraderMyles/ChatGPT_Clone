import os
import json
import sqlite3
from datetime import datetime
from uuid import uuid4
from contextlib import contextmanager

from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS

# -----------------------------
# Config
# -----------------------------
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Check your .env file.")

client = OpenAI(api_key=API_KEY)

MODEL = "gpt-4o-mini"
DB_PATH = os.path.join(os.path.dirname(__file__), "chat_memory.db")

# how many recent non-system messages to send as context
CONTEXT_MESSAGES = 24

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

HELP_TEXT = """
Commands:
  /new                 Start a new chat
  /chats               List recent chats
  /load <chat_id>      Load an existing chat by id
  /history             Print current chat history (user+assistant)
  /delete <chat_id>    Delete a chat (careful)
  /reset               Alias for /new
  /help                Show this help
  quit | exit | bye    Quit
"""

# -----------------------------
# Utils
# -----------------------------
def now_iso() -> str:
    return datetime.utcnow().isoformat()

@contextmanager
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        # small perf/safety tweaks
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("PRAGMA foreign_keys=ON;")
        yield c
        c.commit()
    finally:
        c.close()

# -----------------------------
# Web tool
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
# DB schema
# -----------------------------
def init_db():
    with db() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('system','user','assistant','tool')),
            content TEXT NOT NULL,
            tool_call_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
        """)

        c.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id_id ON messages(chat_id, id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_chats_pk ON chats(pk)")

# -----------------------------
# DB operations
# -----------------------------
def create_chat(title: str | None = None) -> str:
    chat_id = str(uuid4())
    with db() as c:
        c.execute(
            "INSERT INTO chats (id, title, created_at) VALUES (?, ?, ?)",
            (chat_id, title, now_iso()),
        )
        c.execute(
            "INSERT INTO messages (chat_id, role, content, tool_call_id, created_at) VALUES (?, 'system', ?, NULL, ?)",
            (chat_id, SYSTEM, now_iso()),
        )
    return chat_id

def set_chat_title_if_empty(chat_id: str, title: str):
    title = (title or "").strip()[:80]
    if not title:
        return
    with db() as c:
        row = c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row and (row["title"] is None or row["title"].strip() == ""):
            c.execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))

def add_message(chat_id: str, role: str, content: str, tool_call_id: str | None = None):
    with db() as c:
        c.execute(
            "INSERT INTO messages (chat_id, role, content, tool_call_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, role, content, tool_call_id, now_iso()),
        )

def get_context_messages(chat_id: str) -> list[dict]:
    """
    Returns messages ready for OpenAI:
      - first system message (one per chat)
      - last CONTEXT_MESSAGES non-system messages
    """
    with db() as c:
        sys_row = c.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? AND role = 'system' ORDER BY id ASC LIMIT 1",
            (chat_id,),
        ).fetchone()

        rows = c.execute(
            """
            SELECT role, content, tool_call_id
            FROM messages
            WHERE chat_id = ? AND role != 'system'
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, CONTEXT_MESSAGES),
        ).fetchall()

    msgs: list[dict] = []
    if sys_row:
        msgs.append({"role": "system", "content": sys_row["content"]})

    for r in reversed(rows):
        if r["role"] == "tool":
            msgs.append(
                {"role": "tool", "tool_call_id": r["tool_call_id"], "content": r["content"]}
            )
        else:
            msgs.append({"role": r["role"], "content": r["content"]})

    return msgs

def list_chats(limit: int = 20):
    with db() as c:
        rows = c.execute(
            """
            SELECT id, COALESCE(title,'(untitled)') AS title, created_at
            FROM chats
            ORDER BY pk DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]

def fetch_full_history(chat_id: str, limit: int = 200):
    with db() as c:
        rows = c.execute(
            """
            SELECT role, content
            FROM messages
            WHERE chat_id = ? AND role IN ('user','assistant')
            ORDER BY id ASC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]

def delete_chat(chat_id: str):
    with db() as c:
        c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))

# -----------------------------
# Chat logic (tools + SQLite memory)
# -----------------------------
def chat_turn(chat_id: str, user_input: str) -> str:
    add_message(chat_id, "user", user_input)
    set_chat_title_if_empty(chat_id, user_input)

    messages = get_context_messages(chat_id)

    # First call: may request web_search
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    # No tool use -> reply
    if not msg.tool_calls:
        reply = (msg.content or "").strip()
        add_message(chat_id, "assistant", reply)
        return reply

    # Tool(s) requested: append the assistant tool-call message to in-memory context
    messages.append(msg)

    for tool_call in msg.tool_calls:
        if tool_call.function.name == "web_search":
            args = json.loads(tool_call.function.arguments)
            results = web_search(args["query"], args.get("max_results", 5))
            tool_payload = json.dumps(results)

            # store tool output in DB for persistence
            add_message(chat_id, "tool", tool_payload, tool_call_id=tool_call.id)

            # provide tool output to model
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": tool_payload}
            )

    # Second call: model uses tool results
    final = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    reply = final.choices[0].message.content.strip()
    add_message(chat_id, "assistant", reply)
    return reply

# -----------------------------
# CLI
# -----------------------------
def handle_command(current_chat_id: str, raw: str) -> str | None:
    """
    Returns:
      - new chat_id (if command changes it), else None
    Side effects: prints output
    """
    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/help":
        print(HELP_TEXT)
        return None

    if cmd in {"/new", "/reset"}:
        new_id = create_chat()
        print(f"\nChatbot: New chat started.\nCurrent chat_id: {new_id}\n")
        return new_id

    if cmd == "/chats":
        chats = list_chats(limit=20)
        print("\n--- Recent Chats ---")
        for c in chats:
            print(f"{c['id']}  |  {c['title']}  |  {c['created_at']}")
        print("--- End ---\n")
        return None

    if cmd == "/load":
        if not arg:
            print("Chatbot: Usage: /load <chat_id>\n")
            return None
        print(f"\nChatbot: Loaded chat_id: {arg}\n")
        return arg

    if cmd == "/history":
        hist = fetch_full_history(current_chat_id, limit=200)
        print("\n--- History ---")
        if not hist:
            print("(no messages yet)")
        for m in hist:
            print(f"{m['role'].upper()}: {m['content']}")
        print("--- End ---\n")
        return None

    if cmd == "/delete":
        if not arg:
            print("Chatbot: Usage: /delete <chat_id>\n")
            return None
        delete_chat(arg)
        print(f"Chatbot: Deleted chat {arg}\n")
        if arg == current_chat_id:
            new_id = create_chat()
            print(f"Chatbot: New chat started.\nCurrent chat_id: {new_id}\n")
            return new_id
        return None

    print("Chatbot: Unknown command. Type /help\n")
    return None

def main():
    init_db()

    chat_id = create_chat()
    print("SQLite + Web-enabled chatbot started.")
    print("Type /help for commands.\n")
    print(f"Current chat_id: {chat_id}\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Chatbot: Bye.")
            break

        if user_input.startswith("/"):
            maybe_new = handle_command(chat_id, user_input)
            if maybe_new:
                chat_id = maybe_new
            continue

        try:
            reply = chat_turn(chat_id, user_input)
            print(f"Chatbot: {reply}\n")
        except Exception as e:
            print(f"Chatbot error: {e}\n")

if __name__ == "__main__":
    main()
