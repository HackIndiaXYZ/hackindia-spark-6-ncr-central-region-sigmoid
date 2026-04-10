#!/usr/bin/env python3
import sys
import re
import math

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

def syllable_count(word):
    word = word.lower().strip(".,!?;:'\"")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)

def flesch_score(words, sentences, syllables):
    if sentences == 0 or words == 0:
        return 0
    return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

def grade_level(words, sentences, syllables):
    if sentences == 0 or words == 0:
        return 0
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

def reading_time(words):
    minutes = words / 200
    if minutes < 1:
        return f"{int(minutes * 60)} seconds"
    return f"{minutes:.1f} minutes"

def main():
    text = sys.stdin.read().strip()
    if not text:
        print("No input provided.")
        return

    sentences = len(re.findall(r'[.!?]+', text)) or 1
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    word_count = len(words) or 1
    syllables = sum(syllable_count(w) for w in words)
    chars = len(text)
    unique_words = len(set(w.lower() for w in words))
    avg_word_len = sum(len(w) for w in words) / word_count
    avg_sentence_len = word_count / sentences
    long_words = sum(1 for w in words if len(w) > 6)
    long_word_pct = long_words / word_count * 100

    flesch = flesch_score(word_count, sentences, syllables)
    grade = grade_level(word_count, sentences, syllables)

    if flesch >= 70:
        ease = "Easy (plain English)"
    elif flesch >= 50:
        ease = "Medium (standard)"
    elif flesch >= 30:
        ease = "Difficult (academic)"
    else:
        ease = "Very Difficult (technical)"

    print("=" * 44)
    print("   READABILITY ANALYSIS REPORT")
    print("=" * 44)
    print(f"  Words            : {word_count}")
    print(f"  Sentences        : {sentences}")
    print(f"  Characters       : {chars}")
    print(f"  Unique words     : {unique_words}")
    print(f"  Avg word length  : {avg_word_len:.1f} chars")
    print(f"  Avg sentence len : {avg_sentence_len:.1f} words")
    print(f"  Long words (>6)  : {long_word_pct:.1f}%")
    print(f"  Reading time     : {reading_time(word_count)}")
    print()
    print(f"  Flesch score     : {flesch:.1f} / 100")
    print(f"  Grade level      : {grade:.1f}")
    print(f"  Difficulty       : {ease}")
    print("=" * 44)

if __name__ == "__main__":
    main()