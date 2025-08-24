"""Run script for the Claude Relay Station"""

import uvicorn
from app.core.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
        access_log=True,
        workers=1 if settings.is_development else 4,
    )