# Reproduce the hadith source benchmark

Use Python 3.10+ from the directory containing `reports/` and `scripts/`.
No packages or credentials are needed. The benchmark reads existing DBs with
`mode=ro` and `query_only` and writes results to stdout. Prefer stable,
consistent snapshots. The HTTP probe issues bounded GETs.

Download the upstream files independently using the links in the report.
Use Jaguar release v1.1.0 and extract `bukhari.json` from
`collections-json.zip`. Use `editions/ara-bukhari.min.json` and
`editions/eng-bukhari.min.json` from Fawaz CDN version 1, and both Bukhari
CSVs from mhashim6. Use the KG relational `hadith-kg.db` release, not the
application database. Use Visual Isnad's corrected SQLite snapshot.

```sh
python -m unittest discover -s tests -v
python scripts/probe_hadith_sources.py --kg http://127.0.0.1:8077 > probes.json
python scripts/benchmark_bukhari.py --visual visual.sqlite3 \
  --mhashim plain.csv --mhashim-vocalized vocalized.csv \
  --jaguar bukhari.json --fawaz-ar ara-bukhari.min.json \
  --fawaz-en eng-bukhari.min.json > benchmark.json
python scripts/audit_knowledge_graph.py --visual visual.sqlite3 \
  --kg hadith-kg.db --samples benchmark.json --book-id 1 > kg-audit.json
```

The probe's default KG sample is internal hadith ID 17154, Sunan Abi Dawud
832 in the inspected release. It is a smoke test. For Bukhari mappings use
the audit's edition-aware candidates. Candidate output is not an accepted
crosswalk. Current service revisions may report different figures.

Input fingerprints for the published results (SHA-256):

| Input | SHA-256 |
|---|---|
| Visual snapshot | b85f2eec6925a9acb9a7b228def15b1f94ceff3a8faa8bd6819b600a5d30671f |
| KG relational snapshot | d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6 |
| Jaguar extracted Bukhari JSON | 09268f6384da9ae4bd1c4051c4235c2d1c350829d5c56ca82cd770c682374c8e |
| Fawaz Arabic | f887d8724f75fb6e1d5d29342a173af5346ad9b933173c85e6e3cb570063ea33 |
| Fawaz English | 60f8dfcf2cb8bcd2c8e281be68d912ee153e0fc4d02ad317d33c532d3814a04f |
| mhashim6 plain CSV | e78f8ea42c4bdf58027a2b634b0d19393f4a3232645ed79887959a2978685317 |
