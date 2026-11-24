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

    def tearDown(self):
        if hasattr(self, "win"):
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
        self.ctx.fs.update("users", "username", "pat", {"status": rules.SUSPENDED})
        session.refresh()
        self.win.show("catalog")                     # R8: redirected to the wallet
        self.assertEqual(type(self.win.current).__name__, "WalletScreen")


if __name__ == "__main__":
    unittest.main()
