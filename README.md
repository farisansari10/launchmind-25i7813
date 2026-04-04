# 🍱 LaunchMind — SnackAlert

A Multi-Agent System (MAS) where autonomous AI agents collaborate to launch **SnackAlert** — a platform where restaurants list end-of-day unsold food at a discount so customers get cheap quality meals and restaurants reduce food waste.

Built for FAST NUCES Agentic AI / Multi-Agent Systems Assignment.

---

## 💡 Startup Idea

**SnackAlert** connects budget-conscious customers with restaurants offering end-of-day meals at 50-70% discount. Restaurants reduce food waste and recover lost revenue. Customers get quality meals at a fraction of the price. Available daily from 8PM–11PM.

**Target Users:** Restaurant owners + budget-conscious customers  
**Core Feature:** Restaurants post leftover food with price and pickup time; customers browse and claim it  
**Revenue Model:** 10% commission per sale from restaurants

---

## 🤖 Agent Architecture

[You run main.py]
│
▼
[CEO Agent] ──────────────────────────────────────┐
│                                          │
├──── task ──▶ [Product Agent]             │
│                    │                     │
│              spec to both                │
│         ┌──────────┴──────────┐          │
│         ▼                     ▼          │
│  [Engineer Agent]    [Marketing Agent]   │
│         │                     │          │
│   PR+Issue URL          Email+Slack      │
│         └──────────┬──────────┘          │
│                    │                     │
│◀─── results ───────┘                     │
│                                          │
├──── reviews output (LLM) ────────────────┘
│         │
│         ├── approved → continue
│         └── revision_needed → sends revision_request back
│
├──── task ──▶ [QA Agent]
│                    │
│              reviews HTML + copy
│              posts PR comments
│◀─── pass/fail ─────┘
│
└──── posts final summary to Slack

### Agent Responsibilities

| Agent | Model | Responsibility |
|---|---|---|
| CEO | claude-sonnet-4 | Orchestrates everything, reviews outputs, feedback loops |
| Product | claude-3.5-haiku | Generates value prop, personas, features, user stories |
| Engineer | gpt-4o-mini | Writes HTML landing page, commits to GitHub, opens PR |
| Marketing | gemini-2.5-flash | Writes copy, sends email, posts to Slack |
| QA | claude-3.5-haiku | Reviews HTML + copy, posts PR comments, sends verdict |

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/farisansari10/launchmind-25i7813.git
cd launchmind-25i7813
```

### 2. Install dependencies
```bash
pip3 install crewai requests python-dotenv sendgrid
```

### 3. Set up environment variables
Copy `.env.example` to `.env` and fill in your real API keys:
```bash
cp .env.example .env
```

Required keys:

OPENROUTER_API_KEY=your-openrouter-key
GITHUB_TOKEN=your-github-pat
GITHUB_REPO=yourusername/your-repo-name
SLACK_BOT_TOKEN=your-slack-bot-token
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=your-verified-sender-email

### 4. Run the system
```bash
python3 main.py
```

---

## 🌐 Platform Integrations

| Platform | Agent | What it does |
|---|---|---|
| **GitHub** | Engineer | Creates branch, commits index.html, opens PR, creates issue |
| **GitHub** | QA | Posts inline review comments on the PR |
| **Slack** | Marketing | Posts launch message with tagline + PR link using Block Kit |
| **Slack** | CEO | Posts final summary message after all agents complete |
| **SendGrid** | Marketing | Sends cold outreach email with LLM-generated subject + body |
| **OpenRouter** | All agents | LLM calls for reasoning, generation, and review |

---

## 🔗 Links

- **GitHub PR (Engineer Agent):** https://github.com/farisansari10/launchmind-25i7813/pull/7
- **GitHub Issue (Engineer Agent):** https://github.com/farisansari10/launchmind-25i7813/issues/6

### Slack Workspace
[Screenshots below show the bot in action]

![Slack Screenshot](slack_screenshot.png)

---

## 👤 Group Members

| Name | Student ID | Agent Built |
|---|---|---|
| Faris Ansari | 25i-7813 | CEO, Product, Engineer, Marketing, QA |

---

## 📁 Repository Structure

launchmind-snackalert/
├── agents/
│   ├── ceo_agent.py        # Orchestrator - decomposes idea, reviews outputs
│   ├── product_agent.py    # Generates product specification
│   ├── engineer_agent.py   # Builds landing page, commits to GitHub
│   ├── marketing_agent.py  # Sends email, posts to Slack
│   └── qa_agent.py         # Reviews HTML + copy, posts PR comments
├── main.py                 # Single entry point - runs entire system
├── message_bus.py          # Shared messaging implementation
├── requirements.txt        # All dependencies
├── .env.example            # Template for environment variables
└── .gitignore              # Ensures .env is never committed

---

## 💬 Message Bus

Agents communicate using **Option A: Shared Python Dictionary** from Section 4.2.

Every message follows the required schema:
```json
{
    "message_id": "uuid",
    "from_agent": "ceo",
    "to_agent": "product",
    "message_type": "task",
    "payload": {},
    "timestamp": "2026-04-04T13:15:15Z",
    "parent_message_id": null
}
```

---

## 🔄 Feedback Loops

**Loop 1:** CEO reviews Product spec → sends revision_request if not specific enough

**Loop 2:** QA reviews HTML + copy → sends pass/fail to CEO → CEO sends revision_request to Engineer if fail

---

## 🎯 Bonus Features Implemented

- ✅ QA Agent (+5%)
- ✅ Mixed LLM providers — Claude, GPT-4o-mini, Gemini (+2%)

