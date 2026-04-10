#!/usr/bin/env python3
import sys
import re
import math
import string

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

def entropy(password):
    charset = 0
    if re.search(r'[a-z]', password): charset += 26
    if re.search(r'[A-Z]', password): charset += 26
    if re.search(r'[0-9]', password): charset += 10
    if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password): charset += 32
    if charset == 0:
        return 0
    return len(password) * math.log2(charset)

def check_patterns(password):
    issues = []
    if re.search(r'(.)\1{2,}', password):
        issues.append("repeated characters (e.g. aaa)")
    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
        issues.append("sequential pattern detected")
    common = ['password','123456','qwerty','letmein','admin','welcome','monkey','dragon','master','sunshine','princess','iloveyou','superman','batman']
    if password.lower() in common or any(c in password.lower() for c in common):
        issues.append("contains common password pattern")
    if re.search(r'(19|20)\d{2}', password):
        issues.append("contains year (guessable)")
    return issues

def crack_time(entropy_bits):
    guesses_per_second = 1e10
    seconds = (2 ** entropy_bits) / (2 * guesses_per_second)
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    elif seconds < 86400:
        return f"{seconds/3600:.1f} hours"
    elif seconds < 31536000:
        return f"{seconds/86400:.1f} days"
    elif seconds < 3153600000:
        return f"{seconds/31536000:.1f} years"
    else:
        return f"{seconds/3153600000:.1f} centuries"

def score_password(password):
    score = 0
    checks = []

    if len(password) >= 8: score += 1; checks.append(("Length >= 8", True))
    else: checks.append(("Length >= 8", False))

    if len(password) >= 12: score += 1; checks.append(("Length >= 12", True))
    else: checks.append(("Length >= 12", False))

    if re.search(r'[a-z]', password): score += 1; checks.append(("Lowercase letters", True))
    else: checks.append(("Lowercase letters", False))

    if re.search(r'[A-Z]', password): score += 1; checks.append(("Uppercase letters", True))
    else: checks.append(("Uppercase letters", False))

    if re.search(r'[0-9]', password): score += 1; checks.append(("Numbers", True))
    else: checks.append(("Numbers", False))

    if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password): score += 1; checks.append(("Special characters", True))
    else: checks.append(("Special characters", False))

    issues = check_patterns(password)
    if not issues: score += 1; checks.append(("No weak patterns", True))
    else: checks.append(("No weak patterns", False))

    return score, checks, issues

def strength_label(score):
    if score <= 2: return "VERY WEAK", "var(--red)"
    if score <= 3: return "WEAK", ""
    if score <= 5: return "MODERATE", ""
    if score <= 6: return "STRONG", ""
    return "VERY STRONG", ""

def suggest(password):
    suggestions = []
    if len(password) < 12:
        suggestions.append("Use at least 12 characters")
    if not re.search(r'[A-Z]', password):
        suggestions.append("Add uppercase letters")
    if not re.search(r'[0-9]', password):
        suggestions.append("Add numbers")
    if not re.search(r'[!@#$%^&*]', password):
        suggestions.append("Add special characters (!@#$%^&*)")
    if not suggestions:
        suggestions.append("Good password! Consider using a passphrase for memorability.")
    return suggestions

def main():
    password = sys.stdin.read().strip()
    if not password:
        print("No input provided. Send a password to analyze.")
        return

    ent = entropy(password)
    score, checks, issues = score_password(password)
    label, _ = strength_label(score)
    time_to_crack = crack_time(ent)

    print("=" * 44)
    print("   PASSWORD STRENGTH ANALYSIS")
    print("=" * 44)
    print(f"  Length        : {len(password)} characters")
    print(f"  Entropy       : {ent:.1f} bits")
    print(f"  Crack time    : {time_to_crack} (at 10B/sec)")
    print(f"  Score         : {score}/7")
    print(f"  Strength      : {label}")
    print()
    print("  SECURITY CHECKS:")
    for check, passed in checks:
        status = "+" if passed else "-"
        print(f"  [{status}] {check}")

    if issues:
        print()
        print("  WARNINGS:")
        for issue in issues:
            print(f"  ! {issue}")

    print()
    print("  SUGGESTIONS:")
    for s in suggest(password):
        print(f"  > {s}")
    print("=" * 44)

if __name__ == "__main__":
    main()