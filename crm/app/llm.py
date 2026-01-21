import os
from typing import Dict, Any
import requests


def generate_sales_followup_markdown(person: Dict[str, Any]) -> str:
    """
    Generate a rich, conversion-focused markdown body for the CRM task
    using a local LLM (Ollama). Falls back to a static template if the
    LLM call fails, so callers can rely on always getting a usable body.
    """
    full_name = f"{person['name']['firstName']} {person['name']['lastName']}"
    email = person["emails"]["primaryEmail"]

    # Feature flag to disable LLM usage without code changes.
    enable_llm = os.getenv("ENABLE_LLM_COPYWRITING", "true").lower() == "true"
    if not enable_llm:
        return _fallback_template(full_name, email)

    prompt = f"""
You are a senior car sales representative, you are the best sales guy in the world. 
Create a short, high-conversion follow-up note
for a sales rep in markdown format (no code fences).

Customer details:
- Name: {full_name}
- Email: {email}

Requirements:
- Use engaging headings with emojis, for example:
  - "## 🔥 Hot Lead – Action Required"
  - "### 🎯 Key Context"
- Use **bold** for important words and phrases.
- You can use simple HTML spans for subtle color accents, e.g.:
  - <span style="color:#16a34a;font-weight:bold;">High priority</span>
- Structure:
  1. A strong one-line hook that motivates the rep to act now.
  2. A short context section about the customer (2–3 bullet points).
  3. A "Next steps" checklist with 3–5 bullets focused on **closing the sale**:
     - discovery questions
     - identifying budget and timeline
     - proposing the next commitment (call/demo/visit)
- Keep it under 180 words.
- Do NOT include any markdown code fences or backticks in the output.
"""

    try:
        # Ollama local API – choose any of your installed models, e.g. "llama3.1:8b"
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                },
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("response") or "").strip()

        if len(text) > 80:
            return text
    except Exception:
        # On any failure, fall back to static template so task creation still works.
        pass

    return _fallback_template(full_name, email)


def _fallback_template(full_name: str, email: str) -> str:
    """Static body used when LLM is disabled or unavailable."""
    return f"""
## 🔥 CUSTOMER FOLLOW-UP REQUIRED

**Name:** {full_name}  
**Email:** {email}

- Call customer
- Understand requirements
- Update CRM
""".strip()

