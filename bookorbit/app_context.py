"""Builds the FileStore and all services once (SRS 4.24 MainWindow.run step 1)."""
from dataclasses import dataclass

from bookorbit.ai.biometrics import BiometricEngine, get_engine
from bookorbit.ai.recommendations import RecommendationEngine
from bookorbit.config import load_config
from bookorbit.persistence.filestore import FileStore
from bookorbit.services.auth import AuthService
from bookorbit.services.catalog import CatalogService
from bookorbit.services.ratings import RatingService
from bookorbit.services.reviews import ReviewService
from bookorbit.services.wallet import WalletService


@dataclass
class AppContext:
    config: dict
    fs: FileStore
    bio: BiometricEngine
    auth: AuthService
    reviews: ReviewService
    ratings: RatingService
    catalog: CatalogService
    recs: RecommendationEngine
    wallet: WalletService


def build_context(config: dict | None = None, data_dir: str | None = None) -> AppContext:
    cfg = config or load_config()
    fs = FileStore(data_dir or cfg["DATA_DIR"])
    bio = get_engine(fs, cfg["BIOMETRIC_MODE"])
    reviews = ReviewService(fs)
    return AppContext(
        config=cfg, fs=fs, bio=bio, auth=AuthService(fs, bio), reviews=reviews,
        ratings=RatingService(fs), catalog=CatalogService(fs, reviews),
        recs=RecommendationEngine(fs), wallet=WalletService(fs))
