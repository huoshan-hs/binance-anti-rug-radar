# Anti-FOMO Binance Agent

Binance-themed token risk analyzer for OpenClaw-style agents.

This project has two deliverables:

- a runnable local Python agent
- a portable Skill package under `skills/anti-fomo/`

The current version supports:

- automatic real-chain detection
- Binance-first token audit and market lookup
- holder concentration checks
- smart-money signal checks on supported chains
- Chinese risk reports
- Binance Square summary generation flow

## Project Structure

```text
skills/anti-fomo/
  SKILL.md
  agents/openai.yaml
src/
  binance_skills_client.py
  llm_agent.py
  tools.py
main.py
```

## Requirements

- Python 3.10+
- `requests`
- `python-dotenv`
- `openai` (optional, only for LLM mode)
- Internet access

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Edit `.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
BINANCE_SQUARE_OPENAPI_KEY=
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

Notes:

- `OPENAI_API_KEY` is optional. Without it, the project uses rule mode.
- `BINANCE_SQUARE_OPENAPI_KEY` is optional. It is only needed for Binance Square publishing.

## Local Usage

Run:

```bash
python main.py
```

Example prompts:

```text
帮我分析这个合约 0x55d398326f99059ff775485246999027b3197955
帮我分析 eth 链上的 0xd44e2a841256a392d9f4c10eb7f9177eea3c4444
检查这个币的风险 0x0188c8f400736a1d05b47d260138502f67f2c0f2
square 帮我生成一段 Binance Square 风控摘要
```

The report will try to show:

- requested chain
- detected chain
- address type
- confidence
- data sources
- contract security
- holder structure
- market data
- smart-money signals

## Skill Usage

The OpenClaw/OpenClaw-style Skill files are here:

- `skills/anti-fomo/SKILL.md`
- `skills/anti-fomo/agents/openai.yaml`

How to use with OpenClaw:

1. Give `skills/anti-fomo/SKILL.md` to OpenClaw.
2. Ask OpenClaw to install the skill.
3. Test with a real contract address.

Suggested installation/test prompt:

```text
帮我安装这个技能，然后测试下面这个地址：
0xd44e2a841256a392d9f4c10eb7f9177eea3c4444

要求：
1. 先自动识别真实链
2. 优先使用 Binance Skills Hub 官方数据
3. 只有官方和 fallback 都查不到时，才能说“数据缺失”
4. 输出中文报告
5. 必须显示：请求链、识别链、地址类型、分析置信度、数据源
```

## Data Priority

The analysis logic uses this priority:

1. Binance Skills Hub token audit
2. Binance Skills Hub token metadata and dynamic market data
3. Binance Skills Hub trading-signal
4. GoPlus fallback
5. DexScreener fallback

## Supported Chains

- Audit: `eth`, `bsc`, `base`, `solana`
- Market data: `bsc`, `base`, `solana`
- Smart-money signals: `bsc`, `solana`

## GitHub Push Notes

Recommended files to publish:

- `skills/anti-fomo/`
- `src/`
- `main.py`
- `requirements.txt`
- `README.md`

Do not publish:

- `.env`
- `__pycache__/`
- local cache files

## Disclaimer

For reference only. Not investment advice.
