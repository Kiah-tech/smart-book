"""Reset data/ with demo data (CLAUDE.md: ~50 fake books, one Super-User, demo customers).

Everything is generated locally - book covers, demo face photos and voice clips -
so nothing is downloaded. Run:  .venv/bin/python seed.py

Demo accounts (sign in by choosing the matching file in data/samples/):
  sue_admin  Super-User
  alice      Registered Customer, $50 balance
  victor     VIP Customer, $120 balance (seeded as VIP for the demo)
  sid        Registered Customer, SUSPENDED (balance -$1.00 after a fine) -> wallet-only
  bella, carlos, dana, eli, fay   Registered Customers who wrote the seeded reviews
"""
import hashlib
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from bookorbit import rules
from bookorbit.ai import media
from bookorbit.ai.biometrics import FACE, VOICE
from bookorbit.app_context import build_context
from bookorbit.config import PROJECT_ROOT, load_config

RNG = random.Random(322)          # fixed seed: every reset gives the same data
BASE_TIME = datetime(2026, 10, 1, 9, 0, 0)

# 50 original (made-up) books: 10 categories x 5 titles
CATALOG = {
    "Fiction": ["The Lantern Keeper's Daughter", "Salt and Static", "A House of Folded Letters",
                "The Quiet Orchard", "Tuesdays on Marrow Street"],
    "Mystery": ["The Clockmaker's Alibi", "Nine Keys to Harrow Hall", "Murder at the Tidewater Inn",
                "The Vanishing Cartographer", "Ink on the Lighthouse Stairs"],
    "Science Fiction": ["Orbit of the Glass Moons", "The Last Signal from Kepler Bay",
                        "Starlight Freight Company", "The Copper Gardeners of Mars", "Echoes in Hyperlane Six"],
    "Fantasy": ["The Ember Crown", "Songs of the Hollow Forest", "The Dragon Who Collected Maps",
                "A Spell for Rainy Kingdoms", "The Moonbound Archivist"],
    "Romance": ["Letters from the Lavender Coast", "Second Spring in Verona Lane", "The Bookshop Proposal",
                "Hearts Over Harbor Bridge", "A Winter Waltz"],
    "History": ["Rivers of Empire", "The Silk Road Ledgers", "Bridges of the Industrial Age",
                "The Forgotten Fleet of 1588", "Bread and Barricades"],
    "Biography": ["The Woman Who Measured Storms", "Notes of a Midnight Pianist", "The Inventor's Notebook",
                  "A Life Among Glaciers", "The Chess Teacher of Odessa"],
    "Self-Help": ["Small Steps, Steady Days", "The Calm Desk Method", "Habits of the Patient Mind",
                  "Saying No Gracefully", "The Five-Minute Morning"],
    "Science": ["The Secret Life of Fungi", "Atoms in Your Coffee Cup", "Maps of the Deep Ocean",
                "How Bridges Stand Up", "The Curious Physics of Everyday Things"],
    "Poetry": ["Paper Boats and Thunder", "Salt Psalms", "The Orchard Sonnets",
               "City Lights, Country Stars", "Small Hours"],
}
KEYWORDS = {
    "Fiction": ["family", "small town", "secrets", "friendship", "coming of age"],
    "Mystery": ["detective", "murder", "clues", "suspense", "whodunit"],
    "Science Fiction": ["space", "robots", "future", "aliens", "time travel"],
    "Fantasy": ["magic", "dragons", "quest", "kingdom", "adventure"],
    "Romance": ["love", "second chances", "summer", "letters", "wedding"],
    "History": ["empire", "war", "trade", "revolution", "europe"],
    "Biography": ["memoir", "inventor", "artist", "explorer", "true story"],
    "Self-Help": ["habits", "productivity", "mindfulness", "focus", "wellbeing"],
    "Science": ["biology", "physics", "ocean", "engineering", "nature"],
    "Poetry": ["verse", "nature", "city", "love", "seasons"],
}
FIRST = ["Ada", "Bram", "Celia", "Dorian", "Elsa", "Felix", "Greta", "Hugo", "Iris", "Jonah",
         "Kira", "Leon", "Mira", "Nils", "Opal", "Pavel", "Quinn", "Rosa", "Silas", "Tova"]
