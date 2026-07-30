from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clusius_api.routes.runs import router as runs_router
from clusius_api.settings import ApiSettings

app = FastAPI(title="Clusius API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ApiSettings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(runs_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
