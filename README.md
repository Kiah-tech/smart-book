# BookOrbit AI – Smart Bookstore prototype

Local desktop prototype of the BookOrbit AI design report
(`docs/BookOrbit_AI_Phase2_Design_Report.pdf`): Python 3.12 + Tkinter, data in
JSON Lines text files under `data/`.

## Setup (once)
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run
```bash
.venv/bin/python seed.py      # reset data/ with demo data (50 fake books, demo users, sample files)
.venv/bin/python app.py       # start the app
.venv/bin/python -m unittest discover tests -v
```

## Demo sign-in (MOCK biometrics)
Sign In → type a username → **Choose sample file…** → pick the matching file in
`data/samples/` → **Capture & Verify**.

| Username | Role | Face / voice sample |
|----------|------|---------------------|
| `sue_admin` | Super-User | `sue_admin_face.png` / `sue_admin_voice.wav` |
| `alice` | Registered Customer | `alice_face.png` / `alice_voice.wav` |
| `victor` | VIP Customer | `victor_face.png` / `victor_voice.wav` |
| `sid` | Suspended customer (wallet-only) | `sid_face.png` / `sid_voice.wav` |

Exceptional cases: `stranger_face.png` (no match → 3 tries → 5-minute lock),
`no_face.png`, `two_faces.png`, `short_voice.wav` (asked to recapture, not counted).
To register, use `new_user_face.png` / `new_user_voice.wav`.

See `docs/ASSUMPTIONS.md` for every assumption, deviation and mock.

## Layout
```
bookorbit/
  rules.py            business-rule constants (R1-R15)
  persistence/        FileStore (the only code that touches data/)
  services/           Session, Auth, Catalog, Reviews, Ratings, Wallet
  ai/                 BiometricEngine (mock), RecommendationEngine, media helpers
  ui/                 MainWindow + screens (Tkinter)
seed.py, app.py, tests/
```
