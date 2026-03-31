#!/usr/bin/env python3
"""
AgentForge - Text Summarizer Agent
Reads from stdin, writes summary to stdout line by line.
"""
import sys
import os
from groq import Groq

def main():
    input_text = sys.stdin.read().strip()
    if not input_text:
        print("No input provided.")
        return

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        # Fallback: simple extractive summarization
        sentences = [s.strip() for s in input_text.replace("\n", " ").split(".") if len(s.strip()) > 30]
        print("Summary (extractive):\n")
        for i, s in enumerate(sentences[:5], 1):
            print(f"• {s}.")
        return

    client = Groq(api_key=api_key)
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise summarizer. Given a text, produce a clean bulleted summary "
                    "of the key points. Use bullet points (•). Be concise. Max 8 bullets."
                )
            },
            {
                "role": "user",
                "content": f"Summarize this:\n\n{input_text[:6000]}"
            }
        ],
        max_tokens=512,
        stream=True
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()

if __name__ == "__main__":
    main()
