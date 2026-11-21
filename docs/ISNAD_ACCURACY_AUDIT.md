# Sahih al-Bukhari isnad accuracy audit

## Scope and evidence

This audit covers the read-only cloud legacy reproduction and a separate indexed rebuild. Neither is the user's original Windows file. The user-reported Windows edge IDs are identified separately below. The reference code is `c6b5efdfdd58ecdb796b315a52e8016811231f71`.

Evidence came from the checked-in Bukhari CSV (`data/Sahih al-Bukhari.csv`), stored Arabic isnad and full text, narrator catalog and supplement, the [prior identity audit](NARRATOR_MATCHING_AUDIT.md), and selected book-1 records in the published [Hadith Knowledge Graph](https://github.com/qataruts/hadith) SQLite release. Current requests to Sunnah.com returned HTTP 403 from this environment. Source links identify the underlying reference. KG IDs were corroborated with normalized Arabic and named neighbors, never by a shared number. KG routes are comparison evidence and are never adopted by the application.

## Dataset-wide structural scan

| Check | Legacy reproduction | Indexed rebuild |
|---|---:|---:|
| Hadiths / narrators / edges | 7,252 / 28,284 / 41,123 | 7,277 / 32,476 / 39,336 |
| Hadiths without stored edges | 8 | 39 |
| Edges incident to unresolved IDs (≥800000) | 8,090 | 10,738 |
| Hadiths with recorded Prophet as teacher | 3,746 | 2,098 |
| Edges with Prophet as student, flagged as inconsistent | 374 | 0 |
| Duplicate sequence groups within hadith | 94 | 0 |
| Repeated endpoint-pair groups within hadith | 100 | 73 |
| Identical nonblank Arabic names shared by canonical catalog IDs | 540 | 540 |
| Groups with sequence/endpoint discontinuities | 74 | 0 |
| Groups with repeated nodes | 279 | 0 |
| Hadiths with multiple indexed routes | Indeterminate | 58 |
| Foreign-key violations / SQLite quick check | 0 / OK | 0 / OK |
| Non-Bukhari title rows / self-loops | 0 / 0 | 0 / 0 |

The scan groups by hadith and stored index where available, orders by sequence and edge ID, and counts violations where neighbors fail to connect or the sequence ceases to increase. A legacy group is a set of stored edges for a hadith, not a proposed route. Repeated endpoint pairs can represent legitimate overlap between two routes. Equal Arabic names can be homonyms, title variants or duplicated identities. These metrics flag records for review. They do not establish historical accuracy, and the two Prophet counts alone cannot distinguish improved extraction from missing valid links.

## Selected source review

Paths are written compiler → source to match the printed Arabic and storage order. The browser arrows run in the opposite direction, teacher → student.

| Bukhari | Legacy cloud edge IDs | Source evidence and displayed path | Confidence and limits |
|---|---|---|---|
| [1](https://sunnah.com/bukhari:1) | 1–7 | 30001 → 30418 → 20005 → 11062 → 11213 → 11042 → 3 → 1. Printed isnad explicitly says Umar heard the Prophet (سَمِعْتُ رَسُولَ اللَّهِ). KG 1 confirms the named transmitters through Umar. | Reviewed opening route. |
| [5](https://sunnah.com/bukhari:5) | 23–27 | 30001 → 20040 → 20469 → 11399 → 11050 → 17. عَنِ ابْنِ عَبَّاسٍ after Saʿid ibn Jubayr is Ibn ʿAbbas, not ʿAwn ibn ʿAbbas (23557). The adjacent catalog relationship and indexed rebuild corroborate ID 17. | Identity correction on existing edge 27. The revelation report does not supply an extra explicit transmission edge. |
| [15](https://sunnah.com/bukhari:15) | 91–95; 96–99 | First route 30001 → 30400 → 20208 → 11295 → 19 → 1. The source switch ح وَحَدَّثَنَا آدَمُ starts 30001 → 20404 → 20020 → 11019 → 19. KG 14 (29/30) corroborates both named routes through Anas. | First route reviewed. Second legacy segment is incomplete. The Prophet is quoted in the second source route, but the legacy database lacks that terminal edge. Indexed edges 85–89 and 90–94 preserve both full reviewed routes, including the second terminal edge. |
| [832](https://sunnah.com/bukhari:832) | 4451–4456. User-reported Windows 45574–45579. | 30001 → 30330 → 20428 → 11013 → 10511 → 53 → 1. The isnad names Abu al-Yaman, Shuʿayb, al-Zuhri, ʿUrwa and ʿAisha, who relates the Prophet’s supplication. KG 792 (969) corroborates the opening chain through ʿAisha by full text. | Reviewed opening route only. A subsidiary citation begins وَعَنِ الزُّهْرِيِّ later in the full text. It remains in the reader. The legacy snapshot has no independently recorded edges for that citation. The indexed rebuild's two generated tail IDs (800798/800799) remain unresolved and are not covered by the legacy annotation. |
| [1000](https://sunnah.com/bukhari:1000) | 5339–5342 | 30001 → 20040 → 20216 → 11014 → 18. The Arabic opening names Musa ibn Ismaʿil, Juwayriya ibn Asmaʾ, Nafiʿ and Ibn ʿUmar. Published Bukhari KG 950, sanad 1158, corroborates the normalized full text and ordered transmitters. | Reviewed on the matching legacy source and exact stored edge signature. The indexed rebuild substitutes unresolved ID 800976 at the end, so its route stays recorded and unreviewed. The report describes the Prophet’s prayers and supplies no further explicit transmission edge. |
| [1067](https://sunnah.com/bukhari:1067) | 5686–5691 | 30001 → 30160 → 20278 → 20020 → 11049 → 11054 → 16. After Shuʿba, the text gives Abu Ishaq, al-Aswad and ʿAbd Allāh. KG 1010 (1238) agrees on full text and the Kufan identities. Catalog 11049 lists 11054 among teachers, and 11054 lists 16. | Three existing edges receive corrected endpoints. Ibn Masʿud reports the Prophet’s action. No terminal Prophet edge is added. |
| [1381](https://sunnah.com/bukhari:1381) | 7321–7325. User-reported Windows 48444–48448. | 30001 → 30400 → 20208 → 11295 → 19 → 1. KG 1298 (1602) and the catalog support al-Dawraqi and Ibn ʿUlayya. The text explicitly quotes the Prophet (قَالَ قَالَ رَسُولُ اللَّهِ). | Reviewed with prior endpoint corrections; the original Prophet edge remains. |
| [5225](https://sunnah.com/bukhari:5225) | 28156–28159. User-reported Windows 69279–69282. | 30001 → 30026 → 20208 → 11279 → 19. The route is ʿAli → Ibn ʿUlayya → Humayd → Anas (عَنْ حُمَيْدٍ، عَنْ أَنَسٍ). Ibn ʿUlayya and Humayd were checked in the earlier audit with KG 4850. Anas begins the narrative with قَالَ كَانَ النَّبِيُّ. | Reviewed as recorded through Anas. The incident and the quoted غَارَتْ أُمُّكُمْ in the matn do not justify adding a separate edge. |
| [32](https://sunnah.com/bukhari:32) | 187–195 | The source switches from Abu al-Walid → Shuʿba to Bishr → Muhammad → Shuʿba, with a shared continuation through Sulayman, Ibrahim, ʿAlqama and ʿAbd Allāh. The legacy graph loses the restart and encodes the Prophet as a student on edge 191. | Withheld on matching legacy signature. Indexed 182–196 has two separately stored routes but unresolved tail IDs 800029/800030; route structure and terminal identities have different confidence. |
| [74](https://sunnah.com/bukhari:74) | 428–435 | Muhammad ibn Ghurayr opens the chain, but 428 directly identifies al-Zuhri. KG 73 (100) corroborates the intervening narrators through Ibn ʿAbbas. The text later recounts dialogue with Ubayy. | Withheld on matching legacy signature; no repair of the nested attribution attempted. |
| [188](https://sunnah.com/bukhari:188) | 1078 | وَقَالَ أَبُو مُوسَى is a suspended attribution. The import recorded 30001 → placeholder 800109. | The direct compiler edge is unsupported. Withheld on matching legacy signature. |
| [1185](https://sunnah.com/bukhari:1185) | 6319–6326 | The report passes from the chain into Mahmoud’s recollection and a nested account by ʿItban. The legacy includes a 1-as-student edge 6325 and conflicting repeated Prophet links. | Withheld on matching legacy signature pending a route-by-route source review. |

All 13 ancestral corrections remain in the [prior audit](NARRATOR_MATCHING_AUDIT.md), with the individual Arabic evidence, original and corrected IDs, and edge-level notes. Hadiths 15, 1381 and 5225 are described above. The other ten retain source-attributed identity-reviewed prefixes. Remaining edges, including uncertain Prophet attribution on 1639, 2768 and 3063, are excluded from those reviewed prefixes. No missing links are filled from catalog relationships.

## How the application preserves evidence

- Models store an edge as `student_id` and `teacher_id`. Sequence is import order, and a null or absent `chain_index` does not record route membership. Schema detection and the legacy serializer keep both schema variants readable without selecting a missing column.
- The importer extracts names and uses catalog aliases, chronology and teacher adjacency to rank candidates. Errors include treating honorifics as name tokens, choosing a homonym and parsing a narrative clause as a transmitter. Existing anomalies were not globally remapped. `data/isnad_route_evidence.json` binds new display decisions to source URL, normalized stored Arabic and ordered edge signature. Updates preserve edge IDs and sequence, surface original endpoints, and leave the raw edge API and source text intact.
- Graph grouping uses the reviewed edge lists or an explicit stored index with a coherent ordered path. Unreviewed unindexed edges appear by default with their original IDs and an unresolved notice. Consecutive rows with matching endpoints can be shown as a recorded segment. The viewer splits at sequence gaps, endpoint changes, and reviewed or indexed boundaries. It retains repeated and cyclic relationships without inferring a verified route. Inconsistent indexed groups also use recorded segments within their own index. Four known legacy errors are withheld from visualization with a reason. The reader remains available. Other unreviewed imports may still contain incorrect identities or attribution; “recorded” is a storage status, not a scholarly judgment.
- Public hadith endpoints and catalog reads remain Bukhari-scoped. The KG hadith endpoint confirms book metadata, and crosswalk text proposals cannot open an external isnad. The browser uses no non-Bukhari demo or reader.
- Graph labels use Arabic RTL and isolated mixed-language text. Full names remain available through SVG titles, accessible names and the selected profile. Keyboard activation uses Enter or Space, and the generation bands, zoom and pan are retained. Missing edge terminology is left blank.
- Profiles distinguish catalog relationships, general KG observations and imported Bukhari edges. The separate source-reviewed hadith list only links to a verified openable route. It is intentionally small. The Shuʿba catalog and KG profiles retain their original differences and 22 attributed KG evaluations.

## UTF-8 and verification limits

The cloud HTTP responses were checked as UTF-8 bytes and decoded as JSON, and Chromium rendered the original Arabic with RTL direction. Django's normal JSON renderer serves `application/json` with UTF-8 bytes. The KG renderer additionally declares `charset=utf-8`. The reported `Ø¨Ø§Ø¨` is consistent with interpreting UTF-8 bytes as a single-byte encoding. The original Windows PowerShell session was unavailable, so its exact decoding configuration remains unverified. No Arabic strings were rewritten. Windows PowerShell can explicitly decode the bytes with `[Text.Encoding]::UTF8.GetString((New-Object Net.WebClient).DownloadData($url)) | ConvertFrom-Json`.

The whole-catalog scan is structural. The source-level review is limited to the records and evidence listed here. Response and browser checks use isolated Django and local Knowledge Graph HTTP fixtures sourced from the published SQLite release. They do not verify the user's Windows services or original SQLite file. Existing database snapshots were opened read-only and hash-checked.

## Verification results and captures

- Django: 78 tests passed in an isolated in-memory test database. Django system checks passed.
- Frontend: 20 Node tests passed. TypeScript and the Vite production build passed.
- The read-only Django test client checked 21 distinct legacy hadiths, including all 13 prior corrections. It compared raw IDs and endpoints against SQLite, checked the original Arabic and English fields after UTF-8 decoding, and tested the reviewed profile links.
- Chromium exercised the legacy reader and graph for 1, 832, 1381 and 5225, both legacy segments for 15, both reviewed routes on the indexed snapshot, withholding 32, keyboard selection, narrator-to-hadith navigation, Shuʿba’s evaluations, and a 390-pixel mobile viewport. The KG HTTP fixture confirmed that ID 17154 returns 404.
- Captures from those runs: [832](isnad-audit-screenshots/832.png), [1381](isnad-audit-screenshots/1381.png), [5225](isnad-audit-screenshots/5225.png), [indexed 15](isnad-audit-screenshots/15-indexed.png), [Shuʿba](isnad-audit-screenshots/shuba.png), and [mobile profile](isnad-audit-screenshots/mobile.png).
