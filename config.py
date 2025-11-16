import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY in .env file")
if not TAVILY_API_KEY:
    raise ValueError("Please set TAVILY_API_KEY in .env file")
if not SERPER_API_KEY:
    raise ValueError("Please set SERPER_API_KEY in .env file")
if not OPENAI_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY in .env file")  