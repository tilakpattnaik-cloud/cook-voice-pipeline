import re
import math
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "catalog_items"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

MATCH_DISTANCE_THRESHOLD = 1.0

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def match_item_to_catalog(english_item_name):
    if not english_item_name:
        return None, None

    model = _get_model()
    collection = _get_collection()

    query_embedding = model.encode([english_item_name]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=1)

    if not results["ids"] or not results["ids"][0]:
        return None, None

    distance = results["distances"][0][0]
    if distance > MATCH_DISTANCE_THRESHOLD:
        return None, distance

    canonical_item = results["metadatas"][0][0]["canonical_item"]
    return canonical_item, distance


def get_catalog_matches(canonical_item, catalog):
    return [entry for entry in catalog if entry["item"].lower() == canonical_item.lower()]


def match_from_history(canonical_item, household):
    history = household.get("known_sku_history", {})
    for hist_key, pref in history.items():
        if hist_key.lower() == canonical_item.lower():
            return pref
    return None


def stack_rank_by_rating(matches):
    """
    Ranks SKUs for ops to choose from: established items (rating_count >= 20)
    first, sorted by rating descending; then less-proven items. No SKU is
    auto-selected — this list is for a human to pick from.
    """
    established = [
        m for m in matches
        if m.get("rating") is not None and (m.get("rating_count") or 0) >= 20
    ]
    unproven = [m for m in matches if m not in established]

    established.sort(key=lambda m: m["rating"], reverse=True)
    unproven.sort(key=lambda m: (m["rating"] is None, -(m["rating"] or 0), m["price"]))

    return established + unproven


WEIGHT_UNITS = {"g": 1, "gram": 1, "grams": 1, "kg": 1000, "kgs": 1000, "kilogram": 1000, "kilograms": 1000}
VOLUME_UNITS = {"ml": 1, "millilitre": 1, "millilitres": 1, "l": 1000, "liter": 1000, "liters": 1000, "litre": 1000, "litres": 1000}
COUNT_UNITS = {"", "packet", "packets", "pack", "packs", "piece", "pieces", "pc", "pcs", "unit", "units"}


def parse_quantity_string(text):
    if not text:
        return None
    text = str(text).strip().lower()
    match = re.match(r"([\d.]+)\s*([a-zA-Z]+)", text)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit in WEIGHT_UNITS:
        return amount * WEIGHT_UNITS[unit], "weight"
    if unit in VOLUME_UNITS:
        return amount * VOLUME_UNITS[unit], "volume"
    return None


def normalize_requested_quantity(quantity_numeric, unit_english):
    if quantity_numeric is None:
        return None
    unit = (unit_english or "").strip().lower()
    if unit in WEIGHT_UNITS:
        return quantity_numeric * WEIGHT_UNITS[unit], "weight"
    if unit in VOLUME_UNITS:
        return quantity_numeric * VOLUME_UNITS[unit], "volume"
    if unit in COUNT_UNITS:
        return quantity_numeric, "count"
    return None


def is_quantity_specified(quantity_numeric):
    return quantity_numeric is not None and quantity_numeric > 0


def estimate_cost_for_request(quantity_numeric, unit_english, sku):
    requested = normalize_requested_quantity(quantity_numeric, unit_english)
    if not requested:
        return None, "cannot verify total — quantity/unit not confidently understood, needs human check"

    requested_amount, requested_type = requested

    if requested_type == "count":
        packs_needed = math.ceil(requested_amount)
        total = packs_needed * sku["price"]
        return total, f"{packs_needed} x {sku['size']} pack(s) of {sku['brand']} (assumed 1 request-unit = 1 pack)"

    catalog_parsed = parse_quantity_string(sku.get("size", ""))
    if not catalog_parsed:
        return None, "cannot verify total — catalog pack size not in a comparable unit, needs human check"

    catalog_amount, catalog_type = catalog_parsed
    if requested_type != catalog_type:
        return None, f"unit mismatch ({requested_type} requested vs {catalog_type} pack) — needs human check"

    packs_needed = math.ceil(requested_amount / catalog_amount)
    total = packs_needed * sku["price"]
    return total, f"{packs_needed} x {sku['size']} pack(s) of {sku['brand']}"


def max_affordable_quantity(remaining_budget, sku):
    pack_price = sku["price"]
    if pack_price <= 0:
        return None
    affordable_packs = math.floor(remaining_budget / pack_price)
    if affordable_packs <= 0:
        return {"affordable_packs": 0, "affordable_cost": 0, "affordable_quantity_text": "none affordable"}

    parsed_size = parse_quantity_string(sku.get("size", ""))
    if parsed_size:
        amount, unit_type = parsed_size
        total_amount = affordable_packs * amount
        if unit_type == "weight":
            qty_text = f"{total_amount/1000:.2f} kg" if total_amount >= 1000 else f"{total_amount:.0f} g"
        else:
            qty_text = f"{total_amount/1000:.2f} L" if total_amount >= 1000 else f"{total_amount:.0f} ml"
    else:
        qty_text = f"{affordable_packs} x {sku['size']} pack(s)"

    return {
        "affordable_packs": affordable_packs,
        "affordable_cost": affordable_packs * pack_price,
        "affordable_quantity_text": qty_text,
    }


