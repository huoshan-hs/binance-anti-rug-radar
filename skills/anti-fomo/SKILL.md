---
name: anti-fomo
description: Binance-themed token risk screening skill for OpenClaw-style agents. Use when the user wants to analyze a Binance or Web3 token contract, auto-detect the real chain, verify contract risk, inspect holders and liquidity, review smart-money activity, or generate a Chinese risk summary for Binance Square.
---

# Anti-FOMO

Run a strict Binance-native token risk workflow. Output Chinese. Prefer official Binance data. Do not guess.

## Required workflow

1. Extract the contract address from the request.
2. Detect the real chain before writing any conclusion.
3. If the user-specified chain differs from the detected chain, switch to the detected chain and rerun all checks consistently.
4. Query Binance official data first.
5. Use fallback sources only when the official field is unavailable.
6. Write a concise Chinese report.

## Chain detection

Use this order:

1. DexScreener pair lookup to detect which chain actively trades the address.
2. If still unclear, probe Binance token audit and Binance token market data across supported chains.

Always show:

- `请求链`
- `识别链`

If the chain was corrected, explicitly say that the analysis was rerun on the detected chain.

## Official data priority

Use this order:

1. Binance Skills Hub token audit
2. Binance Skills Hub token metadata
3. Binance Skills Hub token dynamic market data
4. Binance Skills Hub trading-signal
5. GoPlus fallback for holder-detail snapshots
6. DexScreener fallback for pair and market context

## Hard rules for missing data

- Do not say "audit missing" if Binance audit returns both `hasResult: true` and `isSupported: true`.
- Do not say "holders missing" on `bsc`, `base`, or `solana` if Binance dynamic market data returns `holders`.
- Do not say "liquidity missing" if Binance dynamic market data returns `liquidity`.
- If an official field exists, use that value instead of a fallback value.
- Only mark a field as missing after both official and fallback checks fail.
- Never silently convert missing fields into zero.

## Address classification

Classify the address before trusting the report fully:

- `token_contract`
- `market_listed_address`
- `unknown_or_non_token`

Always show:

- `地址类型`
- `地址判断`
- `分析置信度`
- `数据源`

If the address is not confidently identified as a token contract, warn that the report is only a clue-level reference.

## Supported chains

- Audit: `eth`, `bsc`, `base`, `solana`
- Market data: `bsc`, `base`, `solana`
- Smart-money signals: `bsc`, `solana`

If a chain does not support a certain module, say so explicitly and continue with the supported modules.

## Report format

Write the final report in Chinese and keep it short. Use this section order:

1. Header
2. `请求链`
3. `识别链`
4. `地址类型`
5. `分析置信度`
6. `数据源`
7. `合约安全`
8. `持仓结构`
9. `市场数据`
10. `聪明钱信号`
11. `关键发现`
12. `建议行动`

End with:

`仅供参考，不构成投资建议。`

## Risk heuristics

- Treat Binance audit `HIGH` as high risk.
- Treat honeypot, scam-related token, rug-pull flags, or sell tax above 10% as severe findings.
- Treat top-10 holder concentration above 50% as severe.
- Treat liquidity below 10,000 USD as severe.
- Treat smart-money sell signals exceeding buy signals as a warning.
- Treat newly launched low-cap tokens with extreme short-term price spikes as caution even without a critical flag.

## Example invocations

- `帮我分析这个合约 0x...`
- `帮我分析 eth 链上的 0x...`
- `检查这个币的风险 0x...`
- `看看这个 Base 代币值不值得关注 0x...`
- `帮我生成一段适合发 Binance Square 的中文风控摘要`

## Style

- Be direct.
- Prefer verified facts over speculation.
- If data conflicts across sources, say which source was trusted and why.
