# Integration architecture

Keep Django/SQLite as Visual Isnad's default application read model and preserve the current React API contract. Use the existing Bukhari snapshot for reviewed edition references and paths. Evaluate the independently versioned Knowledge Graph (KG) as an additional source for new routes, dossiers, source-attributed criticism and Arabic cross-collection search. A wider corpus increases coverage. It does not establish chain accuracy.

| Feature | Primary choice | Enrichment and fallback |
|---|---|---|
| Arabic reading | Existing reviewed Bukhari edition, preserving original vocalization | Pinned KG or Fawaz Arabic editions after reference and text checks. mhashim6 vocalized commentary supports editorial review. |
| English reading | Existing reviewed translation where redistribution rights are confirmed | Official Sunnah.com with permission, or a separately cleared translation. Jaguar and Fawaz are concordance candidates. |
| Isnad | Reviewed Django paths for existing Bukhari | KG candidate paths for additional routes and books. Keep unresolved nodes visible and provenance attached. |
| Narrators | Existing canonical catalog and reviewed local editor overlays | KG dossiers and named jarh wa ta'dil critics, with MuslimScholars profile links as supplemental evidence. |
| Search | Preserve the Django API. Prototype a normalized Arabic and English SQLite FTS5 index and benchmark it before adoption. | KG Arabic FTS and meaning search as optional expansion. |
| Cross-references | Reviewed edition crosswalk and official Sunnah reference/URN interface if licensed | KG meaning groups and takhrij as related reports, with relation types labeled. Dorar as an editorial reference. |

## Identity and provenance

Use immutable internal IDs and external keys scoped by provider, release, edition and native ID. Store collection, book, full printed reference including suffixes, and page or volume if present. Keep physical report, translation, route and meaning-group IDs separate. Allow multiple mappings for split and combined reports. Match first on edition context and conservatively normalized Arabic, then use narrator overlap and reference context. Equal text and numbers can both recur. Fuzzy text and semantics generate proposals that need review.

Record provider URI, checksum/revision, release date, rights, acquisition time, exact source ID, extraction version, reviewer and rationale. Keep raw Arabic for display, and attach provenance independently to text, translation, narrator facts, and every route. Preserve competing attributed judgments and manual editor overlays. Verify common-name narrator mappings using aliases, chronology and teacher/student evidence. Preserve source order, unresolved positions, separate routes, and source direction. Never create a Prophet edge solely from a mention in the matn, dialogue or meaning-group label. Model companion attribution, spoken quotation and graph endpoints separately.

## Serving and validation

Django adapters should ingest or read pinned provider versions. React keeps its existing API and can display labelled source alternatives. Cache by provider/version/native ID/locale, use bounded timeouts and retries for transient HTTP failures, and fall back to last-known reviewed data. Keep credentials server-side, and never fall back by guessing an equivalent hadith or narrator ID. Preserve auth, editor roles and overrides. Search indexes and provider caches should be disposable and reproducible.

1. **Rights first.** Secure translation, biography and criticism terms. Pin approved source files with hashes.
2. **Crosswalk pilot.** Review the Bukhari anchors, reproducible random sample, suffixed refs and repeated texts. Compare entire ordered chains with an edition-based adjudication set. Measure path precision and recall only once that reviewed set exists.
3. **Staging.** Check row coverage, FK integrity, orphan IDs, route direction and continuity, position gaps, ambiguous aliases, explicit terminal evidence and source deduplication. Run editor, Arabic/English reader, search and multi-chain regressions. Measure latency and failures separately for local and provider paths.
4. **Enrich before replacing.** Serve optional KG routes and biographies in shadow or opt-in mode. Keep the existing database and reviewed content active. Any later cutover is a separate approval with consistent backups, manual edit reconciliation and rollback.
