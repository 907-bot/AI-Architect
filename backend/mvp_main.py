from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import router as mvp_router


app = FastAPI(title="AI Architect MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mvp_router, prefix="/api", tags=["mvp-pipeline"])
app.include_router(mvp_router, tags=["mvp-pipeline"])
app.mount("/exports", StaticFiles(directory="exports"), name="exports")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-architect-mvp"}
