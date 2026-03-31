#!/usr/bin/env python3
"""
AgentForge - Code Explainer Agent
Reads code from stdin, explains it in plain English.
"""
import sys
import os
from groq import Groq

def main():
    code_input = sys.stdin.read().strip()
    if not code_input:
        print("No code provided.")
        return

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("Code Explainer Agent\n")
        print(f"Received {len(code_input)} characters of code.")
        print("This agent requires a GROQ_API_KEY to explain code with AI.")
        return

    client = Groq(api_key=api_key)
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert code explainer. Given a code snippet, explain what it does "
                    "in plain English. Break it down section by section. Be clear, beginner-friendly, "
                    "and thorough. Use numbered sections."
                )
            },
            {
                "role": "user",
                "content": f"Explain this code:\n\n```\n{code_input[:4000]}\n```"
            }
        ],
        max_tokens=700,
        stream=True
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()

if __name__ == "__main__":
    main()
