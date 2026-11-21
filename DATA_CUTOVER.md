# Sahih al-Bukhari database rebuild and cutover

## Sources

The React explorer requests hadiths, narrator profiles, and chains from Django REST under `/api/v1`. In development, Vite proxies requests to Django on port 8000. The production build uses the configured `VITE_API_BASE_URL`, which currently points to the Render backend. Bukhari browsing uses the local Django database. Knowledge Graph provides supplementary narrator profiles via `/api/v1/knowledge-graph/rawis/<id>/`. Its hadith endpoint serves confirmed Bukhari text and excludes unreviewed routes. The reader and graph use the local Bukhari catalog. Set `HADITH_KG_API_URL` on the backend to the trusted Knowledge Graph service URL. It defaults to `http://127.0.0.1:8077` for local use.

Django uses `DATABASE_URL` when set and defaults to SQLite otherwise. Check the active deployment configuration privately to identify the database engine and storage. The cloud clone had no active database or `DATABASE_URL`.

The rebuild uses `data/Sahih al-Bukhari.csv` for hadiths and `data/all_rawis.csv` for canonical narrator identities and relationship evidence. The bundled catalog also loads `data/rawis_supplement.csv` for independently documented records missing from the primary export. The loader and validator use the same source rows. A custom `--rawis` file is read on its own. It applies nonempty biographies from `data/muslimscholars_bios.json` by scholar ID when using the bundled rawis catalog. The separate vocalized commentary CSV remains a research reference. Its row numbering differs from the API references, so it is unsuitable as a direct replacement keyed by row number. The existing imported narrator assignments and edge rows are the legacy data being replaced.

## Rebuild and validate a separate database

From the repository root in PowerShell, select a new directory and confirm that neither the database nor the reports already exist. The example writes to your temporary directory. Use the project's Python environment.

```powershell
$build = Join-Path $env:TEMP ("visual-isnad-" + [guid]::NewGuid())
New-Item -ItemType Directory $build | Out-Null
$db = Join-Path $build "bukhari-corrected.sqlite3"
$dbPath = $db.Replace('\', '/')
$priorDatabaseUrl = $env:DATABASE_URL
$env:DATABASE_URL = "sqlite:///$dbPath"

python backend/manage.py migrate --noinput
python backend/manage.py load_bukhari --report (Join-Path $build "import-report.json")
python backend/manage.py check
python backend/validate_bukhari.py $db
python backend/manage.py test isnad
pnpm exec tsc --noEmit
pnpm build
```

Stop if a command fails. The loader requires empty isnad tables and writes the new records in a single database transaction. For a machine with a Unix absolute path, use four slashes before the path, for example `sqlite:////tmp/visual-isnad/bukhari-corrected.sqlite3`.

The JSON import report covers matching margins and unresolved positions, including leading positions on suspended chains. The structural validator reports unresolved teacher edges, checks source coverage and chain continuity, and exits nonzero on validation failures. Its optional `--baseline <read-only-sqlite-copy>` argument compares source references, canonical IDs, and Hadith 1067 with an old SQLite database. Use a consistent snapshot. For a running SQLite database, use SQLite’s online backup API or an equivalent consistent backup procedure.

To preview locally, leave the shell pointed at the candidate, start Django on port 8000, and run `pnpm dev` from a separate shell. Inspect Hadith 1067 and switch between the two paths in Hadith 15. Restore the prior shell setting when the preview finishes.

```powershell
if ($null -eq $priorDatabaseUrl) {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
} else {
    $env:DATABASE_URL = $priorDatabaseUrl
}
```

## Cutover and rollback

1. Obtain a consistent backup of the actual active database. Verify integrity, test restoration to a separate target, and record the active deployment revision and database configuration.
2. Reconcile the candidate against that backup. Preserve editor accounts and permissions, manually edited narrator profiles, and any other application records. Use canonical scholar IDs and full Bukhari numbers for comparison. Review conflicts individually. Legacy unresolved IDs and edge IDs are generated identifiers and should not be transferred as stable identities.
3. Stage the verified data in the database engine and persistent storage used by the deployment. A local SQLite build is a review artifact. For an active PostgreSQL deployment, use a separate PostgreSQL target and repeat the staging checks there.
4. After explicit approval, pause writes, take a final backup, apply any reviewed changes made since staging, and configure Django's `DATABASE_URL` to point at the staged target. Restart Django with the matching backend revision. The frontend can retain its API origin if the backend URL stays the same. Verify editor sign-in, hadith detail and narrator endpoints, Hadiths 1067 and 15 in the explorer, and the first and last pages of large books before restoring writes.
5. If verification fails, pause writes and preserve a snapshot of the new target. Restore the prior database configuration and the compatible backend revision, then restart and verify the old deployment. Reconcile edits made after the switch before any future retry.

## Cloud validation snapshot

The isolated build preserved all 7,277 hadith references and 24,326 canonical IDs, applied 11,880 cached biographies, and produced 39,417 edges. It recorded 8,478 unresolved positions and 39 hadiths without a persisted route. Fifty-eight hadiths have multiple stored routes. Hadith 1067 resolves to `30001 → 30160 → 20278 → 20020 → 11049 → 11054 → 16`. Five links appear in both relationship lists. The Shuʿbah–Abū Isḥāq link appears in Abū Isḥāq's students list.

The separate legacy reproduction stored 7,252 hadiths and 41,123 edges. The candidate retains every source reference and canonical scholar ID present in that reproduction and restores 25 missing references. The candidate reports more uncertainty. The structural checks passed. The regression tests establish identity accuracy for the sampled routes. Inline parallel phrasing and implicit continuations still require review. The active database was unavailable for backup and comparison in the cloud workspace.

## Narrator catalog follow-up

The primary CSV refers to scholar 20208 by ID but omits the scholar's own row. The supplement restores his full name, the aliases Ibn ʿUlayya and Abū Bashr, dates, and the teacher and student IDs from the source profile. In Hadith 15, the commentary identifies Yaʿqūb as al-Dawraqī. The catalog links him to both al-Bukhari and Ibn ʿUlayya, and links Ibn ʿUlayya to ʿAbd al-ʿAzīz ibn Ṣuhayb. Both routes are covered by the API regression test. [Source profile](https://muslimscholars.info/manage.php?ID=20208&submit=scholar)

The follow-up build retains all 7,277 references and 39,417 edges, with 31,209 matched and 8,398 unresolved positions. There are 8,333 edges with an unresolved teacher and 39 hadiths without a stored route. These counts describe matching and coverage. They do not measure identity accuracy for every route.

## Prophet transmission evidence

Hadiths 5 and 1067 describe the Prophet's actions and their explicit imported routes end at Ibn ʿAbbās and Ibn Masʿūd respectively. Explicit source markers such as `عن النبي` in Hadith 94 and `سمعت رسول الله` in Hadith 765 supply a transmission edge. The importer recognizes these markers even when the opening of the report follows the title. Nested questions such as the dialogue in Hadith 7478 require separate reconstruction.

The audit of a new SQLite build compared with the reviewed baseline found 189 hadiths that gained an edge to the Prophet and six whose earlier association was taken from embedded dialogue. It counted 2,098 hadiths with a Prophet edge, 58 with multiple stored routes, 39 without a stored route, and 8,084 unresolved teacher edges. Structural validation passed. The remaining routes need source review before attributing any additional links.

Narrator detail preserves the catalog student list and separately exposes named narrators linked by imported Bukhari edges. Narrator 1 has 15 catalog students and 119 named graph links in the rebuilt database. An existing database can serve the profile and graph changes without schema changes. To see the importer changes, use the separate rebuild procedure above.
