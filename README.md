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
- A decision matrix that only asks a human a clarifying question when there's genuinely
  nothing else to go on — order history takes priority over interrupting anyone
- A multi-item budget overflow that explicitly refuses to guess which item(s) to cut,
  since that's a household preference with no data behind it
- Real local speech-to-text (faster-whisper) wired in, including honest findings about
  how transcription errors can compound with LLM extraction errors in ways a clever
  prompt alone can't fully fix

## Architecture