import sys
import os
import tempfile
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import ollama
from faster_whisper import WhisperModel
from utils import load_json, extract_json_block
from match_engine import (
    process_extracted_item,
    budget_check,
    is_quantity_specified,
    estimate_cost_for_request,
)
from messaging import build_reply_options, translate_messages_to_cook

st.set_page_config(page_title="M — Cook Voice Note Pipeline", layout="wide")

MODEL = "gemma4:latest"
LANGUAGE_CODE_MAP = {"Hindi": "hi", "Bengali": "bn", "English": "en"}


@st.cache_resource
def load_data():
    household = load_json("data/households/household_01.json")
    catalog = load_json("data/catalog/mock_catalog.json")
    return household, catalog


@st.cache_resource
def load_whisper_model():
    return WhisperModel("small", device="cpu", compute_type="int8")


def transcribe_audio(audio_file, language_hint=None):
    model = load_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_file.getvalue())
        tmp_path = tmp.name
    try:
        segments, _ = model.transcribe(tmp_path, language=language_hint)
        return " ".join(seg.text for seg in segments).strip()
    finally:
        os.remove(tmp_path)


HOUSEHOLD, CATALOG = load_data()

PROMPT_TEMPLATE = """You are M's assistant helping manage a household kitchen. A cook has sent a WhatsApp voice note, already transcribed below.

Cook's voice note (in {language}): "{voice_note}"

Extract only what was said — do not decide what should happen next, and do not draft any reply.
The transcript may contain errors from speech-to-text (garbled or nonsense fragments).

Respond with ONLY a JSON object with these exact fields, nothing else:
{{
  "items": [
    {{"item": "...", "item_english": "...", "quantity_raw": "...", "quantity_numeric": <number or null>, "unit_english": "..."}}
  ],
  "unparsed_fragments": ["..."],
  "urgency": "immediate" or "can_batch" or "not_applicable"
}}
Rules:
- "item": the item name exactly as the cook said it, in the original language.
- "item_english": your best English translation of just that item name.
- "quantity_raw": the amount exactly as the cook said it, in their own words/script.
- "quantity_numeric": convert quantity_raw into a plain number. If no specific amount was given, set this to null. Do NOT guess a number that wasn't stated.
- "unit_english": the unit in English. Set to null if quantity_numeric is null.
- List EACH distinct item the cook mentioned as a separate entry in "items".
- "unparsed_fragments": if any word or fragment doesn't clearly correspond to a real grocery/household item, do NOT invent an item for it and do NOT force it into another item's fields — instead put it here verbatim, exactly as heard. Nothing should be silently discarded.
- Never treat a quantity word (e.g. "a little", "some", "थोड़ा") as an item by itself — it can only ever describe another item's quantity_raw field, never stand alone, and never belongs in unparsed_fragments either.
- "urgency": "immediate" only if the cook's phrasing itself signals urgency. "can_batch" if routine, no urgency signaled. "not_applicable" if unrelated to food/inventory.
"""

PRESET_SCENARIOS = {
    "Ambiguous quantity, has history (Hindi)": {"voice_note": "थोड़ा प्याज़ ले आना", "language": "Hindi"},
    "Budget-breaking request (Bengali)": {"voice_note": "আমাকে পাঁচ কেজি কাজু বাদাম এনে দাও", "language": "Bengali"},
    "Routine inventory update, no history (Hindi)": {"voice_note": "तेल खत्म हो गया है", "language": "Hindi"},
    "Urgent, has salt history (Hindi)": {
        "voice_note": "नमक खत्म हो गया है, अभी खाना बना रही हूं, जल्दी चाहिए", "language": "Hindi"
    },
    "Urgent low-value, has salt history (Hindi)": {"voice_note": "अभी थोड़ा नमक चाहिए, तुरंत", "language": "Hindi"},
    "Multi-item over budget (Hindi)": {
        "voice_note": "तीन किलो प्याज़, आठ किलो आलू, दो किलो सर्फ एक्सेल, और पांच सौ ग्राम लहसुन ले आना",
        "language": "Hindi",
    },
    "Custom": {"voice_note": "", "language": "Hindi"},
}

st.title("Cook Voice Note Pipeline — Prototype")
st.caption(
    "Cook voice note → extraction → catalog match / history reorder → ops resolves quantity + SKU → "
    "budget check → reply to cook → approve. Built as a hands-on demo, not a production system."
)

