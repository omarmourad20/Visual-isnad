# Hadith Knowledge Graph audit

## Reproduced against the published release

The relational SQLite release downloaded from Hugging Face is 1,634,877,440 bytes. SHA-256 `d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6` matched the published LFS digest. The audit opened it with SQLite URI `mode=ro` and `query_only`. Source code declares MIT. The dataset card declares CC BY 4.0 and documents provenance. Confirm the attribution and upstream rights for the source edition, especially for derivative dossiers. The application DB is a separate release. [Repository](https://github.com/qataruts/hadith) · [Dataset](https://huggingface.co/datasets/emadjumaah/hadith-kg)

| Metric | Published relational DB, counted |
|---|---:|
| Collections | 425 |
| Hadith rows | 715,790 |
| Narrator records | 49,844 |
| Sanads | 577,024 |
| Ordered sanad positions | 4,414,211 |
| Criticism statements | 127,863 |
| Meaning groups | 20,745 |
| Sanad positions with absent narrator | 0 |
| Non-null inline narrator mentions with absent narrator | 1,976 |

The user previously observed **49,819** narrators on the Windows app endpoint. Treat the 25-row difference as a release or representation discrepancy pending a comparison of exact service revisions and query logic. The Bukhari edition in the relational database is book **1**, edition label **الثالثة**. It has **7,031** rows, **6,534** rows with sanads, **497** without, **1,320** with multiple sanads, and **8,795** total sanads. No duplicate in-edition reference groups and no empty Bukhari sanad records were observed. These are structural measurements. Inline mentions and chain nodes use different tables.

## Chain direction, flags and sample results

The relational schema stores author first and walks toward the source. Preserve that order, position and sanad boundaries. Inferred teacher/student ties from adjacent positions are transmission observations. The dossier can also carry ranks, years, occupation, residence, genealogy, and named criticism statements. A dossier row does not guarantee a full prose biography. Keep grading and critic claims attributed. [Build schema](https://github.com/qataruts/hadith/blob/main/build_hkg.py) · [Data report](https://github.com/qataruts/hadith/blob/main/DATA_REPORT.md)

The matched anchors below are edition-crosswalk candidates based on Arabic text and the attribution context. A `مرْفوع` classification still permits a companion-terminal stored route. No narrator row matched the exact titles `رسول الله`, `النبي`, or `محمد رسول الله` in the name or nickname columns. This exact check cannot rule out every alias. A separate common-name match would be unsafe. The stored routes for KG Bukhari 1, 14, 93 and 726 end at ʿUmar, Anas, Anas and Jubayr respectively, even where Visual Isnad retains an explicit Prophet edge. Another 123 Bukhari routes terminate with a marker labelled `موضع إرسال`. Treat markers as gaps, not people.

| Visual reference | KG edition number / internal ID | Observed sanad structure and review |
|---|---|---|
| 1 | 1 / 1 | One route, 7 nodes, ends at ʿUmar. Both texts contain the intentions report. |
| 5 | 4 / 4 | One route, 6 nodes, ends at Ibn ʿAbbās. Same-number KG 5 is a poor text match. |
| 15 | 14 / 14 | Two routes ending at Anas. KG route 29 preserves Yaʿqūb → Ibn ʿUlayya → ʿAbd al-ʿAzīz in the ordered chain; route 30 takes Ādam → Shuʿbah → Qatādah. |
| 32 | 31 / 31 | Leading text candidate has no sanad, while Visual has two. Needs editorial comparison. |
| 74 | 73 / 73 | One stored route ending at Ibn ʿAbbās. Embedded hearing attribution needs separate review. |
| 94 | 93 / 93 | One route ending at Anas. Visual stores an explicit Prophet edge. |
| 188 | Unresolved | Visual stores no route. KG candidates have low text similarity; no safe crosswalk. |
| 765 | 726 / 726 | One route ending at Jubayr. Visual records explicit hearing. |
| 1067 | 1010 / 1010 | High full-text similarity. Both routes align by name through Muḥammad ibn Bashshār, Ghundar, Shuʿbah, Abū Isḥāq, al-Aswad and Ibn Masʿūd. Their raw IDs differ by namespace. |
| 7478 | 6948 / 6948 | One KG route reaches Ubayy after Ibn ʿAbbās; Visual ends earlier. Useful evidence for reconstructing dialogue attribution. |
| 4211 | 3914 / 3914 | Reproducible random sample. Both have two stored routes. |

Live Windows Docker was unreachable from the Linux research host. No live latency, availability or endpoint behavior was inferred from the SQL data. The earlier Windows Hadith 17154 proxy check is consistent with the published release: **KG internal ID 17154 is Sunan Abi Dawud 832** and has four sanads. Narrator 3567 is Abu Dawud al-Sijistani in the inspected release. This is a useful integration smoke case and belongs outside the Bukhari benchmark. [API routes](https://github.com/qataruts/hadith#api)
