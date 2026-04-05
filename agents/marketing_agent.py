# agents/marketing_agent.py

import os
import ssl
import certifi
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from message_bus import send_message, get_last_message, call_llm_json

load_dotenv()

# Fix Mac SSL certificate issue
ssl._create_default_https_context = ssl.create_default_context
os.environ['SSL_CERT_FILE'] = certifi.where()

MARKETING_MODEL = "google/gemini-2.0-flash-001"


# ─────────────────────────────────────────
# GENERATE ALL MARKETING COPY
# ─────────────────────────────────────────

def generate_marketing_copy(spec):
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

    copy = call_llm_json(MARKETING_MODEL, system_prompt, user_prompt)

    print("✅ Marketing Agent: Copy generated!")
    print(f"   Tagline: {copy['tagline']}")
    print(f"   Subject: {copy['cold_email']['subject']}")
    print(f"   Twitter: {copy['social_posts']['twitter'][:60]}...")
    print(f"   LinkedIn: {copy['social_posts']['linkedin'][:60]}...")
    print(f"   Instagram: {copy['social_posts']['instagram'][:60]}...")

    return copy


# ─────────────────────────────────────────
# SEND EMAIL VIA SENDGRID
# ─────────────────────────────────────────

def send_email(copy):
    print("\n📧 Marketing Agent: Sending email via SendGrid...")

    message = Mail(
        from_email=os.getenv("SENDGRID_FROM_EMAIL"),
        to_emails=os.getenv("SENDGRID_FROM_EMAIL"),
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
# ─────────────────────────────────────────

def post_to_slack(copy, pr_url):
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
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🐦 Twitter:* {copy['social_posts']['twitter']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💼 LinkedIn:* {copy['social_posts']['linkedin'][:200]}..."
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📸 Instagram:* {copy['social_posts']['instagram']}"
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
# ─────────────────────────────────────────

def send_copy_to_ceo(copy, parent_message_id):
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
    print("\n" + "="*50)
    print("🤖 MARKETING AGENT STARTING")
    print("="*50)

    task_message = get_last_message("marketing")

    if not task_message:
        print("❌ Marketing Agent: No task found in message bus!")
        return None

    spec = task_message["payload"]
    parent_id = task_message["message_id"]

    print(f"📥 Received product spec from Product agent")
    print(f"   Value Proposition: {spec['value_proposition']}")

    copy = generate_marketing_copy(spec)
    send_email(copy)

    if not pr_url:
        pr_url = "https://github.com/placeholder/pr"
    post_to_slack(copy, pr_url)
    send_copy_to_ceo(copy, parent_id)

    print("\n✅ Marketing Agent: All done!")
    return copy