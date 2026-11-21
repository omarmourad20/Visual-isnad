# Bukhari legacy narrator matching audit

The legacy matcher at ad3d3af extracted ابن علية but discarded the structural token ابن.
Its remaining token عليه matched the truncated blessing in the raw alias of ID 5888
(نوبة خادم النبي صلى الله عليه). The original catalog did not contain a record row
for Ibn ʿUlayya. The supplement documents his full name, aliases and catalog
relationships under ID 20208. The two identity records remain separate.

The audit used the read-only cloud legacy reproduction and fetched each linked
Sunnah.com page. Every page confirmed the relevant isnad phrase and its adjacent
names. For additional disambiguation, the published KG Arabic report and ordered
sanads were checked under the crosswalk IDs listed below. These are KG internal
IDs. A KG route is evidence for identification and was never copied as a new
local path. Edge IDs below are those in the cloud legacy reproduction. The live
Windows file was unavailable.

| Hadith | Original narrator ID | Correct narrator ID | Edges incident to 5888 | Evidence | Status |
|---|---:|---:|---|---|---|
| 1191 | 5888 | 20208 | 6351, 6352 | [Arabic source](https://sunnah.com/bukhari:1191), KG 1123 | Confirmed, display corrected |
| 1381 | 5888 | 20208 | 7322, 7323 | [Arabic source](https://sunnah.com/bukhari:1381), KG 1298 | Confirmed, display corrected |
| 1573 | 5888 | 20208 | 8412, 8413 | [Arabic source](https://sunnah.com/bukhari:1573), KG 1476 | Confirmed, display corrected |
| 1639 | 5888 | 20208 | 8786, 8787 | [Arabic source](https://sunnah.com/bukhari:1639), KG 1537 | Confirmed, display corrected |
| 2768 | 5888 | 20208 | 14918, 14919 | [Arabic source](https://sunnah.com/bukhari:2768), KG 2574 | Confirmed, display corrected |
| 3063 | 5888 | 20208 | 16445, 16446 | [Arabic source](https://sunnah.com/bukhari:3063), KG 2851 | Confirmed, display corrected |
| 3195 | 5888 | 20208 | 17109, 17110 | [Arabic source](https://sunnah.com/bukhari:3195), KG 2974 | Confirmed, display corrected |
| 4020 | 5888 | 20208 | 21618, 21619 | [Arabic source](https://sunnah.com/bukhari:4020), KG 3741 | Confirmed, display corrected |
| 4617 | 5888 | 20208 | 24687 | [Arabic source](https://sunnah.com/bukhari:4617), KG 4276 | Confirmed, display corrected |
| 5225 | 5888 | 20208 | 28157, 28158 | [Arabic source](https://sunnah.com/bukhari:5225), KG 4850 | Confirmed, display corrected |
| 5549 | 5888 | 20208 | 29923, 29924 | [Arabic source](https://sunnah.com/bukhari:5549), KG 5149 | Confirmed, display corrected |
| 6132 | 5888 | 20208 | 33130, 33131 | [Arabic source](https://sunnah.com/bukhari:6132), KG 5694 | Confirmed, display corrected |

Display corrections match the source URL, normalized full stored isnad,
complete ordered legacy edge signature and absence of recorded chain indices.
They keep original IDs, sequences and raw endpoints available. Indexed and
unmatched records are served unchanged. Further legacy anomalies in tail
attribution and route coverage remain outside this scoped audit.

### 1191

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ ـ هُوَ الدَّوْرَقِيُّ ـ حَدَّثَنَا ابْنُ عُلَيَّةَ، أَخْبَرَنَا أَيُّوبُ، عَنْ نَافِعٍ، أَنَّ ابْنَ عُمَرَ ـ رضى الله عنهما ـ كَانَ لاَ يُصَلِّي مِنَ الضُّحَى إِلاَّ فِي يَوْمَيْنِ يَوْمَ يَقْدَمُ بِمَكَّةَ، فَإِنَّهُ كَانَ يَقْدَمُهَا ضُحًى، فَيَطُوفُ بِالْبَيْتِ، ثُمَّ يُصَلِّي رَكْعَتَيْنِ خَلْفَ الْمَقَامِ، وَيَوْمَ يَأْتِي مَسْجِدَ قُبَاءٍ، فَإِنَّهُ كَانَ يَأْتِيهِ كُلَّ سَبْتٍ، فَإِذَا دَخَلَ الْمَسْجِدَ كَرِهَ أَنْ يَخْرُجَ مِنْهُ حَتَّى يُصَلِّيَ فِيهِ. قَالَ وَكَانَ يُحَدِّثُ أَنَّ رَسُولَ اللَّهِ صلى الله عليه وسلم كَانَ يَزُورُهُ رَاكِبًا وَمَاشِيًا. قَالَ وَكَانَ يَقُولُ إِنَّمَا أَصْنَعُ كَمَا رَأَيْتُ أَصْحَابِي يَصْنَعُونَ، وَلاَ أَمْنَعُ أَحَدًا أَنْ يُصَلِّيَ فِي أَىِّ سَاعَةٍ شَاءَ مِنْ لَيْلٍ أَوْ نَهَارٍ، غَيْرَ أَنْ لاَ تَتَحَرَّوْا طُلُوعَ الشَّمْسِ وَلاَ غُرُوبَهَا.

The text names al-Dawraqī directly. Ayyūb and Nāfiʿ agree with KG; the legacy route lacks the Ibn ʿUmar endpoint. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 1123 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `6350:0 30001→20184`, `6351:1 20184→5888`, `6352:2 5888→13642`, `6353:3 13642→14725`.

Display changes (`edge ID: original → corrected`): `6350: 30001→20184 becomes 30001→30400`, `6351: 20184→5888 becomes 30400→20208`, `6352: 5888→13642 becomes 20208→11015`, `6353: 13642→14725 becomes 11015→11014`.

### 1381

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، حَدَّثَنَا عَبْدُ الْعَزِيزِ بْنُ صُهَيْبٍ، عَنْ أَنَسِ بْنِ مَالِكٍ ـ رضى الله عنه ـ قَالَ قَالَ رَسُولُ اللَّهِ صلى الله عليه وسلم

KG and the documented catalog links identify al-Dawraqī and corroborate ʿAbd al-ʿAzīz ibn Ṣuhayb. The legacy Prophet link is retained. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 1298 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `7321:0 30001→20184`, `7322:1 20184→5888`, `7323:2 5888→11295`, `7324:3 11295→19`, `7325:4 19→1`.

Display changes (`edge ID: original → corrected`): `7321: 30001→20184 becomes 30001→30400`, `7322: 20184→5888 becomes 30400→20208`, `7323: 5888→11295 becomes 20208→11295`.

### 1573

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنِي يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، أَخْبَرَنَا أَيُّوبُ، عَنْ نَافِعٍ، قَالَ كَانَ ابْنُ عُمَرَ ـ رضى الله عنهما ـ إِذَا دَخَلَ أَدْنَى الْحَرَمِ أَمْسَكَ عَنِ التَّلْبِيَةِ، ثُمَّ يَبِيتُ بِذِي طُوًى، ثُمَّ يُصَلِّي بِهِ الصُّبْحَ وَيَغْتَسِلُ، وَيُحَدِّثُ أَنَّ نَبِيَّ اللَّهِ صلى الله عليه وسلم كَانَ يَفْعَلُ ذَلِكَ.

KG identifies al-Dawraqī and Ayyūb al-Sakhtiyānī. The legacy tail uses a generated placeholder; no missing Nāfiʿ or Ibn ʿUmar edge was added. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 1476 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `8411:0 30001→20184`, `8412:1 20184→5888`, `8413:2 5888→13642`, `8414:3 13642→800888`.

Display changes (`edge ID: original → corrected`): `8411: 30001→20184 becomes 30001→30400`, `8412: 20184→5888 becomes 30400→20208`, `8413: 5888→13642 becomes 20208→11015`, `8414: 13642→800888 becomes 11015→800888`.

### 1639

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، عَنْ أَيُّوبَ، عَنْ نَافِعٍ، أَنَّ ابْنَ عُمَرَ ـ رضى الله عنهما ـ دَخَلَ ابْنُهُ عَبْدُ اللَّهِ بْنُ عَبْدِ اللَّهِ، وَظَهْرُهُ فِي الدَّارِ، فَقَالَ إِنِّي لاَ آمَنُ أَنْ يَكُونَ الْعَامَ بَيْنَ النَّاسِ قِتَالٌ، فَيَصُدُّوكَ عَنِ الْبَيْتِ، فَلَوْ أَقَمْتَ. فَقَالَ قَدْ خَرَجَ رَسُولُ اللَّهِ صلى الله عليه وسلم فَحَالَ كُفَّارُ قُرَيْشٍ بَيْنَهُ وَبَيْنَ الْبَيْتِ، فَإِنْ حِيلَ بَيْنِي وَبَيْنَهُ أَفْعَلُ كَمَا فَعَلَ رَسُولُ اللَّهِ صلى الله عليه وسلم {لَقَدْ كَانَ لَكُمْ فِي رَسُولِ اللَّهِ أُسْوَةٌ حَسَنَةٌ} ثُمَّ قَالَ أُشْهِدُكُمْ أَنِّي قَدْ أَوْجَبْتُ مَعَ عُمْرَتِي حَجًّا. قَالَ ثُمَّ قَدِمَ فَطَافَ لَهُمَا طَوَافًا وَاحِدًا.

The text and KG identify Ayyūb and Nāfiʿ. A legacy placeholder and Prophet link in the tail remain outside this correction and require attribution review. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 1537 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `8785:0 30001→20184`, `8786:1 20184→5888`, `8787:2 5888→13642`, `8788:3 13642→14725`, `8789:4 14725→800921`, `8790:5 800921→1`.

Display changes (`edge ID: original → corrected`): `8785: 30001→20184 becomes 30001→30400`, `8786: 20184→5888 becomes 30400→20208`, `8787: 5888→13642 becomes 20208→11015`, `8788: 13642→14725 becomes 11015→11014`, `8789: 14725→800921 becomes 11014→800921`.

### 2768

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ بْنِ كَثِيرٍ، حَدَّثَنَا ابْنُ عُلَيَّةَ، حَدَّثَنَا عَبْدُ الْعَزِيزِ، عَنْ أَنَسٍ ـ رضى الله عنه ـ قَالَ قَدِمَ رَسُولُ اللَّهِ صلى الله عليه وسلم الْمَدِينَةَ لَيْسَ لَهُ خَادِمٌ، فَأَخَذَ أَبُو طَلْحَةَ بِيَدِي، فَانْطَلَقَ بِي إِلَى رَسُولِ اللَّهِ صلى الله عليه وسلم فَقَالَ يَا رَسُولَ اللَّهِ إِنَّ أَنَسًا غُلاَمٌ كَيِّسٌ، فَلْيَخْدُمْكَ. قَالَ فَخَدَمْتُهُ فِي السَّفَرِ وَالْحَضَرِ، مَا قَالَ لِي لِشَىْءٍ صَنَعْتُهُ لِمَ صَنَعْتَ هَذَا هَكَذَا وَلاَ لِشَىْءٍ لَمْ أَصْنَعْهُ لِمَ لَمْ تَصْنَعْ هَذَا هَكَذَا

The text gives Yaʿqūb ibn Ibrāhīm ibn Kathīr. KG identifies the abbreviated ʿAbd al-ʿAzīz as Ibn Ṣuhayb. The legacy Anas placeholder and its Prophet link were left for separate review. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 2574 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `14917:0 30001→20184`, `14918:1 20184→5888`, `14919:2 5888→4612`, `14920:3 4612→801573`, `14921:4 801573→1`.

Display changes (`edge ID: original → corrected`): `14917: 30001→20184 becomes 30001→30400`, `14918: 20184→5888 becomes 30400→20208`, `14919: 5888→4612 becomes 20208→11295`, `14920: 4612→801573 becomes 11295→801573`.

### 3063

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، عَنْ أَيُّوبَ، عَنْ حُمَيْدِ بْنِ هِلاَلٍ، عَنْ أَنَسِ بْنِ مَالِكٍ ـ رضى الله عنه ـ قَالَ خَطَبَ رَسُولُ اللَّهِ صلى الله عليه وسلم فَقَالَ

KG identifies al-Dawraqī and al-Sakhtiyānī, followed by Ḥumayd ibn Hilāl and Anas. The pre-existing legacy Prophet edge is outside this correction. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 2851 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `16444:0 30001→20184`, `16445:1 20184→5888`, `16446:2 5888→13642`, `16447:3 13642→11281`, `16448:4 11281→19`, `16449:5 19→1`.

Display changes (`edge ID: original → corrected`): `16444: 30001→20184 becomes 30001→30400`, `16445: 20184→5888 becomes 30400→20208`, `16446: 5888→13642 becomes 20208→11015`, `16447: 13642→11281 becomes 11015→11281`.

### 3195

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا عَلِيُّ بْنُ عَبْدِ اللَّهِ، أَخْبَرَنَا ابْنُ عُلَيَّةَ، عَنْ عَلِيِّ بْنِ الْمُبَارَكِ، حَدَّثَنَا يَحْيَى بْنُ أَبِي كَثِيرٍ، عَنْ مُحَمَّدِ بْنِ إِبْرَاهِيمَ بْنِ الْحَارِثِ، عَنْ أَبِي سَلَمَةَ بْنِ عَبْدِ الرَّحْمَنِ، كَانَتْ بَيْنَهُ وَبَيْنَ أُنَاسٍ خُصُومَةٌ فِي أَرْضٍ، فَدَخَلَ عَلَى عَائِشَةَ فَذَكَرَ لَهَا ذَلِكَ، فَقَالَتْ يَا أَبَا سَلَمَةَ اجْتَنِبِ الأَرْضَ، فَإِنَّ رَسُولَ اللَّهِ صلى الله عليه وسلم قَالَ

The source says ʿAlī ibn ʿAbd Allāh, identified by KG and the catalog as Ibn al-Madīnī. ʿAlī ibn al-Mubārak already matches locally. Later identities and quoted speech remain outside this correction. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 2974 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `17108:0 30001→20280`, `17109:1 20280→5888`, `17110:2 5888→20449`, `17111:3 20449→11449`, `17112:4 11449→11213`, `17113:5 11213→1`.

Display changes (`edge ID: original → corrected`): `17108: 30001→20280 becomes 30001→10950`, `17109: 20280→5888 becomes 10950→20208`, `17110: 5888→20449 becomes 20208→20449`.

### 4020

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنِي يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، حَدَّثَنَا سُلَيْمَانُ التَّيْمِيُّ، حَدَّثَنَا أَنَسٌ ـ رضى الله عنه ـ قَالَ قَالَ رَسُولُ اللَّهِ صلى الله عليه وسلم يَوْمَ بَدْرٍ

The source explicitly names Sulaymān al-Taymī and Anas. KG corroborates Ibn Ṭarkhān and Anas on the primary route and has an additional suspended route. The additional route was not imported. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 3741 has 2 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `21617:0 30001→20184`, `21618:1 20184→5888`, `21619:2 5888→20160`, `21620:3 20160→14383`, `21621:4 14383→1`.

Display changes (`edge ID: original → corrected`): `21617: 30001→20184 becomes 30001→30400`, `21618: 20184→5888 becomes 30400→20208`, `21619: 5888→20160 becomes 20208→11289`, `21620: 20160→14383 becomes 11289→19`, `21621: 14383→1 becomes 19→1`.

### 4617

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا يَعْقُوبُ بْنُ إِبْرَاهِيمَ، حَدَّثَنَا ابْنُ عُلَيَّةَ، حَدَّثَنَا عَبْدُ الْعَزِيزِ بْنُ صُهَيْبٍ، قَالَ قَالَ أَنَسُ بْنُ مَالِكٍ ـ رضى الله عنه ـ مَا كَانَ لَنَا خَمْرٌ غَيْرُ فَضِيخِكُمْ هَذَا الَّذِي تُسَمُّونَهُ الْفَضِيخَ. فَإِنِّي لَقَائِمٌ أَسْقِي أَبَا طَلْحَةَ وَفُلاَنًا وَفُلاَنًا إِذْ جَاءَ رَجُلٌ فَقَالَ وَهَلْ بَلَغَكُمُ الْخَبَرُ فَقَالُوا وَمَا ذَاكَ قَالَ حُرِّمَتِ الْخَمْرُ. قَالُوا أَهْرِقْ هَذِهِ الْقِلاَلَ يَا أَنَسُ. قَالَ فَمَا سَأَلُوا عَنْهَا وَلاَ رَاجَعُوهَا بَعْدَ خَبَرِ الرَّجُلِ.

Al-Dawraqī is supported by the catalog relationship to Ibn ʿUlayya and the parallel opening in 1381. The KG record has no stored sanads. The two existing edges are corrected; missing ʿAbd al-ʿAzīz and Anas links are not added. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 4276 has 0 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `24686:0 30001→20184`, `24687:1 20184→5888`.

Display changes (`edge ID: original → corrected`): `24686: 30001→20184 becomes 30001→30400`, `24687: 20184→5888 becomes 30400→20208`.

### 5225

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا عَلِيٌّ، حَدَّثَنَا ابْنُ عُلَيَّةَ، عَنْ حُمَيْدٍ، عَنْ أَنَسٍ، قَالَ كَانَ النَّبِيُّ صلى الله عليه وسلم عِنْدَ بَعْضِ نِسَائِهِ فَأَرْسَلَتْ إِحْدَى أُمَّهَاتِ الْمُؤْمِنِينَ بِصَحْفَةٍ فِيهَا طَعَامٌ، فَضَرَبَتِ الَّتِي النَّبِيُّ صلى الله عليه وسلم فِي بَيْتِهَا يَدَ الْخَادِمِ فَسَقَطَتِ الصَّحْفَةُ فَانْفَلَقَتْ، فَجَمَعَ النَّبِيُّ صلى الله عليه وسلم فِلَقَ الصَّحْفَةِ، ثُمَّ جَعَلَ يَجْمَعُ فِيهَا الطَّعَامَ الَّذِي كَانَ فِي الصَّحْفَةِ وَيَقُولُ

KG disambiguates Ḥumayd as al-Ṭawīl and confirms ʿAlī ibn al-Madīnī and Anas. The legacy Anas placeholder includes reporting words. No endpoint beyond Anas was added. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 4850 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `28156:0 30001→30026`, `28157:1 30026→5888`, `28158:2 5888→39936`, `28159:3 39936→800126`.

Display changes (`edge ID: original → corrected`): `28157: 30026→5888 becomes 30026→20208`, `28158: 5888→39936 becomes 20208→11279`, `28159: 39936→800126 becomes 11279→19`.

### 5549

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا صَدَقَةُ، أَخْبَرَنَا ابْنُ عُلَيَّةَ، عَنْ أَيُّوبَ، عَنِ ابْنِ سِيرِينَ، عَنْ أَنَسِ بْنِ مَالِكٍ، قَالَ قَالَ النَّبِيُّ صلى الله عليه وسلم يَوْمَ النَّحْرِ

KG and the Arabic source identify Ṣadaqah ibn al-Faḍl, Ayyūb al-Sakhtiyānī, Muḥammad ibn Sīrīn and Anas. The existing graph has no terminal Prophet edge and none was added. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 5149 has 1 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `29922:0 30001→30343`, `29923:1 30343→5888`, `29924:2 5888→13642`, `29925:3 13642→17630`, `29926:4 17630→14608`.

Display changes (`edge ID: original → corrected`): `29923: 30343→5888 becomes 30343→20208`, `29924: 5888→13642 becomes 20208→11015`, `29925: 13642→17630 becomes 11015→11035`, `29926: 17630→14608 becomes 11035→19`.

### 6132

Stored `arabic_isnad` (legacy field may include matn):

> حَدَّثَنَا عَبْدُ اللَّهِ بْنُ عَبْدِ الْوَهَّابِ، أَخْبَرَنَا ابْنُ عُلَيَّةَ، أَخْبَرَنَا أَيُّوبُ، عَنْ عَبْدِ اللَّهِ بْنِ أَبِي مُلَيْكَةَ، أَنَّ النَّبِيَّ صلى الله عليه وسلم أُهْدِيَتْ لَهُ أَقْبِيَةٌ مِنْ دِيبَاجٍ مُزَرَّرَةٌ بِالذَّهَبِ، فَقَسَمَهَا فِي نَاسٍ مِنْ أَصْحَابِهِ وَعَزَلَ مِنْهَا وَاحِدًا لِمَخْرَمَةَ، فَلَمَّا جَاءَ قَالَ

The explicit ʿAbd Allāh ibn ʿAbd al-Wahhāb route matches one of KG’s three paths. KG confirms Ayyūb al-Sakhtiyānī; local Ibn Abī Mulayka already matches. Two additional KG paths were not imported. The stored graph contains one contiguous segment with a single Ibn ʿUlayya occurrence. Published KG record 5694 has 3 stored sanads. The comparison used the Arabic text and named neighbors to align editions, rather than the printed number alone.

Raw edges in sequence order (`edge ID:sequence student→teacher`): `33129:0 30001→30143`, `33130:1 30143→5888`, `33131:2 5888→13642`, `33132:3 13642→11090`.

Display changes (`edge ID: original → corrected`): `33130: 30143→5888 becomes 30143→20208`, `33131: 5888→13642 becomes 20208→11015`, `33132: 13642→11090 becomes 11015→11090`.
