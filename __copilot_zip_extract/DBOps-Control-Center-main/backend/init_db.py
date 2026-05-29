#!/usr/bin/env python
"""Initialize SQLite database schema and seed demo data."""
import os
import sys

# Set SQLite database URL
os.environ['DATABASE_URL'] = 'sqlite:///./dbops_local.db'

from app.db import engine, Base
from app.models import *
from app.seed_demo import seed_demo_data

# Create all tables
Base.metadata.create_all(bind=engine)
print("✓ Database tables created")

# Set demo passwords
os.environ['SEED_DBA_PASSWORD'] = 'DemoPass123!'
os.environ['SEED_ANALYST_PASSWORD'] = 'DemoPass123!'
os.environ['SEED_VIEWER_PASSWORD'] = 'DemoPass123!'

# Seed demo data
try:
    seed_demo_data()
    print("✓ Demo data seeded")
except Exception as e:
    print(f"Error seeding data: {e}")
    sys.exit(1)
