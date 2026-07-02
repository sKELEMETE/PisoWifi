
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.api import api_router
from core.exceptions import register_exception_handlers

app = FastAPI(
    title="PisoWiFi API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
register_exception_handlers(app)

@app.get("/")
def root():
    return {
        "success": True,
        "message": "PisoWiFi Backend Running"
    }
