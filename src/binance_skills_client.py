import os
import uuid
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BINANCE_ICON_BASE = "https://bin.bnbstatic.com"

AUDIT_CHAIN_IDS = {
    "eth": "1",
    "ethereum": "1",
    "bsc": "56",
    "bnb": "56",
    "base": "8453",
    "sol": "CT_501",
    "solana": "CT_501",
}

MARKET_CHAIN_IDS = {
    "bsc": "56",
    "bnb": "56",
    "base": "8453",
    "sol": "CT_501",
    "solana": "CT_501",
}

SIGNAL_CHAIN_IDS = {
    "bsc": "56",
    "bnb": "56",
    "sol": "CT_501",
    "solana": "CT_501",
}

GOPLUS_CHAIN_IDS = {
    "eth": "1",
    "ethereum": "1",
    "bsc": "56",
    "bnb": "56",
    "polygon": "137",
    "matic": "137",
    "arbitrum": "42161",
    "base": "8453",
    "sol": "solana",
    "solana": "solana",
}


class BinanceSkillsClient:
    """Binance Skills Hub first-party client with optional third-party fallback."""

    def __init__(self) -> None:
        self.square_openapi_key = os.getenv("BINANCE_SQUARE_OPENAPI_KEY", "").strip()
        self.timeout = 20
        self.session = requests.Session()
        self.session.headers.update({"Accept-Encoding": "identity"})

        self.binance_web3_base = "https://web3.binance.com"
        self.binance_square_base = "https://www.binance.com"
        self.goplus_base = "https://api.gopluslabs.io/api/v1"
        self.dexscreener_base = "https://api.dexscreener.com"

    def _get(self, url: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, url: str, *, headers: Optional[Dict[str, str]] = None, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.post(url, headers=headers, json=json_body, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_token_audit(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        chain_id = AUDIT_CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return {"error": f"Binance audit skill does not support chain '{chain}'."}

        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.4 (Skill)",
            "source": "agent",
        }
        payload = {
            "binanceChainId": chain_id,
            "contractAddress": token_address,
            "requestId": str(uuid.uuid4()),
        }

        try:
            data = self._post(
                f"{self.binance_web3_base}/bapi/defi/v1/public/wallet-direct/security/token/audit",
                headers=headers,
                json_body=payload,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance audit request failed: {exc}"}

    def get_token_metadata(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        chain_id = MARKET_CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return {"error": f"Binance token metadata skill does not support chain '{chain}'."}

        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.0 (Skill)",
        }
        params = {
            "chainId": chain_id,
            "contractAddress": token_address,
        }

        try:
            data = self._get(
                f"{self.binance_web3_base}/bapi/defi/v1/public/wallet-direct/buw/wallet/dex/market/token/meta/info",
                headers=headers,
                params=params,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance token metadata request failed: {exc}"}

    def get_token_dynamic_info(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        chain_id = MARKET_CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return {"error": f"Binance market skill does not support chain '{chain}'."}

        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.0 (Skill)",
        }
        params = {
            "chainId": chain_id,
            "contractAddress": token_address,
        }

        try:
            data = self._get(
                f"{self.binance_web3_base}/bapi/defi/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info",
                headers=headers,
                params=params,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance market request failed: {exc}"}

    def search_tokens(self, keyword: str, chains: Optional[List[str]] = None) -> Dict[str, Any]:
        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.0 (Skill)",
        }
        chain_ids = []
        for chain in chains or ["bsc", "base", "solana"]:
            chain_id = MARKET_CHAIN_IDS.get(chain.lower())
            if chain_id:
                chain_ids.append(chain_id)

        params = {
            "keyword": keyword,
            "orderBy": "volume24h",
        }
        if chain_ids:
            params["chainIds"] = ",".join(chain_ids)

        try:
            data = self._get(
                f"{self.binance_web3_base}/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search",
                headers=headers,
                params=params,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance token search request failed: {exc}"}

    def get_smart_money_signals(self, chain: str = "bsc", page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        chain_id = SIGNAL_CHAIN_IDS.get(chain.lower())
        if not chain_id:
            return {"error": f"Binance trading-signal skill does not support chain '{chain}'."}

        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "binance-web3/1.0 (Skill)",
        }
        payload = {
            "smartSignalType": "",
            "page": page,
            "pageSize": page_size,
            "chainId": chain_id,
        }

        try:
            data = self._post(
                f"{self.binance_web3_base}/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money",
                headers=headers,
                json_body=payload,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance trading-signal request failed: {exc}"}

    def get_token_signal_summary(self, token_address: str, chain: str = "bsc", page_size: int = 100) -> Dict[str, Any]:
        raw = self.get_smart_money_signals(chain=chain, page=1, page_size=page_size)
        if raw.get("error"):
            return raw

        signals = raw.get("data") or []
        matches = [signal for signal in signals if str(signal.get("contractAddress", "")).lower() == token_address.lower()]
        return {"success": raw.get("success", False), "data": matches}

    def publish_square_post(self, content: str) -> Dict[str, Any]:
        if not self.square_openapi_key:
            return {"error": "BINANCE_SQUARE_OPENAPI_KEY is not configured."}

        headers = {
            "X-Square-OpenAPI-Key": self.square_openapi_key,
            "Content-Type": "application/json",
            "clienttype": "binanceSkill",
        }
        payload = {"bodyTextOnly": content}

        try:
            data = self._post(
                f"{self.binance_square_base}/bapi/composite/v1/public/pgc/openApi/content/add",
                headers=headers,
                json_body=payload,
            )
            return data
        except Exception as exc:
            return {"error": f"Binance Square publish failed: {exc}"}

    def get_legacy_holder_snapshot(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        chain_id = GOPLUS_CHAIN_IDS.get(chain.lower(), "56")
        try:
            data = self._get(
                f"{self.goplus_base}/token_security/{chain_id}",
                params={"contract_addresses": token_address.lower()},
            )
            result = data.get("result") or {}
            return result.get(token_address.lower(), {})
        except Exception:
            return {}

    def get_legacy_market_snapshot(self, token_address: str) -> Dict[str, Any]:
        try:
            data = self._get(f"{self.dexscreener_base}/latest/dex/tokens/{token_address}")
            pairs = data.get("pairs") or []
            if not pairs:
                return {}
            pairs.sort(key=lambda pair: float(pair.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
            return pairs[0]
        except Exception:
            return {}

    def detect_token_chain(self, token_address: str, requested_chain: Optional[str] = None) -> Dict[str, Any]:
        requested = (requested_chain or "").lower().strip()

        dex_pair = self.get_legacy_market_snapshot(token_address)
        dex_chain = str(dex_pair.get("chainId", "")).lower().strip()
        if dex_chain in {"bsc", "ethereum", "eth", "base", "solana"}:
            normalized = {
                "ethereum": "eth",
                "eth": "eth",
                "bsc": "bsc",
                "base": "base",
                "solana": "solana",
            }[dex_chain]
            return {
                "chain": normalized,
                "source": "dexscreener",
                "pair": dex_pair.get("pairAddress", ""),
                "dex_id": dex_pair.get("dexId", ""),
                "base_symbol": (dex_pair.get("baseToken") or {}).get("symbol", ""),
                "base_name": (dex_pair.get("baseToken") or {}).get("name", ""),
                "requested_chain": requested or "",
                "mismatch": bool(requested and requested != normalized),
            }

        candidates = ["bsc", "base", "solana", "eth"]
        if requested in candidates:
            candidates = [requested] + [chain for chain in candidates if chain != requested]

        for chain in candidates:
            audit = self.get_token_audit(token_address, chain)
            audit_data = audit.get("data") or {}
            if audit_data.get("hasResult") and audit_data.get("isSupported"):
                return {
                    "chain": chain,
                    "source": "binance_audit",
                    "requested_chain": requested or "",
                    "mismatch": bool(requested and requested != chain),
                    "audit_has_result": True,
                }

            if chain in {"bsc", "base", "solana"}:
                market = self.get_token_dynamic_info(token_address, chain)
                market_data = market.get("data") or {}
                if market.get("code") == "000000" and market.get("success") is True and market_data:
                    return {
                        "chain": chain,
                        "source": "binance_market",
                        "requested_chain": requested or "",
                        "mismatch": bool(requested and requested != chain),
                        "market_detected": True,
                    }

        return {
            "chain": requested or "bsc",
            "source": "fallback_default",
            "requested_chain": requested or "",
            "mismatch": False,
        }

    def classify_address(self, token_address: str, chain: str) -> Dict[str, Any]:
        audit = self.get_token_audit(token_address, chain)
        audit_data = audit.get("data") or {}
        market = self.get_token_dynamic_info(token_address, chain) if chain in {"bsc", "base", "solana"} else {}
        market_data = market.get("data") or {}
        dex = self.get_legacy_market_snapshot(token_address)

        if audit_data.get("hasResult") and audit_data.get("isSupported"):
            return {
                "address_type": "token_contract",
                "confidence": "high",
                "reason": "Binance audit 返回有效代币结果",
            }

        if market.get("code") == "000000" and market.get("success") is True and market_data:
            return {
                "address_type": "token_contract",
                "confidence": "medium",
                "reason": "Binance market 返回有效代币结果",
            }

        if dex:
            return {
                "address_type": "market_listed_address",
                "confidence": "medium",
                "reason": "DexScreener 存在交易对，但 Binance 官方代币结果不足",
            }

        return {
            "address_type": "unknown_or_non_token",
            "confidence": "low",
            "reason": "未从官方代币接口或 Dex 交易对确认该地址是标准代币",
        }

    # Compatibility wrappers for older modules in this repo.
    def get_token_contract_audit(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        return self.get_legacy_holder_snapshot(token_address, chain)

    def get_address_insight(self, token_address: str, chain: str = "bsc") -> Dict[str, Any]:
        return self.get_legacy_holder_snapshot(token_address, chain)

    def get_dexscreener_data(self, token_address: str) -> Dict[str, Any]:
        return self.get_legacy_market_snapshot(token_address)

    def execute_spot_trading_sell_all(self, token_symbol: str) -> Dict[str, Any]:
        return {
            "status": "advised",
            "action": "MARKET_SELL_ALL",
            "token_symbol": token_symbol,
            "message": "Manual confirmation required. No live trade was executed.",
        }

    @staticmethod
    def icon_url(path: str) -> str:
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{BINANCE_ICON_BASE}{path}"