LAST = ["Ashdown", "Bellweather", "Corrigan", "Dunmore", "Everly", "Fairbank", "Galloway",
        "Hartwell", "Ironside", "Juniper", "Kestrel", "Lockridge", "Merriweather", "Northcott"]
BLURB = {
    "Fiction": "A tender story about {k1} and {k2}, told over one unforgettable year.",
    "Mystery": "A {k1} story full of {k2}: every page hides a new clue.",
    "Science Fiction": "An adventure through {k1} and {k2} at the edge of the known galaxy.",
    "Fantasy": "A sweeping tale of {k1}, {k2} and an unlikely hero.",
    "Romance": "A warm, witty romance about {k1} and {k2}.",
    "History": "A lively history of {k1} and {k2}, built on letters and ledgers.",
    "Biography": "A {k1} portrait of a remarkable life - a {k2} you won't forget.",
    "Self-Help": "Practical, kind advice on {k1} and {k2} for busy people.",
    "Science": "An accessible tour of {k1} and {k2} for curious readers.",
    "Poetry": "A collection of short poems about {k1} and {k2}.",
}
REVIEW_TEXT = {
    5: ["Absolutely loved it - could not put it down.", "A new favourite, I will reread this.",
        "Beautifully written from start to finish."],
    4: ["Really enjoyable, a couple of slow chapters.", "Great read, would recommend to friends.",
        "Smart and engaging, worth the price."],
    3: ["Decent, but it did not fully grab me.", "Some good moments, some flat ones.",
        "Fine for a weekend read."],
    2: ["The pacing never worked for me.", "I expected more from the premise.",
        "Hard to finish, sadly."],
    1: ["Not for me at all.", "Very disappointing.", "Could not get into it."],
}
DEMO_USERS = [
    # username, full name, role, status, starting deposit, voice pitch (Hz) for the MOCK voiceprint
    ("sue_admin", "Sue Admin", rules.SU, rules.ACTIVE, 0.0, 180),
    ("alice", "Alice Morgan", rules.RC, rules.ACTIVE, 50.0, 220),
    ("victor", "Victor Hale", rules.VC, rules.ACTIVE, 120.0, 130),
    ("sid", "Sid Turner", rules.RC, rules.SUSPENDED, 0.0, 150),
    ("bella", "Bella Cruz", rules.RC, rules.ACTIVE, 20.0, 240),
    ("carlos", "Carlos Ibanez", rules.RC, rules.ACTIVE, 20.0, 110),
    ("dana", "Dana Okafor", rules.RC, rules.ACTIVE, 20.0, 200),
    ("eli", "Eli Novak", rules.RC, rules.ACTIVE, 20.0, 120),
    ("fay", "Fay Lindqvist", rules.RC, rules.ACTIVE, 20.0, 260),
]


