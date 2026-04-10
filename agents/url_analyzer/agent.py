#!/usr/bin/env python3
import sys
import re
from urllib.parse import urlparse, parse_qs, unquote

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

SUSPICIOUS_PATTERNS = [
    (r'bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|tiny\.cc', "URL shortener (destination unknown)"),
    (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', "Raw IP address (no domain)"),
    (r'paypal|amazon|google|apple|microsoft|netflix|bank|secure|login|verify|account|update|confirm', "Phishing keyword in domain"),
    (r'\.tk$|\.ml$|\.ga$|\.cf$|\.gq$', "High-risk free TLD"),
    (r'[0-9]{5,}', "Long numeric string (suspicious)"),
    (r'\.exe$|\.bat$|\.cmd$|\.ps1$|\.vbs$|\.jar$', "Executable file extension"),
]

SAFE_TLDS = {'.com', '.org', '.net', '.edu', '.gov', '.io', '.co', '.uk', '.in', '.dev', '.app'}

def classify_url(parsed):
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in ['.jpg','.png','.gif','.pdf','.mp4','.mp3']):
        return "Media/File"
    if any(kw in path for kw in ['/api/', '/v1/', '/v2/', '/graphql', '/rest/']):
        return "API Endpoint"
    if any(kw in path for kw in ['/login', '/signin', '/auth', '/oauth']):
        return "Authentication"
    if any(kw in path for kw in ['/admin', '/dashboard', '/panel', '/manage']):
        return "Admin/Dashboard"
    if any(kw in path for kw in ['/blog', '/article', '/post', '/news']):
        return "Content/Blog"
    if parsed.path in ['/', '']:
        return "Homepage"
    return "Web Page"

def risk_score(url, parsed, flags):
    score = 0
    if flags:
        score += len(flags) * 20
    if parsed.scheme == 'http':
        score += 15
    if len(url) > 100:
        score += 10
    tld = '.' + parsed.netloc.split('.')[-1].split(':')[0] if '.' in parsed.netloc else ''
    if tld and tld not in SAFE_TLDS:
        score += 10
    subdomain_count = len(parsed.netloc.split('.')) - 2
    if subdomain_count > 2:
        score += 10
    return min(score, 100)

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("No input provided. Send a URL to analyze.")
        return

    url = raw.split('\n')[0].strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
    except Exception as e:
        print(f"Invalid URL: {e}")
        return

    domain = parsed.netloc
    tld = '.' + domain.split('.')[-1].split(':')[0] if '.' in domain else 'unknown'
    scheme = parsed.scheme
    path = parsed.path
    query = parsed.query
    fragment = parsed.fragment
    params = parse_qs(query)
    subdomains = domain.split('.')[:-2] if domain.count('.') >= 2 else []

    # Security flags
    flags = []
    for pattern, label in SUSPICIOUS_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            if 'paypal|amazon' in pattern and not re.search(pattern, domain.split('.')[0], re.IGNORECASE):
                continue
            flags.append(label)

    risk = risk_score(url, parsed, flags)
    url_type = classify_url(parsed)

    if risk == 0:
        risk_label = "SAFE"
    elif risk < 30:
        risk_label = "LOW RISK"
    elif risk < 60:
        risk_label = "MODERATE RISK"
    elif risk < 80:
        risk_label = "HIGH RISK"
    else:
        risk_label = "DANGEROUS"

    print("=" * 44)
    print("   URL INTELLIGENCE REPORT")
    print("=" * 44)
    print(f"  URL           : {url[:60]}{'...' if len(url)>60 else ''}")
    print(f"  Type          : {url_type}")
    print(f"  Protocol      : {scheme.upper()} {'(encrypted)' if scheme=='https' else '(NOT encrypted!)'}")
    print(f"  Domain        : {domain}")
    print(f"  TLD           : {tld} {'(trusted)' if tld in SAFE_TLDS else '(unverified)'}")
    if subdomains:
        print(f"  Subdomains    : {'.'.join(subdomains)}")
    if path and path != '/':
        print(f"  Path          : {path}")
        print(f"  Path depth    : {len([p for p in path.split('/') if p])} levels")
    if params:
        print(f"  Parameters    : {len(params)}")
        for k, v in list(params.items())[:5]:
            print(f"    {k} = {unquote(v[0])[:40]}")
    if fragment:
        print(f"  Fragment      : #{fragment}")
    print(f"  URL length    : {len(url)} chars {'(suspiciously long)' if len(url)>100 else ''}")
    print()
    print(f"  RISK SCORE    : {risk}/100 — {risk_label}")
    if flags:
        print()
        print("  FLAGS:")
        for flag in flags:
            print(f"  ! {flag}")
    else:
        print("  No suspicious patterns detected.")
    print("=" * 44)

if __name__ == "__main__":
    main()