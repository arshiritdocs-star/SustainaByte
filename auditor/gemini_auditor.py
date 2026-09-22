"""
Sustainable AI Lifecycle Auditor – powered by Gemini.

Uses the official google-genai SDK to generate an Eco-Nutrition Label
comparing the greenest qualifying model against the most carbon-intensive one.
"""

import os
import time
import json
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# ── Configuration ────────────────────────────────────────────────────────────
DEBUG_MODE = True  # Set True to skip real API calls and use a fake response

# ── Environment & Client ────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))

_api_key = os.getenv("GEMINI_API_KEY")
_api_key_backup = os.getenv("GEMINI_API_KEY_BACKUP")
print(f"[DEBUG] .env loaded from: {os.path.join(_PROJECT_ROOT, '.env')}")
print(f"[DEBUG] GEMINI_API_KEY loaded: {'YES (non-empty)' if _api_key else 'NO (missing or empty)'}")
print(f"[DEBUG] GEMINI_API_KEY_BACKUP loaded: {'YES (non-empty)' if _api_key_backup else 'NO (missing or empty)'}")
print(f"[DEBUG] Model target: gemini-3.5-flash-lite")
print(f"[DEBUG] DEBUG_MODE: {DEBUG_MODE}")

client = None

if not DEBUG_MODE:
    client = genai.Client()

# ── Fake response for DEBUG_MODE ─────────────────────────────────────────────
_FAKE_GEMINI_RESPONSE = """\
# Eco-Nutrition Label: DEBUG MODE

### 1. Energy Efficiency Grade
**A** (Winning Model: identified by lowest lifecycle carbon)

### 2. Total Avoided CO2e
**4,200 kg CO2e**

### 3. Migration Trade-off Analysis
* **Accuracy:** Minor drop of ~3% from the worst model, well within SLA tolerance.
* **Latency:** Significant improvement — winner responds 4x faster.
* **Carbon Impact:** 84% reduction in total lifecycle emissions.
* **Operational Cost:** Lower compute requirements translate to ~60% infrastructure savings.
* **Risk:** Smaller model may underperform on edge-case queries requiring deep reasoning.
"""


def run_lifecycle_audit(workload_desc, target_acc, max_lat, audited_models):
    """Run a lifecycle carbon audit and return a Gemini-generated
    Eco-Nutrition Label in Markdown.

    Parameters
    ----------
    workload_desc : str
        Free-text description of the ML workload / use-case.
    target_acc : float
        Minimum acceptable accuracy (0-100).
    max_lat : float
        Maximum acceptable latency in milliseconds.
    audited_models : list[dict]
        Each dict must contain: name, accuracy, latency_ms,
        total_lifecycle_carbon_kg.

    Returns
    -------
    str
        Markdown-formatted Eco-Nutrition Label, or an error / fallback string.
    """

    # ── 1. Filter models that meet accuracy & latency constraints ────────
    valid_models = [
        m for m in audited_models
        if m.get("accuracy", 0) >= target_acc
        and m.get("latency_ms", float("inf")) <= max_lat
    ]

    if not valid_models:
        return (
            "## ⚠️ Audit Warning\n\n"
            "**No architectures meet the strict SLAs.**\n\n"
            f"- Required accuracy ≥ **{target_acc}%**\n"
            f"- Required latency ≤ **{max_lat} ms**\n\n"
            "Please relax the thresholds or add more candidate models."
        )

    # ── 2. Identify the winner (lowest carbon) and worst (highest carbon) ─
    winner = min(valid_models, key=lambda m: m["total_lifecycle_carbon_kg"])
    worst = max(valid_models, key=lambda m: m["total_lifecycle_carbon_kg"])

    print(f"[DEBUG] Valid models after filtering: {[m['name'] for m in valid_models]}")
    print(f"[DEBUG] Winner (lowest carbon): {winner['name']} ({winner['total_lifecycle_carbon_kg']} kg)")
    print(f"[DEBUG] Worst  (highest carbon): {worst['name']} ({worst['total_lifecycle_carbon_kg']} kg)")

    # ── 3. Build the prompt ──────────────────────────────────────────────
    prompt = (
        "You are a **Sustainable AI Lifecycle Auditor**.\n\n"
        "Your job is to evaluate two machine-learning models on their full "
        "lifecycle carbon footprint and produce a concise, developer-friendly "
        "**Eco-Nutrition Label** formatted in Markdown.\n\n"
        "The label MUST include exactly these sections:\n\n"
        "1. **Energy Efficiency Grade** – a letter grade from A+ (best) to F "
        "(worst) for the winning (greenest) model, based on its total lifecycle "
        "carbon relative to the worst model.\n"
        "2. **Total Avoided CO2e** – the exact difference in kg CO2e between "
        "the worst model and the winning model, shown as a positive number.\n"
        "3. **Migration Trade-off Analysis** – a concise (3-5 bullet) analysis "
        "of what a team gains and loses by switching from the worst model to "
        "the winning model (accuracy, latency, carbon, operational cost "
        "implications).\n\n"
        "Output ONLY the Markdown label. Do not add any preamble or closing "
        "remarks.\n\n"
        "---\n\n"
        f"### Workload\n{workload_desc}\n\n"
        f"### Winning Model (Greenest)\n"
        f"```json\n{json.dumps(winner, indent=2, default=str)}\n```\n\n"
        f"### Worst Model (Most Carbon-Intensive)\n"
        f"```json\n{json.dumps(worst, indent=2, default=str)}\n```\n\n"
        "Generate the **Eco-Nutrition Label** now."
    )

    # ── 4. DEBUG_MODE: return fake response without hitting the API ───────
    if DEBUG_MODE:
        print("[DEBUG] DEBUG_MODE=True — skipping real API call, returning fake response.")
        return _FAKE_GEMINI_RESPONSE

    # ── 5. Call Gemini via Chat session (primary key → backup key → mock) ─
    _model = "gemini-3.5-flash-lite"
    print(f"[DEBUG] Sending request to model: {_model}")

    return _call_gemini_with_fallback(_model, prompt)


