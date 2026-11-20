# Hadith source matching and preview

The configured application database remains authoritative. A proposal is a
possible correspondence between two edition records. An external sanad is
a route reported by the configured KG service and remains unreviewed in the
application. Neither becomes an authoritative chain through this pipeline.
There is no production adoption or database migration command.

## Windows setup

Use the established project Python environment with Django and the pinned
dependencies installed. From the checkout's `backend` directory, substitute
the paths to existing snapshots or freshly downloaded release files. KG
uses the relational Hugging Face `hadith-kg.db`, not the app DB. Jaguar uses
the Bukhari JSON from release v1.1.0. Fawaz uses the Arabic Bukhari edition,
not the English edition. Give each input an explicit edition or snapshot
identifier. Output files must be new. Open stable copies of live SQLite files
for export if a repeatable comparison is needed.

```powershell
Set-Location backend
$python = (Get-Command python).Source
$run = Join-Path $env:TEMP ("visual-isnad-sources-" + [guid]::NewGuid())
New-Item -ItemType Directory $run | Out-Null
& $python -m isnad.export_source_records --source visual --db 'C:\snapshots\visual.sqlite3' --edition visual-corrected --output "$run\visual.json"
& $python -m isnad.export_source_records --source kg --db 'C:\snapshots\hadith-kg.db' --book-id 1 --edition kg-pinned --output "$run\kg.json"
& $python -m isnad.export_source_records --source fawaz --json 'C:\sources\ara-bukhari.min.json' --edition cdn-v1-ar --output "$run\fawaz.json"
& $python -m isnad.export_source_records --source jaguar --json 'C:\sources\bukhari.json' --edition v1.1.0 --output "$run\jaguar.json"
& $python -m isnad.source_crosswalk --left "$run\visual.json" --right "$run\kg.json" --right "$run\fawaz.json" --right "$run\jaguar.json" --output "$run\proposals.json"
$env:HADITH_SOURCE_CROSSWALK = "$run\proposals.json"
$env:HADITH_KG_API_URL = 'http://127.0.0.1:8077'
& $python manage.py runserver 127.0.0.1:8000
```

Start Vite from the repository root in another terminal with
`pnpm install --frozen-lockfile` and `pnpm dev`. Vite's default development
proxy expects Django on port 8000. The database selected by Django must
correspond to the Visual export; stale proposals are suppressed by a digest
of the local Arabic representations. Keep proposals outside Git. To disable
enrichment, unset `HADITH_SOURCE_CROSSWALK` and restart Django.

## Workflow and safety gates

1. **Discovery.** Read the source representations. Keep separate fields for
   Arabic matn, isnad text and full report when known. Preserve the native
   collection and edition reference context. KG derives spans from bounded
   source offsets. Jaguar provides text splits. Fawaz contributes full
   reports without a guessed split.
2. **Matching.** Generate repeatable proposals from collection-scoped exact
   normalized matn, word-spacing-insensitive longer matn, or normalized full
   report. An identical number is never a search key. Isnad text agreement
   is a separate observation. It cannot verify identity or chain equivalence.
3. **Validation.** Inspect the edition, wording, alternative routes, each
   narrator's identity, and explicit attribution. One-to-many and many-to-one
   matches in a source edition are marked ambiguous. Missing and unmatched
   inputs remain explicit. There is no fuzzy auto-matching.
4. **Enrichment.** Django serves read-only, paginated proposals at
   `/api/v1/hadiths/<local-reference>/sources/`. The corresponding
   `source-routes/?source_key=...` endpoint previews a listed KG record only
   when the current provider confirms the Bukhari collection and corroborates
   the text. The existing KG narrator endpoint returns the provider's
   profiles and reported relationships. The frontend preserves the original
   reader and can restore the local graph without a second request. Provider
   failure leaves the current graph usable. Fawaz and Jaguar contribute
   text proposals only.
5. **Review.** Record decisions in a JSON array. Copy the four binding
   fields `left_key`, `right_key`, `left_text_digest`, and
   `right_text_digest` from a proposal, and add nonempty `reviewer`,
   `evidence`, and `decision` fields. Allowed decisions are
   `accepted_text_reference` and `rejected`. Run
   `python -m isnad.review_source_proposals --crosswalk proposals.json --decisions decisions.json --output reviewed.json`.
   This creates a separate review artifact. A decision about text and
   edition identity leaves narrator and route approval pending.
6. **Adoption.** Require a separate explicit decision, verified route
   provenance, source rights, and a reviewed staging procedure before
   changing the application database. No path in this feature writes to it.

## Snapshot comparison

Measured against 7,277 records in the corrected Visual Bukhari snapshot.
Counts are proposal coverage, not accuracy or independent corroboration.

| External edition | Exported records | Visual records with candidates | Candidate pairs | Visual records flagged ambiguous |
|---|---:|---:|---:|---:|
| KG relational Bukhari, SHA-256 prefix d5280843 | 7,031 | 4,617 | 5,007 | 385 |
| Fawaz CDN v1 Arabic | 7,580 | 7,266 | 7,585 | 305 |
| Jaguar v1.1.0 Bukhari | 7,252 | 7,252 | 7,760 | 429 |

Bukhari 1 produced KG record 1 with normalized matn agreement. Visual Bukhari
15 produced KG record 14 with spacing-normalized matn agreement. Its two
ordered routes were verified in a browser against HTTP fixtures made from
the published KG SQLite release. Text concordance alone cannot establish
chain accuracy or whether different sources share a common transcription.
Review source licenses before redistributing source records.

## Verification

Run the full Django tests from `backend` with
`DATABASE_URL=sqlite:///:memory:` in a separate test shell. Run
`node --test tests/narratorTags.test.mjs tests/transmissionPaths.test.mjs`,
`pnpm exec tsc --noEmit`, and `pnpm build` from the checkout root.
The Django suite passed on Linux with Python 3.12.14 and 3.15.2.
Live Windows KG and Windows-specific behavior still require a local run.
