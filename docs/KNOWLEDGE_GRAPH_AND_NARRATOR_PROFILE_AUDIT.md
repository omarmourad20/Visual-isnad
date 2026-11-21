# Knowledge Graph and narrator profile audit

## Bukhari 832 and KG 17154

The shared printed number 832 refers to two different reports. Read-only
checks against the cloud legacy reproduction and published relational KG
snapshot established the following.

| Field | Visual Isnad | Hadith Knowledge Graph |
|---|---|---|
| Identity | Local ID 832, Sahih al-Bukhari 832 | KG ID 17154, book ID 4, Sunan Abi Dawud 832 |
| Book and chapter | Book 10, Hadith 226, chapter 10, How the Adhan for Prayer was started | Sunan Abi Dawud, first Dar al-Fikr edition in the snapshot. No chapter title in the relational record. |
| Isnad | Abū al-Yamān, Shuʿayb, al-Zuhrī, ʿUrwa, ʿĀʾisha | Opening route via Ḥafṣ ibn ʿUmar, Shuʿba, al-Ḥakam, Ibn Abī Laylā, and Kaʿb ibn ʿUjra |
| Matn | Supplication seeking refuge from punishment of the grave and other trials | Formula for invoking blessings upon Muhammad and his family |
| English | 869 characters in the legacy record | No English supplied in the inspected record |

Normalized full text, matn, and isnad all differed. KG sanad 28706 belongs
to KG 17154. Its seven ordered KG IDs are 3567 → 7426 → 8418 → 3795 → 1372
→ 4287 → 6597, from compiler towards source. The names are Abū Dāwūd,
Musaddad, Yazīd ibn Zurayʿ, Shuʿba, al-Ḥakam, ʿAbd al-Raḥmān ibn Abī Laylā
(catalog name ʿAbd al-Raḥmān ibn Yasār), and Kaʿb ibn ʿUjra. There are six
adjacent links. The report contains Prophet-attributed speech and the
stored sanad ends at Kaʿb.

The other KG routes are 28705 (5 nodes), 28707 (7), and 28708 (6).
They remain provider assertions. Route 28705 includes a suspended
marker and names a different Ibn Abī Laylā catalog ID, 7057. That
attribution needs source review. No remap or new edge was made.

Sources: [Sahih al-Bukhari 832](https://sunnah.com/bukhari:832),
[Sunan Abi Dawud 832](https://sunnah.com/abudawud:832),
[KG relational snapshot](https://huggingface.co/datasets/emadjumaah/hadith-kg).

## Confirmed defects and fixes

- The standalone demo always requested 17154; it did not look up a
  corresponding local hadith. Its full reader nevertheless displayed a
  hard-coded Bukhari header and could reuse the previous local book.
  The example now validates source identifiers, labels the reader and
  graph as a separate Abu Dawud record, and offers a return to the local
  hadith. An empty set of external paths still allows text reading.
- Local source-route previews use a configured collection-aware crosswalk,
  live reference corroboration when supplied, and normalized Arabic
  evidence. Ambiguous candidates remain visible and cannot open a route
  under the local record. The proxy rejects conflicting native IDs.
  Text corroboration leaves all external sanads unreviewed.
- A new selection invalidates pending source-preview responses. Switching
  records or graphs closes stale narrator details as appropriate. The
  browser check delayed the external response until after another local
  selection, and it did not replace that selection.
- A long Arabic card is a matn preview. The reader exposes the full
  original Arabic string, including transmitted variants, where supplied.
  The KG English empty state identifies the external source. Load errors
  are separate. No translation was copied between sources or generated.

## Shuʿba provenance

Local legacy/canonical ID **20020** is Shuʿbah bin al-Hajjaj,
شعبة بن الحجاج. KG rawi **3795** (browser ID **1003795**) is
شعبة بن الحجاج بن الورد, nickname شعبة بن الحجاج العتكي.
Full name and route context corroborate the identity, while each record
stays in its own source namespace.

| Field | Local catalog and legacy SQLite | Published KG |
|---|---|---|
| Birth | 82 AH | 83 AH |
| Death | 160 AH, Basra | 160 AH, البصرة |
| Generation | 7th | 7 |
| Reliability | Generation classification and structured Thiqah note | ثقة حافظ متقن عابد and 22 credited evaluations |
| Names and places | English and Arabic catalog names, catalog places | Canonical Arabic name, nickname, nasab and residence from KG |

The birth-year disagreement is preserved with source attribution. The
local biography field has a structured specialty and grade note. The
bundled biography cache and supplement lack prose for 20020. Fetching
the linked catalog page did not yield qualifying prose via either of the
project's biography extractors. The inspected KG dossier supplies facts
and scholarly criticism and has no prose biography field. Existing
source text remains visible. No prose or translation was fabricated or
added from a source with unverified reuse terms.
[MuslimScholars catalog entry](https://muslimscholars.info/manage.php?ID=20020&submit=scholar)

The legacy row lists 79 distinct teacher references and 42 student
references. Legacy transmission edges identify 31 distinct canonical
Bukhari students. KG relationships are adjacent route observations
across its corpus; its detail API returns up to 15 per side. The UI
now distinguishes KG route links from local catalog links and imported
Bukhari relationships, exposes source attribution, and avoids using a KG
nickname as the full name. It retains the Arabic wording and existing
RTL/LTR presentation. Neither identity nor relationships were merged.

## Verification and scope

Changed the KG proxy, source proposal policy, narrator detail source
metadata, React reader and profile presentation, plus regression tests.
Django tests used an in-memory test database. The HTTP and Chromium checks
used the immutable cloud legacy reproduction and a KG HTTP fixture backed
by the published SQLite snapshot. The live Windows KG service was not
reachable here. The thirteen reviewed Bukhari corrections and original
edge endpoint remain intact.
