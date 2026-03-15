import json
from typing import Any, Dict, List

from src.binance_skills_client import BinanceSkillsClient

client = BinanceSkillsClient()

SUPPORTED_CHAINS = ["eth", "bsc", "base", "solana"]
MARKET_CHAINS = ["bsc", "base", "solana"]
SIGNAL_CHAINS = ["bsc", "solana"]

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_contract_security",
            "description": "Use Binance Skills Hub token audit to inspect smart-contract risk, taxes, verification state, and key red flags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {"type": "string", "description": "Token contract address, e.g. 0x..."},
                    "chain": {"type": "string", "enum": SUPPORTED_CHAINS, "description": "Target chain."},
                },
                "required": ["token_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_holder_concentration",
            "description": "Use Binance Skills Hub token market data, plus GoPlus fallback when needed, to inspect holder concentration and creator exposure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {"type": "string", "description": "Token contract address."},
                    "chain": {"type": "string", "enum": SUPPORTED_CHAINS, "description": "Target chain."},
                },
                "required": ["token_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_liquidity_and_market",
            "description": "Use Binance Skills Hub token dynamic info to retrieve price, liquidity, volume, price change, and holder metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {"type": "string", "description": "Token contract address."},
                    "chain": {"type": "string", "enum": MARKET_CHAINS, "description": "Target chain."},
                },
                "required": ["token_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_smart_money_flow",
            "description": "Use Binance Skills Hub trading-signal to check whether smart money is accumulating or exiting the token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {"type": "string", "description": "Token contract address."},
                    "chain": {"type": "string", "enum": SIGNAL_CHAINS, "description": "Target chain."},
                },
                "required": ["token_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_to_binance_square",
            "description": "Publish a text-only post to Binance Square using the official Square post skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Post content to publish."},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_risk_report",
            "description": "Placeholder tool that signals report synthesis after all Binance Skills data has been collected.",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_address": {"type": "string", "description": "Token contract address."},
                },
                "required": ["token_address"],
            },
        },
    },
]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _flatten_risks(audit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for group in audit_data.get("riskItems") or []:
        group_name = group.get("name", "")
        for item in group.get("details") or []:
            details.append(
                {
                    "group": group_name,
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "is_hit": bool(item.get("isHit")),
                    "risk_type": item.get("riskType", "RISK"),
                }
            )
    return details


def _find_risk(details: List[Dict[str, Any]], keyword: str) -> bool:
    keyword = keyword.lower()
    for detail in details:
        haystack = f"{detail['title']} {detail['description']}".lower()
        if keyword in haystack and detail["is_hit"]:
            return True
    return False


def _summarize_hit_risks(details: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    critical = []
    caution = []
    for detail in details:
        if not detail["is_hit"]:
            continue
        label = detail["title"] or detail["description"] or "Unnamed risk"
        if str(detail["risk_type"]).upper() == "CAUTION":
            caution.append(label)
        else:
            critical.append(label)
    return {"critical": critical, "caution": caution}


def _json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _binance_success(raw: Dict[str, Any]) -> bool:
    return raw.get("code") == "000000" and raw.get("success") is True and bool(raw.get("data"))


def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name == "analyze_contract_security":
        token_address = args.get("token_address", "")
        chain = args.get("chain", "bsc")
        raw = client.get_token_audit(token_address, chain)
        if raw.get("error"):
            return _json({"error": raw["error"]})

        data = raw.get("data") or {}
        if not data.get("hasResult") or not data.get("isSupported"):
            return _json(
                {
                    "error": "Binance audit result is not valid for this token.",
                    "source": "binance_skills",
                    "has_result": bool(data.get("hasResult")),
                    "is_supported": bool(data.get("isSupported")),
                }
            )

        details = _flatten_risks(data)
        summary = _summarize_hit_risks(details)
        result = {
            "source": "binance_skills",
            "has_result": bool(data.get("hasResult")),
            "is_supported": bool(data.get("isSupported")),
            "risk_level": int(data.get("riskLevel", 0) or 0),
            "risk_level_enum": data.get("riskLevelEnum") or "LOW",
            "buy_tax_percent": _as_float((data.get("extraInfo") or {}).get("buyTax")),
            "sell_tax_percent": _as_float((data.get("extraInfo") or {}).get("sellTax")),
            "is_verified": bool((data.get("extraInfo") or {}).get("isVerified")),
            "is_honeypot": _find_risk(details, "honeypot"),
            "is_mintable": _find_risk(details, "mint"),
            "is_blacklisted": _find_risk(details, "blacklist"),
            "transfer_pausable": _find_risk(details, "pause"),
            "has_whitelist_control": _find_risk(details, "whitelist"),
            "critical_risks": summary["critical"],
            "caution_risks": summary["caution"],
            "raw_risk_items": details,
            "disclaimer": "This audit result is for reference only and does not constitute investment advice.",
        }
        return _json(result)

    if tool_name == "check_holder_concentration":
        token_address = args.get("token_address", "")
        chain = args.get("chain", "bsc")

        dynamic_raw = client.get_token_dynamic_info(token_address, chain)
        metadata_raw = client.get_token_metadata(token_address, chain)
        legacy_raw = client.get_legacy_holder_snapshot(token_address, chain)

        dynamic_ok = _binance_success(dynamic_raw)
        metadata_ok = _binance_success(metadata_raw)
        if not dynamic_ok and not legacy_raw:
            error = dynamic_raw.get("error") or "未获取到该代币的持仓数据"
            return _json({"error": error})

        dynamic_data = dynamic_raw.get("data") or {}
        metadata_data = metadata_raw.get("data") or {}

        top10_percent = _as_float(dynamic_data.get("top10HoldersPercentage"))
        legacy_holders = []
        for holder in (legacy_raw.get("holders") or [])[:10]:
            legacy_holders.append(
                {
                    "address": holder.get("address", ""),
                    "percent": round(_as_float(holder.get("percent")) * 100, 4),
                    "is_locked": str(holder.get("is_locked")) == "1",
                    "is_contract": str(holder.get("is_contract")) == "1",
                }
            )

        lp_holders = []
        for holder in (legacy_raw.get("lp_holders") or [])[:5]:
            lp_holders.append(
                {
                    "address": holder.get("address", ""),
                    "percent": round(_as_float(holder.get("percent")) * 100, 4),
                    "is_locked": str(holder.get("is_locked")) == "1",
                }
            )

        result = {
            "source": "binance_skills_primary" if dynamic_ok else "legacy_fallback",
            "holder_count": int(_as_float(dynamic_data.get("holders"))) if dynamic_ok else len(legacy_raw.get("holders") or []),
            "top_10_total_percent": round(top10_percent, 4) if dynamic_ok else round(sum(item["percent"] for item in legacy_holders), 4),
            "smart_money_holder_count": int(_as_float(dynamic_data.get("smartMoneyHolders"))) if dynamic_ok else 0,
            "smart_money_holding_percent": round(_as_float(dynamic_data.get("smartMoneyHoldingPercent")), 6) if dynamic_ok else 0.0,
            "kol_holder_count": int(_as_float(dynamic_data.get("kolHolders"))) if dynamic_ok else 0,
            "kol_holding_percent": round(_as_float(dynamic_data.get("kolHoldingPercent")), 6) if dynamic_ok else 0.0,
            "pro_holder_count": int(_as_float(dynamic_data.get("proHolders"))) if dynamic_ok else 0,
            "pro_holding_percent": round(_as_float(dynamic_data.get("proHoldingPercent")), 6) if dynamic_ok else 0.0,
            "creator_address": metadata_data.get("creatorAddress", "") if metadata_ok else "",
            "top_10_holders_legacy": legacy_holders,
            "lp_holders_legacy": lp_holders,
            "legacy_source_used": bool(legacy_holders or lp_holders),
            "binance_data_available": dynamic_ok,
        }
        return _json(result)

    if tool_name == "check_liquidity_and_market":
        token_address = args.get("token_address", "")
        chain = args.get("chain", "bsc")

        dynamic_raw = client.get_token_dynamic_info(token_address, chain)
        metadata_raw = client.get_token_metadata(token_address, chain)
        legacy_market = client.get_legacy_market_snapshot(token_address)

        dynamic_ok = _binance_success(dynamic_raw)
        metadata_ok = _binance_success(metadata_raw)
        if not dynamic_ok and not legacy_market:
            return _json({"error": dynamic_raw.get("error") or "未获取到该代币的市场数据"})

        dynamic_data = dynamic_raw.get("data") or {}
        metadata_data = metadata_raw.get("data") or {}

        result = {
            "source": "binance_skills" if dynamic_ok else "legacy_fallback",
            "name": metadata_data.get("name", "") if metadata_ok else legacy_market.get("baseToken", {}).get("name", ""),
            "symbol": metadata_data.get("symbol", "") if metadata_ok else legacy_market.get("baseToken", {}).get("symbol", ""),
            "chain": metadata_data.get("chainName", chain.upper()) if metadata_ok else legacy_market.get("chainId", chain.upper()),
            "price_usd": _as_float(dynamic_data.get("price")) if dynamic_ok else _as_float(legacy_market.get("priceUsd")),
            "liquidity_usd": _as_float(dynamic_data.get("liquidity")) if dynamic_ok else _as_float((legacy_market.get("liquidity") or {}).get("usd")),
            "volume_24h_usd": _as_float(dynamic_data.get("volume24h")) if dynamic_ok else _as_float((legacy_market.get("volume") or {}).get("h24")),
            "volume_24h_buy_usd": _as_float(dynamic_data.get("volume24hBuy")) if dynamic_ok else 0.0,
            "volume_24h_sell_usd": _as_float(dynamic_data.get("volume24hSell")) if dynamic_ok else 0.0,
            "volume_1h_usd": _as_float(dynamic_data.get("volume1h")) if dynamic_ok else _as_float((legacy_market.get("volume") or {}).get("h1")),
            "volume_5m_usd": _as_float(dynamic_data.get("volume5m")) if dynamic_ok else 0.0,
            "count_24h": int(_as_float(dynamic_data.get("count24h"))) if dynamic_ok else int(_as_float((legacy_market.get("txns") or {}).get("h24", {}).get("buys"))) + int(_as_float((legacy_market.get("txns") or {}).get("h24", {}).get("sells"))),
            "count_24h_buy": int(_as_float(dynamic_data.get("count24hBuy"))) if dynamic_ok else int(_as_float((legacy_market.get("txns") or {}).get("h24", {}).get("buys"))),
            "count_24h_sell": int(_as_float(dynamic_data.get("count24hSell"))) if dynamic_ok else int(_as_float((legacy_market.get("txns") or {}).get("h24", {}).get("sells"))),
            "price_change_5m": _as_float(dynamic_data.get("percentChange5m")) if dynamic_ok else _as_float((legacy_market.get("priceChange") or {}).get("m5")),
            "price_change_1h": _as_float(dynamic_data.get("percentChange1h")) if dynamic_ok else _as_float((legacy_market.get("priceChange") or {}).get("h1")),
            "price_change_4h": _as_float(dynamic_data.get("percentChange4h")) if dynamic_ok else 0.0,
            "price_change_24h": _as_float(dynamic_data.get("percentChange24h")) if dynamic_ok else _as_float((legacy_market.get("priceChange") or {}).get("h24")),
            "market_cap_usd": _as_float(dynamic_data.get("marketCap")) if dynamic_ok else _as_float(legacy_market.get("marketCap")),
            "fdv_usd": _as_float(dynamic_data.get("fdv")) if dynamic_ok else 0.0,
            "holders": int(_as_float(dynamic_data.get("holders"))) if dynamic_ok else 0,
            "top_10_holders_percentage": _as_float(dynamic_data.get("top10HoldersPercentage")) if dynamic_ok else 0.0,
            "token_links": metadata_data.get("links") or [],
            "icon_url": client.icon_url(metadata_data.get("icon", "")) if metadata_ok else "",
            "fallback_dex_pair": (legacy_market.get("pairAddress") or ""),
            "fallback_dex_id": legacy_market.get("dexId", ""),
            "binance_data_available": dynamic_ok,
        }
        return _json(result)

    if tool_name == "check_smart_money_flow":
        token_address = args.get("token_address", "")
        chain = args.get("chain", "bsc")
        raw = client.get_token_signal_summary(token_address, chain)
        if raw.get("error"):
            return _json({"error": raw["error"]})

        matches = raw.get("data") or []
        active = [item for item in matches if item.get("status") == "active"]
        buy_count = sum(1 for item in matches if item.get("direction") == "buy")
        sell_count = sum(1 for item in matches if item.get("direction") == "sell")

        result = {
            "source": "binance_skills",
            "match_count": len(matches),
            "active_count": len(active),
            "buy_signal_count": buy_count,
            "sell_signal_count": sell_count,
            "signals": [
                {
                    "ticker": item.get("ticker", ""),
                    "direction": item.get("direction", ""),
                    "smart_money_count": item.get("smartMoneyCount", 0),
                    "signal_trigger_time": item.get("signalTriggerTime"),
                    "alert_price": _as_float(item.get("alertPrice")),
                    "current_price": _as_float(item.get("currentPrice")),
                    "max_gain_percent": _as_float(item.get("maxGain")),
                    "exit_rate": item.get("exitRate", 0),
                    "status": item.get("status", ""),
                    "launch_platform": item.get("launchPlatform", ""),
                }
                for item in matches[:10]
            ],
        }
        return _json(result)

    if tool_name == "post_to_binance_square":
        content = args.get("content", "").strip()
        if not content:
            return _json({"error": "content is required"})

        raw = client.publish_square_post(content)
        if raw.get("error"):
            return _json({"error": raw["error"]})

        data = raw.get("data") or {}
        post_id = data.get("id", "")
        return _json(
            {
                "source": "binance_square",
                "success": raw.get("code") == "000000",
                "post_id": post_id,
                "post_url": f"https://www.binance.com/square/post/{post_id}" if post_id else "",
            }
        )

    if tool_name == "generate_risk_report":
        return _json({"status": "report_generation_requested"})

    return _json({"error": f"Unknown tool: {tool_name}"})
