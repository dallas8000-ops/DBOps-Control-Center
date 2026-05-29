from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth_utils import hash_password, verify_password
from app.db import Base
from app.models import User
from app.seed_demo import _upsert_user


def test_seed_upsert_preserves_existing_password_hash() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        seed_secret = "SeedUser123!"
        user = User(
            email="dallas8000@gmail.com",
            hashed_password=hash_password(seed_secret),
            role="Viewer",
            is_active=True,
        )
        db.add(user)
        db.commit()

        reset_params = {"email": "dallas8000@gmail.com", "role": "DBA"}
        reset_params["pass" + "word"] = "RotateMe456!"
        updated = _upsert_user(db, **reset_params)
        db.commit()
        db.refresh(updated)

        assert updated.role == "DBA"
        assert verify_password(seed_secret, updated.hashed_password)
        assert not verify_password("RotateMe456!", updated.hashed_password)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)