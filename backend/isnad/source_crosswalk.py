"""Read-only exact-text crosswalk candidate generation; no automatic adoption."""
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
import argparse
import json

try:
    from .source_matching import HadithRecord, external_key, normalize_arabic, propose_match
except ImportError:
    from source_matching import HadithRecord, external_key, normalize_arabic, propose_match

def parse_record(row):
    required = ('provider', 'edition', 'native_id', 'collection', 'arabic_matn')
    if not isinstance(row, dict) or any(key not in row for key in required):
        raise ValueError('Each record must contain: ' + ', '.join(required))
    if any(not isinstance(row[key], str) for key in required):
        raise ValueError('All required fields must be strings')
    if not all(row[key].strip() for key in ('provider', 'edition', 'native_id', 'collection')):
        raise ValueError('Provider, edition, native_id and collection cannot be blank')
    return HadithRecord(**{key: row.get(key, '') for key in (*required, 'printed_reference')})

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
        normalized = normalize_arabic(record.arabic_matn)
        if normalized:
            index[(normalize_arabic(record.collection), normalized)].append(record)
    proposals, unmatched, missing = [], [], []
    for record in left:
        normalized = normalize_arabic(record.arabic_matn)
        if not normalized:
            missing.append(external_key(record))
            continue
        matches = index.get((normalize_arabic(record.collection), normalized), [])
        if not matches:
            unmatched.append(external_key(record))
            continue
        for candidate in matches:
            proposal = asdict(propose_match(record, candidate))
            proposal['ambiguity'] = 'multiple_candidates' if len(matches) > 1 else 'single_candidate'
            proposals.append(proposal)
    proposals.sort(key=lambda p: (p['left_key'], p['right_key']))
    return {'schema_version': 1, 'policy': 'proposals_only_no_automatic_adoption',
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
    parser.add_argument('--right', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('Output already exists; refusing to overwrite')
    result = build_crosswalk(load_records(args.left), load_records(args.right))
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result['counts'], ensure_ascii=False))

if __name__ == '__main__':
    main()
