"""Dev entrypoint: starts uvicorn with --reload"""
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
