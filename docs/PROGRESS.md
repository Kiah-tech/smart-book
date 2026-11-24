# Progress / handoff notes

Read with `CLAUDE.md` (rules, stack, phases), `docs/ASSUMPTIONS.md` (decisions,
deviations, mocks) and `docs/SRS.md` (text extract of the design report: grep it for
UC-xx / Rxx / class names instead of opening the PDF). This file only holds what those don't.

## Status (2026-11-24)
- **Phase 1 done** (`8f87665`): UC-01..UC-05.
- **Phase 2 done** and committed locally: UC-07..UC-11, rules R5-R13. 78 tests passing.
- **Next: Phase 3** (UC-06, UC-12, UC-13, UC-14, UC-04 cover search, real-model switches).

## Quick start
```bash
.venv/bin/python seed.py                          # resets data/ (deletes it first)
.venv/bin/python -m unittest discover tests -v    # ~2 s
.venv/bin/python app.py
```
The only dependency so far is `numpy`. Ollama is **not installed** on this Mac.

## Demo accounts (MOCK sign-in: choose the file in `data/samples/`)
| Username | State after `seed.py` | Good for demoing |
|----------|-----------------------|------------------|
| `sue_admin` | Super-User | the only SU (A-08) |
| `alice` | RC, $50, 3 purchases | her next Buy Now promotes her to VIP (R5); the discount starts on the purchase after that (R6) |
| `victor` | VC, $120, promoted by his 4th purchase | VIP price on every book (R6); one blocked review demotes him (R10) |
| `sid` | RC, SUSPENDED, -$1.00 (tried to buy with $0) | wallet-only mode (R8); deposit $1 to see the "Super-User can reactivate" note |
| `wes` | RC, $20, 2 warnings | one more blocked review suspends him (R10) |
| `bella`, `carlos`, `dana`, `eli`, `fay` | RC, $10.01, 1 purchase each | buying a $24.99 book: fined $1, not suspended (R7, UC-08 E1) |

Taboo words (A-22): crap, darn, dumb, garbage, heck, idiot, lame, moron, stupid, trash.
A review with 1-3 of them is masked; 4 or more is blocked, e.g.
"Dumb, stupid, lame and darn boring."
Seeded order lists: 4 books are To-Order and 2 are No-Order. 12 seeded reviews are
by verified buyers (weight 2.0).

Each user has `<name>_face.png` and `<name>_voice.wav`. Edge-case files:
`stranger_face.png`, `stranger_voice.wav`, `no_face.png`, `two_faces.png`,
`short_voice.wav`, and `new_user_face.png` / `new_user_voice.wav` for Register.

## Code map for Phase 2
- `bookorbit/services/status.py` `StatusManager`: the only place a role or status changes (R5, R7, R8, R10), and each change is logged to `status_changes.txt`.
- `services/wallet.py` (UC-07, R7), `services/purchases.py` (UC-08/09, R5-R7; `quote()` feeds the Buy Now dialog),
  `services/moderation.py` (R9), `services/warnings.py` (UC-11, R10), `services/reviews.py` (UC-10).
- `bookorbit/money.py`: `cents()` rounds half up (A-19), `parse_amount()` checks a typed amount.
- `bookorbit/clock.py`: `clock.now()` for timestamps; `seed.py` wraps service calls in `clock.frozen(ts)`.
- UI: `BookDetailScreen.on_buy / on_review`, `WalletScreen.on_deposit`, `OrdersScreen`, `MyReviewsScreen`.
  `MainWindow.refresh_chrome()` redraws the sidebar after a promotion, demotion or suspension.

## Known quirks
- **Tk test hang (macOS):** creating a second `tk.Tk()` in one process after
  destroying the first can freeze inside `update()`. Keep every UI check in the single
  test `tests/test_ui_smoke.py::test_all_roles_in_one_window` (add steps there; don't
  add new Tk test methods or classes). Phase 2 steps are in `phase2_flows()`.
- **Dialogs:** screens call `app.confirm(...)` / `app.inform(...)` instead of `messagebox`
  directly, so the smoke test can answer them (a real modal dialog would block the test).
- **Guard against hangs:** macOS has no `timeout` command. When a test might hang, run it with
  `-X faulthandler` and `faulthandler.dump_traceback_later(N, exit=True)`.
- **File paths in records** (`cover_path`, `vector_path`) are relative to `data/`;
  always open them through `fs.resolve(...)`.
- **No visual check of the GUI:** screenshots would need macOS Accessibility and
  Screen Recording permissions, which weren't granted. Verification so far = unit tests,
  the smoke test (which drives the real screens), and the user trying the app.
- `FileStore.lock` is an `RLock`. Wrap read-check-write sequences in `with fs.lock:`
  (see `PurchaseService.purchase`, `WalletService.post_transaction`).
- `tests/helpers.TempStoreCase` gives each test a fresh temporary `data/`, plus
  `add_book`, `add_user`, `session_for`, `user` (fresh copy) and `taboo(...)`.
- `docs/SRS.md` was made with `pypdf` (installed only in a scratch folder, not in `.venv`).
  Tables are flattened to one row per line; figures are not included.

## Phase 3 should start with
1. **Book texts**: `seed.py` writes short original chapter texts (A-11) and sets `text_path`.
2. **`LLMClient`** (SRS 4.22) with `LLM_MODE=mock|real` from `.env`; MOCK label in the UI when Ollama is missing.
3. **`RAGRetriever`** (4.21) + `rag_chunks.txt` (C-05: add `chapter`).
4. **`ChatbotService`** (4.20, UC-12/13, R14) with deviations D-16 and D-17; example admin questions (A-13).
5. **`ReadingCompanion`** (4.23, UC-14, R15 applied to every action, A-10); progress in `reading_progress.txt`.
   Enable the Reading Companion button (owned books: all chapters).
6. **`RecommendationEngine.personalized`** (UC-06, R4), replacing stub M-02.
7. **`CoverIndex`** (UC-04 cover search, `COVER_MODE`), replacing stub M-03.
