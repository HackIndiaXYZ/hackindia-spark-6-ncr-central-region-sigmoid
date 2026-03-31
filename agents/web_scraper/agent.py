#!/usr/bin/env python3
"""
AgentForge - Web Scraper Agent
Reads a URL from stdin, fetches and extracts main text content.
"""
import sys
import re

def extract_text(html: str) -> str:
    # Remove scripts and styles
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    url = sys.stdin.read().strip()
    if not url:
        print("No URL provided.")
        return

    if not url.startswith("http"):
        # Treat as raw text passthrough (for pipeline chaining)
        print(url)
        return

    try:
        import urllib.request
        headers = {"User-Agent": "Mozilla/5.0 AgentForge/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        text = extract_text(html)
        # Trim to reasonable size
        print(f"[Scraped from: {url}]\n")
        print(text[:5000])
    except Exception as e:
        print(f"[Web Scraper Error] Could not fetch {url}: {e}")

if __name__ == "__main__":
    main()
