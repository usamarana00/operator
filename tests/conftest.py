import os
import sys

# Tests must never need real keys.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
