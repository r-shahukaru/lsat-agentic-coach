from dotenv import load_dotenv
import os

# Load .env once for the entire app
load_dotenv()

# Optional: fail fast if key is missing
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY not set. Check your .env file.")
