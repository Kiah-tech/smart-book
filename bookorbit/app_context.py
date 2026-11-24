"""Builds the FileStore and all services once (SRS 4.24 MainWindow.run step 1).

Wiring follows the collaboration diagram (SRS Figure 1): StatusManager is shared
by WalletService, PurchaseService and WarningService, because it is the only
class allowed to change a role or status.
"""
from dataclasses import dataclass

from bookorbit.ai.biometrics import BiometricEngine, get_engine
from bookorbit.ai.llm import LLMClient, get_llm
from bookorbit.ai.recommendations import RecommendationEngine
from bookorbit.config import load_config
from bookorbit.persistence.filestore import FileStore
from bookorbit.services.auth import AuthService
from bookorbit.services.catalog import CatalogService
from bookorbit.services.moderation import ModerationEngine, TabooService
from bookorbit.services.purchases import PurchaseService
from bookorbit.services.ratings import RatingService
from bookorbit.services.reviews import ReviewService
from bookorbit.services.status import StatusManager
from bookorbit.services.wallet import WalletService
from bookorbit.services.warnings import WarningService


@dataclass
class AppContext:
    config: dict
    fs: FileStore
    bio: BiometricEngine
    llm: LLMClient                 # SRS 4.22 (mock / real / offline)
    auth: AuthService
    status: StatusManager
    wallet: WalletService
    purchases: PurchaseService
    taboo: TabooService
    moderation: ModerationEngine
    warnings: WarningService
    ratings: RatingService
    reviews: ReviewService
    catalog: CatalogService
    recs: RecommendationEngine


def build_context(config: dict | None = None, data_dir: str | None = None) -> AppContext:
    cfg = config or load_config()
    fs = FileStore(data_dir or cfg["DATA_DIR"])
    bio = get_engine(fs, cfg["BIOMETRIC_MODE"])
    llm = get_llm(cfg)
    status = StatusManager(fs)
    wallet = WalletService(fs, status)
    purchases = PurchaseService(fs, wallet, status)
    taboo = TabooService(fs)
    moderation = ModerationEngine(taboo)
    warnings = WarningService(fs, status)
    ratings = RatingService(fs)
    reviews = ReviewService(fs, moderation, warnings, ratings, purchases)
    return AppContext(
        config=cfg, fs=fs, bio=bio, llm=llm, auth=AuthService(fs, bio), status=status, wallet=wallet,
        purchases=purchases, taboo=taboo, moderation=moderation, warnings=warnings, ratings=ratings,
        reviews=reviews, catalog=CatalogService(fs, reviews, purchases=purchases),
        recs=RecommendationEngine(fs))
