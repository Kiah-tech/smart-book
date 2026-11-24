"""Phase 1 screens (SRS 4.24). Screens only display data and forward actions to
services; every handler catches the service's named error and shows its
message in the banner. No business rules live here."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from bookorbit import rules
from bookorbit.ai.biometrics import FACE, VOICE
from bookorbit.errors import (LoginError, NoFaceError, NotFound, NoVoiceError, RegistrationError,
                              TemplateMissingError)
from bookorbit.services.catalog import FIELDS
from bookorbit.ui.widgets import (CARD, FONT, MUTED, NAVY, RED, Banner, BookCard, ScrollFrame, draw_cover,
                                  Tooltip, stars)

COVER_SEARCH_TIP = "Cover-image search is disabled: the image model is not loaded (UC-04 E5). Arrives in Phase 3."


class Screen(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent)
        self.app, self.ctx, self.kwargs = app, app.ctx, kwargs
        self.images = []
        self.banner = Banner(self)
        self.banner.pack(fill="x")

    @property
    def session(self):
        return self.app.session

    def render(self):
        if self.app.flash:
            self.banner.show(*self.app.flash)
            self.app.flash = None
        self.build()

    def build(self):
        raise NotImplementedError

    def open_book(self, book_id):
        self.app.show("book", book_id=book_id)


def search_bar(parent, on_search, initial=""):
    """Search box + disabled camera button used on Home and Catalog (UC-04)."""
    row = ttk.Frame(parent)
    entry = ttk.Entry(row, width=48, font=(FONT, 13))
    entry.insert(0, initial)
    entry.pack(side="left", ipady=4)
    entry.bind("<Return>", lambda _e: on_search(entry.get()))
    ttk.Button(row, text="Search", style="Primary.TButton",
               command=lambda: on_search(entry.get())).pack(side="left", padx=6)
    cam = ttk.Button(row, text="📷 Cover", state="disabled")
    cam.pack(side="left")
    Tooltip(cam, COVER_SEARCH_TIP)
    return row, entry


# ---------------------------------------------------------------- Home (UC-03, UC-06)
class HomeScreen(Screen):
    def build(self):
        ttk.Label(self, text="Discover Your Next Favorite Book", style="H1.TLabel").pack(anchor="w")
        ttk.Label(self, text="Search by title, author, keyword or year.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 10))
        row, _ = search_bar(self, lambda q: self.app.show("catalog", query=q, field="title"))
        row.pack(anchor="w", pady=(0, 18))

        if self.session.role == rules.VC:
            tk.Label(self, text="👑  VIP Member - you receive a 10% discount on all purchases (R6)",
                     bg="#fff4d6", fg="#7a5200", font=(FONT, 13, "bold"), anchor="w",
                     padx=12, pady=8).pack(fill="x", pady=(0, 14))

        title, books = self.ctx.recs.home_books(self.session)
        ttk.Label(self, text=title, style="H2.TLabel").pack(anchor="w")
        if self.session.is_customer:
            ttk.Label(self, text="Personalized recommendations (UC-06) arrive in Phase 3; until then the "
                                 "SRS fallback shows popular books.", style="Muted.TLabel").pack(anchor="w")
        cards = ttk.Frame(self)
        cards.pack(anchor="w", pady=10)
        if not books:
            ttk.Label(cards, text="No books available yet", style="Muted.TLabel").pack()  # UC-03 E2
        for b in books:
            BookCard(cards, b, self.open_book, self.images, self.ctx.fs.resolve(b["cover_path"])).pack(side="left", padx=(0, 14))

        if self.session.is_customer:
            box = ttk.Frame(self, style="Card.TFrame", padding=14)
            box.pack(anchor="w", pady=10)
            ttk.Label(box, text="Account Balance", style="Card.TLabel", font=(FONT, 13, "bold")).pack(anchor="w")
            bal = self.ctx.wallet.get_balance(self.session.user["user_id"])
            ttk.Label(box, text=f"${bal:,.2f}", style="Card.TLabel", font=(FONT, 22, "bold")).pack(anchor="w")
            ttk.Button(box, text="Open My Balance", command=lambda: self.app.show("wallet")).pack(anchor="w", pady=4)


# ---------------------------------------------------------------- Catalog (UC-04)
class CatalogScreen(Screen):
    def build(self):
        self.page = 1
        self.results = []
        ttk.Label(self, text="Browse & Search", style="H1.TLabel").pack(anchor="w", pady=(0, 8))

        controls = ttk.Frame(self)
        controls.pack(fill="x")
        ttk.Label(controls, text="Category").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, text="Search in").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(controls, text="Query (year: 1990 or 1990-2000)").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Label(controls, text="Sort").grid(row=0, column=3, sticky="w", padx=(10, 0))
        self.category = ttk.Combobox(controls, state="readonly", width=16,
                                     values=["All categories"] + self.ctx.catalog.categories())
        self.category.set(self.kwargs.get("category") or "All categories")
        self.category.grid(row=1, column=0)
        self.field = ttk.Combobox(controls, state="readonly", width=9, values=list(FIELDS))
        self.field.set(self.kwargs.get("field", "title"))
        self.field.grid(row=1, column=1, padx=(10, 0))
        self.query = tk.Entry(controls, width=30, font=(FONT, 13), highlightthickness=2,
                              highlightbackground="#cfd5e1", highlightcolor=NAVY)
        self.query.insert(0, self.kwargs.get("query", ""))
        self.query.grid(row=1, column=2, padx=(10, 0), ipady=3)
        self.query.bind("<Return>", lambda _e: self.run_search())
        self.sort = ttk.Combobox(controls, state="readonly", width=12,
                                 values=["title", "price", "weighted_avg", "pub_year"])
        self.sort.set("title")
        self.sort.grid(row=1, column=3, padx=(10, 0))
        ttk.Button(controls, text="Search", style="Primary.TButton",
                   command=self.run_search).grid(row=1, column=4, padx=(10, 0))
        ttk.Button(controls, text="Clear filters", command=self.clear).grid(row=1, column=5, padx=(6, 0))
        cam = ttk.Button(controls, text="📷 Cover", state="disabled")
        cam.grid(row=1, column=6, padx=(6, 0))
        Tooltip(cam, COVER_SEARCH_TIP)
        for cb in (self.category, self.sort):
            cb.bind("<<ComboboxSelected>>", lambda _e: self.run_search())

        self.status = ttk.Label(self, text="", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=(10, 4))
        self.grid_frame = ttk.Frame(self)
        self.grid_frame.pack(anchor="w", fill="both", expand=True)
        pager = ttk.Frame(self)
        pager.pack(fill="x", pady=(6, 0))
        self.prev_btn = ttk.Button(pager, text="‹ Prev", command=lambda: self.go(-1))
        self.prev_btn.pack(side="left")
        self.page_label = ttk.Label(pager, text="")
        self.page_label.pack(side="left", padx=10)
        self.next_btn = ttk.Button(pager, text="Next ›", command=lambda: self.go(1))
        self.next_btn.pack(side="left")
        if self.kwargs.get("focus_search"):
            self.query.focus_set()
        self.run_search()

    def clear(self):
        self.category.set("All categories")
        self.field.set("title")
        self.query.delete(0, "end")
        self.run_search()

    def run_search(self):
        self.banner.clear()
        self.query.configure(highlightbackground="#cfd5e1")
        cat = None if self.category.get() == "All categories" else self.category.get()
        q = self.query.get()
        try:
            if q.strip():
                self.results = self.ctx.catalog.search(q, self.field.get(), category=cat)
                if self.sort.get() != "title":   # search keeps best-match order unless a sort is picked
                    from bookorbit.services.catalog import SORT_KEYS
                    key, rev = SORT_KEYS[self.sort.get()]
                    self.results.sort(key=key, reverse=rev)
            else:
                self.results = self.ctx.catalog.browse(cat, self.sort.get())
        except ValueError as e:                  # UC-04 E2: invalid year range
            self.query.configure(highlightbackground=RED)
            self.banner.show(str(e), "error")
            self.results = []
        self.page = 1
        self.draw()

    def go(self, delta):
        self.page += delta
        self.draw()

    def draw(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.images.clear()
        total = len(self.results)
        pages = max(1, -(-total // rules.PAGE_SIZE))
        self.page = min(max(1, self.page), pages)
        if total == 0:                           # UC-04 E1
            box = ttk.Frame(self.grid_frame, padding=30)
            box.pack()
            ttk.Label(box, text="No books found", style="H2.TLabel").pack()
            ttk.Button(box, text="Clear filters", command=self.clear).pack(pady=8)
        for i, b in enumerate(self.ctx.catalog.page(self.results, self.page)):
            BookCard(self.grid_frame, b, self.open_book, self.images, self.ctx.fs.resolve(b["cover_path"])).grid(
                row=i // 6, column=i % 6, padx=(0, 12), pady=(0, 12))
        self.status.configure(text=f"{total} book(s) found")
        self.page_label.configure(text=f"Page {self.page} of {pages}")
        self.prev_btn.configure(state="normal" if self.page > 1 else "disabled")
        self.next_btn.configure(state="normal" if self.page < pages else "disabled")


# ---------------------------------------------------------------- Book details (UC-05)
class BookDetailScreen(Screen):
    def build(self):
        try:
            book = self.ctx.catalog.get_details(self.kwargs["book_id"], self.session)
        except NotFound as e:                    # UC-05 E1
            self.app.set_flash(f"{e} - returning to the catalog.", "error")
            self.after(1, lambda: self.app.show("catalog"))
            return
        ttk.Button(self, text="‹ Back to Browse", command=lambda: self.app.show("catalog")).pack(anchor="w")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=10)
        draw_cover(top, book, self.ctx.fs.resolve(book["cover_path"]), self.images).pack(side="left", anchor="n")

        info = ttk.Frame(top, padding=(18, 0))
        info.pack(side="left", fill="both", expand=True)
        ttk.Label(info, text=book["title"], style="H1.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"{book['author']}  ·  {book['category']}  ·  {book['pub_year']}",
                  style="Muted.TLabel").pack(anchor="w")
        rating = (f"{stars(book['weighted_avg'])}  {book['weighted_avg']:.2f} weighted average "
                  f"({book['rating_count']} ratings)" if book["rating_count"] else "No ratings yet")
        ttk.Label(info, text=rating, foreground="#b7791f").pack(anchor="w", pady=(4, 0))
        ttk.Label(info, text=f"${book['display_price']:.2f}", font=(FONT, 20, "bold")).pack(anchor="w", pady=4)
        ttk.Label(info, text=book["description"], wraplength=640, justify="left").pack(anchor="w")
        ttk.Label(info, text=f"Keywords: {book['keywords']}", style="Muted.TLabel").pack(anchor="w", pady=(4, 8))

        buttons = ttk.Frame(info)
        buttons.pack(anchor="w")
        if self.session.is_customer:
            # Role-based buttons (UC-05 step 5). Their actions arrive in later phases.
            for text, tip in (("Buy Now", "Purchasing (UC-08/09) arrives in Phase 2."),
                              ("Write Review", "Reviews (UC-10/11) arrive in Phase 2."),
                              ("Reading Companion", "The Smart Reading Companion (UC-14) arrives in Phase 3.")):
                b = ttk.Button(buttons, text=text, state="disabled")
                b.pack(side="left", padx=(0, 8))
                Tooltip(b, tip)
        elif self.session.role == rules.VISITOR:
            ttk.Label(buttons, text="Sign in to buy, review or read this book.", style="Muted.TLabel").pack()

        ttk.Label(self, text=f"Reviews ({len(book['reviews'])})", style="H2.TLabel").pack(anchor="w", pady=(8, 4))
        if not book["reviews"]:
            ttk.Label(self, text="No reviews yet", style="Muted.TLabel").pack(anchor="w")   # UC-05 E2
            return
        sf = ScrollFrame(self, height=260)
        sf.pack(fill="both", expand=True)
        for r in book["reviews"]:
            card = tk.Frame(sf.inner, bg=CARD, highlightbackground="#d9dee8", highlightthickness=1,
                            padx=10, pady=6)
            card.pack(fill="x", pady=3, padx=(0, 6))
            head = f"{r['author']}   {stars(r['rating'])}   {r['timestamp'][:10]}"
            if r["verified_buyer"]:
                head += "   ✔ Verified buyer"
            tk.Label(card, text=head, bg=CARD, font=(FONT, 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(card, text=r["display_text"], bg=CARD, anchor="w", justify="left",
                     wraplength=820).pack(fill="x")


# ---------------------------------------------------------------- Sign in (UC-02)
def pick_sample(method: str, data_dir: str) -> str:
    """MOCK capture: choose a photo / WAV file instead of the camera / microphone."""
    types = ([("Photos", "*.png *.jpg *.jpeg")] if method == FACE else [("WAV audio", "*.wav")])
    initial = Path(data_dir) / "samples"
    return filedialog.askopenfilename(title=f"Choose a {method.lower()} sample", filetypes=types,
                                      initialdir=str(initial if initial.exists() else data_dir))


class LoginScreen(Screen):
    def build(self):
        card = ttk.Frame(self, style="Card.TFrame", padding=24)
        card.pack(pady=30)
        ttk.Label(card, text="Sign in to BookOrbit AI", style="Card.TLabel",
                  font=(FONT, 20, "bold")).pack()
        ttk.Label(card, text="Customers and Super-Users verify with a face or voice sample (R1).",
                  style="Card.TLabel", foreground=MUTED).pack(pady=(2, 10))
        if self.ctx.bio.is_mock:
            tk.Label(card, text=self.ctx.bio.mode_label + ".\nDemo files are in data/samples/ "
                     "(e.g. alice_face.png, alice_voice.wav).", bg="#fff4e0", fg="#8a5300",
                     font=(FONT, 11), justify="left", padx=8, pady=6).pack(fill="x", pady=(0, 10))
        ttk.Label(card, text="Username", style="Card.TLabel", font=(FONT, 12, "bold")).pack(anchor="w")
        self.username = ttk.Entry(card, width=36, font=(FONT, 13))
        self.username.insert(0, self.kwargs.get("username", ""))
        self.username.pack(anchor="w", pady=(0, 10))
        self.method = tk.StringVar(value=FACE)
        tabs = ttk.Frame(card, style="Card.TFrame")
        tabs.pack(anchor="w")
        for m, label in ((FACE, "Face"), (VOICE, "Voice")):
            ttk.Radiobutton(tabs, text=label, value=m, variable=self.method,
                            command=self._reset_file).pack(side="left", padx=(0, 12))
        self.file = None
        self.file_label = ttk.Label(card, text="No sample chosen", style="Card.TLabel", foreground=MUTED)
        ttk.Button(card, text="Choose sample file…", command=self.choose).pack(anchor="w", pady=(8, 2))
        self.file_label.pack(anchor="w")
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(anchor="w", pady=(12, 4))
        ttk.Button(row, text="Capture & Verify", style="Primary.TButton", command=self.on_submit).pack(side="left")
        self.attempt = ttk.Label(row, text="", style="Card.TLabel", foreground=MUTED)
        self.attempt.pack(side="left", padx=10)
        link = ttk.Label(card, text="No account? Register", style="Card.TLabel", foreground=NAVY, cursor="hand2")
        link.pack(pady=(8, 0))
        link.bind("<Button-1>", lambda _e: self.app.show("register"))

    def _reset_file(self):
        self.file = None
        self.file_label.configure(text="No sample chosen")

    def choose(self):
        path = pick_sample(self.method.get(), self.ctx.fs.dir)
        if path:
            self.file = path
            self.file_label.configure(text=Path(path).name)

    def on_submit(self):
        self.banner.clear()
        if not self.file:
            self.banner.show("Choose a sample first.", "error")
            return
        try:
            session = self.ctx.auth.login(self.username.get(), self.method.get(), Path(self.file).read_bytes())
        except LoginError as e:
            msg = {"UNKNOWN_USER": "No account with that username.",                       # E1
                   "NO_MATCH": f"Not recognised - try again (attempt "
                               f"{rules.MAX_LOGIN_FAILS - e.attempts_left} of {rules.MAX_LOGIN_FAILS}).",  # E2
                   "LOCKED": f"Too many failed attempts. This username is locked for "
                             f"{e.minutes_left} more minute(s)."}[e.kind]                   # E3
            self.banner.show(msg, "error")
            if e.kind == "NO_MATCH":
                self.attempt.configure(text=f"Attempt {rules.MAX_LOGIN_FAILS - e.attempts_left} of "
                                            f"{rules.MAX_LOGIN_FAILS}")
        except (NoFaceError, NoVoiceError) as e:                                            # E5, not counted
            self.banner.show(f"{e} (not counted as a failed attempt).", "warn")
        except TemplateMissingError as e:                                                    # E6
            self.banner.show(str(e), "error")
        except OSError as e:
            self.banner.show(f"Could not read the file: {e}", "error")
        else:
            self.app.on_login(session)


# ---------------------------------------------------------------- Register (UC-01)
class RegisterScreen(Screen):
    FIELDS = (("full_name", "Full name"), ("username", "Username (3-20 letters, digits, _)"),
              ("email", "Email"))

    def build(self):
        self.face_tries = 0
        card = ttk.Frame(self, style="Card.TFrame", padding=24)
        card.pack(pady=20)
        ttk.Label(card, text="Create an account", style="Card.TLabel", font=(FONT, 20, "bold")).pack(anchor="w")
        if self.ctx.bio.is_mock:
            tk.Label(card, text=self.ctx.bio.mode_label + ".\nTry data/samples/new_user_face.png and "
                     "new_user_voice.wav.", bg="#fff4e0", fg="#8a5300", font=(FONT, 11),
                     justify="left", padx=8, pady=6).pack(fill="x", pady=(6, 10))
        self.entries, self.errors = {}, {}
        for key, label in self.FIELDS:
            ttk.Label(card, text=label, style="Card.TLabel", font=(FONT, 12, "bold")).pack(anchor="w")
            e = tk.Entry(card, width=38, font=(FONT, 13), highlightthickness=2,
                         highlightbackground="#cfd5e1", highlightcolor=NAVY)
            e.pack(anchor="w")
            err = ttk.Label(card, text="", style="Error.TLabel", background=CARD)
            err.pack(anchor="w", pady=(0, 6))
            self.entries[key], self.errors[key] = e, err
        self.face = self.voice = None
        self.face_label = ttk.Label(card, text="Face photo: none", style="Card.TLabel", foreground=MUTED)
        self.voice_label = ttk.Label(card, text="Voice clip (optional): none", style="Card.TLabel", foreground=MUTED)
        ttk.Button(card, text="Capture Face (choose photo)…", command=lambda: self.choose(FACE)).pack(anchor="w")
        self.face_label.pack(anchor="w", pady=(0, 6))
        ttk.Button(card, text="Record Voice (choose WAV)…", command=lambda: self.choose(VOICE)).pack(anchor="w")
        self.voice_label.pack(anchor="w")
        self.errors["biometric"] = ttk.Label(card, text="", style="Error.TLabel", background=CARD)
        self.errors["biometric"].pack(anchor="w", pady=(0, 6))
        ttk.Button(card, text="Create account", style="Primary.TButton", command=self.on_submit).pack(anchor="w", pady=6)

    def choose(self, method):
        path = pick_sample(method, self.ctx.fs.dir)
        if not path:
            return
        if method == FACE:
            self.face = path
            self.face_label.configure(text=f"Face photo: {Path(path).name}")
        else:
            self.voice = path
            self.voice_label.configure(text=f"Voice clip: {Path(path).name}")

    def on_submit(self):
        self.banner.clear()
        for key, err in self.errors.items():
            err.configure(text="")
            if key in self.entries:
                self.entries[key].configure(highlightbackground="#cfd5e1")
        try:
            user = self.ctx.auth.register(
                self.entries["full_name"].get(), self.entries["username"].get(), self.entries["email"].get(),
                Path(self.face).read_bytes() if self.face else None,
                Path(self.voice).read_bytes() if self.voice else None)
        except RegistrationError as e:                       # E1 / E2: outline the invalid fields
            for key, reason in e.problems.items():
                self.errors[key].configure(text=reason)
                if key in self.entries:
                    self.entries[key].configure(highlightbackground=RED)
            self.banner.show("Please fix the highlighted fields. Nothing was saved.", "error")
        except (NoFaceError, NoVoiceError) as e:            # E3: retake, up to 3 tries
            self.face_tries += 1
            if self.face_tries >= rules.MAX_FACE_RETRIES:
                self.app.set_flash("Registration cancelled after 3 unsuccessful captures.", "error")
                self.app.show("home")
                return
            self.banner.show(f"{e} - please retake (try {self.face_tries} of {rules.MAX_FACE_RETRIES}).", "warn")
        except OSError as e:                                  # E5: write error, nothing kept
            self.banner.show(f"Could not create the account: {e}", "error")
        else:
            self.app.set_flash("Account created - please sign in.", "ok")
            self.app.build_sidebar("Sign In")
            self.app.show("login", username=user["username"])


# ---------------------------------------------------------------- My Balance (UC-07 read side)
class WalletScreen(Screen):
    def build(self):
        if not self.session.is_customer:
            ttk.Label(self, text="My Balance is for customers.", style="H2.TLabel").pack(anchor="w")
            return
        u = self.session.user
        ttk.Label(self, text="My Balance", style="H1.TLabel").pack(anchor="w", pady=(0, 10))
        top = ttk.Frame(self)
        top.pack(fill="x")
        box = ttk.Frame(top, style="Card.TFrame", padding=16)
        box.pack(side="left", fill="y")
        ttk.Label(box, text="Current balance", style="Card.TLabel", foreground=MUTED).pack(anchor="w")
        bal = self.ctx.wallet.get_balance(u["user_id"])
        ttk.Label(box, text=f"${bal:,.2f}", style="Card.TLabel", font=(FONT, 28, "bold"),
                  foreground=RED if bal < 0 else "black").pack(anchor="w")
        status_color = RED if u["status"] == rules.SUSPENDED else "#1e8449"
        ttk.Label(box, text=f"Status: {u['status']}    Role: {u['role']}    Warnings: {u['warnings']}",
                  style="Card.TLabel", foreground=status_color).pack(anchor="w")
        dep = ttk.Frame(top, style="Card.TFrame", padding=16)
        dep.pack(side="left", fill="both", expand=True, padx=(12, 0))
        ttk.Label(dep, text="Add funds", style="Card.TLabel", font=(FONT, 13, "bold")).pack(anchor="w")
        row = ttk.Frame(dep, style="Card.TFrame")
        row.pack(anchor="w", pady=4)
        ttk.Entry(row, width=12, state="disabled").pack(side="left")
        btn = ttk.Button(row, text="Add Funds", state="disabled")
        btn.pack(side="left", padx=6)
        Tooltip(btn, "Deposits (UC-07) arrive in Phase 2.")
        ttk.Label(dep, text="Suspended accounts: deposit until the balance is >= $0, then a Super-User "
                            "can reactivate the account (R8).", style="Card.TLabel", foreground=MUTED,
                  wraplength=420).pack(anchor="w")

        ttk.Label(self, text="Ledger", style="H2.TLabel").pack(anchor="w", pady=(16, 4))
        tree = ttk.Treeview(self, columns=("date", "type", "desc", "amount", "balance"), show="headings", height=12)
        for col, label, w in (("date", "Date", 170), ("type", "Type", 100), ("desc", "Description", 320),
                              ("amount", "Amount", 110), ("balance", "Balance", 110)):
            tree.heading(col, text=label)
            tree.column(col, width=w, anchor="w")
        for t in self.ctx.wallet.get_ledger(u["user_id"]):
            tree.insert("", "end", values=(t["timestamp"], t["type"], t["note"],
                                           f"{t['amount']:+,.2f}", f"{t['balance_after']:,.2f}"))
        tree.pack(fill="x")


# ---------------------------------------------------------------- not built yet
class PlaceholderScreen(Screen):
    def build(self):
        ttk.Label(self, text=self.kwargs.get("title", "Coming soon"), style="H1.TLabel").pack(anchor="w")
        tk.Label(self, text=f"STUB - this screen ({self.kwargs.get('uc', '')}) arrives in Phase "
                            f"{self.kwargs.get('phase', '?')}.", bg="#fff4e0", fg="#8a5300",
                 font=(FONT, 13), padx=12, pady=10, anchor="w").pack(fill="x", pady=12)
