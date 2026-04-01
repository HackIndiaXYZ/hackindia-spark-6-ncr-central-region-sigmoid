#!/usr/bin/env python3
import sys
import os
import json

def fallback_analyze(text):
    words = text.lower().split()
    pos_words = ['good','great','love','excellent','happy','amazing','wonderful','fantastic','best','brilliant']
    neg_words = ['bad','hate','terrible','awful','sad','angry','horrible','worst','poor','disappointing']
    pos = sum(1 for w in words if w.strip('.,!?') in pos_words)
    neg = sum(1 for w in words if w.strip('.,!?') in neg_words)
    sentiment = "POSITIVE" if pos > neg else "NEGATIVE" if neg > pos else "NEUTRAL"
    emotion = "Joy" if pos > neg else "Frustration" if neg > pos else "Neutral"
    print(f"Sentiment: {sentiment}")
    print(f"Emotion: {emotion}")
    print(f"Confidence: MEDIUM")
    print(f"Reasoning: Rule-based analysis detected {pos} positive and {neg} negative signals.")

def main():
    text = sys.stdin.read().strip()
    if not text:
        print("No input provided.")
        return

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        fallback_analyze(text)
        return

    try:
        import urllib.request
        import urllib.error
        payload = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "Analyze sentiment and emotion. Reply in exactly this format:\nSentiment: POSITIVE/NEGATIVE/NEUTRAL\nEmotion: (one word)\nConfidence: HIGH/MEDIUM/LOW\nReasoning: (one sentence max)"},
                {"role": "user", "content": text[:1500]}
            ],
            "max_tokens": 120,
            "temperature": 0.3
        }).encode('utf-8')

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(result["choices"][0]["message"]["content"])
    except Exception:
        fallback_analyze(text)

if __name__ == "__main__":
    main()