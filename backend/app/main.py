from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title="SONIQWERK API",
    version="2.0.0",
    description="AI agent for electronic music production",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "2.0.0"}


from app.api.v1.chat import router as chat_router
app.include_router(chat_router, prefix="/v1", tags=["chat"])
