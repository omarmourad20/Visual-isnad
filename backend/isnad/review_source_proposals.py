"""Validate explicit decisions against a crosswalk and write a separate review manifest."""
import argparse
import json
from pathlib import Path

BINDINGS = ("left_key", "right_key", "left_text_digest", "right_text_digest")
REVIEW_FIELDS = (*BINDINGS, "decision", "reviewer", "evidence")


def review(bundle, decisions):
    if bundle["schema_version"] != 2 or bundle["policy"] != "proposals_only_no_automatic_adoption":
        raise ValueError("Expected a version 2 proposal bundle")
    proposals = {tuple(row[key] for key in BINDINGS): row for row in bundle["proposals"]}
    reviews = {}
    for decision in decisions:
        binding = tuple(decision[key] for key in BINDINGS)
        if binding not in proposals or binding in reviews:
            raise ValueError("Decision must uniquely identify a current, text-bound proposal")
        if decision["decision"] not in {"accepted_text_reference", "rejected"}:
            raise ValueError("Unsupported decision")
        if any(not isinstance(decision[key], str) or not decision[key].strip() for key in REVIEW_FIELDS):
            raise ValueError("Each review field must be a nonempty string")
        reviews[binding] = {key: decision[key] for key in REVIEW_FIELDS}
    return {
        "schema_version": 1,
        "policy": "text_reference_review_only_no_chain_adoption",
        "unreviewed_count": len(proposals) - len(reviews),
        "reviews": [reviews[key] for key in sorted(reviews)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = review(json.loads(args.crosswalk.read_text(encoding="utf-8")),
                      json.loads(args.decisions.read_text(encoding="utf-8")))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
