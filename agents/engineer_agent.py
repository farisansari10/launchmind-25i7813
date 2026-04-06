# agents/engineer_agent.py

import os
import json
import base64
import time
import requests
from dotenv import load_dotenv
from message_bus import send_message, get_last_message, call_llm, call_llm_json, message_bus

load_dotenv()

ENGINEER_MODEL = "openai/gpt-4o-mini"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


# ─────────────────────────────────────────
# GENERATE HTML LANDING PAGE
# ─────────────────────────────────────────

def generate_landing_page(spec):
    print("\n🧠 Engineer Agent: Generating HTML landing page...")

    system_prompt = """You are an expert frontend developer.
    You write clean, complete, well-styled HTML pages.
    Return ONLY the raw HTML code. No explanations, no markdown, no backticks.
    Just pure HTML starting with <!DOCTYPE html>"""

    user_prompt = f"""
    Create a complete, beautiful HTML landing page for this startup:

    Value Proposition: {spec['value_proposition']}

    Features:
    {json.dumps(spec['features'], indent=2)}

    The landing page MUST include:
    1. A headline based on the value proposition
    2. A subheadline explaining the product
    3. A features section listing all {len(spec['features'])} features
    4. A call-to-action button that says "Get Early Access"
    5. Basic but attractive CSS styling inline in a <style> tag
    6. A footer with the startup name

    Make it look professional and modern.
    Use a clean color scheme - white background with green accents.
    """

    html_content = call_llm(ENGINEER_MODEL, system_prompt, user_prompt)

    # Clean response if LLM added backticks
    html_content = html_content.strip()
    if html_content.startswith("```"):
        html_content = html_content.split("```")[1]
        if html_content.startswith("html"):
            html_content = html_content[4:]
    html_content = html_content.strip()

    print("✅ Engineer Agent: Landing page generated!")
    return html_content

def generate_improved_landing_page(spec, feedback):
    """
    Generates an improved HTML landing page based on QA feedback.
    Called when CEO sends a revision_request to Engineer.
    """
    print("\n🧠 Engineer Agent: Generating IMPROVED HTML landing page based on QA feedback...")

    system_prompt = """You are an expert frontend developer.
    You write clean, complete, well-styled HTML pages.
    Return ONLY the raw HTML code. No explanations, no markdown, no backticks.
    Just pure HTML starting with <!DOCTYPE html>"""

    user_prompt = f"""
    You previously built a landing page for this startup:
    Value Proposition: {spec['value_proposition']}
    Features: {[f['name'] for f in spec['features']]}

    The QA team reviewed it and found these specific issues:
    {feedback}

    Create an improved, complete HTML landing page that:
    1. Fixes ALL the issues mentioned in the QA feedback
    2. Includes ALL {len(spec['features'])} features clearly
    3. Has a strong headline matching the value proposition
    4. Has a clear "Get Early Access" call-to-action button
    5. Has professional green color scheme
    6. Is noticeably better than the previous version

    Return ONLY the raw HTML. No backticks, no explanations.
    """

    html_content = call_llm(ENGINEER_MODEL, system_prompt, user_prompt)

    # Clean response
    html_content = html_content.strip()
    if html_content.startswith("```"):
        html_content = html_content.split("```")[1]
        if html_content.startswith("html"):
            html_content = html_content[4:]
    html_content = html_content.strip()

    print("✅ Engineer Agent: Improved landing page generated!")
    return html_content

# ─────────────────────────────────────────
# GET BASE SHA
# ─────────────────────────────────────────

def get_base_sha():
    response = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/main",
        headers=HEADERS
    )
    sha = response.json()["object"]["sha"]
    print(f"✅ Engineer Agent: Got base SHA: {sha[:7]}...")
    return sha


# ─────────────────────────────────────────
# CREATE GITHUB BRANCH
# ─────────────────────────────────────────

def create_branch(base_sha, branch_name):
    print("\n🔧 Engineer Agent: Creating GitHub branch...")

    response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
        headers=HEADERS,
        json={
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
    )

    if response.status_code == 201:
        print(f"✅ Engineer Agent: Branch '{branch_name}' created!")
    elif response.status_code == 422:
        print("⚠️ Engineer Agent: Branch already exists, continuing...")
    else:
        print(f"❌ Engineer Agent: Branch creation failed: {response.json()}")

    return branch_name


# ─────────────────────────────────────────
# COMMIT HTML FILE TO GITHUB
# ─────────────────────────────────────────

def commit_html_to_github(html_content, branch_name):
    print("\n📁 Engineer Agent: Committing HTML file to GitHub...")

    content_encoded = base64.b64encode(html_content.encode()).decode()

    # Check if file already exists on this branch
    existing = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html",
        headers=HEADERS,
        params={"ref": branch_name}
    )

    payload = {
        "message": "Add SnackAlert landing page - generated by EngineerAgent",
        "content": content_encoded,
        "branch": branch_name,
        "author": {
            "name": "EngineerAgent",
            "email": "agent@launchmind.ai"
        }
    }

    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]

    response = requests.put(
        f"https://api.github.com/repos/{GITHUB_REPO}/contents/index.html",
        headers=HEADERS,
        json=payload
    )

    if response.status_code in [200, 201]:
        print("✅ Engineer Agent: index.html committed to GitHub!")
    else:
        print(f"❌ Engineer Agent: Commit failed: {response.json()}")

    return response.status_code in [200, 201]


