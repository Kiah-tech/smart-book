# Progress / handoff notes

Read with `CLAUDE.md` (rules, stack, phases) and `docs/ASSUMPTIONS.md` (decisions,
deviations, mocks). This file only holds what those two don't.

## Status (2026-11-23)
- **Phase 1 done** and committed locally (`8f87665`): UC-01..UC-05, 39 tests passing.
- **Next: Phase 2** (UC-07..UC-11). Nothing for it has been started.

## Quick start
```bash
.venv/bin/python seed.py                          # resets data/ (deletes it first)
.venv/bin/python -m unittest discover tests -v    # ~1.5 s
.venv/bin/python app.py
```
The only dependency so far is `numpy`. Ollama is **not installed** on this Mac.

## Demo accounts (MOCK sign-in: choose the file in `data/samples/`)
| Username | State | Notes |
|----------|-------|-------|
| `sue_admin` | Super-User | the only SU (seeded, A-08) |
| `alice` | RC, $50 | |
| `victor` | VC, $120 | seeded as VIP directly, with no purchases behind it |
| `sid` | RC, SUSPENDED, -$1.00 | signs in to wallet-only mode |
| `bella`, `carlos`, `dana`, `eli`, `fay` | RC, $20 | authors of the seeded reviews |

Each user has `<name>_face.png` and `<name>_voice.wav`. Edge-case files:
`stranger_face.png`, `stranger_voice.wav`, `no_face.png`, `two_faces.png`,
`short_voice.wav`, and `new_user_face.png` / `new_user_voice.wav` for Register.
Seeded order lists: 4 books are To-Order and 2 are No-Order (5 reviews each).

## Known quirks
- **Tk test hang (macOS):** creating a second `tk.Tk()` in one process after
  destroying the first can freeze inside `update()`. Keep every UI check in the single
  test `tests/test_ui_smoke.py::test_all_roles_in_one_window` (add steps there; don't
  add new Tk test methods or classes).
- **Guard against hangs:** macOS has no `timeout` command. When a test might hang, run it with
  `-X faulthandler` and `faulthandler.dump_traceback_later(N, exit=True)`.
- **File paths in records** (`cover_path`, `vector_path`) are relative to `data/`;
  always open them through `fs.resolve(...)`.
- **No visual check of the GUI:** screenshots would need macOS Accessibility and
  Screen Recording permissions, which weren't granted. Verification so far = unit tests,
  the smoke test, and the user trying the app.
- `FileStore.lock` is an `RLock`. Wrap read-increment-write sequences in `with fs.lock:`
  (see `CatalogService.record_browse`).
- `tests/helpers.TempStoreCase` gives each test a fresh temporary `data/`, and
  `make_face_photo` / `make_voice` (from `seed.py`) build samples.

## Phase 2 should start with
1. **`StatusManager`** (SRS 4.13). Wallet, purchase and warnings all depend on it.
2. **`WalletService`**: `deposit`, `post_transaction`, `charge_fine` (read side already exists).
   Enable the Add Funds field/button in `WalletScreen`.
3. **`PurchaseService`** (`purchase`, `final_price`, `already_owned`), then replace the
   `display_price` stub in `CatalogService.get_details` (M-04) and enable Buy Now.
   Keep R7 as written (F-18).
4. **`TabooService.list_words` + `ModerationEngine`**; seed a taboo list.
5. **`ReviewService.submit`** with one review per customer per book (A-09), **`WarningService`**,
   `RatingService.recalculate` after publishing. Enable Write Review.
6. Replace the **My Orders / My Reviews** placeholders (A-14).
7. **Update `seed.py`** so purchases (and `victor`'s VIP promotion) go through the real services.
   Seeded reviews by buyers then become verified (weight 2.0), and the promo counters stay consistent.
8. Add a test for each rule R5–R11 to the existing suite.

Phase 1 stubs to remove as you go are marked "Phase 2" in the code:
`grep -rn "Phase 2" bookorbit`.
