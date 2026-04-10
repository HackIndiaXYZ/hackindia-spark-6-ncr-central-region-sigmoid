#!/usr/bin/env python3
import sys
import json
import re
import math
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

def detect_type(val):
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, int):
        return "integer"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "string"
    if isinstance(val, list):
        return "array"
    if isinstance(val, dict):
        return "object"
    return "unknown"

def stats_for_numbers(nums):
    if not nums:
        return None
    n = len(nums)
    mean = sum(nums) / n
    sorted_nums = sorted(nums)
    mid = n // 2
    median = sorted_nums[mid] if n % 2 else (sorted_nums[mid-1] + sorted_nums[mid]) / 2
    variance = sum((x - mean) ** 2 for x in nums) / n
    std = math.sqrt(variance)
    return {"count": n, "min": min(nums), "max": max(nums), "mean": round(mean, 4), "median": median, "std_dev": round(std, 4)}

def analyze_object(obj, depth=0, max_depth=3):
    results = []
    if depth > max_depth:
        return ["  (max depth reached)"]
    if isinstance(obj, dict):
        results.append(f"  Keys ({len(obj)}): {', '.join(list(obj.keys())[:10])}")
        nums = [v for v in obj.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if nums:
            s = stats_for_numbers(nums)
            results.append(f"  Numeric values -> mean: {s['mean']}, min: {s['min']}, max: {s['max']}")
        str_vals = [v for v in obj.values() if isinstance(v, str)]
        if str_vals:
            avg_len = sum(len(s) for s in str_vals) / len(str_vals)
            results.append(f"  String values ({len(str_vals)}) -> avg length: {avg_len:.1f} chars")
    elif isinstance(obj, list):
        results.append(f"  Length: {len(obj)}")
        if obj:
            types = Counter(detect_type(item) for item in obj)
            results.append(f"  Item types: {dict(types)}")
            nums = [x for x in obj if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if nums:
                s = stats_for_numbers(nums)
                results.append(f"  Numeric stats -> mean: {s['mean']}, min: {s['min']}, max: {s['max']}, std: {s['std_dev']}")
    return results

def flatten_keys(obj, prefix='', keys=None):
    if keys is None:
        keys = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.append(full_key)
            flatten_keys(v, full_key, keys)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:3]):
            flatten_keys(item, f"{prefix}[{i}]", keys)
    return keys

def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print("No input provided. Send valid JSON.")
        return

    # Try parsing JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        # Try extracting JSON from text
        match = re.search(r'[\[{].*[\]}]', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                print(f"Invalid JSON: {e}")
                print("Tip: Send raw JSON or a string containing JSON.")
                return
        else:
            print(f"Invalid JSON: {e}")
            return

    root_type = detect_type(data)
    print("=" * 44)
    print("   JSON DATA INTELLIGENCE REPORT")
    print("=" * 44)
    print(f"  Root type     : {root_type}")

    raw_str = json.dumps(data)
    print(f"  Size          : {len(raw_str)} chars")
    print(f"  Depth         : {str(raw_str).count('{') + str(raw_str).count('[')}")

    if isinstance(data, dict):
        print(f"  Keys          : {len(data)}")
        key_types = Counter(detect_type(v) for v in data.values())
        print(f"  Value types   : {dict(key_types)}")
        print()
        print("  FIELD ANALYSIS:")
        for line in analyze_object(data):
            print(line)
        all_keys = flatten_keys(data)
        print()
        print(f"  All paths ({len(all_keys)}):")
        for k in all_keys[:15]:
            print(f"    {k}")
        if len(all_keys) > 15:
            print(f"    ... and {len(all_keys)-15} more")

    elif isinstance(data, list):
        print(f"  Length        : {len(data)}")
        if data:
            item_types = Counter(detect_type(x) for x in data)
            print(f"  Item types    : {dict(item_types)}")
            print()
            print("  ARRAY ANALYSIS:")
            for line in analyze_object(data):
                print(line)
            if all(isinstance(x, dict) for x in data):
                all_keys = set()
                for item in data:
                    all_keys.update(item.keys())
                print(f"  Common keys   : {', '.join(sorted(all_keys)[:10])}")
                nums_per_key = {}
                for key in all_keys:
                    vals = [item.get(key) for item in data if isinstance(item.get(key), (int, float))]
                    if vals:
                        nums_per_key[key] = stats_for_numbers(vals)
                if nums_per_key:
                    print()
                    print("  NUMERIC FIELD STATS:")
                    for key, s in list(nums_per_key.items())[:5]:
                        print(f"    {key:<20} mean={s['mean']}, min={s['min']}, max={s['max']}")

    elif isinstance(data, (int, float)):
        print(f"  Value         : {data}")

    elif isinstance(data, str):
        print(f"  Length        : {len(data)} chars")
        print(f"  Words         : {len(data.split())}")

    print("=" * 44)

if __name__ == "__main__":
    main()