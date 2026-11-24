"""ReviewService (SRS 4.14). Phase 1 implements only the read side used by
UC-05 (list_reviews); submit() with moderation arrives in Phase 2 (UC-10)."""


class ReviewService:
    def __init__(self, fs):
        self.fs = fs

    def list_reviews(self, book_id: str) -> list[dict]:
        """Published reviews, newest first, with the author's name.
        Only display_text (masked) is ever shown; original_text never is."""
        names = {u["user_id"]: u["full_name"] for u in self.fs.load("users")}
        rs = [dict(r) for r in self.fs.load("reviews")
              if r["book_id"] == book_id and r["status"] == "PUBLISHED"]
        for r in rs:
            r["author"] = names.get(r["user_id"], "Former customer")
        return sorted(rs, key=lambda r: r["timestamp"], reverse=True)
