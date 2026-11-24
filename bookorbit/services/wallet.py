"""WalletService (SRS 4.11). Phase 1 implements the read side only, because a
suspended customer who signs in (UC-02 E4, R8) lands on the wallet. Deposits,
fines and purchases arrive in Phase 2 (UC-07, UC-08)."""


class WalletService:
    def __init__(self, fs):
        self.fs = fs

    def get_balance(self, user_id: str) -> float:
        return self.fs.find("users", "user_id", user_id)["balance"]

    def get_ledger(self, user_id: str) -> list[dict]:
        """Every deposit, purchase and fine of the user, newest first."""
        txns = [t for t in self.fs.load("transactions") if t["user_id"] == user_id]
        return sorted(txns, key=lambda t: t["timestamp"], reverse=True)
