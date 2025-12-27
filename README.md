# 🧠 SQLite + Web-Enabled Chatbot (Terminal)

A local, terminal-based AI chatbot with:

- ✅ Persistent memory (SQLite)
- 🔍 Optional web search (DuckDuckGo)
- 💬 Multi-chat support (like ChatGPT threads)
- ♻️ Reloadable conversation history
- 🧰 Simple CLI commands

This project is designed to be **transparent, hackable, and educational** — no frameworks, no magic.

---

## ✨ Features

- **Persistent memory**  
  All chats are saved in a local SQLite database (`chat_memory.db`).

- **Multiple chats**  
  Start new conversations, list past ones, and reload them anytime.

- **Web search tool**  
  The bot can search the web for up-to-date information when needed.

- **Context management**  
  Only the most recent messages are sent to the model to keep costs low.

- **Terminal-first**  
  Runs entirely in the terminal — fast, minimal, distraction-free.

---

## 🗂 Project Structure

├── chatbot_sqlite.py # Main chatbot script
├── chat_memory.db # SQLite database (auto-created)
├── .env # API key (not committed)
└── README.md

---

## 🧩 Requirements

- Python **3.10+**
- An OpenAI API key

## 🚀 Quick Start (Basic Instructions)

Follow these steps to run the chatbot locally.

---

### 1️⃣ Clone the repository
```bash
git clone <REPO_URL>
cd <REPO_NAME>

2️⃣ Create and activate a virtual environment

Windows

python -m venv venv
venv\Scripts\activate


Mac / Linux

python3 -m venv venv
source venv/bin/activate

3️⃣ Install dependencies

pip install openai python-dotenv ddgs

4️⃣ Create a .env file

In the project root, create a file called .env and add:

OPENAI_API_KEY=your_openai_api_key_here

You can get an API key from https://platform.openai.com/account/api-keys

5️⃣ Run the chatbot
python chatbot_sqlite.py

That’s it.
The chatbot will start in your terminal and automatically create a local SQLite database for memory.

💬 Commands (Type these in the chatbot)

| Command                 | What it does              |
|-------------------------|---------------------------|
| `/new` or `/reset`      | Start a new chat          |
| `/chats`                | List saved chats          |
| `/load <chat_id>`       | Load a previous chat      |
| `/history`              | Show current chat history |
| `/delete <chat_id>`     | Delete a chat             |
| `/help`                 | Show all commands         |
| `quit` / `exit` / `bye` | Exit the chatbot          |

🧠 Notes

Chats are stored locally in chat_memory.db

Memory persists between sessions

Only recent messages are sent to the model to control cost