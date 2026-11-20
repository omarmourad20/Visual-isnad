"""Read-only exact-text crosswalk candidate generation; no automatic adoption."""
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
import argparse
import json

try:
    from .source_matching import HadithRecord, external_key, normalize_arabic, propose_match, text_digest, text_keys
except ImportError:
    from source_matching import HadithRecord, external_key, normalize_arabic, propose_match, text_digest, text_keys

def parse_record(row):
    required = ('provider', 'edition', 'native_id', 'collection', 'arabic_matn')
    if not isinstance(row, dict) or any(key not in row for key in required):
        raise ValueError('Each record must contain: ' + ', '.join(required))
    if any(not isinstance(row[key], str) for key in required):
        raise ValueError('All required fields must be strings')
    if not all(row[key].strip() for key in ('provider', 'edition', 'native_id', 'collection')):
        raise ValueError('Provider, edition, native_id and collection cannot be blank')
    if any(not isinstance(row.get(key, ''), str) for key in ('printed_reference', 'arabic_full', 'arabic_isnad')):
        raise ValueError('Optional text fields must be strings')
    return HadithRecord(**{key: row.get(key, '') for key in (*required, 'printed_reference', 'arabic_full', 'arabic_isnad')})

def load_records(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('Expected JSON array of records')
    records = [parse_record(row) for row in data]
    keys = [external_key(record) for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate provider/edition/native_id keys')
    return records

def build_crosswalk(left, right):
    """Preserve every exact normalized match, including ambiguous many-to-many pairs."""
    index = defaultdict(list)
    for record in right:
        for key in text_keys(record):
            index[(normalize_arabic(record.collection), key)].append(record)
    proposals, unmatched, missing = [], [], []
    for record in left:
        keys = text_keys(record)
        if not keys:
            missing.append(external_key(record))
            continue
        collection = normalize_arabic(record.collection)
        matches = {
            external_key(candidate): candidate
            for key in keys for candidate in index.get((collection, key), ())
        }
        if not matches:
            unmatched.append(external_key(record))
            continue
        for candidate in matches.values():
            proposal = asdict(propose_match(record, candidate))
            proposal.update(
                left_id=record.native_id, left_provider=record.provider, left_text_digest=text_digest(record),
                right_id=candidate.native_id, provider=candidate.provider, edition=candidate.edition,
                reference=candidate.printed_reference, right_text_digest=text_digest(candidate),
                ambiguity="single_candidate",
            )
            proposals.append(proposal)
    left_groups, right_groups = Counter(), defaultdict(set)
    for proposal in proposals:
        left_groups[proposal["left_key"], proposal["provider"], proposal["edition"]] += 1
        right_groups[proposal["right_key"]].add(proposal["left_key"])
    for proposal in proposals:
        peers = left_groups[proposal["left_key"], proposal["provider"], proposal["edition"]]
        if peers > 1 or len(right_groups[proposal["right_key"]]) > 1:
            proposal["ambiguity"] = "multiple_candidates"
            proposal["confidence"] = "ambiguous"
    proposals.sort(key=lambda p: (p['left_key'], p['right_key']))
    return {'schema_version': 2, 'policy': 'proposals_only_no_automatic_adoption',
            'counts': {'left_records': len(left), 'right_records': len(right),
                       'left_with_candidates': len({p['left_key'] for p in proposals}),
                       'candidate_pairs': len(proposals), 'left_unmatched': len(unmatched),
                       'left_missing_text': len(missing),
                       'ambiguous_left': len({p['left_key'] for p in proposals if p['ambiguity'] == 'multiple_candidates'})},
            'proposals': proposals, 'unmatched_left_keys': sorted(unmatched),
            'missing_text_left_keys': sorted(missing)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', required=True)
    parser.add_argument('--right', required=True, action='append', help='Repeat for each external source')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('Output already exists; refusing to overwrite')
    right = [record for path in args.right for record in load_records(path)]
    if len(right) != len({external_key(record) for record in right}):
        parser.error('Duplicate source keys across right-hand inputs')
    result = build_crosswalk(load_records(args.left), right)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result['counts'], ensure_ascii=False))

if __name__ == '__main__':
    main()
