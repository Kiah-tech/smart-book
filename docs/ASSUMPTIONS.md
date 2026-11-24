# Assumptions, decisions, deviations and mocks

Source of truth: `docs/BookOrbit_AI_Phase2_Design_Report.pdf` (v2.0), use cases
UC-01..UC-18 and business rules R1..R15 (Table 2). The Phase I SRS that the report
cites (`Phase1_Specification.pdf`) is not in `docs/`, so the Phase II report is used alone.

Status legend: **RESOLVED** (decided with the project owner), **ASSUMPTION** (our reading
of something the SRS leaves open), **DEVIATION** (we knowingly differ from the SRS
pseudo-code), **FLAG** (kept as written but worth noting), **MOCK / STUB** (not the real thing).

## Conflicts

| ID | Topic | Status | Decision |
|----|-------|--------|----------|
| C-01 | Stack: CLAUDE.md's default was React/FastAPI/SQLite; the SRS (Section 1.1) names Python 3.12 + Tkinter and JSON Lines text files ("flat-file storage required by the specification") | **RESOLVED** | Follow the SRS: Tkinter desktop app, `FileStore` over `data/*.txt`. |
| C-02 | Cart: mockups (Fig. 28-31) and the old CLAUDE.md mention a cart; UC-08, the E-R diagram and the sidebar pseudo-code have only single-book "Buy Now" | **RESOLVED** | No cart. Buy Now paid from the wallet balance (UC-08/09). |
| C-03 | Stock / inventory: Fig. 30/32 show stock counts; BOOK has no stock field and "already owned" + Reading Companion imply digital books | **RESOLVED** | No stock. Books are digital; one purchase per customer per book. |
| C-04 | Fig. 32 shows Edit / Delete book buttons, but no use case or method covers them | OPEN | Not built unless asked; only UC-15 Add New Books. |
| C-05 | Data dictionary vs pseudo-code: BOOK lacks `indexed`, RAG_CHUNK lacks `chapter`, scopes CUSTOMER/ADMIN are never created, `SEARCH_HIT` is never written, TABOO_WORD's key (the word) is edited in place | ASSUMPTION | Follow the pseudo-code: add `indexed` (already in seeded books) and `chapter` fields; the extra enum values stay unused. |
| C-06 | Single-instance lock file (Section 6.1) vs "two SUs at once" scenarios (UC-16 E2, UC-17 E2) | ASSUMPTION | Treat the "two SUs" cases as stale-screen cases: the list is simply reloaded. |

## Gaps filled

| ID | Gap | Status | Decision |
|----|-----|--------|----------|
| A-08 | UC-01 only creates Registered Customers; how is a Super-User created? | **RESOLVED** | `seed.py` creates the Super-User account (`sue_admin`). |
| A-09 | May a customer review the same book more than once? | **RESOLVED** | One review per customer per book (enforced in Phase 2, UC-10). Seeded reviews follow this. |
| A-10 | R15: summarize / explain / ask on non-owned books do not check the chapter | **RESOLVED** | R15's chapter-1 limit applies to *every* Reading Companion action (Phase 3). |
| A-11 | Book texts and covers | **RESOLVED** | Generated locally by `seed.py` (abstract PNG covers now; short original chapter texts in Phase 3). Nothing is downloaded. All 50 books are made up. |
| A-12 | `keywords` is typed `str` but the recommender loops over it | ASSUMPTION | Stored as a comma-separated string ("family, secrets"), split on commas where a list is needed. Keyword search matches keywords + description (SRS 4.8). |
| A-13 | UC-13 E3 "lists example admin questions" has no pseudo-code | ASSUMPTION | Will show a fixed list of example questions (Phase 3). |
| A-14 | "My Orders" and "My Reviews" sidebar items have no use case | ASSUMPTION | My Orders = the customer's purchases; My Reviews = their reviews and warnings (UC-11 step 3). Phase 2. |
| A-15 | `browse_count` (R3) counts every view | ASSUMPTION | Counts views by everyone (Visitors and SUs included), as UC-05 step 3 says; only RC/VC views create a BROWSE_EVENT. |
| A-16 | UC-04 cover search returns the top 5; text search ordering when a sort is chosen | ASSUMPTION | Text search keeps best-match order (exact, prefix, contains) unless the user picks a sort other than title. |
| A-17 | Year search input format | ASSUMPTION | A single year (`1995`) or a range (`1990-2000`). |

