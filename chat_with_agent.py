#!/usr/bin/env python3
"""
Simple chat client for WriteSense Agent API
"""
import requests
import json
import sys

# Configuration
API_BASE = "http://localhost:8123"
ASSISTANT_ID = "agent"

def create_thread():
    """Create a new conversation thread"""
    response = requests.post(f"{API_BASE}/threads", json={})
    if response.status_code == 200:
        return response.json()["thread_id"]
    else:
        print(f"Error creating thread: {response.text}")
        return None

def send_message(thread_id, message):
    """Send a message and get response"""
    payload = {
        "assistant_id": ASSISTANT_ID,
        "input": {
            "messages": [
                {
                    "role": "human",
                    "content": message
                }
            ]
        }
    }
    
    response = requests.post(
        f"{API_BASE}/threads/{thread_id}/runs/wait",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        # Get the last AI message
        for msg in reversed(data["messages"]):
            if msg["type"] == "ai":
                return msg["content"]
        return "No response received"
    else:
        return f"Error: {response.text}"

def stream_message(thread_id, message):
    """Send a message and stream the response"""
    payload = {
        "assistant_id": ASSISTANT_ID,
        "input": {
            "messages": [
                {
                    "role": "human",
                    "content": message
                }
            ]
        },
        "stream_mode": "updates"
    }
    
    response = requests.post(
        f"{API_BASE}/threads/{thread_id}/runs/stream",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: ' prefix
                        if 'agent' in data and 'messages' in data['agent']:
                            for msg in data['agent']['messages']:
                                if msg['type'] == 'ai':
                                    return msg['content']
                    except json.JSONDecodeError:
                        continue
    return "No response received"

def get_thread_history(thread_id):
    """Get the conversation history"""
    response = requests.get(f"{API_BASE}/threads/{thread_id}/state")
    if response.status_code == 200:
        data = response.json()
        return data["values"]["messages"]
    return []

def main():
    print("🤖 WriteSense Agent Chat Client")
    print("================================")
    print("Commands:")
    print("  /new    - Start a new conversation")
    print("  /stream - Toggle streaming mode")
    print("  /history - Show conversation history")
    print("  /quit   - Exit the chat")
    print("================================\n")
    
    # Create initial thread
    thread_id = create_thread()
    if not thread_id:
        print("Failed to create thread. Exiting.")
        return
    
    print(f"💬 Started new conversation (Thread: {thread_id[:8]}...)")
    
    streaming = False
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input == "/quit":
                print("👋 Goodbye!")
                break
            elif user_input == "/new":
                thread_id = create_thread()
                if thread_id:
                    print(f"💬 Started new conversation (Thread: {thread_id[:8]}...)")
                continue
            elif user_input == "/stream":
                streaming = not streaming
                print(f"🔄 Streaming mode: {'ON' if streaming else 'OFF'}")
                continue
            elif user_input == "/history":
                history = get_thread_history(thread_id)
                print("\n📜 Conversation History:")
                for i, msg in enumerate(history, 1):
                    role = "👤" if msg["type"] == "human" else "🤖"
                    print(f"{i}. {role} {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
                continue
            
            # Send message
            print("🤖 Agent: ", end="", flush=True)
            
            if streaming:
                response = stream_message(thread_id, user_input)
            else:
                response = send_message(thread_id, user_input)
            
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main() 