# ─────────────────────────────────────────
# CREATE GITHUB ISSUE
# ─────────────────────────────────────────

def create_github_issue(spec):
    print("\n📋 Engineer Agent: Creating GitHub issue...")

    system_prompt = "You are a software engineer writing a GitHub issue. Be concise and technical."

    user_prompt = f"""
    Write a GitHub issue description for building a landing page for this startup:
    Value proposition: {spec['value_proposition']}
    Features to showcase: {[f['name'] for f in spec['features']]}

    Keep it under 150 words. Include what needs to be built and why.
    Return plain text only, no markdown headers.
    """

    issue_description = call_llm(ENGINEER_MODEL, system_prompt, user_prompt)

    response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues",
        headers=HEADERS,
        json={
            "title": "Initial landing page",
            "body": issue_description
        }
    )

    if response.status_code == 201:
        issue_url = response.json()["html_url"]
        print(f"✅ Engineer Agent: GitHub issue created!")
        print(f"   Issue URL: {issue_url}")
        return issue_url
    else:
        print(f"❌ Engineer Agent: Issue creation failed: {response.json()}")
        return None


# ─────────────────────────────────────────
# OPEN PULL REQUEST
# ─────────────────────────────────────────

def open_pull_request(spec, branch_name):
    print("\n🔀 Engineer Agent: Opening pull request...")

    system_prompt = "You are a software engineer writing a GitHub pull request. Be professional and concise. Return only JSON."

    user_prompt = f"""
    Write a pull request title and body for a landing page built for this startup:
    Value proposition: {spec['value_proposition']}

    Return ONLY this JSON:
    {{
        "title": "PR title here",
        "body": "PR body here - what was built and why, under 100 words"
    }}
    """

    pr_data = call_llm_json(ENGINEER_MODEL, system_prompt, user_prompt)

    response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
        headers=HEADERS,
        json={
            "title": pr_data["title"],
            "body": pr_data["body"],
            "head": branch_name,
            "base": "main"
        }
    )

    if response.status_code == 201:
        pr_url = response.json()["html_url"]
        print(f"✅ Engineer Agent: Pull request opened!")
        print(f"   PR URL: {pr_url}")
        return pr_url
    else:
        print(f"❌ Engineer Agent: PR creation failed: {response.json()}")
        return None


# ─────────────────────────────────────────
# SEND RESULTS BACK TO CEO
# ─────────────────────────────────────────

def send_results_to_ceo(pr_url, issue_url, parent_message_id):
    print("\n📤 Engineer Agent: Sending results to CEO...")

    send_message(
        from_agent="engineer",
        to_agent="ceo",
        message_type="result",
        payload={
            "pr_url": pr_url,
            "issue_url": issue_url,
            "status": "completed",
            "files_committed": ["index.html"]
        },
        parent_message_id=parent_message_id
    )


# ─────────────────────────────────────────
# MAIN ENGINEER AGENT FUNCTION
# ─────────────────────────────────────────

def run_engineer_agent():
    print("\n" + "="*50)
    print("🤖 ENGINEER AGENT STARTING")
    print("="*50)

    task_message = get_last_message("engineer")

    if not task_message:
        print("❌ Engineer Agent: No task found in message bus!")
        return None

    # Handle both result (product spec) and revision_request message types
    if task_message["message_type"] == "revision_request":
        # CEO sent revision request - get original spec from earlier message
        # Find the product spec message in engineer's inbox
        engineer_messages = message_bus["engineer"]
        spec_message = None
        for msg in engineer_messages:
            if msg["message_type"] == "result" and msg["from_agent"] == "product":
                spec_message = msg
                break

        if not spec_message:
            print("❌ Engineer Agent: No product spec found!")
            return None

        spec = spec_message["payload"]
        feedback = task_message["payload"]["feedback"]
        parent_id = task_message["message_id"]

        print(f"📥 Received revision request from CEO")
        print(f"   Feedback: {feedback[:80]}...")

        # Generate IMPROVED HTML with feedback
        html_content = generate_improved_landing_page(spec, feedback)

    else:
        # Normal product spec message
        spec = task_message["payload"]
        parent_id = task_message["message_id"]
        feedback = None

        print(f"📥 Received product spec from Product agent")
        print(f"   Value Proposition: {spec['value_proposition']}")

        # Generate HTML landing page
        html_content = generate_landing_page(spec)

    # GitHub actions
    base_sha = get_base_sha()
    branch_name = create_branch(base_sha, f"agent-landing-page-{int(time.time())}")
    commit_html_to_github(html_content, branch_name)
    issue_url = create_github_issue(spec)
    pr_url = open_pull_request(spec, branch_name)

    if pr_url and issue_url:
        send_results_to_ceo(pr_url, issue_url, parent_id)

    print("\n✅ Engineer Agent: All done!")
    return pr_url, issue_url, html_content