"""
llm_engine.py
Talks to a LOCALLY installed Llama 3.2 model served by Ollama (https://ollama.com).
100% free / offline - no API key, no cloud billing.

Enhanced for African Agricultural Extension:
- Injects full farm operational context: active batches, feed inventory, vaccination due dates,
  mortality rates, crop plots, financial cash position, and local weather flags.
- WhatsApp-ready response styling with practical numbers and actionable steps.
"""

import json
import requests
import datetime
from modules import database, market_data

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"
TIMEOUT = 8


def is_ollama_running(host: str = DEFAULT_HOST) -> bool:
    try:
        r = requests.get(f"{host}/api/tags", timeout=TIMEOUT)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def list_local_models(host: str = DEFAULT_HOST):
    try:
        r = requests.get(f"{host}/api/tags", timeout=TIMEOUT)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except requests.exceptions.RequestException:
        pass
    return []


SYSTEM_PROMPT_TEMPLATE = """You are "Agri_OS Africa AI" - the senior agricultural extension officer \
and farm business advisor for smallholder and commercial farmers across Sub-Saharan Africa.

Your job is NOT to write long academic essays or generic disclaimers. You provide DIRECT, \
PRACTICAL, NUMERICAL, and ACTIONABLE guidance tailored to the realities of African farming \
(high feed costs, unpredictable power/heat, tropical disease vectors, cash-flow constraints, and local markets).

Format your response cleanly (like an experienced advisor chatting on WhatsApp):
• *Direct Verdict & Numbers First*: Tell the farmer exact quantities (kg of feed, bags, selling prices, costs).
• *Today's Action Steps*: What should the farmer physically do right now?
• *Profit & Cost Impact*: Express figures in the farm's local currency ({currency}).
• *Veterinary / Weather Caution*: Highlight any urgent risk (heat stress, vaccine due, biosecurity).

Always leverage the live farm data provided below.

=== LIVE FARM SITUATION ===
{farm_context}
=== END LIVE FARM SITUATION ===
"""


def build_holistic_farm_context(farm_id: int) -> tuple[str, str]:
    """Compile active batches, inventory, upcoming vaccines, cash position, and prices into context."""
    farm = database.get_farm(farm_id)
    if not farm:
        return "No farm profile registered.", "NGN"

    currency = farm.get("currency") or "NGN"
    lines = [
        f"Farm Name: {farm['name']}",
        f"Location: {farm.get('country', 'Nigeria')} ({farm.get('region', 'West Africa')})",
        f"Primary Focus: {farm.get('farm_type', 'Mixed')}",
        f"Operating Currency: {currency}",
    ]

    # Active livestock batches
    batches = database.get_livestock_batches(farm_id, status="active")
    if batches:
        b_lines = []
        for b in batches:
            mort = database.get_batch_mortality_summary(b["id"])
            b_lines.append(
                f"Batch #{b['id']} ({b['species']}): {b['count']} remaining (started with {mort['initial_count']}, "
                f"lost {mort['total_dead']} [{mort['mortality_pct']}% mortality]). Age: {b.get('age_weeks', '-')} weeks. "
                f"Feed price: {currency} {b.get('feed_price_per_kg', 0)}/kg"
            )
        lines.append("Active Livestock Batches:\n  " + "\n  ".join(b_lines))
    else:
        lines.append("Active Livestock Batches: None currently registered.")

    # Feed inventory & low stock alerts
    inventory = database.get_feed_inventory(farm_id)
    if inventory:
        inv_lines = [f"{item['feed_name']}: {item['quantity_bags']:.1f} bags ({item['total_kg']:.0f} kg remaining)" for item in inventory]
        lines.append("Feed Inventory in Store:\n  " + "\n  ".join(inv_lines))
    low_feed = database.get_low_feed_alerts(farm_id)
    if low_feed:
        lines.append("⚠️ CRITICAL FEED WARNING: " + ", ".join(f"{i['feed_name']} is below minimum stock ({i['quantity_bags']} bags left)" for i in low_feed))

    # Upcoming vaccinations
    upcoming_vacs = database.get_upcoming_vaccinations_for_farm(farm_id, days_ahead=7)
    if upcoming_vacs:
        lines.append("⏰ URGENT VACCINATIONS DUE THIS WEEK: " + "; ".join(f"{v['vaccine_name']} on {v['due_date']} for Batch #{v['batch_id']}" for v in upcoming_vacs))

    # Active crop plots
    plots = database.get_crop_plots(farm_id, status="active")
    if plots:
        p_lines = [f"Plot #{p['id']}: {p['crop']} ({p['area_ha']} ha), planted on {p['planting_date']}, soil: {p.get('soil_type', 'standard')}" for p in plots]
        lines.append("Active Crop Plots:\n  " + "\n  ".join(p_lines))

    # Financial position
    txs = database.get_transactions(farm_id)
    if txs:
        income = sum(t["amount"] for t in txs if t["tx_type"] == "income")
        expense = sum(t["amount"] for t in txs if t["tx_type"] == "expense")
        net = income - expense
        lines.append(f"Financial Position: Total Income {currency} {income:,.0f} | Total Expense {currency} {expense:,.0f} | Net Cash Balance: {currency} {net:,.0f}")

    return "\n".join(lines), currency


def build_farm_context(context: dict) -> str:
    lines = []
    for key, value in context.items():
        if value in (None, "", [], {}):
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "No farm data recorded yet."


def generate_extension_advice(question: str, farm_id: int = None, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST, channel: str = "web"):
    """Holistic extension query handler used for both web UI and WhatsApp/SMS gateway."""
    if farm_id:
        context_str, currency = build_holistic_farm_context(farm_id)
    else:
        context_str, currency = "No farm selected.", "NGN"

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(currency=currency, farm_context=context_str)
    
    # Ingest recent chat history
    history = database.get_chat_history(farm_id, limit=6) if farm_id else []
    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    success, reply = chat_once(messages, model=model, host=host)
    if success and farm_id:
        database.save_chat_message(farm_id, "user", question, channel=channel)
        database.save_chat_message(farm_id, "assistant", reply, channel=channel)
    return success, reply


def chat_once(messages, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
    try:
        r = requests.post(
            f"{host}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        if r.status_code == 200:
            return True, r.json().get("message", {}).get("content", "")
        return False, f"Ollama returned status {r.status_code}. Is '{model}' pulled?"
    except requests.exceptions.ConnectionError:
        return False, (
            "⚠️ Local Llama 3.2 model unreachable. Start Ollama (`ollama serve`) and ensure `ollama pull llama3.2` has completed."
        )
    except requests.exceptions.RequestException as e:
        return False, f"⚠️ Error communicating with Ollama: {e}"


def stream_chat(messages, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
    try:
        with requests.post(
            f"{host}/api/chat",
            json={"model": model, "messages": messages, "stream": True},
            stream=True,
            timeout=120,
        ) as r:
            if r.status_code != 200:
                yield f"⚠️ Ollama returned status {r.status_code}. Check that '{model}' is available."
                return
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        yield "⚠️ **Local AI model unreachable.** Ensure `ollama serve` is running in your terminal."
    except requests.exceptions.RequestException as e:
        yield f"⚠️ Unexpected error talking to Ollama: {e}"
