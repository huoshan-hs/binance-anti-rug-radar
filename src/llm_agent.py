import os
import re
from typing import Optional

from colorama import Fore

from src.radar_engine import (
    analyze_token_contract,
    build_bsc_watchlist,
    render_token_report,
    render_watchlist,
)

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


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
        api_key = os.getenv("OPENAI_API_KEY", "").strip()

        if api_key and HAS_OPENAI:
            self.client = OpenAI(api_key=api_key)
            self.has_llm = True
            print(Fore.GREEN + f"  已启用 LLM 模式 ({self.model})")
        else:
            print(Fore.YELLOW + "  已启用规则模式（未配置 OpenAI Key 或未安装 openai 包）")

    def process(self, user_input: str, chain: str = "bsc") -> str:
        lower = user_input.lower().strip()

        if self._is_watch_request(lower):
            snapshot = build_bsc_watchlist(limit=5)
            return render_watchlist(snapshot)

        requested_chain = self._detect_chain(lower) or chain
        address = self._extract_address(user_input)

        if address:
            report = analyze_token_contract(address, requested_chain=requested_chain)
            return render_token_report(report)

        return (
            "支持的用法：\n"
            "1. 直接输入合约地址，生成单币风控结论\n"
            "2. 输入“雷达 bsc”或“监控 bsc”，查看每 10 分钟观察名单的当前快照\n"
            "\n"
            "仅供参考，不构成投资建议。"
        )

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

    @staticmethod
    def _is_watch_request(lower_text: str) -> bool:
        keywords = [
            "雷达",
            "监控",
            "观察名单",
            "watchlist",
            "watch",
            "scan bsc",
            "meme monitor",
        ]
        return any(keyword in lower_text for keyword in keywords)