def process_extracted_item(extracted_item, household, catalog):
    """
    2x2 decision matrix on (quantity given?) x (order history exists?):
      qty + history      -> auto-match brand from history, cost from given qty
      qty + no history   -> ops picks a SKU from the ranked list
      no qty + history   -> suggest reordering last SKU+qty, ops ratifies
      no qty + no history -> only now do we ask the cook — nothing else to go on
    """
    raw_name = extracted_item.get("item", "")
    english_name = extracted_item.get("item_english", "")
    quantity_numeric = extracted_item.get("quantity_numeric")
    unit_english = extracted_item.get("unit_english")
    quantity_specified = extracted_item.get("quantity_specified", False)
    canonical, distance = match_item_to_catalog(english_name)

    result = {
        "source_item_text": raw_name,
        "translated_item": english_name,
        "canonical_item": canonical,
        "match_distance": distance,
        "quantity_specified": quantity_specified,
        "quantity_numeric": quantity_numeric,
        "unit_english": unit_english,
        "status": None,
        "matched_sku": None,
        "ranked_options": None,
        "suggested_reorder": None,
        "chosen_sku": None,
        "price": None,
        "cost_note": None,
        "cost_verified": False,
        "needs_ops_action": False,
        "needs_cook_reply": False,
    }

    if not canonical:
        result["status"] = "unmapped_item"
        result["needs_ops_action"] = True
        return result

    matches = get_catalog_matches(canonical, catalog)
    if not matches:
        result["status"] = "no_catalog_match"
        result["needs_ops_action"] = True
        return result

    history_pref = match_from_history(canonical, household)

    if quantity_specified and history_pref:
        preferred = next(
            (m for m in matches if m["brand"].lower() == history_pref.get("brand", "").lower()), None
        )
        if preferred:
            result["status"] = "matched_from_history"
            result["matched_sku"] = preferred
            result["chosen_sku"] = preferred
        else:
            result["status"] = "no_history_needs_ops_selection"
            result["ranked_options"] = stack_rank_by_rating(matches)
            result["needs_ops_action"] = True

    elif quantity_specified and not history_pref:
        result["status"] = "no_history_needs_ops_selection"
        result["ranked_options"] = stack_rank_by_rating(matches)
        result["needs_ops_action"] = True

    elif not quantity_specified and history_pref:
        preferred = next(
            (m for m in matches if m["brand"].lower() == history_pref.get("brand", "").lower()), None
        )
        if preferred:
            typical_qty = history_pref.get("typical_qty", 1)
            result["status"] = "reorder_suggested_from_history"
            result["suggested_reorder"] = {
                "sku": preferred,
                "typical_qty": typical_qty,
                "typical_size": history_pref.get("typical_size"),
            }
            result["ranked_options"] = stack_rank_by_rating(matches)  # fallback if ops wants to change
            result["needs_ops_action"] = True
            result["chosen_sku"] = preferred
            result["price"] = typical_qty * preferred["price"]
            result["cost_note"] = (
                f"Reorder suggestion: {typical_qty} x {preferred['size']} pack(s) of "
                f"{preferred['brand']} (same as last order)"
            )
            result["cost_verified"] = True
            return result
        else:
            # Historical brand no longer in catalog and no quantity to fall back
            # on — safer to ask the cook than to guess.
            result["status"] = "needs_clarification_from_cook"
            result["needs_cook_reply"] = True
            return result

    else:  # not quantity_specified and not history_pref
        result["status"] = "needs_clarification_from_cook"
        result["needs_cook_reply"] = True
        return result

    if result["chosen_sku"] and quantity_specified:
        cost, note = estimate_cost_for_request(quantity_numeric, unit_english, result["chosen_sku"])
        result["price"] = cost
        result["cost_note"] = note
        result["cost_verified"] = cost is not None

    return result


def budget_check(matched_items, household):
    verified_items = [i for i in matched_items if i.get("cost_verified")]
    priced_candidates = [i for i in matched_items if i.get("matched_sku") or i.get("chosen_sku")]
    unverified_count = len([i for i in priced_candidates if not i.get("cost_verified")])

    total = sum(i["price"] for i in verified_items)
    remaining = household.get("wallet_balance", 0)
    exceeded = total > remaining
    shortfall = round(total - remaining, 2) if exceeded else 0

    result = {
        "estimated_total": total,
        "remaining_balance": remaining,
        "budget_exceeded": exceeded,
        "shortfall": shortfall,
        "unverified_items_count": unverified_count,
        "note": None,
        "decision_note": None,
        "affordable_alternative": None,
    }

    if unverified_count:
        result["note"] = (
            f"Total only reflects items with a confidently scaled cost — "
            f"{unverified_count} item(s) need human pricing before this budget check can be fully trusted."
        )

    if exceeded:
        if len(verified_items) == 1:
            sku = verified_items[0].get("chosen_sku")
            if sku:
                result["affordable_alternative"] = max_affordable_quantity(remaining, sku)
            result["decision_note"] = (
                f"Exceeds remaining balance by ₹{shortfall}. Suggested affordable "
                "quantity included — ops/homeowner should confirm."
            )
        else:
            result["decision_note"] = (
                f"Combined request exceeds remaining balance by ₹{shortfall}. "
                "This system will not choose which item(s) to reduce or drop — "
                "that needs to go back to the household or ops team."
            )

    return result