def ts(offset_minutes: int) -> str:
    return (BASE_TIME + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- images / audio
def _hue_rgb(h: float, s: float, v: float) -> np.ndarray:
    import colorsys
    return np.array(colorsys.hsv_to_rgb(h, s, v)) * 255


def make_cover(book_id: str, category_index: int) -> bytes:
    """120x180 abstract cover: category hue, a band and a circle placed by the book's hash."""
    h = int(hashlib.sha256(book_id.encode()).hexdigest(), 16)
    w, hgt = 120, 180
    yy, xx = np.mgrid[0:hgt, 0:w]
    hue = (category_index / 10 + (h % 7) / 70) % 1.0
    img = np.zeros((hgt, w, 3)) + _hue_rgb(hue, 0.55, 0.55)
    band_y = 30 + h % 90
    img[(yy > band_y) & (yy < band_y + 18)] = _hue_rgb((hue + 0.08) % 1, 0.35, 0.85)
    cx, cy, r = 20 + (h >> 8) % 80, 110 + (h >> 16) % 50, 14 + (h >> 24) % 18
    img[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = _hue_rgb((hue + 0.5) % 1, 0.6, 0.95)
    return media.encode_png(img.astype(np.uint8), {"book_id": book_id})


def make_face_photo(person: str | None, faces: int, variant: int) -> bytes:
    """Simple cartoon face(s). The PNG text tags tell the MOCK detector who and how many."""
    rng = np.random.default_rng(int(hashlib.sha256(f"{person}{variant}".encode()).hexdigest()[:8], 16))
    w, h = 160, 160
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3)) + np.array([200, 215, 230]) + rng.integers(-12, 12, (h, w, 3))
    centers = {1: [(80, 80)], 2: [(45, 80), (115, 80)]}.get(faces, [])
    r = 50 if faces == 1 else 32
    for cx, cy in centers:
        img[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = [235, 195, 160]
        for ex in (cx - r // 3, cx + r // 3):
            img[(xx - ex) ** 2 + (yy - (cy - r // 4)) ** 2 < (r // 8) ** 2] = [40, 40, 40]
        img[(abs(yy - (cy + r // 3)) < 3) & (abs(xx - cx) < r // 3)] = [150, 60, 60]
    tags = {"faces": faces}
    if person:
        tags["person"] = person
    return media.encode_png(np.clip(img, 0, 255).astype(np.uint8), tags)


def make_voice(pitch: int, seconds: float, variant: int) -> bytes:
    rate = 16000
    t = np.arange(int(rate * seconds)) / rate
    rng = np.random.default_rng(pitch * 10 + variant)
    wave_ = 0.5 * np.sin(2 * np.pi * pitch * t) + 0.15 * np.sin(2 * np.pi * pitch * 2 * t)
    return media.encode_wav(wave_ + 0.05 * rng.standard_normal(len(t)), rate)


# ---------------------------------------------------------------- main
def main() -> None:
    cfg = load_config()
    data_dir = Path(cfg["DATA_DIR"]).resolve()
    if data_dir != (PROJECT_ROOT / "data").resolve() and "--force" not in sys.argv:
        sys.exit(f"Refusing to wipe {data_dir} (not the project's data/ folder). Use --force.")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    ctx = build_context(cfg)
    fs = ctx.fs
    for sub in ("covers", "samples", "biometrics"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    samples = data_dir / "samples"

    # --- users (+ biometric templates enrolled through the same engine as UC-01) ---
    users, minute = {}, 0
    for username, name, role, status, deposit, pitch in DEMO_USERS:
        uid = fs.next_id("users", "U")
        enroll_face = make_face_photo(username, 1, 0)
        enroll_voice = make_voice(pitch, 3.0, 0)
        (samples / f"{username}_face.png").write_bytes(make_face_photo(username, 1, 1))
        (samples / f"{username}_voice.wav").write_bytes(make_voice(pitch, 3.0, 1))
        ctx.bio.enroll(uid, FACE, enroll_face)
        ctx.bio.enroll(uid, VOICE, enroll_voice)
        user = {"user_id": uid, "username": username, "full_name": name, "email": f"{username}@example.com",
                "role": role, "status": rules.ACTIVE, "balance": 0.0, "warnings": 0,
                "purchase_count": 0, "total_spent": 0.0, "promo_purchases": 0, "promo_spent": 0.0,
                "created_at": ts(minute)}
        fs.append("users", user)
        users[username] = user
        minute += 5
        if deposit:
            fs.append("transactions", {"txn_id": fs.next_id("transactions", "X"), "user_id": uid,
                                       "type": "DEPOSIT", "amount": deposit, "balance_after": deposit,
                                       "book_id": None, "note": "Add funds", "timestamp": ts(minute)})
            fs.update("users", "user_id", uid, {"balance": deposit})
        if role == rules.VC:
            # Seeded VIP for the demo; real promotions (R5) are earned through purchases in Phase 2.
            fs.append("status_changes", {"change_id": fs.next_id("status_changes", "SC"), "user_id": uid,
                                         "from_role": rules.RC, "to_role": rules.VC, "from_status": rules.ACTIVE,
                                         "to_status": rules.ACTIVE, "reason": "seed: demo VIP",
                                         "timestamp": ts(minute)})
        if status == rules.SUSPENDED:
            # R7: a purchase attempt with $0 -> $1.00 fine -> negative balance -> SUSPENDED
            fs.append("transactions", {"txn_id": fs.next_id("transactions", "X"), "user_id": uid,
                                       "type": "FINE", "amount": -rules.FINE_AMOUNT,
                                       "balance_after": -rules.FINE_AMOUNT, "book_id": "B-0001",
                                       "note": "Insufficient funds", "timestamp": ts(minute)})
            fs.append("status_changes", {"change_id": fs.next_id("status_changes", "SC"), "user_id": uid,
                                         "from_role": rules.RC, "to_role": rules.RC, "from_status": rules.ACTIVE,
                                         "to_status": rules.SUSPENDED, "reason": "negative balance",
                                         "timestamp": ts(minute)})
            fs.update("users", "user_id", uid, {"balance": -rules.FINE_AMOUNT, "status": rules.SUSPENDED})

    # extra demo samples for the exceptional scenarios of UC-01 / UC-02
    (samples / "stranger_face.png").write_bytes(make_face_photo("stranger", 1, 0))
    (samples / "no_face.png").write_bytes(make_face_photo(None, 0, 0))
    (samples / "two_faces.png").write_bytes(make_face_photo("crowd", 2, 0))
    (samples / "new_user_face.png").write_bytes(make_face_photo("new_user", 1, 0))
    (samples / "new_user_voice.wav").write_bytes(make_voice(300, 3.0, 0))
    (samples / "stranger_voice.wav").write_bytes(make_voice(90, 3.0, 0))
    (samples / "short_voice.wav").write_bytes(make_voice(220, 1.0, 0))

    # --- books ---
    su_id = users["sue_admin"]["user_id"]
    used_authors = set()
    for ci, (category, titles) in enumerate(CATALOG.items()):
        for title in titles:
            bid = fs.next_id("books", "B")
            while True:
                author = f"{RNG.choice(FIRST)} {RNG.choice(LAST)}"
                if author not in used_authors:
                    used_authors.add(author)
                    break
            kws = RNG.sample(KEYWORDS[category], 3)
            cover = data_dir / "covers" / f"{bid}.png"
            cover.write_bytes(make_cover(bid, ci))
            fs.append("books", {
                "book_id": bid, "title": title, "author": author, "category": category,
                "keywords": ", ".join(kws), "pub_year": RNG.randint(1950, 2025),
                "price": round(RNG.choice([4.99, 7.99, 9.99, 12.99, 14.99, 16.99, 19.99, 24.99, 34.99]), 2),
                "description": BLURB[category].format(k1=kws[0], k2=kws[1]),
                "cover_path": f"covers/{bid}.png", "cover_vec_path": None, "text_path": None,
                "added_by": su_id, "browse_count": RNG.randint(0, 60), "purchase_count": 0,
                "rating_count": 0, "weighted_avg": 0.0, "list_status": rules.LIST_NONE,
                "indexed": False, "added_at": ts(minute)})
            minute += 1

    # --- reviews: one per customer per book (ASSUMPTIONS A-09); clean text only ---
    reviewers = [users[u]["user_id"] for u in ("alice", "victor", "bella", "carlos", "dana", "eli", "fay")]
    book_ids = [b["book_id"] for b in fs.load("books")]
    loved, disliked = book_ids[0:50:9][:4], book_ids[3:50:11][:2]   # demo R13 lists
    review_minute = 60 * 24 * 30
    for bid in book_ids:
        if bid in loved:
            who, ratings = reviewers[:5], [5, 5, 4, 5, 5]
        elif bid in disliked:
            who, ratings = reviewers[2:7], [1, 2, 1, 1, 2]
        else:
            who = RNG.sample(reviewers, RNG.randint(0, 3))
            ratings = [RNG.choice([2, 3, 3, 4, 4, 4, 5, 5]) for _ in who]
        for uid, rating in zip(who, ratings):
            text = RNG.choice(REVIEW_TEXT[rating])
            fs.append("reviews", {
                "review_id": fs.next_id("reviews", "R"), "book_id": bid, "user_id": uid,
                "rating": rating, "original_text": text, "display_text": text, "taboo_count": 0,
                "status": "PUBLISHED", "verified_buyer": False, "weight": rules.W_OTHER,
                "timestamp": ts(review_minute)})
            review_minute += RNG.randint(30, 600)
    ctx.ratings.recalculate_all()

    print(f"Seeded {len(fs.load('users'))} users, {len(fs.load('books'))} books, "
          f"{len(fs.load('reviews'))} reviews into {data_dir}")
    print(f"Demo sign-in samples: {samples}")


if __name__ == "__main__":
    main()
