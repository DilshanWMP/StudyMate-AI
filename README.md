# StudyMate-AI

## How to Run the Server

1. Activate virtual environment:
   ```powershell
   venv\Scripts\activate
   ```
2. Start the Uvicorn server:
   ```powershell
   uvicorn agent_server.main:app --reload --port 8000
   ```

## How to Test It Properly

You'll need three terminal windows open simultaneously, all with `(venv)` active:

### Terminal 1 — Server (already running)
```powershell
uvicorn agent_server.main:app --reload --port 8000
```

### Terminal 2 — The Stream Listener
```powershell
python test_stream.py
```
This will just sit there printing `Connecting to stream...` and wait — that's correct, it's listening for events.

### Terminal 3 — Send a Chat Message
```powershell
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"hi there\", \"thread_id\": \"t2\"}'
```

### What Should Happen
Right after Terminal 3's curl command runs, Terminal 2 should immediately print something like:
```json
RECEIVED: data: {"type": "chat_reply", "text": "Hello! How can I help you?"}
```
This proves the full loop works: `/chat` → graph runs → reply pushed to `stream_queue` → `/stream` picks it up → your listener receives it live.

---

## Testing the Confirmation Flow

1. In **Terminal 3**, send a schedule request:
   ```powershell
   curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"remind me to study DSP tomorrow at 6pm\", \"thread_id\": \"t2\"}'
   ```
2. **Terminal 2** should show a `confirmation_prompt` type message asking for approval.
3. In **Terminal 3**, send the approval using the same `thread_id`:
   ```powershell
   curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"message\": \"yes\", \"thread_id\": \"t2\"}'
   ```
4. Check that `schedules.txt` gets the new entry.
