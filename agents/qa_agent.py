# agents/qa_agent.py

import os
import json
import requests
from dotenv import load_dotenv
from message_bus import send_message, get_last_message

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


# ─────────────────────────────────────────
# LLM HELPER FUNCTION
# Uses Haiku - simple review task
# ─────────────────────────────────────────

def call_llm(system_prompt, user_prompt):
    """
    Sends a prompt to OpenRouter and returns the response.
    Uses claude-3.5-haiku - fast and cheap for review tasks.
    """
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "anthropic/claude-3.5-haiku",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


# ─────────────────────────────────────────
# REVIEW HTML LANDING PAGE
# LLM checks if HTML matches product spec
# ─────────────────────────────────────────

def review_html(html_content, spec):
    """
    Uses LLM to review the HTML landing page.
    Checks if it matches the product spec.
    Returns a review with verdict and issues.
    """
    print("\n🧠 QA Agent: Reviewing HTML landing page...")

    system_prompt = """You are a strict QA engineer reviewing a landing page.
    You must return ONLY a valid JSON object. No markdown, no backticks, pure JSON."""

    user_prompt = f"""
    Review this HTML landing page against the product specification.
    
    Product Spec:
    - Value Proposition: {spec['value_proposition']}
    - Features: {[f['name'] for f in spec['features']]}
    
    HTML Content:
    {html_content[:2000]}
    
    Check:
    1. Does the headline match the value proposition?
    2. Are the features mentioned in the page?
    3. Is there a clear call-to-action button?
    4. Is the content specific to the startup idea?
    
    Return ONLY this JSON:
    {{
        "verdict": "pass" or "fail",
        "score": number between 1-10,
        "issues": [
            "specific issue 1",
            "specific issue 2"
        ],
        "positives": [
            "what was done well 1",
            "what was done well 2"
        ],
        "summary": "2 sentence overall assessment"
    }}
    """

    response = call_llm(system_prompt, user_prompt)

    # Clean response
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    review = json.loads(response)
    print(f"✅ QA Agent: HTML review complete!")
    print(f"   Verdict: {review['verdict']}")
    print(f"   Score: {review['score']}/10")
    return review


# ─────────────────────────────────────────
# REVIEW MARKETING COPY
# LLM checks if copy is compelling
# ─────────────────────────────────────────

def review_marketing_copy(copy):
    """
    Uses LLM to review the marketing copy.
    Checks tagline, email CTA, and tone.
    Returns a review with verdict and issues.
    """
    print("\n🧠 QA Agent: Reviewing marketing copy...")

    system_prompt = """You are a strict marketing QA reviewer.
    You must return ONLY a valid JSON object. No markdown, no backticks, pure JSON."""

    user_prompt = f"""
    Review this marketing copy critically.
    
    Tagline: {copy['tagline']}
    Short Description: {copy['short_description']}
    Email Subject: {copy['cold_email']['subject']}
    Email Body: {copy['cold_email']['body'][:500]}
    Twitter: {copy['social_posts']['twitter']}
    
    Check:
    1. Is the tagline under 10 words and compelling?
    2. Does the cold email have a clear call to action?
    3. Is the tone appropriate for the target audience?
    4. Are the social posts engaging and specific?
    
    Return ONLY this JSON:
    {{
        "verdict": "pass" or "fail",
        "score": number between 1-10,
        "issues": [
            "specific issue 1",
            "specific issue 2"
        ],
        "positives": [
            "what was done well 1",
            "what was done well 2"
        ],
        "summary": "2 sentence overall assessment"
    }}
    """

    response = call_llm(system_prompt, user_prompt)

    # Clean response
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
    response = response.strip()

    review = json.loads(response)
    print(f"✅ QA Agent: Marketing copy review complete!")
    print(f"   Verdict: {review['verdict']}")
    print(f"   Score: {review['score']}/10")
    return review


# ─────────────────────────────────────────
# GET PR NUMBER FROM URL
# Extracts PR number from URL for GitHub API
# ─────────────────────────────────────────

def get_pr_number(pr_url):
    """
    Extracts the PR number from the PR URL.
    e.g. https://github.com/user/repo/pull/2 → 2
    """
    return int(pr_url.split("/")[-1])


# ─────────────────────────────────────────
# GET PR COMMIT SHA
# Needed for posting inline PR comments
# ─────────────────────────────────────────

def get_pr_commit_sha(pr_number):
    """
    Gets the latest commit SHA from the PR.
    Needed to post inline review comments on GitHub.
    """
    response = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/commits",
        headers=HEADERS
    )
    commits = response.json()
    return commits[-1]["sha"]


# ─────────────────────────────────────────
# POST PR REVIEW COMMENTS ON GITHUB
# PDF requires at least 2 inline comments
# ─────────────────────────────────────────