## Deviations from the SRS pseudo-code

| ID | Where | Status | What and why |
|----|-------|--------|--------------|
| D-15 | `AuthService.is_locked` (SRS 4.6), R2 | **DEVIATION** (done, Phase 1) | The pseudo-code checks "the last 3 attempts all failed within 5 minutes". After a lock expires, the 3 old failures are still the last 3, so one more failure re-locks at once. We replay the attempts in order and reset the counter after a success **or** after a lock expires, so the user gets 3 fresh tries. Code: `AuthService.lock_state`; test: `test_lock_expiry_gives_three_fresh_tries`. |
| D-16 | `ChatbotService.ask` (SRS 4.20) | **DEVIATION** (planned, Phase 3) | `classify_intent` may call the LLM before `is_available()` is checked, so the bot would crash when Ollama is offline. We check availability first; offline, intent uses the keyword rules only. |
| D-17 | `ChatbotService.ask`, Visitor with no store context | **DEVIATION** (planned, Phase 3) | The pseudo-code returns "I couldn't find that..." labelled source `RAG`. The Petri net (UC-12 P10) says "store questions only". We return the P10 message with source `DENIED`. |

## Flags

| ID | Rule | Note |
|----|------|------|
| F-18 | R7 | Kept exactly as written: a customer with $0.00 who clicks Buy is fined $1.00, the balance becomes -$1.00 and the account is **suspended at once**. Strict, but it is what the SRS says. The seeded user `sid` is in that state. |

## Mocks and stubs (also shown in the UI)

| ID | What | Status | Details |
|----|------|--------|---------|
| M-01 | Biometric sign-in (UC-01, UC-02, R1, R2) | **MOCK** (`BIOMETRIC_MODE=mock`) | No webcam / microphone / PyTorch. The user picks a sample *file* (PNG/JPG photo or WAV clip). The mock turns it into a unit vector: a fixed random "person" vector plus a small per-file offset. Two different samples of the same person score about 0.92 cosine and different people about 0.0, so the real R2 thresholds (0.60 face / 0.75 voice), the lockout and E3/E5/E6 all behave as specified. The person comes from a PNG text tag written by `seed.py` (any other photo is identified by its file hash); for voice it is the clip's dominant pitch. Templates are stored as `.npy` files exactly as in the SRS. Real models: Phase 3 (optional). The sidebar shows "MOCK biometrics". |
| M-02 | Personalized recommendations (UC-06, R4) | **STUB** until Phase 3 | Customers see popular books under "Popular right now", which is the SRS's own no-history fallback (UC-06 E1). |
| M-03 | Cover-image search (UC-04 step 4) | **STUB** until Phase 3 | The camera button is disabled with a tooltip, exactly as UC-04 E5 ("image model not loaded"). |
| M-04 | VIP price on the details page (UC-05 step 5) | **STUB** until Phase 2 | Everyone sees the list price until `PurchaseService.final_price` exists. |
| M-05 | Screens for later phases | **STUB** | Sidebar items for later phases open a placeholder naming the phase and use case. Buy / Review / Companion buttons are disabled with tooltips. |
| M-06 | Seed data | Seeded directly | `victor` is seeded as a VIP and `sid` as suspended (with matching ledger and status-change records) so those states can be demoed before Phase 2 can create them through purchases. Seeded reviews are clean text, unverified (weight 1.0). |
