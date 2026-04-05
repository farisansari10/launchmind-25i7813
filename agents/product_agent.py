# agents/product_agent.py

import os
import json
from dotenv import load_dotenv
from message_bus import send_message, get_last_message, call_llm_json

load_dotenv()

PRODUCT_MODEL = "anthropic/claude-3.5-haiku"


# ─────────────────────────────────────────
# GENERATE PRODUCT SPECIFICATION
# ─────────────────────────────────────────

def generate_product_spec(idea, task):
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

    spec = call_llm_json(PRODUCT_MODEL, system_prompt, user_prompt)

    print("✅ Product Agent: Specification generated!")
    print(f"   Value Proposition: {spec['value_proposition']}")
    print(f"   Personas: {len(spec['personas'])} defined")
    print(f"   Features: {len(spec['features'])} features")
    print(f"   User Stories: {len(spec['user_stories'])} stories")

    return spec


# ─────────────────────────────────────────
# SEND SPEC TO ENGINEER AND MARKETING
# ─────────────────────────────────────────

def send_spec_to_agents(spec, parent_message_id):
    print("\n📤 Product Agent: Sending spec to Engineer and Marketing agents...")

    msg_to_engineer = send_message(
        from_agent="product",
        to_agent="engineer",
        message_type="result",
        payload=spec,
        parent_message_id=parent_message_id
    )

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
# ─────────────────────────────────────────

def send_confirmation_to_ceo(spec, parent_message_id):
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
    print("\n" + "="*50)
    print("🤖 PRODUCT AGENT STARTING")
    print("="*50)

    task_message = get_last_message("product")

    if not task_message:
        print("❌ Product Agent: No task found in message bus!")
        return None

    idea = task_message["payload"]["idea"]
    task = task_message["payload"]["task"]
    parent_id = task_message["message_id"]

    print(f"📥 Received task from CEO: {task[:80]}...")

    spec = generate_product_spec(idea, task)
    send_spec_to_agents(spec, parent_id)
    send_confirmation_to_ceo(spec, parent_id)

    print("\n✅ Product Agent: All done!")
    return spec