def post_pr_review_comments(pr_url, html_review, copy_review):
    """
    Posts review comments on the GitHub PR.
    PDF requires at least 2 inline comments on the HTML file.
    """
    print("\n💬 QA Agent: Posting review comments on GitHub PR...")

    pr_number = get_pr_number(pr_url)
    commit_sha = get_pr_commit_sha(pr_number)

    # Build review comments from the issues found
    # PDF requires at least 2 inline comments on the HTML file
    comments = []

    # Comment 1 - from HTML review
    if html_review["issues"]:
        comments.append({
            "path": "index.html",
            "position": 1,
            "body": f"🔍 **QA Review - HTML Issue:**\n\n{html_review['issues'][0]}\n\n*Score: {html_review['score']}/10*"
        })

    # Comment 2 - from marketing copy review
    if copy_review["issues"]:
        comments.append({
            "path": "index.html",
            "position": 2,
            "body": f"📢 **QA Review - Marketing Copy:**\n\n{copy_review['issues'][0]}\n\n*Score: {copy_review['score']}/10*"
        })

    # Comment 3 - overall summary
    comments.append({
        "path": "index.html",
        "position": 3,
        "body": f"📋 **QA Overall Summary:**\n\n{html_review['summary']}\n\n**HTML Verdict:** {html_review['verdict'].upper()}\n**Copy Verdict:** {copy_review['verdict'].upper()}"
    })

    # Post the review to GitHub
    response = requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}/reviews",
        headers=HEADERS,
        json={
            "commit_id": commit_sha,
            "body": f"## QA Agent Review\n\n**HTML Score:** {html_review['score']}/10\n**Copy Score:** {copy_review['score']}/10\n\n{html_review['summary']}",
            "event": "COMMENT",
            "comments": comments
        }
    )

    if response.status_code == 200:
        print(f"✅ QA Agent: Review comments posted on PR!")
    else:
        print(f"❌ QA Agent: Failed to post comments: {response.json()}")


# ─────────────────────────────────────────
# SEND REVIEW REPORT TO CEO
# CEO uses this to decide next action
# ─────────────────────────────────────────

def send_review_report_to_ceo(html_review, copy_review, parent_message_id):
    """
    Sends structured review report to CEO.
    CEO will use this to decide whether to approve
    or send revision requests to agents.
    """
    print("\n📤 QA Agent: Sending review report to CEO...")

    # Overall verdict - fail if either review fails
    html_pass = html_review["verdict"].lower() in ["pass", "partial"]
    copy_pass = copy_review["verdict"].lower() in ["pass", "partial"]
    overall_verdict = "pass" if html_pass and copy_pass else "fail"

    send_message(
        from_agent="qa",
        to_agent="ceo",
        message_type="result",
        payload={
            "overall_verdict": overall_verdict,
            "html_review": html_review,
            "copy_review": copy_review,
            "issues": html_review["issues"] + copy_review["issues"],
            "recommendation": "Approve and merge" if overall_verdict == "pass" else "Request revisions from agents"
        },
        parent_message_id=parent_message_id
    )

    print(f"   Overall Verdict: {overall_verdict.upper()}")


# ─────────────────────────────────────────
# MAIN QA AGENT FUNCTION
# ─────────────────────────────────────────

def run_qa_agent():
    """
    Main function that runs the QA agent lifecycle:
    1. Read HTML and marketing copy from message bus
    2. Review HTML using LLM
    3. Review marketing copy using LLM
    4. Post review comments on GitHub PR
    5. Send pass/fail report to CEO
    """
    print("\n" + "="*50)
    print("🤖 QA AGENT STARTING")
    print("="*50)

    # Step 1: Read task from message bus
    # CEO sends both HTML content and marketing copy
    task_message = get_last_message("qa")

    if not task_message:
        print("❌ QA Agent: No task found in message bus!")
        return None

    payload = task_message["payload"]
    parent_id = task_message["message_id"]

    html_content = payload["html_content"]
    marketing_copy = payload["marketing_copy"]
    pr_url = payload["pr_url"]
    spec = payload["spec"]

    print(f"📥 Received task from CEO")
    print(f"   PR URL: {pr_url}")

    # Step 2: Review HTML using LLM
    html_review = review_html(html_content, spec)

    # Step 3: Review marketing copy using LLM
    copy_review = review_marketing_copy(marketing_copy)

    # Step 4: Post review comments on GitHub PR
    post_pr_review_comments(pr_url, html_review, copy_review)

    # Step 5: Send review report to CEO
    send_review_report_to_ceo(html_review, copy_review, parent_id)

    print("\n✅ QA Agent: All done!")
    return {
        "html_review": html_review,
        "copy_review": copy_review
    }


