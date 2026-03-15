---
name: anti-fomo
description: Binance-themed token intelligence and risk screening skill for OpenClaw-style agents. Use when the user wants to analyze a Binance or Web3 token contract, auto-detect the real chain, discover hot on-chain tokens, monitor unusual market moves, review smart-money activity, or generate a Chinese risk summary using Binance official skills first.
---

# Anti-FOMO

Run a strict Binance-native workflow. Output Chinese. Prefer Binance official skills. Do not guess.

## Supported tasks

1. Single-token risk analysis
2. Real-chain auto-detection
3. Hot token discovery
4. Smart-money inflow discovery
5. Meme Rush discovery
6. Market anomaly monitoring
7. Binance Square risk-summary generation

## Official Binance skills to use

Use these official skills first:

1. `query-token-audit`
2. `query-token-info`
3. `trading-signal`
4. `crypto-market-rank`
5. `meme-rush`
6. `square-post` when the user wants to publish

Only use fallback data after the official skill path cannot provide the required field.

## Required workflow for token analysis

1. Extract the contract address.
2. Detect the real chain before writing any conclusion.
3. If the user-specified chain differs from the detected chain, switch to the detected chain and rerun all checks consistently.
4. Query Binance official audit and market data first.
5. Query smart-money signals if the chain supports them.
6. Write a concise Chinese report.

## Required workflow for hot tokens

If the user asks for hot tokens, use official Binance ranking skills:

- Trending / Top Search / Alpha: use `crypto-market-rank`
- Social hype: use `crypto-market-rank`
- Smart money inflow rank: use `crypto-market-rank`
- Meme new / finalizing / migrated: use `meme-rush`

Always show:

- 链
- 数据源
- 合约地址
- 价格
- 市值
- 流动性
- 持有人数
- 关键热度或资金流指标

## Required workflow for anomaly monitoring

If the user asks for 异动, 监控, abnormal move, anomaly, or alerts:

1. Use `crypto-market-rank` to pull official ranked market data.
2. Use `trading-signal` or smart-money inflow rank when supported.
3. Look for:
   - extreme short-term price spikes
   - buy/sell imbalance
   - high volume relative to liquidity
   - low-cap rapid moves
   - strong smart-money inflow
4. Return a short ranked anomaly list in Chinese.

Do not claim a field is missing until both official and fallback checks fail.

## Hard rules for missing data

- Do not say "audit missing" if Binance audit returns `hasResult: true` and `isSupported: true`.
- Do not say "holders missing" on `bsc`, `base`, or `solana` if Binance market data returns `holders`.
- Do not say "liquidity missing" if Binance market data returns `liquidity`.
- If an official field exists, use it instead of a fallback value.
- Never silently convert missing fields into zero.

## Address classification

Always show:

- `请求链`
- `识别链`
- `地址类型`
- `地址判断`
- `分析置信度`
- `数据源`

If the address is not confidently identified as a token contract, warn that the report is only a clue-level reference.

## Supported chains

- Audit: `eth`, `bsc`, `base`, `solana`
- Market data: `eth`, `bsc`, `base`, `solana` when officially supported by the current ranking endpoint
- Smart-money signals: `bsc`, `solana`
- Meme Rush: `bsc`, `solana`

If a chain does not support a module, say so explicitly and continue with the supported modules.

## Example invocations

- `帮我分析这个合约 0x...`
- `帮我分析 eth 链上的 0x...`
- `热门 bsc`
- `聪明钱流入 bsc`
- `meme 新币 bsc`
- `异动监控 bsc`
- `帮我生成一段适合发 Binance Square 的中文风控摘要`

## Style

- Be direct.
- Prefer verified facts over speculation.
- Keep the result short and scannable.
- End with: `仅供参考，不构成投资建议。`
