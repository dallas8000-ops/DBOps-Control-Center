from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth_utils import hash_password, verify_password
from app.db import Base
from app.demo_public import lock_public_demo
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


def test_seed_upsert_updates_password_when_requested() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        original = "SeedUser123!"
        user = User(
            email="rotate@example.com",
            hashed_password=hash_password(original),
            role="Viewer",
            is_active=True,
        )
        db.add(user)
        db.commit()

        updated = _upsert_user(
            db,
            email="rotate@example.com",
            role="Viewer",
            password="RotateMe456!",
            update_password=True,
        )
        db.commit()
        db.refresh(updated)

        assert verify_password("RotateMe456!", updated.hashed_password)
        assert not verify_password(original, updated.hashed_password)
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_lock_public_demo_disables_admin_seed_users(monkeypatch) -> None:
    monkeypatch.setenv("SEED_VIEWER_PASSWORD", "ViewerOnly123!")

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        known = hash_password("dba-b91b26064ea0a8!")
        db.add_all(
            [
                User(email="barney@example.com", hashed_password=known, role="DBA", is_active=True),
                User(email="analyst@example.com", hashed_password=known, role="Analyst", is_active=True),
                User(email="viewer@example.com", hashed_password=known, role="Viewer", is_active=True),
            ]
        )
        db.commit()

        results = lock_public_demo(db=db)
        db.expire_all()

        dba = db.query(User).filter(User.email == "barney@example.com").one()
        analyst = db.query(User).filter(User.email == "analyst@example.com").one()
        viewer = db.query(User).filter(User.email == "viewer@example.com").one()

        assert dba.is_active is False
        assert analyst.is_active is False
        assert viewer.is_active is True
        assert not verify_password("dba-b91b26064ea0a8!", dba.hashed_password)
        assert verify_password("ViewerOnly123!", viewer.hashed_password)
        assert "disabled" in results["barney@example.com"]
        assert "SEED_VIEWER_PASSWORD" in results["viewer@example.com"]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
