# Binance 土狗防 Rug 雷达

这是一个面向 OpenClaw / 小龙虾 / Codex 风格 Agent 的参赛版 skill，主题不是“分析一个币”，而是：

`用 Binance 官方技能做一个会筛、会排、会给行动建议的防 Rug 雷达。`

它现在重点演示三件事：

1. 单币风控结论
2. Smart Money + 风控联动判断
3. BSC 新 meme 持续监控观察名单

## Demo 卖点

- 先自动识别真实链，再统一重跑分析
- 优先使用 Binance 官方数据，缺字段时再回退
- 输出不是流水账，而是 Agent 风格结论：
  - 是否值得继续看
  - 最大风险点
  - 下一步建议
- 提供每 10 分钟扫描一次的 BSC 观察名单快照

## 目录

- `skills/anti-fomo/SKILL.md`
- `skills/anti-fomo/agents/openai.yaml`
- `src/radar_engine.py`：参赛版雷达逻辑
- `scripts/bsc_watchlist.py`：持续监控脚本
- `web.py` + `static/`：演示用网页
- `demo-script.md`：1-2 分钟录屏提纲

## 本地运行

```bash
pip install -r requirements.txt
python main.py
```

## Web 演示

```bash
python web.py
```

打开 [http://localhost:8000](http://localhost:8000)

推荐演示顺序：

1. 先输入一个 BSC 合约地址，展示单币风控结论
2. 强调“是否值得继续看 / 最大风险点 / 下一步建议”
3. 再点击“刷新观察名单”，展示 BSC 新 meme 的持续监控能力

## 持续监控脚本

运行一次：

```bash
python scripts/bsc_watchlist.py --once
```

每 10 分钟持续扫描一次：

```bash
python scripts/bsc_watchlist.py
```

输出 JSON：

```bash
python scripts/bsc_watchlist.py --once --json
```

## Demo 话术建议

单币分析：

```text
帮我分析这个合约 0x...
先识别真实链，再告诉我这个币值不值得继续看，最大风险点是什么，下一步我该怎么做。
```

持续监控：

```text
雷达 bsc
监控 bsc
```

## 数据优先级

1. Binance token audit
2. Binance token info / dynamic market data
3. Binance trading-signal
4. Binance crypto-market-rank
5. Binance meme-rush
6. GoPlus fallback
7. DexScreener fallback

## 当前最适合参赛展示的点

- Binance 原生能力组合，而不是单接口查询
- 风控结果不是静态报告，而是可执行建议
- 有持续监控和候选排序，像真正的 Agent

仅供参考，不构成投资建议。
