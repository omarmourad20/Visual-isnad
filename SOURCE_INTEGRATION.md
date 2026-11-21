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

## Automated Windows setup and end-to-end check

Run in a dedicated PowerShell session from the checkout root. The expected
hadith and edge counts default to 7,252 and 41,123 for the reported Windows
database. Override both counts only when intentionally selecting another
Visual Isnad build. The project venv is used automatically.

```powershell
.\scripts\Setup-SourcePreview.ps1 -KnowledgeGraphDb 'C:\sources\hadith-kg.db' `
  -FawazJson 'C:\sources\ara-bukhari.min.json' -JaguarJson 'C:\sources\bukhari.json'
.\backend\venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
```

Omit Fawaz or Jaguar when you only need KG. Pass `-VisualDb` to use an
explicit alternate Visual Isnad file. Build input checks happen before any
output is written. A fresh temp directory holds the exports and proposals.
The setup configures `HADITH_SOURCE_CROSSWALK`, `HADITH_KG_API_URL`, and
`HADITH_SOURCE_PREVIEW_DB` in the calling PowerShell session. The preview
server uses SQLite URI `mode=ro` for the exact selected file. Use a dedicated
shell so normal editor sessions continue to use their own database
configuration. For an active WAL database use a consistent backup if you
also need to avoid touching SQLite's shared-memory sidecars.

Download the audited **relational** [KG release](https://huggingface.co/datasets/emadjumaah/hadith-kg/resolve/main/hadith-kg.db),
the [Fawaz Arabic minified edition](https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-bukhari.min.json),
and extract `bukhari.json` from [Jaguar release v1.1.0](https://github.com/Jaguar16/open-hadith-data/releases/tag/v1.1.0).
The setup rejects files whose SHA-256 does not match the audited bytes,
including reserialized JSON and the KG app database. Keep inputs and
generated manifests out of Git.

After Django is listening, run from another terminal:

```powershell
.\scripts\Setup-SourcePreview.ps1 -VerifyOnly
```

The verifier checks the configured KG stats and Hadith 14 upstream, Django's
conversion, its HTTP proposal for Visual 15, both ordered KG routes and
their provenance, and the original graph before and after preview. Set
`-DjangoUrl` and `-KnowledgeGraphUrl` if using different ports. If the original
chain endpoint fails, check that the selected Visual SQLite schema already
matches the running Django code. The tools do not alter the schema. If
Django reports `not_configured`, start it from the shell that built the
crosswalk. A `stale` response indicates that indexed local content no
longer matches the digest. An `available` response with count zero indicates
no proposal for that record.

In React, open Bukhari 15, expand **External source proposals**, and preview
Knowledge Graph. Select sanad 29 and 30, then restore Visual Isnad. Each route
ends at Anas in the provider graph. The local selected chain, narrator and
edge are restored. A provider failure preserves the graph already on screen.

## Windows legacy SQLite and one-command preview

Migration `isnad.0003_transmissionedge_chain_index` added a nullable
`chain_index` column. Databases at schema 0002 can now serve hadith detail,
bootstrap, narrator relationships, and edge reads without applying 0003.
The API preserves IDs, endpoints and sequence and returns null for unknown
indices. The browser displays contiguous recorded edge segments and labels
unknown route boundaries. It never writes an index or treats an external
sanad as an original route. Staff edge edits are disabled when the column
is absent. Database editing is also unavailable in the read-only preview.

For a standard Windows checkout run from its repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Setup-SourcePreview.ps1 -KnowledgeGraphDb 'C:\sources\hadith-kg.db' -DjangoUrl 'http://127.0.0.1:8769' -StartServer
```

The child PowerShell's execution policy applies to that process only. The
wrapper resolves the project and venv from its script location. It checks
the requested loopback port, and starts Django in the same worktree with
the exact validated SQLite path and crosswalk in its inherited environment.
It reports the new server PID and log paths and leaves that server running
for browser verification. If the port is occupied, choose another one.
The wrapper never terminates an existing process. If you start Django
manually instead, run the setup in the same shell or set
`HADITH_SOURCE_PREVIEW_DB` and `HADITH_SOURCE_CROSSWALK` explicitly.

For the legacy database expect the verifier to report
`chain_index_available=False`, then pass both converted KG routes and the
unchanged local graph check. Keep the original database at its current
schema for this verification. Any future editor schema decision should
first use a consistent SQLite backup and validate integrity and foreign
keys on a disposable copy. Migration 0003 alone leaves existing indices
null and does not reconstruct routes; reverse migration removes that
column and would discard any indices subsequently recorded there.

If using Vite with the server on 8769, start it from another shell with
`$env:VITE_API_BASE_URL = 'http://127.0.0.1:8769'`. If the browser reports
a cross-origin error, configure Django's explicit
`CORS_ALLOWED_ORIGINS` for the exact Vite URL in the shell that launches
setup and Django.

### Diagnose a missing chain_index error at bootstrap

If `/api/v1/hadiths/bootstrap/` reports `no such column:
isnad_transmissionedge.chain_index`, confirm the running Django process
uses this checkout and includes commit `a34e5ff`. The narrator profile
presentation branch at `4176470` already includes that compatibility
commit. Check ancestry from the checkout with
`git merge-base --is-ancestor a34e5ff HEAD`. Exit code 0 confirms the
local checkout includes the fix. Check the served process separately:
another worktree or a still-running server can serve older code.

A compatible server returns HTTP 200 with `chain_index_available: false`
and null edge indices for the legacy database. It returns the stored
indices for an indexed database. The database does not need a schema
change for bootstrap. The focused bootstrap tests can run without a
database or migrations:

```powershell
.\backend\venv\Scripts\python.exe .\backend\manage.py test isnad.tests.test_bootstrap_schema
```
