#!/usr/bin/env python3
import sys

def main():
    input_text = sys.stdin.read().strip()
    if not input_text:
        print("No input provided.")
        return

    # Your agent logic here
    words = input_text.split()
    print(f"Word count: {len(words)}")
    print(f"Characters: {len(input_text)}")

if __name__ == "__main__":
    main()