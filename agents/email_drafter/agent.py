#!/usr/bin/env python3
"""
AgentForge - Email Drafter Agent
Reads text or summary from stdin, drafts a professional email.
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
        print("Subject: Update on the Following Points\n")
        print("Dear [Recipient],\n")
        print("I hope this message finds you well. I wanted to reach out regarding the following:\n")
        for line in input_text.split("\n")[:5]:
            if line.strip():
                print(f"  {line.strip()}")
        print("\nPlease let me know if you have any questions.\n")
        print("Best regards,\n[Your Name]")
        return

    client = Groq(api_key=api_key)
    stream = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional email writer. Given some text or bullet points, "
                    "draft a clear, professional email with:\n"
                    "Subject: <subject line>\n\n"
                    "Dear [Recipient],\n\n"
                    "<email body>\n\n"
                    "Best regards,\n[Sender]\n\n"
                    "Keep it concise and professional."
                )
            },
            {
                "role": "user",
                "content": f"Draft an email based on this content:\n\n{input_text[:3000]}"
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
