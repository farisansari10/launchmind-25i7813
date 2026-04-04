# agents/engineer_agent.py

import os
import json
import base64
import requests
from dotenv import load_dotenv
from message_bus import send_message, get_last_message

load_dotenv()

# GitHub config loaded from .env - never hardcoded
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


# ─────────────────────────────────────────
# LLM HELPER FUNCTION
# Uses gpt-4o-mini - great at writing code
# ─────────────────────────────────────────

def call_llm(system_prompt, user_prompt):
    """
    Sends a prompt to OpenRouter and returns the response text.
    Uses gpt-4o-mini because it's excellent at writing HTML/CSS
    """
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ─────────────────────────────────────────
# GENERATE HTML LANDING PAGE
# LLM writes complete HTML + CSS
# ─────────────────────────────────────────

def generate_landing_page(spec):
    """
    Uses LLM to generate a complete HTML landing page
    based on the product specification.
    Must include: headline, subheadline, features section,
    call-to-action button, and basic CSS styling
    """
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
    Use a clean color scheme - white background with green accents 
    (green fits the food/sustainability theme).
    """

    html_content = call_llm(system_prompt, user_prompt)

    # Clean response if LLM added backticks
    html_content = html_content.strip()
    if html_content.startswith("```"):
        html_content = html_content.split("```")[1]
        if html_content.startswith("html"):
            html_content = html_content[4:]
    html_content = html_content.strip()

    print("✅ Engineer Agent: Landing page generated!")
    return html_content


# ─────────────────────────────────────────
# GET BASE SHA
# We need the latest commit SHA to create a branch
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
# Creates a new branch called agent-landing-page
# ─────────────────────────────────────────

def create_branch(base_sha, branch_name="agent-landing-page"):
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
# Encodes HTML as base64 and commits to branch
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

    # If file exists, include its SHA so GitHub allows the update
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
# Creates issue titled 'Initial landing page'
# with LLM-generated description
# ─────────────────────────────────────────

def create_github_issue(spec):
    """
    Creates a GitHub issue titled 'Initial landing page'
    with a description generated by the LLM.
    Returns the issue URL.
    """
    print("\n📋 Engineer Agent: Creating GitHub issue...")

    # Use LLM to generate the issue description
    system_prompt = "You are a software engineer writing a GitHub issue. Be concise and technical."

    user_prompt = f"""
    Write a GitHub issue description for building a landing page for this startup:
    Value proposition: {spec['value_proposition']}
    Features to showcase: {[f['name'] for f in spec['features']]}
    
    Keep it under 150 words. Include what needs to be built and why.
    Return plain text only, no markdown headers.
    """

    issue_description = call_llm(system_prompt, user_prompt)

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
# Opens PR with LLM-generated title and body
# ─────────────────────────────────────────

def open_pull_request(spec, branch_name):
    """
    Opens a pull request on GitHub.
    Title and body are generated by the LLM.
    Returns the PR URL.
    """
    print("\n🔀 Engineer Agent: Opening pull request...")

    # Use LLM to generate PR title and body
    system_prompt = "You are a software engineer writing a GitHub pull request. Be professional and concise."

    user_prompt = f"""
    Write a pull request title and body for a landing page built for this startup:
    Value proposition: {spec['value_proposition']}
    
    Return ONLY this JSON:
    {{
        "title": "PR title here",
        "body": "PR body here - what was built and why, under 100 words"
    }}
    No markdown, no backticks. Pure JSON only.
    """

    pr_content = call_llm(system_prompt, user_prompt)

    # Clean and parse response
    pr_content = pr_content.strip()
    if pr_content.startswith("```"):
        pr_content = pr_content.split("```")[1]
        if pr_content.startswith("json"):
            pr_content = pr_content[4:]
    pr_content = pr_content.strip()

    pr_data = json.loads(pr_content)

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
# PDF requires PR URL and issue URL sent to CEO
# ─────────────────────────────────────────

def send_results_to_ceo(pr_url, issue_url, parent_message_id):
    """
    Sends PR URL and GitHub issue URL back to CEO
    as required by the PDF
    """
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
import time
def run_engineer_agent():
    """
    Main function that runs the Engineer agent lifecycle:
    1. Read product spec from message bus
    2. Generate HTML landing page using LLM
    3. Create GitHub branch
    4. Commit HTML to GitHub
    5. Create GitHub issue
    6. Open pull request
    7. Send PR URL and issue URL back to CEO
    """
    print("\n" + "="*50)
    print("🤖 ENGINEER AGENT STARTING")
    print("="*50)

    # Step 1: Read product spec from message bus
    # Product agent sends spec to engineer's inbox
    task_message = get_last_message("engineer")

    if not task_message:
        print("❌ Engineer Agent: No task found in message bus!")
        return None

    spec = task_message["payload"]
    parent_id = task_message["message_id"]

    print(f"📥 Received product spec from Product agent")
    print(f"   Value Proposition: {spec['value_proposition']}")

    # Step 2: Generate HTML landing page using LLM
    html_content = generate_landing_page(spec)

    # Step 3: Get base SHA and create branch
    base_sha = get_base_sha()
    branch_name = create_branch(base_sha, f"agent-landing-page-{int(time.time())}")

    # Step 4: Commit HTML file to GitHub
    commit_html_to_github(html_content, branch_name)

    # Step 5: Create GitHub issue
    issue_url = create_github_issue(spec)

    # Step 6: Open pull request
    pr_url = open_pull_request(spec, branch_name)

    # Step 7: Send results back to CEO
    if pr_url and issue_url:
        send_results_to_ceo(pr_url, issue_url, parent_id)

    print("\n✅ Engineer Agent: All done!")
    return pr_url, issue_url, html_content #add html content here


