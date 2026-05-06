from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="AttackScope AI")


@app.get("/v1/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
