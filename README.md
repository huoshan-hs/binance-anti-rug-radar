# Anti-FOMO Binance Skill

这是一个面向 OpenClaw / 小龙虾 的币安主题 Skill，核心目标是：

- 自动识别代币真实所在链
- 分析单个代币的合约风险
- 查看热门链上代币
- 查看聪明钱流入榜
- 查看 Meme 新币榜
- 监控链上异动代币
- 生成适合发 Binance Square 的中文摘要

这个 Skill 优先使用 **Binance 官方 Skills**：

- `query-token-audit`
- `query-token-info`
- `trading-signal`
- `crypto-market-rank`
- `meme-rush`
- `square-post`

只有官方字段缺失时，才回退到其他公开数据源。

## Skill 文件位置

主要文件：

- `skills/anti-fomo/SKILL.md`
- `skills/anti-fomo/agents/openai.yaml`

如果你要把它交给 OpenClaw / 小龙虾，重点就是这两个文件。

## 这个 Skill 能做什么

### 1. 单个代币风险分析

适合场景：

- 想看一个合约地址到底安不安全
- 想确认真实链
- 想看持仓、流动性、聪明钱信号

示例：

```text
帮我分析这个合约 0x55d398326f99059ff775485246999027b3197955
帮我分析 eth 链上的 0xd44e2a841256a392d9f4c10eb7f9177eea3c4444
检查这个币的风险 0x0188c8f400736a1d05b47d260138502f67f2c0f2
```

输出重点：

- 请求链
- 识别链
- 地址类型
- 分析置信度
- 数据源
- 合约安全
- 持仓结构
- 市场数据
- 聪明钱信号

### 2. 热门代币发现

适合场景：

- 想看当前链上最热门的代币
- 想看搜索热度高的代币
- 想看 Alpha 方向代币
- 想看社交热度高的代币

示例：

```text
热门 bsc
热门 base
alpha bsc
社交热度 bsc
```

### 3. 聪明钱流入榜

适合场景：

- 想看最近聪明钱重点流入哪些代币
- 想快速发现资金正在关注的币

示例：

```text
聪明钱流入 bsc
smart money inflow solana
```

### 4. Meme 新币榜

适合场景：

- 想看 FourMeme / Meme Rush 的新币
- 想看即将迁移或已迁移的 meme 币

示例：

```text
meme 新币 bsc
meme 即将迁移 bsc
meme 已迁移 bsc
```

### 5. 异动监控

适合场景：

- 想看哪些币在短时间内暴涨
- 想看买卖失衡、低市值快速拉升、异常交易量
- 想看聪明钱流入异常的标的

示例：

```text
异动监控 bsc
异动监控 solana
anomaly bsc
```

### 6. Binance Square 摘要

适合场景：

- 想把分析结果整理成一段适合发 Binance Square 的中文摘要

示例：

```text
帮我生成一段适合发 Binance Square 的中文风控摘要
square 帮我生成一段 Binance Square 风控摘要
```

## 如何在 OpenClaw / 小龙虾 中使用

### 安装方法

把下面这个文件发给 OpenClaw：

```text
skills/anti-fomo/SKILL.md
```

然后对 OpenClaw 说：

```text
帮我安装这个技能
```

如果它支持读取元数据，也一并使用：

```text
skills/anti-fomo/agents/openai.yaml
```

### 推荐测试话术

#### 风控分析测试

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

#### 热门代币测试

```text
热门 bsc
聪明钱流入 bsc
meme 新币 bsc
异动监控 bsc
```

## 本地调试方法

如果你想本地运行这个项目：

```bash
pip install -r requirements.txt
python main.py
```

本地可测试：

```text
热门 bsc
聪明钱流入 bsc
meme 新币 bsc
异动监控 bsc
帮我分析这个合约 0x55d398326f99059ff775485246999027b3197955
```

## 数据优先级

分析时使用的优先级是：

1. Binance Skills Hub token audit
2. Binance Skills Hub token metadata / dynamic market data
3. Binance Skills Hub trading-signal
4. Binance Skills Hub crypto-market-rank
5. Binance Skills Hub meme-rush
6. GoPlus fallback
7. DexScreener fallback

## 支持链

- Audit: `eth`, `bsc`, `base`, `solana`
- 热门榜/市场数据: 以 Binance 官方 ranking / market 支持链为准
- Smart Money: `bsc`, `solana`
- Meme Rush: `bsc`, `solana`

## 适合作为参赛展示的功能点

如果你要拿这个 Skill 去参赛，最适合展示的是这几个点：

- 自动识别真实链
- 单币风险分析
- 官方热门榜
- 官方聪明钱流入榜
- 官方 Meme 新币榜
- 官方异动监控

## 提醒

仅供参考，不构成投资建议。
