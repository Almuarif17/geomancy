# Corpus manifest

Auto-generated inventory. `hits` = occurrences of technique keywords; treat low-hit files as unmined, not empty.

| file | words | signal |
|---|---:|---|
| BSG_ms_occult_sciences.txt | 152,513 | figure:36, thief:1, enem:4, voyage:3, prison:1 |
| agrippa_Three_Books_of_Occult_Philosophy_(Cudworth)_Book_II.txt | 3 | - |
| agrippa_Three_Books_of_Occult_Philosophy_Book_II.txt | 3 | - |
| agrippa_bk2_ch48_geomantic_figures.txt | 1,056 | figure:11, enem:1, prison:1 |
| agrippa_book2_djvu.txt | 50,264 | figure:87, mother:5, daughter:3, nephew:1, witness:5, judge:16, enem:15, sick:26, marriage:3, voyage:2, prison:10 |
| binsbergen_arabic_geomancy.txt | 23,498 | figure:33, mother:17, daughter:8, nephew:5, witness:3, judge:5, sick:1, voyage:6, prison:2 |
| cal_appendices_translation.txt | 34,266 | figure:18, mother:1, daughter:3, judge:2, enem:59, sick:17, marriage:2, prison:3 |
| cal_days_table6.txt | 1,787 | figure:27, witness:3, judge:10 |
| cal_figtable4.txt | 3,465 | figure:52, mother:1, witness:4, judge:8, thief:1, enem:4, marriage:2, prison:4 |
| cal_housetable5.txt | 3,514 | figure:23, mother:1, witness:5, judge:4, thief:1, enem:3, marriage:1, prison:1 |
| cal_lunar_table3.txt | 1,794 | figure:27 |
| cal_names_table2.txt | 919 | figure:22, prison:1 |
| cal_steps10.txt | 2,281 | figure:24, witness:2, judge:3 |
| calatarama_Chapter_2_.txt | 18 | figure:1 |
| calatarama_Chapter_5_.txt | 15 | - |
| calatarama_casting_interpretation_118_145.txt | 9,463 | figure:126, mother:6, daughter:7, niece:6, nephew:1, witness:11, judge:15, thief:1, enem:4, marriage:3, prison:2 |
| calatarama_example_questions_175_225.txt | 19,649 | figure:222, mother:3, daughter:1, witness:4, judge:15, thief:8, enem:17, sick:16, marriage:3, prison:7 |
| calatarama_figures_houses_78_95.txt | 5,428 | figure:41 |
| calatarama_lunar_mansions_95_110.txt | 3,759 | figure:62, judge:1, prison:1 |
| calatarama_thesis_fulltext.txt | 138,247 | figure:898, mother:13, daughter:12, niece:7, nephew:1, witness:21, judge:101, thief:10, enem:90, sick:37, marriage:9, prison:15 |
| calatarama_time_number_145_170.txt | 10,071 | figure:202, mother:2, daughter:1, niece:1, witness:4, judge:29, thief:1, enem:9, sick:1, marriage:1 |
| cattan_geomancie_1591.txt | 94,422 | figure:666, mother:55, daughter:32, nephew:1, judge:9, enem:45, marriage:39, voyage:1 |
| cattan_geomancie_1608.txt | 84,134 | figure:804, mother:60, daughter:48, nephew:8, witness:35, judge:44, enem:65, sick:80, marriage:28, voyage:50, prison:2 |
| fr_geomancie_nomancie.txt | 22,730 | figure:64, enem:5, voyage:31 |
| heydon_theomagia_1663.txt | 255,397 | figure:1140, mother:67, daughter:28, nephew:3, judge:303, thief:51, enem:159, sick:14, marriage:53, voyage:66 |
| opus_geomantiae_1638.txt | 137,842 | figure:26, enem:4 |
| cattan1591_book3 (OCR) | 6,677 | pages:18, mean_keyword_hits:1.56 |
| cattan1591_sample (OCR) | 867 | pages:3, mean_keyword_hits:1.33 |


## Added in the second pass

| directory | contents | why |
|---|---|---|
| `ia/` | 33 open text layers from the Internet Archive sweep (Latin, German, Italian, English, Persian, Arabic, Hindi/Urdu) + `fasciculus_ocr/` (my own OCR of 32 Quaestiones leaves) + `_fetch_report.json` (url, licence, borrow flag per item) | the casebook stratum |
| `ia2/` | the horary question literature: Prasna Marga, Shatpanchashika (+ translation), Prashna Chandeshwara, Kerala Prasna Shastra, Lal Kitab 1939/1941, Thorndike vol. 1, Amazulu divination, Beinecke Arabic MS | sub-question taxonomy + the 'named particulars' model |
| `../ia/IA_CATALOG.md` | 249 relevant IA items with text-layer/licence/borrow status | the shopping list |

Page scans (PDF/EPUB) are deliberately not in the workspace: `scripts/refetch.py <name>` restores any.
