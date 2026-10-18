"""Standalone check of the classify_reason node: no graph, no database.

Run inside the container so the env vars from docker-compose are present:
    docker compose run --rm backend python test.py
"""
from graph.classify_reason import classify_reason

ALLOWED = {"Changed Mind", "Defective", "Incorrect Items Delivered", "Other"}

# (customer's reason, category we expect)
CASES = [
    ("I changed my mind, I don't want it anymore", "Changed Mind"),
    ("It doesn't suit my style after all", "Changed Mind")
    # ("The screen was cracked when I turned it on", "Defective"),
    # ("It stopped working after two days", "Defective"),
    # ("I received the wrong size", "Incorrect Items Delivered"),
    # ("You sent me a blue one but I ordered black", "Incorrect Items Delivered"),
    # ("asdf qwerty", "Other"),
    # ("My cat likes the box more than the product", "Other"),
    # ("", "Other"),
]


def main():
    matches = 0
    invalid = 0
    for reason, expected in CASES:
        actual = classify_reason({"return_reason": reason}).get("reason_category")
        if actual not in ALLOWED:
            flag = "NOT ALLOWED"
            invalid += 1
        elif actual == expected:
            flag = "ok"
            matches += 1
        else:
            flag = "MISMATCH"
        print(f"{flag:<12} expected={expected:<26} got={actual!s:<26} | {reason!r}")

    print(f"\n{matches}/{len(CASES)} matched, {invalid} invalid values")


if __name__ == "__main__":
    main()