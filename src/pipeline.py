import sys
import os
sys.path.append(os.path.dirname(__file__))

import json
import ollama
from utils import load_json, extract_json_block
from match_engine import process_extracted_item, budget_check, is_quantity_specified
from messaging import build_reply_options, translate_messages_to_cook

MODEL = "gemma4:latest"

HOUSEHOLD = load_json("data/households/household_01.json")
CATALOG = load_json("data/catalog/mock_catalog.json")

SCENARIOS = [
    {"name": "Ambiguous quantity, has history (Hindi)", "voice_note": "थोड़ा प्याज़ ले आना", "language": "Hindi"},
    {"name": "Budget-breaking request (Bengali)", "voice_note": "আমাকে পাঁচ কেজি কাজু বাদাম এনে দাও", "language": "Bengali"},
    {"name": "Routine inventory update, no history (Hindi)", "voice_note": "तेल खत्म हो गया है", "language": "Hindi"},
    {"name": "Urgent, has salt history (Hindi)", "voice_note": "नमक खत्म हो गया है, अभी खाना बना रही हूं, जल्दी चाहिए", "language": "Hindi"},
    {"name": "Urgent low-value, has salt history (Hindi)", "voice_note": "अभी थोड़ा नमक चाहिए, तुरंत", "language": "Hindi"},
    {
        "name": "Multi-item request exceeding budget (Hindi)",
        "voice_note": "तीन किलो प्याज़, आठ किलो आलू, दो किलो सर्फ एक्सेल, और पांच सौ ग्राम लहसुन ले आना",
        "language": "Hindi",
        "wallet_override": 300,
    },
]

PROMPT_TEMPLATE = """You are M's assistant helping manage a household kitchen. A cook has sent a WhatsApp voice note, already transcribed below.

Cook's voice note (in {language}): "{voice_note}"

Extract only what was said — do not decide what should happen next, and do not draft any reply.

Respond with ONLY a JSON object with these exact fields, nothing else:
{{
  "items": [
    {{"item": "...", "item_english": "...", "quantity_raw": "...", "quantity_numeric": <number or null>, "unit_english": "..."}}
  ],
  "urgency": "immediate" or "can_batch" or "not_applicable"
}}
Rules:
- "item": the item name exactly as the cook said it, in the original language.
- "item_english": your best English translation of just that item name.
- "quantity_raw": the amount exactly as the cook said it, in their own words/script.
- "quantity_numeric": convert quantity_raw into a plain number. If no specific amount was given, set this to null. Do NOT guess a number that wasn't stated.
- "unit_english": the unit in English. Set to null if quantity_numeric is null.
- List EACH distinct item the cook mentioned as a separate entry in "items".
- "urgency": "immediate" only if the cook's phrasing itself signals urgency. "can_batch" if routine, no urgency signaled. "not_applicable" if unrelated to food/inventory.
"""


def run_scenario(scenario):
    print("=" * 70)
    print(f"SCENARIO: {scenario['name']}")
    print("=" * 70)

    prompt = PROMPT_TEMPLATE.format(voice_note=scenario["voice_note"], language=scenario["language"])
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
    raw_text = response["message"]["content"]

    extracted = extract_json_block(raw_text)
    if not extracted:
        print("\n[Pipeline] Could not parse JSON — would route to human review.\n")
        return

    print("\n[LLM extracted]:", json.dumps(extracted, ensure_ascii=False))

    household_for_scenario = {
        **HOUSEHOLD,
        "wallet_balance": scenario.get("wallet_override", HOUSEHOLD["wallet_balance"]),
    }

    matched_items = []
    for item in extracted.get("items", []):
        item_with_flag = {**item, "quantity_specified": is_quantity_specified(item.get("quantity_numeric"))}
        match_result = process_extracted_item(item_with_flag, household_for_scenario, CATALOG)
        matched_items.append(match_result)
        print("\n[Match result]:", json.dumps(match_result, ensure_ascii=False, indent=2))

    priced_items = [m for m in matched_items if m.get("price") is not None]
    budget_result = None
    if priced_items:
        budget_result = budget_check(priced_items, household_for_scenario)
        print("\n[Budget check]:", json.dumps(budget_result, ensure_ascii=False, indent=2))

    reply_options = build_reply_options(matched_items)
    english_labels = [o["label"] for o in reply_options]
    translated_labels = translate_messages_to_cook(english_labels, scenario["language"])
    print("\n[Reply options for ops to choose from]:")
    for opt, translated in zip(reply_options, translated_labels):
        marker = " (recommended)" if opt.get("recommended") else ""
        print(f"  - [{opt['key']}]{marker}: {translated}")

    ops_pending = [m for m in matched_items if m.get("needs_ops_action")]
    print(f"\n[Order status]: {len(ops_pending)} item(s) pending ops action before this order can be approved.")
    print()


if __name__ == "__main__":
    for s in SCENARIOS:
        run_scenario(s)