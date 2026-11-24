"""Test fixtures: a fresh temporary data folder per test, plus sample generators."""
import shutil
import tempfile
import unittest

from bookorbit.app_context import build_context
from bookorbit.config import DEFAULTS
from seed import make_face_photo, make_voice


class TempStoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bookorbit_test_")
        self.ctx = build_context(dict(DEFAULTS, DATA_DIR=self.tmp))
        self.fs = self.ctx.fs

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # samples (MOCK biometrics)
    @staticmethod
    def face(person="pat", variant=0, faces=1):
        return make_face_photo(person, faces, variant)

    @staticmethod
    def voice(pitch=220, seconds=3.0, variant=0):
        return make_voice(pitch, seconds, variant)

    def add_book(self, **over):
        b = {"book_id": self.fs.next_id("books", "B"), "title": "Book", "author": "Author A",
             "category": "Fiction", "keywords": "family, secrets", "pub_year": 2000, "price": 10.0,
             "description": "A story.", "cover_path": None, "cover_vec_path": None, "text_path": None,
             "added_by": "U-0001", "browse_count": 0, "purchase_count": 0, "rating_count": 0,
             "weighted_avg": 0.0, "list_status": "NONE", "indexed": False, "added_at": "2026-11-01 10:00:00"}
        b.update(over)
        return self.fs.append("books", b)
