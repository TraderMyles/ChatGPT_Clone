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

.
├── chatbot_sqlite.py # Main chatbot script
├── chat_memory.db # SQLite database (auto-created)
├── .env # API key (not committed)
└── README.md

yaml
Copy code

---

## 🧩 Requirements

- Python **3.10+**
- An OpenAI API key

### Python packages
```bash
pip install openai python-dotenv ddgs
🔑 Setup
1️⃣ Create a .env file
In the project root:

env
Copy code
OPENAI_API_KEY=your_api_key_here
⚠️ Do not commit this file.

2️⃣ Run the chatbot
bash
Copy code
python chatbot_sqlite.py
On first run, the app will:

Create chat_memory.db

Start a new chat session

Store the system prompt automatically

💬 How to Use
Normal chat
Just type and press Enter:

makefile
Copy code
You: explain embeddings simply
Chatbot: Embeddings are numerical representations of meaning...
The chatbot remembers the conversation automatically.

🧭 Commands
Command	Description
/new or /reset	Start a new chat
/chats	List recent chats
/load <chat_id>	Load an existing chat
/history	Print current chat history
/delete <chat_id>	Delete a chat
/help	Show help
quit / exit / bye	Exit program

Example
jboss-cli
Copy code
/chats
/load 3c7a4c2b-...
/history
🧠 How Memory Works
Every message is stored in SQLite

On each turn, the bot:

Loads the system prompt

Loads the last N messages (configurable)

Responds using that context

Older messages stay in the database but are not always sent to the model

This keeps responses relevant without token explosion.

🔍 Web Search
The bot can call a web search tool automatically when:

Information may be time-sensitive

Verification is needed

Search results are:

Retrieved via DuckDuckGo

Passed back to the model

Stored in the database for traceability

⚙️ Configuration
Inside chatbot_sqlite.py:

python
Copy code
MODEL = "gpt-4o-mini"
CONTEXT_MESSAGES = 24
Increase CONTEXT_MESSAGES for more memory

Lower it to reduce cost

🧪 Development Notes
SQLite uses WAL mode for reliability

Chat ordering is based on an autoincrement primary key (not timestamps)

Tool outputs are stored alongside messages

🚀 Possible Extensions
Add embeddings for long-term semantic memory

Summarize old conversations automatically

Add a GUI or web interface

Add user profiles

Add export/import for chats

🛠 Troubleshooting
Chats not showing correctly?
Delete the database and restart:

bash
Copy code
del chat_memory.db   # Windows
rm chat_memory.db    # Mac/Linux
API key not found?
Make sure .env exists and is loaded.

📜 License
Use, modify, and build on this freely.
This project is meant for learning and experimentation.

yaml
Copy code

---

If you want, next I can:
- Add a **“How memory works visually”** section
- Write a **developer-focused README**
- Create a **second README** for non-technical users
- Add screenshots / architecture diagrams

Just say the word.