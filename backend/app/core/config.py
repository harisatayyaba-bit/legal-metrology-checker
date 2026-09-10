from pydantic import BaseModel
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "Legal Metrology Packaged Commodities Compliance Checker"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]
    # Maximum upload size in bytes (e.g. 15MB)
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

settings = Settings()
