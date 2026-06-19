# StudyMate AI

An agentic reminder assistant built with **LangChain**, **LangGraph**, and **Temporal**. The agent chats naturally with the user, decides on its own when a message is a schedule request (via LLM tool calling), pauses for human approval (Human-in-the-Loop) before saving anything, and automatically delivers reminders at the scheduled time through a separate Temporal worker — with zero further input from the user.

Built as a Week 1 AI internship learning project to cover LangChain tool calling, LangGraph's native HITL `interrupt()` mechanism, and Temporal workflow fundamentals.

---

## Architecture

Three independent processes communicating only over HTTP on `localhost`:

| Component | Tech | Role |
|---|---|---|
| **Agent Server** | FastAPI + LangGraph + Groq | The brain — conversation, tool calling, HITL confirmation, reminder storage |
| **CLI Client** | Python | Terminal interface — chat input, live notifications |
| **Temporal Worker** | Temporal Python SDK | Checks saved reminders on a schedule, triggers due ones |

```
You → CLI Client → POST /chat → Agent Server (LLM + LangGraph)
                                       │
                          tool call proposed? ──No──► reply normally
                                       │
                                      Yes
                                       │
                          interrupt() pauses ──► confirmation_prompt
                                       │
                          approve ──► save to schedules.txt
                          reject  ──► discard, nothing saved

Temporal Worker (every 10s) → reads schedules.txt → due? → POST /trigger
                                                              │
                                            Agent Server → GET /stream → CLI 🔔
```

---

## Project Structure

```
studymate-ai/
├── agent_server/
│   ├── main.py              # FastAPI: /chat, /trigger, /stream
│   ├── graph.py             # LangGraph: tool calling + HITL interrupt
│   ├── tools.py             # create_schedule tool definition
│   └── reminder_store.py    # Append / read / remove schedules.txt entries
├── cli_client/
│   └── client.py            # Terminal app: input + SSE listener
├── temporal_worker/
│   ├── worker.py            # Temporal worker process
│   ├── workflow.py          # Repeating reminder-check workflow
│   ├── activities.py        # Activity: reads schedules.txt, calls /trigger
│   └── start_workflow.py    # One-off script to kick off the workflow
├── schedules.txt            # Saved reminders (created at runtime)
├── requirements.txt
├── .gitignore
├── .env                     # GROQ_API_KEY (never committed)
└── README.md
```

---

## Tech Stack

- **Python 3.11+**
- **FastAPI + Uvicorn** — REST endpoints and SSE streaming
- **Groq API** (`llama-3.3-70b-versatile`) — free-tier LLM provider
- **LangChain** — tool definitions, message handling
- **LangGraph** — state graph + native Human-in-the-Loop `interrupt()`
- **Temporal** — reliable, retry-safe scheduled reminder checks

---

## Setup

### 1. Clone and create a virtual environment

```powershell
cd StudyMate-AI
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure your API key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_actual_groq_key_here
```

Get a free key at [console.groq.com/keys](https://console.groq.com/keys).

### 4. Install the Temporal CLI (Windows)

```powershell
winget install TemporalTechnologies.temporal
```

---

## Running the Full System

The system needs **4 terminals** running simultaneously, all with `(venv)` active (except the Temporal dev server itself).

### Terminal 1 — Temporal Dev Server

```powershell
temporal server start-dev
```

Runs on `localhost:7233`. Web UI available at [http://localhost:8233](http://localhost:8233) for visually inspecting workflow runs.

### Terminal 2 — Agent Server

```powershell
venv\Scripts\activate
uvicorn agent_server.main:app --reload --port 8000
```

### Terminal 3 — Temporal Worker

```powershell
venv\Scripts\activate
python temporal_worker/worker.py
```

Then, once (it doesn't need to stay open after this), start the reminder-check workflow:

```powershell
venv\Scripts\activate
python temporal_worker/start_workflow.py
```

This only needs to be run once — the workflow itself loops forever, checking `schedules.txt` every 10 seconds.

### Terminal 4 — CLI Client

```powershell
venv\Scripts\activate
python cli_client/client.py
```

This is the actual interface you chat through. Type a message and press Enter; notifications appear automatically without you doing anything.

---

## Testing It

### 1. Memory Test

```
You: My name is Praveen
You: How are you?
You: What is my name?
```
Expected: the agent correctly recalls your name in the final reply.

### 2. Casual Chat (No Tool Call)

```
You: Tell me a joke
```
Expected: a plain reply, no confirmation prompt, nothing written to `schedules.txt`.

### 3. Reminder Confirmation — Approval

```
You: Remind me to study DSP at 6pm
```
Expected: a `[CONFIRM]` prompt appears asking yes/no.

```
You: yes
```
Expected: `Agent: Schedule created: Study DSP at <time>` and a new line appended to `schedules.txt`.

### 4. Reminder Confirmation — Rejection

```
You: Remind me to call mom at 8pm
You: no
```
Expected: `Agent: Schedule request discarded by user.` and **no** new line in `schedules.txt`.

### 5. Automatic Reminder (End-to-End)

```
You: Remind me to check email in 1 minute
You: yes
```
Then wait, without typing anything. Within ~10–20 seconds of the scheduled time (the workflow checks every 10s), a notification appears automatically:

```
🔔 Reminder: Check email (scheduled for <time>)
```

This confirms the full chain: Agent Server → `schedules.txt` → Temporal Worker → `/trigger` → SSE stream → CLI, with zero user input at the moment of delivery.

---

## Manual API Testing (curl, optional)

The CLI client covers everything above, but the raw HTTP endpoints can also be tested directly if needed — useful for debugging a specific endpoint in isolation.

> PowerShell's built-in `curl` is an alias for `Invoke-WebRequest` and uses different syntax. Use `curl.exe` directly for real curl-style commands shown below.

**Listen to the stream** (separate terminal):
```powershell
python -c "import requests; r = requests.get('http://localhost:8000/stream', stream=True); [print(l.decode()) for l in r.iter_lines() if l]"
```

**Send a chat message:**
```powershell
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"hi there\", \"thread_id\": \"t1\"}'
```

**Approve/reject a pending confirmation** (same `thread_id` as the request that triggered it):
```powershell
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"yes\", \"thread_id\": \"t1\"}'
```

**Manually fire a trigger** (simulates what Temporal does):
```powershell
curl.exe -X POST http://localhost:8000/trigger -H "Content-Type: application/json" -d '{\"description\": \"Test reminder\", \"datetime\": \"2026-06-20 18:00\"}'
```

---

## Key Design Notes

- **Tool calling, not manual classification.** The LLM decides whether a message warrants calling `create_schedule` — there's no hand-written if/else intent classifier.
- **HITL via LangGraph's native `interrupt()`.** Execution genuinely pauses before the tool runs; nothing is written to `schedules.txt` without explicit approval.
- **`.stream()` over `.invoke()`.** On the installed LangGraph version, interrupts are only reliably surfaced via `.stream()` — this is used consistently throughout `main.py`.
- **Real-time injected into the LLM context.** The agent is given the actual current date/time on every turn so it can correctly resolve relative expressions like "in 1 minute" or "tomorrow" — without this, the LLM has no ground truth for "now."
- **Workflows never touch the filesystem directly.** Only the Temporal *Activity* (`check_and_trigger_reminders`) reads `schedules.txt` and calls `/trigger`; the *Workflow* just orchestrates timing and retries.