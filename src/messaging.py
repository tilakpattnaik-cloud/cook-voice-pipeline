import ollama

TRANSLATION_PROMPT = """Translate the following messages into {language} for a household cook —
keep it short, natural, and simple, since the cook may have low literacy.
Return ONLY the translated lines, one per line, in the same order, no numbering or extra text.

Messages:
{messages}
"""


def build_reply_options(matched_items):
    unavailable_items = [
        m.get("translated_item") or m.get("source_item_text")
        for m in matched_items if m.get("status") == "unavailable"
    ]
    resolved_count = len([m for m in matched_items if m.get("price") is not None])

    options = []

    if unavailable_items:
        options.append({"key": "ask_clarify_item", "label": f"Checking on {', '.join(unavailable_items)} — one moment."})

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
        return messages
    return lines