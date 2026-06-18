import threading
import json
import requests

SERVER_URL = "http://localhost:8000"
THREAD_ID = "cli-session-1"


def listen_to_stream():
    """Runs in a background thread. Listens to /stream and prints
    incoming messages as they arrive, without blocking user input."""
    try:
        with requests.get(f"{SERVER_URL}/stream", stream=True) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    payload = decoded[len("data: "):]
                    try:
                        message = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    display_message(message)
    except requests.exceptions.ConnectionError:
        print("\n[Connection to server lost. Is the Agent Server still running?]")


def display_message(message: dict):
    msg_type = message.get("type")
    text = message.get("text", "")

    if msg_type == "notification":
        print(f"\n{text}")
    elif msg_type == "confirmation_prompt":
        print(f"\n[CONFIRM] {text}")
    elif msg_type == "chat_reply":
        print(f"\nAgent: {text}")
    else:
        print(f"\n[{msg_type}] {text}")

    print("You: ", end="", flush=True)


def send_message(message: str):
    try:
        requests.post(
            f"{SERVER_URL}/chat",
            json={"message": message, "thread_id": THREAD_ID},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        print("[Could not reach Agent Server. Is it running?]")


def main():
    print("=== StudyMate AI — CLI Client ===")
    print("Type a message and press Enter. Ctrl+C to quit.\n")

    stream_thread = threading.Thread(target=listen_to_stream, daemon=True)
    stream_thread.start()

    try:
        while True:
            user_input = input("You: ")
            if user_input.strip():
                send_message(user_input)
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()