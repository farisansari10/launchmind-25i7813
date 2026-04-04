# message_bus.py

import uuid          # generates unique IDs for each message
from datetime import datetime  # for creating timestamps

# This is the shared message bus
# Think of it as a group WhatsApp - each agent has their own inbox
# When CEO wants to send to Product, it drops message in product's list
message_bus = {
    "ceo": [],
    "product": [],
    "engineer": [],
    "marketing": [],
    "qa": []
}

def send_message(from_agent, to_agent, message_type, payload, parent_message_id=None):
    # Build the message following exact schema from PDF Section 4.1
    message = {
        "message_id": str(uuid.uuid4()),  # unique ID like "a3f2b1-..."
        "from_agent": from_agent,          # who sent it e.g. "ceo"
        "to_agent": to_agent,              # who receives it e.g. "product"
        "message_type": message_type,      # "task", "result", "revision_request", "confirmation"
        "payload": payload,                # actual content - different for each message
        "timestamp": datetime.utcnow().isoformat() + "Z",  # e.g. "2026-04-03T10:00:00Z"
        "parent_message_id": parent_message_id  # links reply to original message
    }

    # Drop message into recipient's inbox
    message_bus[to_agent].append(message)

    # Print to terminal so we can see messages live during demo
    # This is important - evaluator must see messages in terminal
    print(f"\n📨 MESSAGE SENT")
    print(f"   FROM:    {from_agent}")
    print(f"   TO:      {to_agent}")
    print(f"   TYPE:    {message_type}")
    print(f"   ID:      {message['message_id']}")
    print(f"   TIME:    {message['timestamp']}")

    return message  # return message so sender can store the message_id

def get_messages(agent_name):
    # Returns ALL messages in an agent's inbox
    return message_bus[agent_name]

def get_last_message(agent_name):
    # Returns only the most recent message
    # Used when an agent just needs to read its latest instruction
    messages = message_bus[agent_name]
    if messages:
        return messages[-1]
    return None  # returns None if inbox is empty

def get_full_history():
    # Collects ALL messages from ALL agents and sorts by time
    # This is what you show evaluator when they ask
    # "show me every message the CEO sent and received"
    all_messages = []
    for agent, messages in message_bus.items():
        all_messages.extend(messages)
    all_messages.sort(key=lambda x: x["timestamp"])
    return all_messages

def print_full_history():
    # Prints complete message history in readable format
    # Call this at the end of main.py for the demo
    print("\n" + "="*50)
    print("📋 FULL MESSAGE HISTORY")
    print("="*50)
    history = get_full_history()
    for msg in history:
        print(f"\n[{msg['timestamp']}]")
        print(f"  FROM:    {msg['from_agent']}")
        print(f"  TO:      {msg['to_agent']}")
        print(f"  TYPE:    {msg['message_type']}")
        print(f"  ID:      {msg['message_id']}")
        if msg['parent_message_id']:
            print(f"  REPLY TO: {msg['parent_message_id']}")
    print("\n" + "="*50)