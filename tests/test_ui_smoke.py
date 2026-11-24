"""Opens every Phase 1 screen for every role in a real Tk window (then closes it).
Skipped automatically when no display is available."""
import tkinter as tk
import unittest

from bookorbit import rules
from bookorbit.ai.biometrics import FACE
from bookorbit.ui.main_window import SIDEBAR, MainWindow
from seed import make_face_photo
from tests.helpers import TempStoreCase


class UISmokeTests(TempStoreCase):
    def setUp(self):
        super().setUp()
        for i in range(15):
            self.add_book(title=f"Book {i:02d}", browse_count=i)
        self.ctx.auth.register("Pat", "pat", "p@x.com", make_face_photo("pat", 1, 0))
        try:
            self.win = MainWindow(self.ctx)
        except tk.TclError as e:
            self.skipTest(f"no display: {e}")
        self.win.withdraw()
        self.assertTrue(self.ctx.ai_ready.wait(30))      # background AI indexing (SRS 4.24)

    def tearDown(self):
        if hasattr(self, "win"):
            self.ctx.ai_ready.wait(30)                   # never delete data/ under the indexing thread
            self.win.destroy()
        super().tearDown()

    def visit_all(self, role):
        for _label, screen, kwargs in SIDEBAR[role]:
            if screen != "logout":
                self.win.show(screen, **kwargs)
                self.win.update()
        self.win.show("book", book_id="B-0001")
        self.win.update()
        self.win.show("catalog", query="2015-2000", field="year")   # invalid range -> banner
        self.win.update()
        self.assertIn("year", self.win.current.banner.text)

    def test_all_roles_in_one_window(self):
        # One test on purpose: on macOS, creating a second Tk root in the same
        # process after destroying the first can hang inside update().
        self.visit_all(rules.VISITOR)
        session = self.ctx.auth.login("pat", FACE, make_face_photo("pat", 1, 1))
        self.win.on_login(session)
        self.visit_all(rules.RC)
        self.phase2_flows()
        self.ctx.fs.update("users", "username", "pat", {"status": rules.SUSPENDED})
        session.refresh()
        self.win.show("catalog")                     # R8: redirected to the wallet
        self.assertEqual(type(self.win.current).__name__, "WalletScreen")

    def screen(self):
        return type(self.win.current).__name__

    def buy(self, book_id):
        self.win.show("book", book_id=book_id)
        self.win.current.on_buy(self.ctx.fs.find("books", "book_id", book_id))
        self.win.update()

    def phase2_flows(self):
        """UC-07..UC-11 through the real screens. Dialogs are answered by stubs."""
        self.win.confirm = lambda *_a: True
        self.win.inform = lambda *_a: None
        self.taboo("dumb", "stupid", "lame", "darn")
        # UC-07: invalid then valid deposit
        self.win.show("wallet")
        self.win.current.amount.insert(0, "12.345")
        self.win.current.on_deposit()
        self.assertIn("valid amount", self.win.current.banner.text)
        self.win.current.amount.delete(0, "end")
        self.win.current.amount.insert(0, "100")
        self.win.current.on_deposit()
        self.assertIn("100.00", self.win.current.banner.text)
        # UC-08: Buy Now -> receipt -> owned
        self.buy("B-0001")
        self.assertIn("You bought", self.win.current.banner.text)
        self.assertEqual(self.screen(), "BookDetailScreen")
        # UC-10: masked review
        detail = self.win.current
        detail.toggle_review_form()
        detail.stars_var.set(5)
        detail.review_text.insert("1.0", "Not dumb at all, great book.")
        detail.on_review(self.ctx.fs.find("books", "book_id", "B-0001"))
        self.win.update()
        self.assertIn("1 word masked", self.win.current.banner.text)
        # R5: 4th purchase promotes; sidebar now says VIP
        for bid in ("B-0002", "B-0003", "B-0004"):
            self.buy(bid)
        self.assertEqual(self.win.session.role, rules.VC)
        self.assertIn("VIP", self.win.current.banner.text)
        for name in ("orders", "my_reviews", "home"):
            self.win.show(name)
            self.win.update()
        # UC-11 E1: blocked review demotes the VIP
        self.win.show("book", book_id="B-0005")
        detail = self.win.current
        detail.stars_var.set(1)
        detail.review_text.insert("1.0", "Dumb, stupid, lame and darn boring.")
        detail.on_review(self.ctx.fs.find("books", "book_id", "B-0005"))
        self.win.update()
        self.assertEqual(self.win.session.role, rules.RC)
        self.assertIn("blocked", self.win.current.banner.text)
        # R7 / UC-08 E2: fine below $0 -> suspended -> wallet-only
        self.ctx.fs.update("users", "username", "pat", {"balance": 0.0})
        self.buy("B-0006")
        self.assertEqual(self.screen(), "WalletScreen")
        self.assertTrue(self.win.session.wallet_only)
        self.assertIn("SUSPENDED", self.win.current.banner.text)
        # R8: deposit back to >= $0 shows the reactivation note; an SU reopens (Phase 4 screen)
        self.win.current.amount.insert(0, "1")
        self.win.current.on_deposit()
        self.assertIn("reactivate", self.win.current.banner.text)
        self.ctx.status.reopen("U-0000", self.win.session.user["user_id"])
        self.win.refresh_chrome()


if __name__ == "__main__":
    unittest.main()
