# Evaluation report

Generated 2026-10-29 · model `gemini-3.5-flash-lite` · prompt `v1` · split `test`: 15 sets, 45 documents (11 scanned, with no text layer).

Produced by `python -m app.evaluation` (services/api). Every number below comes from that run; the documents are generated, so the right answers are known.

## Summary

- **Document type:** 100.0% (45/45)
- **Header fields read exactly right:** 99.7% (344/345) (digital 99.6% (260/261), scanned 100.0% (84/84))
- **Line items found:** 100.0% (270/270); **line values right:** 100.0% (720/720)
- **Values located on the page:** digital 100.0% (781/781), scanned 100.0% (252/252)
- **3-way match, sets with exactly the expected problems:** 100.0% (15/15)
- **Documents that could not be read:** 0

## Document type

Rows: the real type. Columns: what the AI said.

| Real type | invoice | purchase_order | goods_receipt | unknown |
|---|---|---|---|---|
| invoice | 15 | 0 | 0 | 0 |
| purchase_order | 0 | 15 | 0 | 0 |
| goods_receipt | 0 | 0 | 15 | 0 |

## Header fields

Text is compared ignoring case and extra spaces; dates and amounts must be exact. An empty answer is right only where the value is really absent.

| Field | Right |
|---|---|
| Document number | 100.0% (45/45) |
| Vendor | 100.0% (45/45) |
| Buyer | 100.0% (45/45) |
| Date | 97.8% (44/45) |
| Due date | 100.0% (15/15) |
| PO reference | 100.0% (30/30) |
| Currency | 100.0% (30/30) |
| Subtotal | 100.0% (30/30) |
| Tax | 100.0% (30/30) |
| Total | 100.0% (30/30) |
| **All fields** | **99.7% (344/345)** |

Digital documents: 99.6% (260/261) · scanned documents: 100.0% (84/84)

## Line items

Lines found (matched by SKU): 100.0% (270/270)

| Value | Right |
|---|---|
| Quantity (billed / ordered / received) | 100.0% (270/270) |
| Quantity ordered (receipts) | 100.0% (90/90) |
| Unit price | 100.0% (180/180) |
| Line total | 100.0% (180/180) |

## Evidence (where each value is on the page)

Share of the values the AI read that were found on the page, so the app can highlight them. Digital pages use the PDF's own words; scans use OCR.

- Digital documents: 100.0% (781/781)
- Scanned documents: 100.0% (252/252)

## 3-way match

The matching rules run on what the AI read. A set is right when the problems found are exactly the injected ones (none for clean sets).

Sets with exactly the expected problems: **100.0% (15/15)**

| Problem | Found | Missed | False alarm |
|---|---|---|---|
| `LINE_TOTAL_MISMATCH` | 1 | 0 | 0 |
| `MISSING_PO_REFERENCE` | 2 | 0 | 0 |
| `PRICE_MISMATCH` | 2 | 0 | 0 |
| `QTY_EXCEEDS_RECEIVED` | 1 | 0 | 0 |
| `TOTAL_MISMATCH` | 2 | 0 | 0 |

## Speed and usage

- AI reading time per document: median 4.2 s, 95th percentile 9.6 s
- Tokens per document: 1,584 in, 618 out
- OCR time per scanned document (CPU): median 4.9 s
- Answers used in this run: 45 from file cache (cached answers are reused, so re-running costs no AI quota)

## Every mistake

| Set | File | Field | Expected | Read |
|---|---|---|---|---|
| SET-0028 | SIP-58351.pdf | issue_date | 2026-04-03 | 2026-03-04 |

## Limits of this test

- The documents are generated: realistic layouts, fonts, currencies and noisy scans, but cleaner than many real-world invoices.
- The sample is small, and this split may not contain every kind of problem (see the 3-way match table for what was tested).
- Accuracy on a client's own documents should be measured on a sample of them before relying on these numbers.