with st.sidebar:
    st.header("Scenario")
    scenario_name = st.selectbox("Pick a scenario", list(PRESET_SCENARIOS.keys()))
    preset = PRESET_SCENARIOS[scenario_name]

    if scenario_name == "Custom":
        language = st.selectbox("Language", ["Hindi", "Bengali", "English"])
    else:
        language = preset["language"]

    if st.session_state.get("last_scenario") != scenario_name:
        st.session_state["voice_note_text_value"] = preset["voice_note"]
        st.session_state["last_scenario"] = scenario_name

    if "pending_transcript" in st.session_state:
        st.session_state["voice_note_text_value"] = st.session_state.pop("pending_transcript")

    voice_note = st.text_area("Voice note text (simulated transcript)", key="voice_note_text_value")

    with st.expander("🎙️ Or record real audio instead"):
        recorded_audio = st.audio_input("Record the cook's voice note", key="recorded_audio_input")
        if recorded_audio is not None and st.button("Transcribe recording"):
            with st.spinner("Transcribing with local Whisper (first run downloads the model)..."):
                transcript = transcribe_audio(recorded_audio, LANGUAGE_CODE_MAP.get(language))
            st.session_state["pending_transcript"] = transcript
            st.rerun()
        st.caption(
            "The transcribed text replaces the box above — review or edit it before "
            "running the pipeline, same as any other input here."
        )

    st.divider()
    st.header("Household wallet")
    wallet_balance = st.number_input(
        "Remaining balance this month (₹)", min_value=0, value=HOUSEHOLD["wallet_balance"], step=100
    )

    run_button = st.button("Run through pipeline", type="primary", use_container_width=True)

if run_button:
    if not voice_note.strip():
        st.warning("Enter or record a voice note first.")
        st.stop()

    st.session_state["voice_note"] = voice_note
    st.session_state["language"] = language
    st.session_state["household_for_run"] = {**HOUSEHOLD, "wallet_balance": wallet_balance}
    st.session_state["order_approved"] = False
    st.session_state["reply_options"] = None
    st.session_state["sent_messages"] = []

    prompt = PROMPT_TEMPLATE.format(voice_note=voice_note, language=language)
    with st.spinner("Extracting from voice note..."):
        response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}])
        st.session_state["extracted"] = extract_json_block(response["message"]["content"])

    for key in list(st.session_state.keys()):
        if key.startswith("pick_") or key.startswith("qty_"):
            del st.session_state[key]

extracted = st.session_state.get("extracted")

