import asyncio
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from graph import app_graph

app = FastAPI()

# Tracks which thread_ids currently have a paused graph awaiting confirmation
pending_confirmations: set[str] = set()

# Simple in-memory queue for SSE messages
stream_queue: asyncio.Queue = asyncio.Queue()


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


def extract_last_ai_text(messages) -> str:
    """Find the most recent AI message with plain text content."""
    for msg in reversed(messages):
        if msg.__class__.__name__ == "AIMessage" and msg.content:
            return msg.content
    return ""


async def push_to_stream(message_type: str, text: str):
    payload = json.dumps({"type": message_type, "text": text})
    await stream_queue.put(payload)


@app.post("/chat")
async def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    if req.thread_id in pending_confirmations:
        # Resume a paused graph with the user's yes/no
        decision = "approve" if req.message.strip().lower() in ("yes", "y", "approve") else "reject"
        stream_input = Command(resume=decision)
        pending_confirmations.discard(req.thread_id)
    else:
        stream_input = {"messages": [("user", req.message)]}

    interrupted = False
    final_chunk = None

    for chunk in app_graph.stream(stream_input, config=config):
        final_chunk = chunk
        if "__interrupt__" in chunk:
            interrupted = True
            payload = chunk["__interrupt__"][0].value
            action = payload.get("action")
            args = payload.get("args", {})
            text = (
                f"Do you want me to set a reminder for "
                f"'{args.get('description')}' at '{args.get('datetime')}'? (yes/no)"
            )
            pending_confirmations.add(req.thread_id)
            await push_to_stream("confirmation_prompt", text)

    if not interrupted:
        state = app_graph.get_state(config)
        reply_text = extract_last_ai_text(state.values.get("messages", []))
        if not reply_text and final_chunk:
            for node_output in final_chunk.values():
                if "messages" in node_output:
                    last = node_output["messages"][-1]
                    if hasattr(last, "content") and last.content:
                        reply_text = last.content
        await push_to_stream("chat_reply", reply_text or "Done.")

    return {"status": "ok"}


@app.post("/trigger")
async def trigger(payload: dict):
    description = payload.get("description", "your reminder")
    datetime_str = payload.get("datetime", "")
    text = f"🔔 Reminder: {description} (scheduled for {datetime_str})"
    await push_to_stream("notification", text)
    return {"status": "triggered"}


@app.get("/stream")
async def stream():
    async def event_generator():
        while True:
            message = await stream_queue.get()
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")