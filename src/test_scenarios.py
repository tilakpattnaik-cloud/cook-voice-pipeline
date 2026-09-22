import ollama
import json

MODELS = ["gemma4:latest"]

SCENARIOS = [
    {
        "name": "Ambiguous quantity (Hindi)",
        "context": "Household monthly budget: ₹12,000. Remaining balance this month: ₹2,500. No prior order history for this item.",
        "voice_note": "थोड़ा प्याज़ ले आना",
        "language": "Hindi",
    },
    {
        "name": "Budget-breaking request (Bengali)",
        "context": "Household monthly budget: ₹12,000. Remaining balance this month: ₹2,500. Cashews cost approximately ₹850 per kg.",
        "voice_note": "আমাকে পাঁচ কেজি কাজু বাদাম এনে দাও",
        "language": "Bengali",
    },
    {
        "name": "Routine inventory update, no urgency (Hindi)",
        "context": "Household monthly budget: ₹12,000. Remaining balance this month: ₹2,500.",
        "voice_note": "तेल खत्म हो गया है",
        "language": "Hindi",
    },
    {
        "name": "Urgent inventory depletion (Hindi)",
        "context": "Household monthly budget: ₹12,000. Remaining balance this month: ₹2,500.",
        "voice_note": "नमक खत्म हो गया है, अभी खाना बना रही हूं, जल्दी चाहिए",
        "language": "Hindi",
    },
    {
        "name": "Urgent, low-value single item — sets up free-delivery bundling test (Hindi)",
        "context": "Household monthly budget: ₹12,000. Remaining balance this month: ₹2,500. Salt costs approximately ₹20 per packet.",
        "voice_note": "अभी थोड़ा नमक चाहिए, तुरंत",
        "language": "Hindi",
    },
]

PROMPT_TEMPLATE = """You are M's assistant helping manage a household kitchen. A cook has sent a WhatsApp voice note, already transcribed below.

Context: {context}

Cook's voice note (in {language}): "{voice_note}"

Your job is ONLY to extract what was said — do not decide what should happen next or when.

Respond in two parts:

PART 1 - A JSON object with these exact fields:
{{
  "items": [{{"item": "...", "quantity": "...", "unit": "..."}}],
  "urgency": "immediate" or "can_batch" or "not_applicable",
  "quantity_specified": true or false,
  "budget_exceeded": true or false
}}
Rules:
- "urgency": "immediate" only if the cook's phrasing itself signals urgency (e.g. "need it right now", "cooking today", "जल्दी चाहिए", "अभी चाहिए"). "can_batch" if it's a routine mention with no urgency signaled. "not_applicable" if the message isn't about food or inventory at all.
- "quantity_specified": true only if an actual amount/number was given — a vague word like "a little" or "some" does NOT count as specified.
- "budget_exceeded": true only if the total cost of the requested items would exceed the "remaining balance this month" stated in context. Do not compare against the full monthly budget — compare against what's actually left.
- Do not guess a quantity that wasn't stated.

PART 2 - A short message to send back to the cook, written in {language}, followed by its English translation on a new line.
"""

for scenario in SCENARIOS:
    print("=" * 70)
    print(f"SCENARIO: {scenario['name']}")
    print("=" * 70)
    prompt = PROMPT_TEMPLATE.format(**scenario)

    for m in MODELS:
        print(f"\n--- {m} ---")
        try:
            response = ollama.chat(model=m, messages=[{"role": "user", "content": prompt}])
            print(response["message"]["content"])
        except Exception as e:
            print(f"Failed: {e}")
    print()