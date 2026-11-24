"""RecommendationEngine - the three Home-page books (SRS 4.10, UC-03, UC-06, R3, R4)."""
from bookorbit import rules


def popularity(book: dict) -> int:
    """R3: browse_count + 3 x purchase_count."""
    return book["browse_count"] + rules.POPULAR_PURCHASE_WEIGHT * book["purchase_count"]


class RecommendationEngine:
    def __init__(self, fs):
        self.fs = fs

    def home_books(self, session) -> tuple[str, list[dict]]:
        k = rules.HOME_BOOK_COUNT
        if session.role in (rules.VISITOR, rules.SU):
            return "Top 3 Most Popular", self.top_popular(k)
        recs = self.personalized(session.user["user_id"], k)
        if not recs:                                    # UC-06 E1: no history yet
            return "Popular right now", self.top_popular(k)
        return "Recommended for You", recs

    def top_popular(self, k: int = 3, exclude=frozenset()) -> list[dict]:
        """Ties broken by weighted average (desc), then title (UC-03 E3)."""
        books = [b for b in self.fs.load("books") if b["book_id"] not in exclude]
        books.sort(key=lambda b: (-popularity(b), -b["weighted_avg"], b["title"].lower()))
        return books[:k]                                # UC-03 E1/E2: fewer / none

    def personalized(self, user_id: str, k: int = 3) -> list[dict]:
        """UC-06 / R4. STUB until Phase 3: returns [] so customers see popular books
        under "Popular right now" (the SRS's own no-history fallback, UC-06 E1)."""
        return []