def _call_gemini_with_fallback(model, prompt):
    """Try primary key, swap to backup on 429, then fall back to mock."""

    # ── Attempt 1: primary key ───────────────────────────────────────────
    try:
        chat = client.chats.create(model=model)
        response = chat.send_message(prompt)
        print("[DEBUG] Success with primary GEMINI_API_KEY")
        return response.text
    except errors.ClientError as e:
        print(f"[DEBUG] 1st attempt failed — {type(e).__name__}: {e}")
        if "RESOURCE_EXHAUSTED" in str(e):
            # 429 quota error → try backup key
            print("[DEBUG] 429 detected — switching to GEMINI_API_KEY_BACKUP...")
            return _try_backup_key(model, prompt)
        else:
            # Other ClientError (404, etc.) → go straight to mock
            print("[DEBUG] Non-quota error — skipping backup key, returning mock data...")
            return _mock_fallback()
    except errors.ServerError as e:
        print(f"[DEBUG] 1st attempt failed — {type(e).__name__}: {e}")
        print("Google API busy. Retrying in 2 seconds...")
        time.sleep(2)
        # Retry once with same key
        try:
            chat = client.chats.create(model=model)
            response = chat.send_message(prompt)
            print("[DEBUG] Success with primary GEMINI_API_KEY (2nd attempt)")
            return response.text
        except (errors.ServerError, errors.ClientError) as e2:
            print(f"[DEBUG] 2nd attempt failed — {type(e2).__name__}: {e2}")
            print("Google API still busy. Returning mock data...")
            return _mock_fallback()


def _try_backup_key(model, prompt):
    """Create a new client with the backup key and attempt the call."""
    backup_key = os.getenv("GEMINI_API_KEY_BACKUP")
    if not backup_key:
        print("[DEBUG] No GEMINI_API_KEY_BACKUP found — returning mock data...")
        return _mock_fallback()

    try:
        backup_client = genai.Client(api_key=backup_key)
        chat = backup_client.chats.create(model=model)
        response = chat.send_message(prompt)
        print("[DEBUG] Success with GEMINI_API_KEY_BACKUP")
        return response.text
    except (errors.ServerError, errors.ClientError) as e:
        print(f"[DEBUG] Backup key also failed — {type(e).__name__}: {e}")
        print("Google API still busy. Returning mock data...")
        return _mock_fallback()


def _mock_fallback():
    """Return the hardcoded mock Eco-Nutrition Label."""
    return (
        "### 🍃 AI Eco-Nutrition Label (Mock Fallback)\n"
        "Energy Efficiency Grade: A-\n"
        "Total Avoided Carbon: 4,200 kg CO2e\n\n"
        "Trade-off Analysis:\n\n"
        "The recommended architecture reduces lifecycle emissions by 84%.\n\n"
        "Accuracy drops by only 2.5%, remaining perfectly within your SLA constraints."
    )


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    # 3 distinct models: one fails accuracy, one fails latency, one passes
    mock_models = [
        {
            "name": "70B Cloud GPU",
            "accuracy": 96,
            "latency_ms": 350,        # ← FAILS latency SLA (> 200 ms)
            "total_lifecycle_carbon_kg": 5200,
        },
        {
            "name": "14B Distilled",
            "accuracy": 85,            # ← FAILS accuracy SLA (< 90%)
            "latency_ms": 60,
            "total_lifecycle_carbon_kg": 1400,
        },
        {
            "name": "8B Quantized Edge",
            "accuracy": 91,            # ✅ passes accuracy (≥ 90)
            "latency_ms": 42,          # ✅ passes latency  (≤ 200)
            "total_lifecycle_carbon_kg": 780,
        },
    ]

    print("=" * 60)
    print("TEST 1: target_acc=90, max_lat=200 → only '8B Quantized Edge' should pass")
    print("=" * 60)
    result = run_lifecycle_audit("Customer Support Bot", 90, 200, mock_models)
    print(result)

    print("\n" + "=" * 60)
    print("TEST 2: target_acc=80, max_lat=400 → all 3 pass, '8B Quantized Edge' wins on carbon")
    print("=" * 60)
    result2 = run_lifecycle_audit("Customer Support Bot", 80, 400, mock_models)
    print(result2)

    print("\n" + "=" * 60)
    print("TEST 3: target_acc=97, max_lat=30 → NONE pass")
    print("=" * 60)
    result3 = run_lifecycle_audit("Customer Support Bot", 97, 30, mock_models)
    print(result3)
