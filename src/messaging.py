import ollama

TRANSLATION_PROMPT = """Translate the following messages into {language} for a household cook —
keep it short, natural, and simple, since the cook may have low literacy.
Return ONLY the translated lines, one per line, in the same order, no numbering or extra text.

Messages:
{messages}
"""


def build_reply_options(matched_items):
    """
    Builds a small set of consolidated reply options for ops to choose from —
    one option per DECISION (confirm / ask quantity / ask timing / flag issue),
    not one message per item. The first option present is marked recommended
    based on the overall order state.
    """
    needs_clarification_items = [
        m.get("translated_item") or m.get("source_item_text")
        for m in matched_items if m.get("needs_cook_reply")
    ]
    unresolved_items = [
        m.get("translated_item") or m.get("source_item_text")
        for m in matched_items if m.get("status") in ("unmapped_item", "no_catalog_match")
    ]
    resolved_count = len([m for m in matched_items if m.get("chosen_sku")])

    options = []

    if needs_clarification_items:
        options.append({"key": "ask_quantity", "label": f"How much {', '.join(needs_clarification_items)} do you need?"})

    if unresolved_items:
        options.append({"key": "ask_clarify_item", "label": f"Checking on {', '.join(unresolved_items)} — one moment."})

    if resolved_count:
        options.append({"key": "confirm_all", "label": "Ok, I'll arrange everything."})

    options.append({"key": "ask_timing", "label": "Do you need this right now, or can it wait?"})

    for i, opt in enumerate(options):
        opt["recommended"] = (i == 0)

    return options


def translate_messages_to_cook(messages, language, model="gemma4:latest"):
    if not messages:
        return []
    if language.lower() == "english":
        return messages

    prompt = TRANSLATION_PROMPT.format(language=language, messages="\n".join(messages))
    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    translated = response["message"]["content"].strip()
    lines = [l.strip() for l in translated.split("\n") if l.strip()]

    if len(lines) != len(messages):
        return messages  # fall back to English rather than risk a misaligned translation
    return lines