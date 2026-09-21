# 🧠 Vumbi AI – Autonomous Marketing Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with Strands SDK](https://img.shields.io/badge/Built%20with-Strands%20SDK-blueviolet)](https://strandsagents.com)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini-blue)](https://deepmind.google/technologies/gemini/)
[![Hackathon](https://img.shields.io/badge/Agents%20for%20Humans-2026-ff6b6b)](https://agentsforhumans.devpost.com)

> An autonomous, multi‑agent marketing system that monitors opportunities, makes decisions, executes actions, verifies outcomes, and learns — freeing solo founders from busywork.

---

## 🎯 The Problem

Solo founders and small-business owners spend 30%+ of their time on repetitive marketing tasks:

- Checking SEO issues across dozens of pages
- Fixing broken links and missing meta tags
- Following up with leads manually
- Creating consistent content
- Monitoring campaign performance

These tasks are highly judgment-heavy, time-consuming, and drain creative energy. Most founders cannot afford a marketing team, so they either burn out, hire expensive agencies, or stagnate.

**Vumbi AI solves this problem.**

---

## 💡 The Solution

**Vumbi AI** is a hierarchical multi‑agent system written in Python that handles marketing busywork autonomously. It is composed of:

- 🧠 **Supervisor Agent** — orchestrates the workflow and delegates tasks
- 🎯 **Specialist Agents** — SEO, Lead, and Content specialists with domain expertise
- 🔮 **Intelligent Decision Engine** — uses Gemini reasoning together with experience memory
- 🛡️ **Safety Policy** — governs actions with deterministic rules
- ✅ **Verification & Rollback** — confirms outcomes and reverses failures when needed
- 📚 **Experience Memory** — learns from past actions to improve future decisions

The system runs every 15 minutes and only surfaces when human judgment is needed.

---

## 🏗️ Architecture Overview

This system coordinates a supervisor, specialist agents, decision logic, execution, verification, and learning.

```mermaid
flowchart TD

subgraph group_runtime["Runtime Coordination"]
  node_main["Agent Cycle<br/>[main.py]"]
  node_orchestrator["Supervisor Orchestrator<br/>[orchestrator.py]"]
  node_monitor["Opportunity Monitor<br/>[monitor.py]"]
end

subgraph group_specialists["Marketing Specialists"]
  node_seo["SEO Specialist<br/>[seo.py]"]
  node_leads["Lead Specialist<br/>[leads.py]"]
  node_content["Content Specialist<br/>[content.py]"]
  node_analytics["Analytics Specialist<br/>[analytics.py]"]
end

subgraph group_intelligence["Decision Governance"]
  node_specialist_base["Specialist Reasoning<br/>[base.py]"]
  node_memory[("Experience Memory<br/>[experience.py]")]
  node_safety["Safety Policy<br/>[safety.py]"]
end

subgraph group_execution["Execution Learning"]
  node_executor["Action Executor<br/>[executor.py]"]
  node_verifier["Outcome Verifier<br/>[verifier.py]"]
  node_learner["Learning Recorder<br/>[learner.py]"]
  node_rollback["Rollback Engine<br/>[executor.py]"]
end

subgraph group_backend["Backend Integration"]
  node_api_client["Laravel API Client<br/>[api_client.py]"]
  node_laravel["Laravel Backend"]
  node_backend_db[("Marketing Database")]
end

node_operator(("Business Owner"))
node_gemini["Gemini Model"]
node_human_review(("Human Review"))

node_main -->|"runs cycle"| node_orchestrator
node_orchestrator -->|"scans opportunities"| node_monitor
node_orchestrator -->|"gathers evidence"| node_api_client
node_orchestrator -->|"delegates SEO"| node_seo
node_orchestrator -->|"delegates leads"| node_leads
node_orchestrator -->|"delegates content"| node_content
node_orchestrator -->|"delegates analytics"| node_analytics
node_seo -->|"reasons"| node_specialist_base
node_leads -->|"reasons"| node_specialist_base
node_content -->|"reasons"| node_specialist_base
node_analytics -->|"reasons"| node_specialist_base
node_specialist_base -->|"requests decision"| node_gemini
node_specialist_base -->|"analyzes patterns"| node_memory
node_specialist_base -->|"checks action"| node_safety
node_orchestrator -->|"submits action"| node_executor
node_executor -->|"executes remotely"| node_api_client
node_safety -.->|"requests approval"| node_human_review
node_human_review -.->|"approves action"| node_executor
node_executor -->|"triggers verification"| node_verifier
node_verifier -->|"measures outcome"| node_api_client
node_verifier -->|"requests rollback"| node_rollback
node_rollback -->|"reverses action"| node_api_client
node_verifier -->|"reports outcome"| node_learner
node_learner -->|"records learning"| node_memory
node_api_client -->|"calls backend"| node_laravel
node_laravel -->|"reads writes"| node_backend_db
node_operator -.->|"reviews decisions"| node_human_review

click node_main "https://github.com/dante-viq/autonomous-agent/blob/main/src/main.py"
click node_orchestrator "https://github.com/dante-viq/autonomous-agent/blob/main/src/orchestrator.py"
click node_monitor "https://github.com/dante-viq/autonomous-agent/blob/main/src/tools/monitor.py"
click node_seo "https://github.com/dante-viq/autonomous-agent/blob/main/src/specialists/seo.py"
click node_leads "https://github.com/dante-viq/autonomous-agent/blob/main/src/specialists/leads.py"
click node_content "https://github.com/dante-viq/autonomous-agent/blob/main/src/specialists/content.py"
click node_analytics "https://github.com/dante-viq/autonomous-agent/blob/main/src/specialists/analytics.py"
click node_specialist_base "https://github.com/dante-viq/autonomous-agent/blob/main/src/specialists/base.py"
click node_memory "https://github.com/dante-viq/autonomous-agent/blob/main/src/memory/experience.py"
click node_safety "https://github.com/dante-viq/autonomous-agent/blob/main/src/policies/safety.py"
click node_executor "https://github.com/dante-viq/autonomous-agent/blob/main/src/executor.py"
click node_verifier "https://github.com/dante-viq/autonomous-agent/blob/main/src/verifier.py"
click node_learner "https://github.com/dante-viq/autonomous-agent/blob/main/src/learner.py"
click node_rollback "https://github.com/dante-viq/autonomous-agent/blob/main/src/executor.py"
click node_api_client "https://github.com/dante-viq/autonomous-agent/blob/main/src/utils/api_client.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_main,node_orchestrator,node_monitor,node_human_review toneBlue
class node_seo,node_leads,node_content,node_analytics toneAmber
class node_specialist_base,node_memory,node_safety toneMint
class node_executor,node_verifier,node_learner,node_rollback toneRose
class node_api_client,node_laravel,node_backend_db,node_operator,node_gemini toneIndigo
```

---

## 🔄 How It Works

1. **Monitor** — The supervisor scans for SEO issues, pending leads, and content gaps.
2. **Delegate** — The supervisor assigns each opportunity to the right specialist.
3. **Reason** — Each specialist invokes its Strands agent loop, gathering evidence and consulting experience memory.
4. **Decide** — GeminiReasoningService proposes an action with a confidence score.
5. **Govern** — SafetyPolicy checks whether the action is permitted and reversible.
6. **Execute** — The action is executed via the Laravel API or queued for human review.
7. **Verify** — After a wait period, metrics are compared to confirm improvement.
8. **Learn** — The outcome is stored in ExperienceMemory for future decisions.
9. **Rollback** — If verification fails, the action is automatically rolled back.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PHP 8.2+ for the Laravel backend
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
- MySQL 8.0+

### 1) Clone the Repository

```bash
git clone https://github.com/Dante-VIQ/Autonomous-Agent.git
cd Autonomous-Agent
```

### 2) Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3) Install Dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure Environment

```bash
cp .env.example .env
```
Then update `.env` with values similar to:

```env
GEMINI_API_KEY=your_key_here
STRANDS_MODEL_ID=gemini-2.5-flash
LARAVEL_API_URL=http://localhost:8000/api
LARAVEL_API_KEY=your_api_key_here
BRAND_ID=1
AGENT_INTERVAL=900
```
If you prefer to use Ollama locally, set OLLAMA_HOST and OLLAMA_MODEL in .env.

### 5) Run The Agent

```bash
python run.py
```
This starts the agent loop, which will monitor and act on opportunities every AGENT_INTERVAL seconds.

### 6) Development Mode

```bash
python run.py --once   # run a single cycle and exit
```

---

## 🛠️ Tools & Components

| Component               | Purpose                                                                           |
| ----------------------- | --------------------------------------------------------------------------------- |
| Supervisor Agent        | Orchestrates the workflow and delegates tasks using Strands agent logic           |
| SEO Specialist          | Handles meta tags, broken links, rankings, and domain-specific SEO tasks          |
| Lead Specialist         | Scores leads and suggests follow-up actions based on engagement signals           |
| Content Specialist      | Identifies content gaps and generates outlines or content recommendations         |
| IntelligentDecisionTool | Combines Gemini reasoning, memory, and safety policy checks                       |
| GeminiReasoningService  | Performs structured prompting for business decisions and JSON output              |
| ExperienceMemory        | Stores past actions and calculates success patterns for future decisions          |
| SafetyPolicy            | Applies deterministic governance, risk scoring, rate limits, and tenant isolation |
| VerifyTool              | Measures before/after metrics to validate whether an action worked                |
| RollbackEngine          | Reverses failed actions such as content unpublishing or campaign resume           |
| LaravelApiService       | Centralizes backend communication with the Laravel API                            |

---

## 📁 Project Structure

```text
Autonomous-Agent/
├── src/
│   ├── __init__.py
│   ├── main.py                     # Entry point
│   ├── config.py                   # Environment config
│   ├── orchestrator.py             # Core orchestrator
│   ├── executor.py                 # Action executor with retry
│   ├── verifier.py                 # Action‑specific verification
│   ├── learner.py                  # Learning with real storage
│   ├── specialists/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseSpecialist with reason()
│   │   ├── seo.py                  # SEO specialist
│   │   ├── leads.py                # Lead specialist
│   │   ├── content.py              # Content specialist
│   │   └── analytics.py            # Analytics specialist
│   ├── policies/
│   │   ├── __init__.py
│   │   └── safety.py               # SafetyPolicy
│   ├── memory/
│   │   ├── __init__.py
│   │   └── experience.py           # ExperienceMemory
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── monitor.py              # monitor_opportunities
│   │   └── domain/
│   │       ├── __init__.py
│   │       ├── seo.py
│   │       ├── leads.py
│   │       ├── content.py
│   │       └── analytics.py
│   └── utils/
│       ├── __init__.py
│       ├── api_client.py           # Async Laravel client
│       └── logger.py               # Logging setup
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py
│   └── ...
├── .env.example
├── requirements.txt
├── pyproject.toml
├── README.md
└── run.py
```

---

## 🔐 Security & Governance

- **Tenant Isolation** — Each brand operates in its own context; the LLM never chooses its tenant.
- **Safety Policy** — Actions are rate-limited, risk-assessed, and require approval for high-impact tasks.
- **Human-in-the-Loop** — High-risk or low-confidence actions are queued for human review.
- **Rollback** — All actions are reversible; failed actions are automatically undone.
- **Audit Logging** — Every decision, execution, verification, and rollback is logged.

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run a single cycle manually
python run.py --once

# Health check (if Laravel backend is running)
curl http://localhost:8000/api/agent/health
```

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a pull request.

---

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for full details.

---

## 🙌 Acknowledgments

- Strands Agents SDK — Multi-agent orchestration
- Google Gemini — AI model provider
- Laravel — Backend API framework
- AWS — Agents for Humans Hackathon sponsor

---

## 📬 Contact

- Project: https://github.com/Dante-VIQ/Autonomous-Agent
- Hackathon: Agents for Humans 2026
