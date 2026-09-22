from faster_whisper import WhisperModel
import ollama

print("Checking faster-whisper loads...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("faster-whisper OK.\n")

print("Checking local Ollama models respond...")
test_models = ["gemma4:latest", "qwen3.5:9b", "deepseek-v4-flash:cloud"]

prompt = (
    "A cook sends this WhatsApp voice note in Bengali: "
    "'Please get 500 grams of onions and one packet of coriander.' "
    "Respond in Bengali with a short confirmation, then on a new line "
    "give the English translation of your own response."
)

for m in test_models:
    print(f"--- {m} ---")
    try:
        response = ollama.chat(model=m, messages=[{"role": "user", "content": prompt}])
        print(response["message"]["content"])
    except Exception as e:
        print(f"Failed: {e}")
    print()