# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

> **Note:** Vumbi AI is currently in active development. Only the latest stable release receives security updates. We encourage users to always run the latest version.

---

## Reporting a Vulnerability

We take security seriously at Vumbi AI. If you believe you have found a security vulnerability, please report it to us as soon as possible.

**Please DO NOT report security vulnerabilities through public GitHub issues, discussions, or pull requests.** This ensures the issue can be properly addressed before disclosure.

**To report a vulnerability:**

1. **Email us directly:**  
   📧 **[vumbiventures@gmail.com](mailto:vumbiventures@gmail.com)** – _Use this email for all security reports._

2. **Include as much detail as possible:**
   - A clear description of the issue
   - Steps to reproduce the vulnerability
   - The version(s) affected
   - Any potential impact or exploit scenario
   - (Optional) Suggested fix or mitigation

3. **What to expect:**
   - **Acknowledgment:** You will receive a confirmation of receipt within **48 hours**.
   - **Investigation:** We will investigate the reported issue and determine its severity and impact.
   - **Updates:** We will provide regular updates on our progress toward a fix.
   - **Disclosure:** Once a fix is available, we will publicly disclose the issue with credit to the reporter (unless you prefer to remain anonymous).

---

## Responsible Disclosure

We believe in responsible disclosure. We kindly ask that you:

- Give us reasonable time to investigate and fix the issue before any public disclosure.
- Do not exploit the vulnerability for any purpose other than reporting it to us.
- Do not disclose the issue publicly until we have released a fix or confirmed it is no longer a risk.

---

## Security Best Practices for Users

If you are self‑hosting Vumbi AI, we recommend the following:

- **Keep your API keys secure** – Never commit `.env` files to version control. Use environment variables or secret management tools.
- **Use strong API keys** – Your `LARAVEL_API_KEY` and `AGENT_API_KEY` should be long, random strings.
- **Limit access** – Restrict access to your Laravel API endpoints to trusted IPs or networks when possible.
- **Keep dependencies up to date** – Regularly update Python packages, PHP dependencies, and your AI model versions.
- **Enable HTTPS** – Always use TLS/SSL in production to protect data in transit.
- **Monitor logs** – Review `storage/logs/laravel.log` and agent logs periodically for suspicious activity.

---

## Security Features Built into Vumbi AI

| Feature | Description |
| ------- | ----------- |
| **API Key Authentication** | All agent ↔ Laravel API requests require a valid `X-API-Key` header. |
| **Tenant Isolation** | Each brand operates in its own context; the agent cannot access data from other tenants. |
| **Safety Policy** | A deterministic governance layer prevents the LLM from executing high‑risk actions without approval. |
| **Human‑in‑the‑Loop** | High‑risk or low‑confidence actions are queued for human review. |
| **Rollback Engine** | Failed actions can be automatically undone (content unpublish, campaign resume, etc.). |
| **Audit Logging** | Every decision, execution, verification, and rollback is logged in `guardian_audit_logs`. |

---

## Acknowledgments

We would like to thank the security community and our users for helping us keep Vumbi AI safe and reliable. If you report a valid security issue, we will add your name to our acknowledgments page (with your permission).

---

**Last updated:** September 2026
