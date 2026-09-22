# Cook Voice-Note Pipeline

A hands-on prototype exploring one specific, hard problem in AI-powered home-services
products: turning a household cook's spoken voice note (Hindi/Bengali/English, often
informal or low-literacy) into a correct, budget-safe, human-approved grocery order.

Inspired by a conversation about "Home OS" products — AI systems that manage household
operations end to end, starting with the kitchen. This project doesn't build that whole
product; it builds and stress-tests the single hardest step in it.

**What this demonstrates
**
The interesting part of this project isn't the AI's language ability — it's the judgment
calls about where to trust the AI, where to override it with deterministic logic, and
where a human has to stay in the loop. Concretely:

A deterministic budget hard-gate — evaluated with real quantity-aware cost scaling,
after an early version silently under-priced a large order and would have let it pass
A real vector-embedding catalog matcher (not a hardcoded translation dictionary),
including a documented, deliberately-unpatched limitation where general-purpose
embeddings mismatch domain-specific vocabulary
A decision matrix that only asks a human a clarifying question when there's genuinely
nothing else to go on — order history takes priority over interrupting anyone
A multi-item budget overflow that explicitly refuses to guess which item(s) to cut,
since that's a household preference with no data behind it
Real local speech-to-text (faster-whisper) wired in, including honest findings about
how transcription errors can compound with LLM extraction errors in ways a clever
prompt alone can't fully fix

**Architecture**

Cook voice note (audio or text)
        │
        ▼
Transcription (faster-whisper, local)
        │
        ▼
Extraction (Gemma 4, via Ollama, local) — item, translation, quantity, unit, urgency
        │
        ▼
Catalog matching (sentence-transformers + ChromaDB, local vector search)
        │
        ▼
Decision matrix (deterministic Python):
  quantity given? × order history exists? → auto-match / ask ops / suggest reorder / ask cook
        │
        ▼
Budget check (deterministic hard gate)
        │
        ▼
Reply to cook (consolidated options + custom text/voice) → human approval

**Stack**

Transcription: faster-whisper ("small" model)
Extraction / translation: Gemma 4, running locally via Ollama
Catalog matching: sentence-transformers (all-MiniLM-L6-v2) + ChromaDB
Interface: Streamlit

Everything runs locally and free — no paid API calls required.

Running it
python -m venv venv
venv\Scripts\activate          # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

python src/generate_catalog.py
python src/build_embeddings.py

streamlit run app.py

Requires Ollama installed and running locally, with the gemma4
model pulled (ollama pull gemma4).

**Known limitations
**
Mock catalog only (~170 items) — not live grocery-platform inventory
Product ratings/review counts are fabricated stand-in data
No real order placement or payment — the flow stops at a human-approved, priced order
AI-drafted replies are text-only; no real voice-out (TTS)
General-purpose embedding model occasionally mismatches domain-specific vocabulary
(documented, not hidden — a real production system would need a domain-tuned model)
Ambiguous generic terms (e.g. a generic word for "oil" when multiple oil types exist
in the catalog) can resolve inconsistently between runs
Single simulated household, single session — no persistent spend tracking
Why these limitations are listed instead of hidden

A demo that hides its own edges is less useful than one that names them. Several of these
were found, understood, and deliberately left unfixed rather than patched — patching a
single symptom (e.g. one mistranslated word) without fixing the underlying cause creates a
false impression of robustness. The reasoning behind each of those calls is in the code
comments and commit history.
