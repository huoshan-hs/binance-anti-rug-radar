import json
import os
import re
from typing import Any, Dict, Optional

from colorama import Fore
from dotenv import load_dotenv

from src.binance_skills_client import BinanceSkillsClient
from src.tools import TOOL_SCHEMAS, execute_tool

load_dotenv()

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


SYSTEM_PROMPT = """
你是 Anti-FOMO Agent，一个币安主题的加密风控分析助手。

要求：
1. 先识别代币真实所在链，再调用对应工具。
2. 优先使用 Binance Skills Hub 官方接口。
3. 缺失字段才允许使用兜底数据。
4. 最终输出中文报告，先写风险，再写建议。
5. 结尾固定写：仅供参考，不构成投资建议。
"""

CHAIN_ALIASES = {
    "eth": "eth",
    "ethereum": "eth",
    "bsc": "bsc",
    "bnb": "bsc",
    "base": "base",
    "sol": "solana",
    "solana": "solana",
}

ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")


class LLMAgent:
    def __init__(self) -> None:
        self.has_llm = False
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.chain_client = BinanceSkillsClient()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and HAS_OPENAI:
            self.client = OpenAI(api_key=api_key)
            self.has_llm = True
            print(Fore.GREEN + f"  已启用 LLM 模式 ({self.model})")
        else:
            print(Fore.YELLOW + "  已启用规则模式（未配置 OpenAI Key 或未安装 openai 包）")

    def process(self, user_input: str, chain: str = "bsc") -> str:
        if self.has_llm:
            try:
                return self._llm_process(user_input)
            except Exception as exc:
                return f"LLM 模式失败，已切换到规则模式：{exc}\n\n{self._rule_process(user_input, chain)}"
        return self._rule_process(user_input, chain)

    def _llm_process(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        for _ in range(8):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content or "未生成响应。"

            messages.append(message)
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments or "{}")
                result = execute_tool(fn_name, fn_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "Agent 在生成最终结论前已达到工具调用上限。"

    def _rule_process(self, user_input: str, chain: str = "bsc") -> str:
        lower = user_input.lower()
        if lower.startswith("square "):
            content = user_input.split(" ", 1)[1].strip()
            return self._render_square_result(execute_tool("post_to_binance_square", {"content": content}))

        requested_chain = self._detect_chain(lower) or chain
        address = self._extract_address(user_input)
        if not address:
            return "请提供类似 0x1234... 的代币合约地址，我才能执行风控检查。"

        detected = self.chain_client.detect_token_chain(address, requested_chain=requested_chain)
        resolved_chain = detected.get("chain", requested_chain)
        address_profile = self.chain_client.classify_address(address, resolved_chain)

        results: Dict[str, Dict[str, Any]] = {}
        tool_order = [
            ("analyze_contract_security", {"token_address": address, "chain": resolved_chain}),
            ("check_holder_concentration", {"token_address": address, "chain": resolved_chain}),
        ]
        if resolved_chain in {"bsc", "base", "solana"}:
            tool_order.append(("check_liquidity_and_market", {"token_address": address, "chain": resolved_chain}))
        if resolved_chain in {"bsc", "solana"}:
            tool_order.append(("check_smart_money_flow", {"token_address": address, "chain": resolved_chain}))

        for tool_name, payload in tool_order:
            results[tool_name] = json.loads(execute_tool(tool_name, payload))

        return self._build_rule_report(address, requested_chain, resolved_chain, detected, address_profile, results)

    def _build_rule_report(
        self,
        address: str,
        requested_chain: str,
        resolved_chain: str,
        detected: Dict[str, Any],
        address_profile: Dict[str, Any],
        results: Dict[str, Dict[str, Any]],
    ) -> str:
        audit = results.get("analyze_contract_security", {})
        holders = results.get("check_holder_concentration", {})
        market = results.get("check_liquidity_and_market", {})
        smart = results.get("check_smart_money_flow", {})

        critical: list[str] = []
        warnings: list[str] = []

        if audit.get("error"):
            warnings.append(f"审计不可用：{audit['error']}")
        else:
            critical.extend(audit.get("critical_risks", []))
            warnings.extend(audit.get("caution_risks", []))
            if audit.get("sell_tax_percent", 0) > 10:
                critical.append(f"卖出税过高：{audit['sell_tax_percent']}%")
            if audit.get("is_honeypot"):
                critical.append("检测到疑似蜜罐行为")

        if holders and not holders.get("error"):
            if holders.get("top_10_total_percent", 0) > 50:
                critical.append(f"前 10 地址持仓占比达到 {holders['top_10_total_percent']}%")
            if holders.get("creator_address"):
                warnings.append(f"发现创建者地址：{holders['creator_address']}")

        if market and not market.get("error"):
            if market.get("liquidity_usd", 0) < 10000:
                critical.append(f"流动性过低：${market['liquidity_usd']:.2f}")
            buy_count = market.get("count_24h_buy", 0)
            sell_count = market.get("count_24h_sell", 0)
            if sell_count > buy_count * 1.5 and market.get("price_change_24h", 0) < -10:
                warnings.append("近期卖压明显强于买盘")

        if smart and not smart.get("error"):
            if smart.get("sell_signal_count", 0) > smart.get("buy_signal_count", 0):
                warnings.append("聪明钱卖出信号多于买入信号")
            if smart.get("active_count", 0) > 0:
                warnings.append(f"发现 {smart['active_count']} 条活跃聪明钱信号")

        data_sources = []
        if not audit.get("error"):
            data_sources.append("Binance Audit")
        if market and not market.get("error"):
            data_sources.append("Binance Market" if market.get("binance_data_available", False) else "DexScreener Fallback")
        if holders and not holders.get("error"):
            if holders.get("binance_data_available", False):
                data_sources.append("Binance Holder")
            if holders.get("legacy_source_used", False):
                data_sources.append("GoPlus Fallback")
        if smart and not smart.get("error"):
            data_sources.append("Binance Smart Money")

        confidence = "低"
        if address_profile.get("confidence") == "high" and "Binance Audit" in data_sources and "Binance Market" in data_sources:
            confidence = "高"
        elif address_profile.get("confidence") in {"high", "medium"}:
            confidence = "中"

        risk_label = "低风险"
        if critical:
            risk_label = "高风险"
        elif warnings:
            risk_label = "中风险"

        lines = [
            "=" * 64,
            "代币风险分析报告",
            "=" * 64,
            f"合约地址：{address}",
            f"请求链：{requested_chain.upper()}",
            f"识别链：{resolved_chain.upper()}（来源：{detected.get('source', 'unknown')}）",
            f"地址类型：{address_profile.get('address_type', 'unknown')}",
            f"分析置信度：{confidence}",
            f"数据源：{', '.join(data_sources) if data_sources else '无'}",
        ]
        if detected.get("mismatch"):
            lines.append("链路修正：用户输入链与真实链不一致，已按识别出的真实链重跑全部分析。")
        if address_profile.get("reason"):
            lines.append(f"地址判断：{address_profile['reason']}")

        lines.extend(["", f"综合风险：{risk_label}", "", "[合约安全]"])
        if audit.get("error"):
            lines.append(f"- {audit['error']}")
        else:
            lines.append(f"- 数据来源：{audit.get('source', 'unknown')}")
            lines.append(f"- 官方风险等级：{audit.get('risk_level_enum', 'UNKNOWN')} ({audit.get('risk_level', '?')})")
            lines.append(f"- 合约已验证：{audit.get('is_verified', False)}")
            lines.append(f"- 买入税/卖出税：{audit.get('buy_tax_percent', 0)}% / {audit.get('sell_tax_percent', 0)}%")

        lines.extend(["", "[持仓结构]"])
        if holders.get("error"):
            lines.append(f"- {holders['error']}")
        else:
            lines.append(f"- 持币地址数：{holders.get('holder_count', 0)}")
            lines.append(f"- 前 10 持仓占比：{holders.get('top_10_total_percent', 0)}%")
            lines.append(f"- Binance 官方数据可用：{holders.get('binance_data_available', False)}")

        lines.extend(["", "[市场数据]"])
        if market:
            if market.get("error"):
                lines.append(f"- {market['error']}")
            else:
                lines.append(f"- 数据来源：{market.get('source', 'unknown')}")
                lines.append(f"- 代币：{market.get('name', '')} ({market.get('symbol', '')})")
                lines.append(f"- 当前价格：${market.get('price_usd', 0):.8f}")
                lines.append(f"- 流动性：${market.get('liquidity_usd', 0):,.2f}")
                lines.append(f"- 24h 交易量：${market.get('volume_24h_usd', 0):,.2f}")
                lines.append(f"- 24h 涨跌幅：{market.get('price_change_24h', 0)}%")

        lines.extend(["", "[聪明钱信号]"])
        if smart:
            if smart.get("error"):
                lines.append(f"- {smart['error']}")
            else:
                lines.append(f"- 匹配到的信号数：{smart.get('match_count', 0)}")
                lines.append(f"- 活跃信号数：{smart.get('active_count', 0)}")
                lines.append(f"- 买入/卖出信号：{smart.get('buy_signal_count', 0)}/{smart.get('sell_signal_count', 0)}")

        lines.extend(["", "[关键结论]"])
        if critical:
            for item in critical[:6]:
                lines.append(f"- 严重风险：{item}")
        if warnings:
            for item in warnings[:6]:
                lines.append(f"- 风险提示：{item}")
        if not critical and not warnings:
            lines.append("- 当前未发现明显重大红旗。")
        if address_profile.get("address_type") != "token_contract":
            lines.append("- 当前地址未被高置信度识别为标准代币合约，报告仅可作线索参考。")

        lines.extend(["", "[建议动作]"])
        if risk_label == "高风险":
            lines.append("- 建议暂不入场，或先降低仓位，等高风险项解除后再评估。")
        elif risk_label == "中风险":
            lines.append("- 建议仅在人工复核后小仓位参与。")
        else:
            lines.append("- 建议持续观察，目前未见立即性的严重风险。")

        lines.append("")
        lines.append("仅供参考，不构成投资建议。")
        return "\n".join(lines)

    @staticmethod
    def _render_square_result(raw_json: str) -> str:
        data = json.loads(raw_json)
        if data.get("error"):
            return f"Binance Square 发布失败：{data['error']}"
        if data.get("success"):
            return f"Binance Square 已发布：{data.get('post_url', '（未返回 URL）')}"
        return "Binance Square 返回了非成功响应。"

    @staticmethod
    def _extract_address(user_input: str) -> Optional[str]:
        match = ADDRESS_PATTERN.search(user_input)
        return match.group(0) if match else None

    @staticmethod
    def _detect_chain(lower_text: str) -> Optional[str]:
        for alias, canonical in CHAIN_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lower_text):
                return canonical
        return None
