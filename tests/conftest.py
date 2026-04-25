import os
import sys
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
