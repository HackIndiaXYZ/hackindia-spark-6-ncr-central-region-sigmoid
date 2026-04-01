#!/usr/bin/env python3
import sys
import re
import math
from collections import Counter

def tfidf_keywords(text, top_n=8):
    # Manual TF-IDF — no sklearn needed, works anywhere
    stopwords = {
        'the','a','an','and','or','but','in','on','at','to','for','of','with',
        'is','was','are','were','it','this','that','i','you','we','they','he',
        'she','be','been','being','have','has','had','do','does','did','will',
        'would','could','should','may','might','can','not','no','so','if','as',
        'by','from','up','about','into','through','during','its','our','your'
    }
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        sentences = [text]

    def tokenize(s):
        return [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', s) if w.lower() not in stopwords]

    all_tokens = [tokenize(s) for s in sentences]
    flat = [w for tokens in all_tokens for w in tokens]
    tf = Counter(flat)
    total = len(flat) or 1

    # IDF
    n_docs = len(sentences)
    idf = {}
    for word in set(flat):
        containing = sum(1 for tokens in all_tokens if word in tokens)
        idf[word] = math.log((n_docs + 1) / (containing + 1)) + 1

    scores = {w: (count/total) * idf.get(w, 1) for w, count in tf.items()}
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

def detect_topics(keywords):
    topic_map = {
        'Technology': ['software','code','data','algorithm','model','system','network','api','python','machine'],
        'Business': ['market','revenue','growth','company','product','customer','sales','profit','strategy'],
        'Science': ['research','study','experiment','analysis','results','hypothesis','evidence','theory'],
        'Health': ['patient','treatment','disease','clinical','medical','health','drug','symptoms'],
        'Finance': ['investment','stock','financial','economy','bank','money','fund','trading'],
    }
    kw_set = {k.lower() for k,_ in keywords}
    scores = {}
    for topic, words in topic_map.items():
        scores[topic] = sum(1 for w in words if w in kw_set or any(w in k for k in kw_set))
    best = max(scores.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else "General"

def main():
    text = sys.stdin.read().strip()
    if not text:
        print("No input provided.")
        return

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    sentences = len(re.split(r'[.!?]+', text))
    keywords = tfidf_keywords(text)
    topic = detect_topics(keywords)

    print("=" * 42)
    print("  TF-IDF KEYWORD & TOPIC ANALYSIS")
    print("=" * 42)
    print(f"  Words     : {len(words)}")
    print(f"  Sentences : {sentences}")
    print(f"  Topic     : {topic}")
    print()
    print("  TOP KEYWORDS (by TF-IDF score):")
    for i, (word, score) in enumerate(keywords, 1):
        print(f"  {i:2}. {word:<18} {score:.4f}")
    print("=" * 42)

if __name__ == "__main__":
    main()