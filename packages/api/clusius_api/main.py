from fastapi import FastAPI

from clusius_api.routes.runs import router as runs_router

app = FastAPI(title="Clusius API", version="0.1.0")
app.include_router(runs_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
