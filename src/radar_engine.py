import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.binance_skills_client import BinanceSkillsClient
from src.tools import execute_tool


@dataclass
class RiskDecision:
    level: str
    score: int
    worth_watching: str
    max_risk_point: str
    next_action: str


def _tool_json(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(execute_tool(name, payload))


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{number:,.{digits}f}"


def _fmt_pct(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{number:.{digits}f}%"


def _fmt_usd(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"${number:,.{digits}f}"


def _launch_time_text(raw_ms: Any) -> str:
    try:
        ts = int(raw_ms) / 1000
    except (TypeError, ValueError):
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _collect_sources(
    audit: Dict[str, Any],
    holders: Dict[str, Any],
    market: Dict[str, Any],
    smart: Dict[str, Any],
    detected: Dict[str, Any],
) -> List[str]:
    sources: List[str] = []
    if detected.get("source"):
        sources.append(f"chain_detect:{detected['source']}")
    if not audit.get("error"):
        sources.append("binance_audit")
    if not holders.get("error"):
        if holders.get("binance_data_available"):
            sources.append("binance_holder")
        if holders.get("legacy_source_used"):
            sources.append("goplus_fallback")
    if market and not market.get("error"):
        sources.append("binance_market" if market.get("binance_data_available") else "dexscreener_fallback")
    if smart and not smart.get("error"):
        sources.append("binance_smart_money")
    return _dedupe(sources)


def _evaluate_decision(
    audit: Dict[str, Any],
    holders: Dict[str, Any],
    market: Dict[str, Any],
    smart: Dict[str, Any],
    address_profile: Dict[str, Any],
) -> RiskDecision:
    score = 100
    major_risks: List[str] = []
    caution_risks: List[str] = []

    if audit.get("error"):
        score -= 10
        caution_risks.append("官方审计不完整")
    else:
        if audit.get("is_honeypot"):
            score -= 90
            major_risks.append("疑似蜜罐")
        sell_tax = float(audit.get("sell_tax_percent", 0) or 0)
        buy_tax = float(audit.get("buy_tax_percent", 0) or 0)
        if max(sell_tax, buy_tax) >= 20:
            score -= 40
            major_risks.append("税率过高")
        elif max(sell_tax, buy_tax) >= 10:
            score -= 20
            caution_risks.append("税率偏高")
        if audit.get("critical_risks"):
            score -= min(35, len(audit["critical_risks"]) * 8)
            major_risks.extend(audit["critical_risks"][:3])
        if audit.get("caution_risks"):
            score -= min(18, len(audit["caution_risks"]) * 4)
            caution_risks.extend(audit["caution_risks"][:3])

    if holders and not holders.get("error"):
        top10 = float(holders.get("top_10_total_percent", 0) or 0)
        holder_count = int(holders.get("holder_count", 0) or 0)
        if top10 >= 95:
            score -= 45
            major_risks.append("筹码极端集中")
        elif top10 >= 70:
            score -= 30
            major_risks.append("筹码高度集中")
        elif top10 >= 50:
            score -= 15
            caution_risks.append("筹码偏集中")
        if holder_count <= 10:
            score -= 18
            major_risks.append("持有人极少")
        elif holder_count <= 100:
            score -= 8
            caution_risks.append("持有人偏少")

    if market and not market.get("error"):
        liquidity = float(market.get("liquidity_usd", 0) or 0)
        holders_count = int(market.get("holders", 0) or 0)
        if liquidity < 1_000:
            score -= 40
            major_risks.append("几乎没有流动性")
        elif liquidity < 10_000:
            score -= 22
            major_risks.append("流动性很低")
        elif liquidity < 50_000:
            score -= 8
            caution_risks.append("流动性一般")
        if holders_count and holders_count < 30:
            score -= 10
            caution_risks.append("市场参与度很低")

    if smart and not smart.get("error"):
        buy_count = int(smart.get("buy_signal_count", 0) or 0)
        sell_count = int(smart.get("sell_signal_count", 0) or 0)
        active_count = int(smart.get("active_count", 0) or 0)
        if sell_count > buy_count and sell_count > 0:
            score -= 8
            caution_risks.append("聪明钱偏卖出")
        if buy_count > sell_count and active_count > 0:
            score += 6

    if address_profile.get("confidence") == "low":
        score -= 10
        caution_risks.append("地址识别置信度低")

    score = max(0, min(100, score))
    major_risks = _dedupe(major_risks)
    caution_risks = _dedupe(caution_risks)

    if score < 35:
        return RiskDecision(
            level="高风险",
            score=score,
            worth_watching="不值得继续看",
            max_risk_point=major_risks[0] if major_risks else "综合风险过高",
            next_action="先不要参与，除非后续流动性、持仓结构和税率明显改善。",
        )
    if score < 65:
        return RiskDecision(
            level="中风险",
            score=score,
            worth_watching="只适合观察",
            max_risk_point=major_risks[0] if major_risks else (caution_risks[0] if caution_risks else "存在不确定性"),
            next_action="只做观察名单，继续跟踪流动性、持有人增长和聪明钱信号。",
        )
    return RiskDecision(
        level="低风险",
        score=score,
        worth_watching="值得继续看",
        max_risk_point=major_risks[0] if major_risks else (caution_risks[0] if caution_risks else "暂未发现明显硬伤"),
        next_action="可以继续深挖项目背景、链上成交与社区质量，再决定是否参与。",
    )


def analyze_token_contract(token_address: str, requested_chain: str = "bsc") -> Dict[str, Any]:
    client = BinanceSkillsClient()
    detected = client.detect_token_chain(token_address, requested_chain=requested_chain)
    resolved_chain = detected.get("chain", requested_chain)
    address_profile = client.classify_address(token_address, resolved_chain)

    audit = _tool_json("analyze_contract_security", {"token_address": token_address, "chain": resolved_chain})
    holders = _tool_json("check_holder_concentration", {"token_address": token_address, "chain": resolved_chain})
    market: Dict[str, Any] = {}
    smart: Dict[str, Any] = {}

    if resolved_chain in {"bsc", "base", "solana"}:
        market = _tool_json("check_liquidity_and_market", {"token_address": token_address, "chain": resolved_chain})
    if resolved_chain in {"bsc", "solana"}:
        smart = _tool_json("check_smart_money_flow", {"token_address": token_address, "chain": resolved_chain})

    decision = _evaluate_decision(audit, holders, market, smart, address_profile)
    token_name = market.get("name") or market.get("symbol") or "-"
    token_symbol = market.get("symbol") or token_name
    key_risks = _dedupe(
        (audit.get("critical_risks") or [])
        + (audit.get("caution_risks") or [])
    )

    if holders and not holders.get("error"):
        top10 = float(holders.get("top_10_total_percent", 0) or 0)
        if top10 >= 50:
            key_risks.append(f"Top10 持仓占比 {top10:.2f}%")
    if market and not market.get("error"):
        liq = float(market.get("liquidity_usd", 0) or 0)
        if liq < 10_000:
            key_risks.append(f"流动性仅 {_fmt_usd(liq)}")
    if smart and not smart.get("error") and int(smart.get("sell_signal_count", 0) or 0) > int(smart.get("buy_signal_count", 0) or 0):
        key_risks.append("聪明钱卖出信号更多")

    summary = {
        "token": {
            "address": token_address,
            "name": token_name,
            "symbol": token_symbol,
            "launch_time": _launch_time_text((market or {}).get("launchTime")),
        },
        "classification": {
            "requested_chain": requested_chain,
            "detected_chain": resolved_chain,
            "detected_by": detected.get("source", "unknown"),
            "address_type": address_profile.get("address_type", "unknown"),
            "address_judgement": address_profile.get("reason", ""),
            "confidence": address_profile.get("confidence", "low"),
            "data_sources": _collect_sources(audit, holders, market, smart, detected),
        },
        "decision": {
            "risk_level": decision.level,
            "score": decision.score,
            "worth_watching": decision.worth_watching,
            "max_risk_point": decision.max_risk_point,
            "next_action": decision.next_action,
        },
        "facts": {
            "audit": audit,
            "holders": holders,
            "market": market,
            "smart_money": smart,
            "key_risks": _dedupe(key_risks),
        },
    }
    return summary


def render_token_report(report: Dict[str, Any]) -> str:
    token = report["token"]
    classification = report["classification"]
    decision = report["decision"]
    facts = report["facts"]
    audit = facts["audit"]
    holders = facts["holders"]
    market = facts["market"]
    smart = facts["smart_money"]

    lines = [
        "=" * 64,
        "Binance 土狗防 Rug 雷达",
        "=" * 64,
        f"代币: {token['name']} ({token['symbol']})",
        f"合约: {token['address']}",
        f"请求链: {classification['requested_chain'].upper()}",
        f"识别链: {classification['detected_chain'].upper()}",
        f"地址类型: {classification['address_type']}",
        f"地址判断: {classification['address_judgement'] or '-'}",
        f"分析置信度: {classification['confidence']}",
        f"数据源: {', '.join(classification['data_sources']) or '-'}",
        "",
        "[结论]",
        f"- 综合风险: {decision['risk_level']} (评分 {decision['score']}/100)",
        f"- 是否值得继续看: {decision['worth_watching']}",
        f"- 最大风险点: {decision['max_risk_point']}",
        f"- 下一步建议: {decision['next_action']}",
        "",
        "[关键指标]",
    ]

    if not audit.get("error"):
        lines.extend(
            [
                f"- 官方审计等级: {audit.get('risk_level_enum', 'UNKNOWN')} ({audit.get('risk_level', '-')})",
                f"- 合约已验证: {audit.get('is_verified', False)}",
                f"- 买/卖税: {_fmt_pct(audit.get('buy_tax_percent'))} / {_fmt_pct(audit.get('sell_tax_percent'))}",
            ]
        )
    if holders and not holders.get("error"):
        lines.extend(
            [
                f"- 持有人数: {holders.get('holder_count', '-')}",
                f"- Top10 持仓: {_fmt_pct(holders.get('top_10_total_percent'))}",
            ]
        )
    if market and not market.get("error"):
        lines.extend(
            [
                f"- 流动性: {_fmt_usd(market.get('liquidity_usd'))}",
                f"- 24h 交易量: {_fmt_usd(market.get('volume_24h_usd'))}",
                f"- 当前价格: {_fmt_usd(market.get('price_usd'), 8)}",
                f"- 市值: {_fmt_usd(market.get('market_cap_usd'))}",
                f"- 启动时间: {token.get('launch_time', '-')}",
            ]
        )
    if smart and not smart.get("error"):
        lines.append(
            f"- 聪明钱信号: 买入 {smart.get('buy_signal_count', 0)} / 卖出 {smart.get('sell_signal_count', 0)}"
        )

    lines.extend(["", "[最大关注点]"])
    for item in facts.get("key_risks")[:6]:
        lines.append(f"- {item}")
    if not facts.get("key_risks"):
        lines.append("- 暂未发现明显硬风险，但仍需继续观察。")

    lines.extend(["", "仅供参考，不构成投资建议。"])
    return "\n".join(lines)


def _watchlist_score(candidate: Dict[str, Any]) -> int:
    score = 0
    liquidity = float(candidate.get("liquidity_usd", 0) or 0)
    holders = int(candidate.get("holders", 0) or 0)
    top10 = float(candidate.get("top10_percent", 0) or 0)
    market_cap = float(candidate.get("market_cap_usd", 0) or 0)
    change = float(candidate.get("price_change_percent", 0) or 0)
    tax = max(float(candidate.get("buy_tax_percent", 0) or 0), float(candidate.get("sell_tax_percent", 0) or 0))
    buy_signals = int(candidate.get("buy_signal_count", 0) or 0)
    sell_signals = int(candidate.get("sell_signal_count", 0) or 0)

    if liquidity >= 100_000:
        score += 25
    elif liquidity >= 30_000:
        score += 15
    elif liquidity >= 10_000:
        score += 8

    if holders >= 1_000:
        score += 20
    elif holders >= 300:
        score += 12
    elif holders >= 100:
        score += 6

    if top10 <= 20:
        score += 18
    elif top10 <= 40:
        score += 10
    elif top10 <= 60:
        score += 4
    else:
        score -= 10

    if 0 < market_cap <= 5_000_000:
        score += 10
    elif market_cap > 5_000_000:
        score += 4

    if 0 <= change <= 80:
        score += 8
    elif change > 120:
        score -= 5

    if tax >= 10:
        score -= 15
    elif tax > 0:
        score -= 6

    score += min(10, buy_signals * 2)
    score -= min(10, sell_signals * 2)
    return score


def build_bsc_watchlist(limit: int = 5) -> Dict[str, Any]:
    raw = _tool_json("discover_hot_tokens", {"chain": "bsc", "mode": "meme_new", "limit": 15})
    tokens = raw.get("tokens") or []
    source = raw.get("source", "binance_meme_rush")

    fallback = _tool_json("discover_hot_tokens", {"chain": "bsc", "mode": "trending", "limit": 10})
    existing = {item.get("contract_address") for item in tokens}
    for item in fallback.get("tokens") or []:
        if item.get("contract_address") in existing:
            continue
        tokens.append(item)
    source = f"{source} + {fallback.get('source', 'binance_unified_rank')}"

    ranked: List[Dict[str, Any]] = []

    for token in tokens:
        address = token.get("contract_address")
        if not address:
            continue
        audit = _tool_json("analyze_contract_security", {"token_address": address, "chain": "bsc"})
        holders = _tool_json("check_holder_concentration", {"token_address": address, "chain": "bsc"})
        market = _tool_json("check_liquidity_and_market", {"token_address": address, "chain": "bsc"})
        smart = _tool_json("check_smart_money_flow", {"token_address": address, "chain": "bsc"})

        if audit.get("error") or market.get("error") or holders.get("error"):
            continue

        entry = {
            "name": token.get("name") or market.get("name") or token.get("symbol"),
            "symbol": token.get("symbol") or market.get("symbol"),
            "address": address,
            "price_usd": market.get("price_usd"),
            "market_cap_usd": market.get("market_cap_usd"),
            "liquidity_usd": market.get("liquidity_usd"),
            "holders": market.get("holders") or holders.get("holder_count"),
            "top10_percent": holders.get("top_10_total_percent"),
            "price_change_percent": token.get("price_change_percent") or market.get("price_change_24h"),
            "buy_tax_percent": audit.get("buy_tax_percent"),
            "sell_tax_percent": audit.get("sell_tax_percent"),
            "buy_signal_count": smart.get("buy_signal_count", 0),
            "sell_signal_count": smart.get("sell_signal_count", 0),
            "critical_risks": audit.get("critical_risks", []),
            "caution_risks": audit.get("caution_risks", []),
        }

        hard_reject = audit.get("is_honeypot") or max(
            float(entry["buy_tax_percent"] or 0),
            float(entry["sell_tax_percent"] or 0),
        ) >= 20
        if hard_reject:
            continue

        entry["watchlist_score"] = _watchlist_score(entry)
        if float(entry["liquidity_usd"] or 0) < 5_000 and float(entry["top10_percent"] or 0) > 90:
            continue
        if entry["watchlist_score"] < 10:
            continue

        reasons: List[str] = []
        if float(entry["liquidity_usd"] or 0) >= 30_000:
            reasons.append(f"流动性 {_fmt_usd(entry['liquidity_usd'])}")
        if int(entry["holders"] or 0) >= 100:
            reasons.append(f"持有人 {entry['holders']}")
        if float(entry["top10_percent"] or 0) <= 40:
            reasons.append(f"Top10 {_fmt_pct(entry['top10_percent'])}")
        if int(entry["buy_signal_count"] or 0) > int(entry["sell_signal_count"] or 0):
            reasons.append("聪明钱偏买入")
        if float(entry["price_change_percent"] or 0) > 0:
            reasons.append(f"24h 涨幅 {_fmt_pct(entry['price_change_percent'])}")

        entry["reasons"] = reasons[:4]
        ranked.append(entry)

    ranked.sort(key=lambda item: item["watchlist_score"], reverse=True)
    return {
        "chain": "bsc",
        "source": source,
        "scan_time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
        "candidates": ranked[:limit],
    }


def render_watchlist(snapshot: Dict[str, Any]) -> str:
    lines = [
        "=" * 64,
        "Binance 土狗防 Rug 雷达 - BSC 每 10 分钟观察名单",
        "=" * 64,
        f"扫描时间: {snapshot['scan_time']}",
        f"数据源: {snapshot['source']}",
        "",
    ]

    candidates = snapshot.get("candidates") or []
    if not candidates:
        lines.append("本轮没有通过筛选的新 meme 候选。")
        lines.append("")
        lines.append("仅供参考，不构成投资建议。")
        return "\n".join(lines)

    for idx, item in enumerate(candidates, 1):
        lines.append(f"{idx}. {item['name']} ({item['symbol']})")
        lines.append(f"   合约: {item['address']}")
        lines.append(f"   雷达分: {item['watchlist_score']}")
        lines.append(f"   流动性 / 市值: {_fmt_usd(item['liquidity_usd'])} / {_fmt_usd(item['market_cap_usd'])}")
        lines.append(f"   持有人 / Top10: {item['holders']} / {_fmt_pct(item['top10_percent'])}")
        lines.append(f"   税率: {_fmt_pct(item['buy_tax_percent'])} / {_fmt_pct(item['sell_tax_percent'])}")
        lines.append(f"   推荐原因: {'；'.join(item['reasons']) or '通过基础风控筛选'}")
        lines.append("")

    lines.append("仅供参考，不构成投资建议。")
    return "\n".join(lines)
