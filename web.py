import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.radar_engine import analyze_token_contract, build_bsc_watchlist

app = FastAPI(title="Binance Anti-Rug Radar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class AnalyzeRequest(BaseModel):
    token_address: str
    chain: str = "bsc"


@app.post("/api/analyze")
async def analyze_token(req: AnalyzeRequest):
    address = req.token_address.strip()
    if not address.startswith("0x") or len(address) != 42:
        return JSONResponse(status_code=400, content={"error": "无效的合约地址格式，应为 0x 开头的 42 位地址。"})

    try:
        return analyze_token_contract(address, requested_chain=req.chain.strip())
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "分析失败", "detail": str(exc)})


@app.get("/api/watchlist")
async def watchlist():
    try:
        return build_bsc_watchlist(limit=5)
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "观察名单生成失败", "detail": str(exc)})


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


if __name__ == "__main__":
    import uvicorn

    print("启动 Web 服务: http://localhost:8000")
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
