import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from db.sqlite import init_db

if __name__ == "__main__":
    init_db("backend/data/projects.db")
    print("Database seeded.")
