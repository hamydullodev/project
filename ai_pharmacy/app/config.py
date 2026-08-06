import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

DATABASE_PATH = str(BASE_DIR / os.getenv("DATABASE_PATH", "app/database/pharmacy.db"))
MEMORY_DB_PATH = str(BASE_DIR / os.getenv("MEMORY_DB_PATH", "app/memory/checkpoints.sqlite"))

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