if extracted:
    household_for_run = st.session_state["household_for_run"]

    st.subheader("1. Extraction")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cook's voice note**")
        st.info(f"({st.session_state['language']}) {st.session_state['voice_note']}")
    with col2:
        st.markdown("**Urgency**")
        urgency = extracted.get("urgency", "unknown")
        badge = {"immediate": "🔴 Immediate", "can_batch": "🟡 Can batch", "not_applicable": "⚪ Not applicable"}.get(
            urgency, urgency
        )
        st.markdown(f"### {badge}")

    with st.expander("Raw extracted JSON"):
        st.json(extracted)

    if extracted.get("unparsed_fragments"):
        st.warning(
            f"⚠️ Heard something that couldn't be confidently matched to an item — "
            f"check with the cook: {', '.join(extracted['unparsed_fragments'])}"
        )

    st.subheader("2. Catalog matching & ops resolution")
    matched_items = []

    for idx, item in enumerate(extracted.get("items", [])):
        item_with_flag = {**item, "quantity_specified": is_quantity_specified(item.get("quantity_numeric"))}
        match_result = process_extracted_item(item_with_flag, household_for_run, CATALOG)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                st.markdown(f"**{match_result['source_item_text']}**")
                st.caption(f"→ {match_result['translated_item'] or '—'}")
            with c2:
                st.markdown(f"Matched: **{match_result['canonical_item'] or 'No match'}**")
                if match_result["match_distance"] is not None:
                    st.caption(f"distance: {match_result['match_distance']:.3f}")
            with c3:
                status = match_result["status"] or ""

                if status == "matched_from_history":
                    sku = match_result["matched_sku"]
                    st.success(f"✓ From order history — {sku['brand']} {sku['size']}")

                elif status == "reorder_suggested_from_history":
                    st.warning("📋 No quantity given — confirm or adjust the usual reorder")
                    options = match_result["ranked_options"]

                    def label_for(sku):
                        rc = sku.get("rating_count")
                        rating_text = f"★{sku['rating']} ({rc} ratings)" if sku.get("rating") else "no ratings"
                        return f"{sku['brand']} — {sku['size']} — ₹{sku['price']} — {rating_text}"

                    default_brand = match_result["suggested_reorder"]["sku"]["brand"]
                    default_idx = next((i for i, o in enumerate(options) if o["brand"] == default_brand), 0)
                    pick_key = f"pick_{idx}"
                    chosen_label = st.selectbox(
                        "Ops: SKU", options=[label_for(o) for o in options], index=default_idx, key=pick_key
                    )
                    chosen_sku = next(o for o in options if label_for(o) == chosen_label)

                    qty_key = f"qty_{idx}"
                    default_qty = match_result["suggested_reorder"]["typical_qty"]
                    packs = st.number_input(
                        "Ops: number of packs", min_value=1, value=default_qty, step=1, key=qty_key
                    )
                    match_result["chosen_sku"] = chosen_sku
                    match_result["price"] = packs * chosen_sku["price"]
                    match_result["cost_note"] = f"{packs} x {chosen_sku['size']} pack(s) of {chosen_sku['brand']}"
                    match_result["cost_verified"] = True

                elif status == "no_history_needs_ops_selection":
                    st.warning("No order history — ops must pick a SKU below")
                    options = match_result["ranked_options"]

                    def label_for2(sku):
                        rc = sku.get("rating_count")
                        rating_text = f"★{sku['rating']} ({rc} ratings)" if sku.get("rating") else "no ratings"
                        return f"{sku['brand']} — {sku['size']} — ₹{sku['price']} — {rating_text}"

                    pick_key = f"pick_{idx}"
                    chosen_label = st.selectbox(
                        "Ops: pick the SKU to order", options=[label_for2(o) for o in options], key=pick_key
                    )
                    chosen_sku = next(o for o in options if label_for2(o) == chosen_label)
                    cost, note = estimate_cost_for_request(
                        match_result["quantity_numeric"], match_result["unit_english"], chosen_sku
                    )
                    match_result["chosen_sku"] = chosen_sku
                    match_result["price"] = cost
                    match_result["cost_note"] = note
                    match_result["cost_verified"] = cost is not None

                elif status == "no_history_no_qty_needs_ops_selection":
                    st.warning("No quantity given, no order history — ops picks SKU and sets quantity")
                    options = match_result["ranked_options"]

                    def label_for3(sku):
                        rc = sku.get("rating_count")
                        rating_text = f"★{sku['rating']} ({rc} ratings)" if sku.get("rating") else "no ratings"
                        return f"{sku['brand']} — {sku['size']} — ₹{sku['price']} — {rating_text}"

                    pick_key = f"pick_{idx}"
                    chosen_label = st.selectbox(
                        "Ops: pick the SKU to order", options=[label_for3(o) for o in options], key=pick_key
                    )
                    chosen_sku = next(o for o in options if label_for3(o) == chosen_label)

                    qty_key = f"qty_{idx}"
                    packs = st.number_input("Ops: number of packs", min_value=1, value=1, step=1, key=qty_key)
                    match_result["chosen_sku"] = chosen_sku
                    match_result["price"] = packs * chosen_sku["price"]
                    match_result["cost_note"] = (
                        f"{packs} x {chosen_sku['size']} pack(s) of {chosen_sku['brand']} (quantity set by ops)"
                    )
                    match_result["cost_verified"] = True

                elif status == "unavailable":
                    st.error("❌ Unavailable — item not recognized in catalog")

            if match_result.get("cost_note"):
                price_text = f" — ₹{match_result['price']}" if match_result.get("price") else ""
                st.caption(f"💰 {match_result['cost_note']}{price_text}")

        matched_items.append(match_result)

    st.session_state["matched_items"] = matched_items

    priced_items = [m for m in matched_items if m.get("price") is not None]
    budget_result = None
    if priced_items:
        st.subheader("3. Budget check")
        budget_result = budget_check(priced_items, household_for_run)

        b1, b2, b3 = st.columns(3)
        b1.metric("Estimated total", f"₹{budget_result['estimated_total']:,}")
        b2.metric("Remaining balance", f"₹{budget_result['remaining_balance']:,}")
        b3.metric("Status", "❌ Over budget" if budget_result["budget_exceeded"] else "✅ Within budget")

        if budget_result["decision_note"]:
            st.warning(budget_result["decision_note"])
        if budget_result["affordable_alternative"]:
            alt = budget_result["affordable_alternative"]
            st.info(f"Affordable alternative: {alt['affordable_quantity_text']} (₹{alt['affordable_cost']})")
        if budget_result["note"]:
            st.caption(budget_result["note"])

    st.subheader("4. Message to cook")

    if st.button("Suggest replies"):
        options = build_reply_options(matched_items)
        labels = [o["label"] for o in options]
        translated = translate_messages_to_cook(labels, st.session_state["language"])
        st.session_state["reply_options"] = [{**o, "translated": t} for o, t in zip(options, translated)]

    if st.session_state.get("reply_options"):
        for i, opt in enumerate(st.session_state["reply_options"]):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                tag = " ⭐ recommended" if opt.get("recommended") else ""
                st.info(f"{opt['translated']}{tag}")
            with col_b:
                if st.button("Send", key=f"send_{opt['key']}_{i}"):
                    st.session_state["sent_messages"].append({"type": "text", "content": opt["translated"]})
                    st.rerun()

    st.markdown("**Custom text reply** (always available, regardless of the suggestions above)")
    c1, c2 = st.columns([5, 1])
    with c1:
        custom_text = st.text_input("Type a reply in the cook's language", key="custom_reply_text")
    with c2:
        if st.button("Send", key="send_custom_text"):
            if custom_text.strip():
                st.session_state["sent_messages"].append({"type": "text", "content": custom_text.strip()})
                st.rerun()

    st.markdown("**Or record a voice reply** — sent to the cook exactly as recorded, no transcription or translation")
    voice_reply = st.audio_input("Record your reply", key="voice_reply_input")
    if voice_reply is not None:
        if st.button("Send voice reply", key="send_custom_voice"):
            st.session_state["sent_messages"].append({"type": "voice", "content": voice_reply.getvalue()})
            st.rerun()

    if st.session_state["sent_messages"]:
        st.markdown("**Sent to cook:**")
        for msg in st.session_state["sent_messages"]:
            if msg["type"] == "voice":
                st.markdown("✓ Voice message sent:")
                st.audio(msg["content"])
            else:
                st.success(f"✓ {msg['content']}")

    st.subheader("5. Approve order")
    unresolved = [m for m in matched_items if m.get("price") is None and m.get("status") != "unavailable"]
    can_approve = len(matched_items) > 0 and not unresolved

    if unresolved:
        st.caption("⚠️ Cannot approve — one or more items still need ops to pick a SKU/quantity above.")

    if st.button("✅ Approve order for ops placement", disabled=not can_approve, type="primary"):
        st.session_state["order_approved"] = True

    if st.session_state.get("order_approved"):
        st.success("Order approved — ready to hand off to the ops placement step (not built in this demo).")
        with st.expander("Final order payload"):
            st.json({"items": matched_items, "budget_check": budget_result})

st.divider()
with st.expander("⚠️ Known limitations — read before showing this to anyone"):
    st.markdown(
        """
- **Mock catalog only** — ~200 hand-built items, not live Blinkit/Zepto/Snabbit inventory.
- **Rating counts are fabricated** — real review-count data per SKU isn't available.
- **No real order placement or payment** — "Approve" stops at a confirmed, priced order.
- **AI-drafted replies are text-only** — no real voice-out (TTS) in the cook's language yet;
  the voice-reply option sends ops's own recorded voice as-is, with no AI involvement.
- **General-purpose embedding model, not grocery-tuned** — matching can occasionally land on
  the wrong item. At production scale this needs a domain-tuned embedding model or a proper
  item taxonomy, not one-off fixes.
- **Ambiguous generic terms can flip between runs** — e.g. "oil" alone may resolve inconsistently.
- **Single household, single session** — no persistent multi-household spend tracking yet.
- **Wallet balance is modeled as a simple monthly cap** — in reality M fronts working capital
  and reconciles with the owner monthly, not a pre-funded deposit.
- **Ops always resolves missing quantity/SKU directly** — the system never blocks waiting on
  a reply from the cook for these, since a cook won't reliably state a quantity in normal speech.
"""
    )