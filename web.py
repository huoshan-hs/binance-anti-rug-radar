"""
Web 版本的防FOMO杀猪盘 Agent - 后端服务
使用 FastAPI 提供 REST 接口，复用现有的风控逻辑。
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import traceback
import json
import asyncio

# 复用原有的工具逻辑
from src.tools import execute_tool
from src.llm_agent import LLMAgent

app = FastAPI(title="Anti-FOMO Agent Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

agent = LLMAgent()

class AnalyzeRequest(BaseModel):
    token_address: str
    chain: str = "bsc"


@app.post("/api/analyze")
async def analyze_token(req: AnalyzeRequest):
    """
    执行 5 维风控扫描并返回结构化 JSON 数据。
    为了在前端单独展示卡片，这里我们直接调用 tools 获取原始数据，
    如果你配置了 OpenAI，也会返回一份 LLM 的综合分析文本。
    """
    addr = req.token_address.strip()
    chain = req.chain.strip()
    
    if not addr.startswith("0x") or len(addr) != 42:
        return JSONResponse(status_code=400, content={"error": "无效的合约地址格式 (应为 0x 开头的 42 位字符)"})

    try:
        # 并发获取各个维度的数据 (提速)
        loop = asyncio.get_event_loop()
        
        # 包装同步的 Execute 工具调用为异步
        def fetch_tool(name, args):
            try:
                res = execute_tool(name, args)
                return json.loads(res)
            except Exception as e:
                return {"error": str(e)}

        results = await asyncio.gather(
            loop.run_in_executor(None, fetch_tool, "analyze_contract_security", {"token_address": addr, "chain": chain}),
            loop.run_in_executor(None, fetch_tool, "check_holder_concentration", {"token_address": addr, "chain": chain}),
            loop.run_in_executor(None, fetch_tool, "check_liquidity_and_market", {"token_address": addr}),
            loop.run_in_executor(None, fetch_tool, "check_smart_money_flow", {"token_address": addr, "chain": chain}),
        )

        audit, holders, market, smart = results
        
        # 判断全局维度危险级别 (极简版红线逻辑抽离到前端展示)
        red_flags = []
        warnings = []
        
        # 1. 审计
        if audit.get("is_honeypot"): red_flags.append("☠️ 发现蜜罐 (Honeypot)")
        if audit.get("is_mintable"): red_flags.append("☠️ 合约允许无限增发")
        if audit.get("sell_tax_percent", 0) > 10: red_flags.append(f"🔴 卖出税极高 ({audit.get('sell_tax_percent')}%)")
        if not audit.get("is_open_source", True): warnings.append("🟡 合约未开源")
        
        # 2. 持仓
        t10 = holders.get('top_10_total_percent', 0)
        if t10 > 50: red_flags.append(f"🔴 筹码高度集中 (Top10: {t10}%)")
        for lp in holders.get("lp_holders", []):
            if lp.get("percent", 0) > 90 and not lp.get("is_locked"):
                red_flags.append("🔴 LP 未锁仓且高度集中，准备 Rug")
                
        # 3. 流动性
        liq = market.get("liquidity_usd", 0)
        if liq < 10000 and "error" not in market:
            red_flags.append(f"🔴 流动性极低 (${liq:,.0f})")
            
        # 4. 社交与聪明钱
        for sig in smart.get("signals", []):
            if "高风险" in sig:
                red_flags.append(f"🔴 {sig}")
            elif "中风险" in sig or "🟡" in sig:
                warnings.append(sig)

        risk_level = "HIGH" if red_flags else ("MEDIUM" if len(warnings) >= 3 else "LOW")
        
        # 生成 AI 建议 (如果开启了 LLM)
        ai_summary = ""
        if agent.has_llm:
            try:
                ai_summary = await loop.run_in_executor(None, agent.process, f"分析此地址的风险并给出简短建议：{addr}")
            except:
                ai_summary = "AI 分析暂不可用"

        # 优先使用市场数据(含元数据)中的代币名称和符号
        token_name = market.get("name") or audit.get("token_name") or "Unknown"
        token_symbol = market.get("symbol") or audit.get("token_symbol") or "N/A"

        return {
            "token": {"address": addr, "chain": chain, "name": token_name, "symbol": token_symbol},
            "risk_level": risk_level,
            "red_flags": red_flags,
            "warnings": warnings,
            "data": {
                "audit": audit,
                "holders": holders,
                "market": market,
                "smart": smart
            },
            "ai_summary": ai_summary
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "服务器内部错误分析失败", "detail": str(e)})


@app.get("/")
async def root():
    # 自动重定向到静态主页
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 Web 服务器: http://localhost:8000")
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
