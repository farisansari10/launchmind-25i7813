# agents/product_agent.py

import os
import json
import requests
from dotenv import load_dotenv
from message_bus import send_message, get_last_message

load_dotenv()

# ─────────────────────────────────────────
# LLM HELPER FUNCTION
# Same pattern as CEO agent but uses Haiku
# (cheaper, fast enough for structured output)
# ─────────────────────────────────────────

def call_llm(system_prompt, user_prompt):
    """
    Sends a prompt to OpenRouter and returns the response text.
    """
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "anthropic/claude-haiku-4.5",  # cheaper model, perfect for structured output
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ─────────────────────────────────────────
# GENERATE PRODUCT SPECIFICATION
# Uses LLM to create the full product spec
# Returns exact JSON structure required by PDF
# ─────────────────────────────────────────

def generate_product_spec(idea, task):
    """
    Uses LLM to generate a complete product specification.
    Returns a dictionary with value_proposition, personas,
    features, and user_stories exactly as PDF requires.
    """
    print("\n🧠 Product Agent: Generating product specification...")

    system_prompt = """You are an experienced product manager. You create detailed, 
    specific product specifications. You must return ONLY a valid JSON object with 
    no extra text, no markdown, no backticks. Just pure JSON."""

    user_prompt = f"""
    Startup idea: {idea}
    Your task: {task}
    
    Generate a complete product specification. Return ONLY this exact JSON structure:
    {{
        "value_proposition": "One sentence describing what the product does and for whom",
        "personas": [
            {{
                "name": "persona name",
                "role": "their role e.g. Restaurant Owner",
                "pain_point": "their specific pain point"
            }},
            {{
                "name": "persona name",
                "role": "their role e.g. Budget-conscious Student",
                "pain_point": "their specific pain point"
            }},
            {{
                "name": "persona name",
                "role": "their role",
                "pain_point": "their specific pain point"
            }}
        ],
        "features": [
            {{
                "name": "feature name",
                "description": "what this feature does",
                "priority": 1
            }},
            {{
                "name": "feature name",
                "description": "what this feature does",
                "priority": 2
            }},
            {{
                "name": "feature name",
                "description": "what this feature does",
                "priority": 3
            }},
            {{
                "name": "feature name",
                "description": "what this feature does",
                "priority": 4
            }},
            {{
                "name": "feature name",
                "description": "what this feature does",
                "priority": 5
            }}
        ],
        "user_stories": [
            {{
                "as_a": "user type",
                "i_want": "action they want to do",
                "so_that": "benefit they get"
            }},
            {{
                "as_a": "user type",
                "i_want": "action they want to do",
                "so_that": "benefit they get"
            }},
            {{
                "as_a": "user type",
                "i_want": "action they want to do",
                "so_that": "benefit they get"
            }}
        ]
    }}
    
    Make everything specific to the startup idea. No generic responses.
    """

    
    response = call_llm(system_prompt, user_prompt)

    # Strip markdown backticks if LLM wrapped response in them
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    spec = json.loads(response)

    print("✅ Product Agent: Specification generated!")
    print(f"   Value Proposition: {spec['value_proposition']}")
    print(f"   Personas: {len(spec['personas'])} defined")
    print(f"   Features: {len(spec['features'])} features")
    print(f"   User Stories: {len(spec['user_stories'])} stories")

    return spec


# ─────────────────────────────────────────
# SEND SPEC TO ENGINEER AND MARKETING
# PDF requires spec goes to BOTH agents
# ─────────────────────────────────────────

def send_spec_to_agents(spec, parent_message_id):
    """
    Sends the product specification to both
    Engineer agent and Marketing agent as required by PDF
    """
    print("\n📤 Product Agent: Sending spec to Engineer and Marketing agents...")

    # Send to Engineer agent
    msg_to_engineer = send_message(
        from_agent="product",
        to_agent="engineer",
        message_type="result",
        payload=spec,
        parent_message_id=parent_message_id
    )

    # Send to Marketing agent
    msg_to_marketing = send_message(
        from_agent="product",
        to_agent="marketing",
        message_type="result",
        payload=spec,
        parent_message_id=parent_message_id
    )

    return msg_to_engineer, msg_to_marketing


# ─────────────────────────────────────────
# SEND CONFIRMATION TO CEO
# PDF requires confirmation sent back to CEO
# ─────────────────────────────────────────

def send_confirmation_to_ceo(spec, parent_message_id):
    """
    Sends a short confirmation back to CEO
    indicating the product spec is ready
    """
    print("\n📤 Product Agent: Sending confirmation to CEO...")

    send_message(
        from_agent="product",
        to_agent="ceo",
        message_type="confirmation",
        payload={
            "status": "spec_ready",
            "value_proposition": spec["value_proposition"],
            "feature_count": len(spec["features"]),
            "persona_count": len(spec["personas"])
        },
        parent_message_id=parent_message_id
    )


# ─────────────────────────────────────────
# MAIN PRODUCT AGENT FUNCTION
# ─────────────────────────────────────────

def run_product_agent():
    """
    Main function that runs the Product agent lifecycle:
    1. Read task from message bus
    2. Generate product spec using LLM
    3. Send spec to Engineer and Marketing
    4. Send confirmation to CEO
    """
    print("\n" + "="*50)
    print("🤖 PRODUCT AGENT STARTING")
    print("="*50)

    # Step 1: Read task from message bus
    task_message = get_last_message("product")

    if not task_message:
        print("❌ Product Agent: No task found in message bus!")
        return None

    idea = task_message["payload"]["idea"]
    task = task_message["payload"]["task"]
    parent_id = task_message["message_id"]

    print(f"📥 Received task from CEO: {task[:80]}...")

    # Step 2: Generate product spec using LLM
    spec = generate_product_spec(idea, task)

    # Step 3: Send spec to Engineer and Marketing agents
    send_spec_to_agents(spec, parent_id)

    # Step 4: Send confirmation back to CEO
    send_confirmation_to_ceo(spec, parent_id)

    print("\n✅ Product Agent: All done!")
    return spec
