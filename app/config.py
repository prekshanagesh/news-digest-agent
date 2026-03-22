import os
from dotenv import load_dotenv
load_dotenv()
NEWSAPI_KEY=os.getenv("NEWSAPI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GMAIL_SENDER=os.getenv("GMAIL_SENDER")
DATABASE_PATH=os.getenv("DATABASE_PATH")
DIGEST_RECIPIENT = os.getenv("DIGEST_RECIPIENT")