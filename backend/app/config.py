import os

# Comma-separated list of allowed CORS origins.
# Set CORS_ORIGINS in your environment for production.
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
