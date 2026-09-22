# Cook Voice-Note Pipeline

A hands-on prototype exploring one specific, hard problem in AI-powered home-services
products: turning a household cook's spoken voice note (Hindi/Bengali/English, often
informal or low-literacy) into a correct, budget-safe, human-approved grocery order.

Inspired by a conversation about "Home OS" products — AI systems that manage household
operations end to end, starting with the kitchen. This project doesn't build that whole
product; it builds and stress-tests the single hardest step in it.

## What this demonstrates

The interesting part of this project isn't the AI's language ability — it's the judgment
calls about **where to trust the AI, where to override it with deterministic logic, and
where a human has to stay in the loop.** Concretely:

- A deterministic budget hard-gate — evaluated with real quantity-aware cost scaling,
  after an early version silently under-priced a large order and would have let it pass
- A real vector-embedding catalog matcher (not a hardcoded translation dictionary),
  including a documented, deliberately-unpatched limitation where general-purpose
  embeddings mismatch domain-specific vocabulary
- A decision matrix that never lets a missing quantity become a dead-end waiting on the
  cook — a cook won't reliably state a quantity in normal speech, so an operator is
  always shown a way to resolve it directly (a suggested reorder, or a catalog pick plus
  a manual quantity field). This was a real design flaw found and fixed after testing
  against actual usage, not caught by re-reading the logic itself.
- A multi-item budget overflow that explicitly refuses to guess which item(s) to cut,
  since that's a household preference with no data behind it
- Real local speech-to-text (faster-whisper) wired in, including honest findings about
  how transcription errors can compound with LLM extraction errors in ways a clever
  prompt alone can't fully fix

## Architecture

```
Cook voice note (audio or text)
        |
        v
Transcription (faster-whisper, local)
        |
        v
Extraction (Gemma 4, via Ollama, local) -- item, translation, quantity, unit, urgency
        |
        v
Catalog matching (sentence-transformers + ChromaDB, local vector search)
        |
        v
Decision matrix (deterministic Python) -- an operator always has a path to resolve
the order, never blocked waiting on the cook:
  qty + history      -> auto-match the household's usual brand
  qty + no history   -> ops picks a SKU from a ranked list
  no qty + history   -> ops confirms/adjusts a suggested reorder
  no qty + no history -> ops picks a SKU AND sets a quantity directly
        |
        v
Budget check (deterministic hard gate)
        |
        v
Reply to cook (consolidated options + custom text/voice) -> human approval
```

## Stack

- **Transcription:** faster-whisper ("small" model)
- **Extraction / translation:** Gemma 4, running locally via [Ollama](https://ollama.com)
- **Catalog matching:** sentence-transformers (`all-MiniLM-L6-v2`) + ChromaDB
- **Interface:** Streamlit

Everything runs locally and free — no paid API calls required.

## Running it

```bash
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

python src/generate_catalog.py
python src/build_embeddings.py

streamlit run app.py
```

Requires [Ollama](https://ollama.com) installed and running locally, with the `gemma4`
model pulled (`ollama pull gemma4`).

## Known limitations

- Mock catalog only (~170 items) — not live grocery-platform inventory
- Product ratings/review counts are fabricated stand-in data
- No real order placement or payment — the flow stops at a human-approved, priced order
- AI-drafted replies are text-only; no real voice-out (TTS)
- General-purpose embedding model occasionally mismatches domain-specific vocabulary
  (documented, not hidden -- a real production system would need a domain-tuned model)
- Ambiguous generic terms (e.g. a generic word for "oil" when multiple oil types exist
  in the catalog) can resolve inconsistently between runs
- Single simulated household, single session -- no persistent spend tracking
- Wallet balance is modeled as a simple monthly cap -- a real deployment would likely
  front working capital and reconcile with the household later, not hold a pre-funded
  balance

## Why these limitations are listed instead of hidden

A demo that hides its own edges is less useful than one that names them. Several of these
were found, understood, and *deliberately left unfixed* rather than patched -- patching a
single symptom (e.g. one mistranslated word) without fixing the underlying cause creates a
false impression of robustness. The reasoning behind each of those calls is in the code
comments and commit history.
