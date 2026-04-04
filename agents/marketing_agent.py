# agents/marketing_agent.py
import re
import os
import json
import ssl
import certifi
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from message_bus import send_message, get_last_message

load_dotenv()

# Fix Mac SSL certificate issue
ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()


# ─────────────────────────────────────────
# LLM HELPER FUNCTION
# Uses Gemini Flash - great at creative copy
# ─────────────────────────────────────────

def call_llm(system_prompt, user_prompt):
    """
    Sends a prompt to OpenRouter and returns the response.
    Uses Gemini Flash - excellent at creative marketing copy.
    """
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ─────────────────────────────────────────
# GENERATE ALL MARKETING COPY
# LLM generates tagline, description,
# cold email, and social media posts
# ─────────────────────────────────────────

def generate_marketing_copy(spec):
    """
    Uses LLM to generate all marketing copy:
    - tagline (under 10 words)
    - short product description (2-3 sentences)  
    - cold outreach email
    - 3 social media posts
    Returns a dictionary with all copy.
    """
    print("\n🧠 Marketing Agent: Generating marketing copy...")

    system_prompt = """You are an expert growth marketer and copywriter.
    You write compelling, specific marketing copy.
    Return ONLY a valid JSON object. No markdown, no backticks, pure JSON."""

    user_prompt = f"""
    Write marketing copy for this startup:
    
    Value Proposition: {spec['value_proposition']}
    Target Users: {[p['role'] for p in spec['personas']]}
    Key Features: {[f['name'] for f in spec['features']]}
    
    Return ONLY this exact JSON:
    {{
        "tagline": "under 10 words, punchy and memorable",
        "short_description": "2-3 sentences describing the product for a landing page",
        "cold_email": {{
            "subject": "email subject line",
            "body": "cold outreach email body - 3-4 paragraphs, personalized, clear call to action"
        }},
        "social_posts": {{
            "twitter": "tweet under 280 characters with relevant hashtags",
            "linkedin": "professional linkedin post 2-3 paragraphs",
            "instagram": "instagram caption with emojis and hashtags"
        }}
    }}
    
    Make everything specific to the startup idea. No generic copy.
    """

    response = call_llm(system_prompt, user_prompt)

    # Clean response if LLM wrapped in backticks
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    # Remove trailing commas before } or ] which are invalid JSON
    response = re.sub(r',\s*([}\]])', r'\1', response)

    copy = json.loads(response)

    print("✅ Marketing Agent: Copy generated!")
    print(f"   Tagline: {copy['tagline']}")
    print(f"   Subject: {copy['cold_email']['subject']}")

    return copy


# ─────────────────────────────────────────
# SEND EMAIL VIA SENDGRID
# PDF requires real email sent to real inbox
# ─────────────────────────────────────────

def send_email(copy):
    """
    Sends the cold outreach email via SendGrid.
    Subject and body are LLM-generated.
    Sent to test email address.
    """
    print("\n📧 Marketing Agent: Sending email via SendGrid...")

    message = Mail(
        from_email=os.getenv("SENDGRID_FROM_EMAIL"),
        to_emails=os.getenv("SENDGRID_FROM_EMAIL"),  # sending to yourself as test
        subject=copy["cold_email"]["subject"],
        html_content=f"<p>{copy['cold_email']['body'].replace(chr(10), '<br>')}</p>"
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Marketing Agent: Email sent! Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Marketing Agent: Email failed: {e}")
        return False


# ─────────────────────────────────────────
# POST TO SLACK WITH BLOCK KIT
# PDF requires Block Kit formatting
# Must include tagline, description, PR link
# ─────────────────────────────────────────

def post_to_slack(copy, pr_url):
    """
    Posts a formatted message to Slack #launches channel.
    Uses Block Kit as required by PDF.
    Must include tagline, one-line description, and PR link.
    """
    print("\n💬 Marketing Agent: Posting to Slack...")

    token = os.getenv("SLACK_BOT_TOKEN")

    payload = {
        "channel": "#launches",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🍱 {copy['tagline']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": copy["short_description"]
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Status:* 🚀 Ready for review"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Twitter:* {copy['social_posts']['twitter']}"
                }
            }
        ]
    }

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json=payload
    )

    result = response.json()
    if result["ok"]:
        print("✅ Marketing Agent: Posted to Slack #launches!")
    else:
        print(f"❌ Marketing Agent: Slack post failed: {result['error']}")


# ─────────────────────────────────────────
# SEND COPY BACK TO CEO
# PDF requires all copy sent back as structured JSON
# ─────────────────────────────────────────

def send_copy_to_ceo(copy, parent_message_id):
    """
    Sends all generated marketing copy back to CEO
    as a structured JSON message.
    """
    print("\n📤 Marketing Agent: Sending copy to CEO...")

    send_message(
        from_agent="marketing",
        to_agent="ceo",
        message_type="result",
        payload={
            "status": "completed",
            "tagline": copy["tagline"],
            "short_description": copy["short_description"],
            "cold_email": copy["cold_email"],
            "social_posts": copy["social_posts"]
        },
        parent_message_id=parent_message_id
    )


# ─────────────────────────────────────────
# MAIN MARKETING AGENT FUNCTION
# ─────────────────────────────────────────

def run_marketing_agent(pr_url=None):
    """
    Main function that runs the Marketing agent lifecycle:
    1. Read product spec from message bus
    2. Generate all marketing copy using LLM
    3. Send real email via SendGrid
    4. Post to Slack with Block Kit
    5. Send all copy back to CEO
    """
    print("\n" + "="*50)
    print("🤖 MARKETING AGENT STARTING")
    print("="*50)

    # Step 1: Read product spec from message bus
    task_message = get_last_message("marketing")

    if not task_message:
        print("❌ Marketing Agent: No task found in message bus!")
        return None

    spec = task_message["payload"]
    parent_id = task_message["message_id"]

    print(f"📥 Received product spec from Product agent")
    print(f"   Value Proposition: {spec['value_proposition']}")

    # Step 2: Generate all marketing copy using LLM
    copy = generate_marketing_copy(spec)

    # Step 3: Send real email via SendGrid
    send_email(copy)

    # Step 4: Post to Slack with Block Kit
    # PDF says Marketing agent needs PR URL before posting to Slack
    if not pr_url:
        pr_url = "https://github.com/placeholder/pr"
    post_to_slack(copy, pr_url)

    # Step 5: Send all copy back to CEO
    send_copy_to_ceo(copy, parent_id)

    print("\n✅ Marketing Agent: All done!")
    return copy



    