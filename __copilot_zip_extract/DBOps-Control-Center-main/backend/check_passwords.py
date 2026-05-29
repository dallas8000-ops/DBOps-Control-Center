#!/usr/bin/env python
"""Check password hashes in database."""
import os
os.environ['DATABASE_URL'] = 'sqlite:///./dbops_local.db'

from app.db import SessionLocal
from app.models import User
from app.auth_utils import verify_password, hash_password

db = SessionLocal()
users = db.query(User).all()
for user in users:
    print(f"\n{user.email} ({user.role}):")
    print(f"  hashed_password: {user.hashed_password[:50]}...")
    
    # Test the password we tried
    if verify_password("DemoPass123!", user.hashed_password):
        print("  ✓ DemoPass123! is CORRECT")
    else:
        print("  ✗ DemoPass123! is WRONG")
        # Set the correct password
        new_hash = hash_password("DemoPass123!")
        user.hashed_password = new_hash
        db.add(user)

db.commit()
db.close()
print("\n✓ Passwords updated in database")
