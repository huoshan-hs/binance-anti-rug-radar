"""
RiskEvaluator + AlertAndActionEngine
真实数据驱动的五维风控引擎 + 完整分析报告输出
"""
import time
import pyttsx3
import threading
from colorama import init, Fore, Style
from src.binance_skills_client import BinanceSkillsClient

init(autoreset=True)

# ============================================================
# 工具函数：安全地把 GoPlus 的 "0"/"1" 字段解析成布尔
# ============================================================
def _is_risk(value) -> bool:
    """GoPlus 返回 '1' 表示是/有风险, '0' 表示否/安全"""
    return str(value) == "1"

def _is_safe(value) -> bool:
    return str(value) == "1"

def _pct(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class AlertAndActionEngine:
    """处理文本告警、语音播报与自动交易平仓动作"""

    def _speak(self, text: str):
        def run_tts():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass  # TTS 失败不影响主流程
        threading.Thread(target=run_tts, daemon=True).start()

    def trigger_red_alert(self, reason: str, token_symbol: str, client: BinanceSkillsClient):
        warning_text = f"警告！{token_symbol} 检测到严重杀猪盘风险！原因：{reason}。建议立刻平仓！"
        print("\n" + Fore.RED + Style.BRIGHT + "=" * 60)
        print(Fore.RED + Style.BRIGHT + "🚨 🚨 🚨 红线风控触发 🚨 🚨 🚨")
        print(Fore.RED + Style.BRIGHT + warning_text)
        print(Fore.RED + Style.BRIGHT + "=" * 60)
        self._speak(warning_text)
        client.execute_spot_trading_sell_all(token_symbol)


class RiskEvaluator:
    """负责汇总真实链上数据，判断是否触碰红线，并输出完整分析报告"""

    # 红线阈值 (可调)
    SELL_TAX_THRESHOLD = 10       # 卖出税 > 10% 即警报
    HOLDER_CONCENTRATION_THRESHOLD = 50  # Top10 持有 > 50%
    MIN_LIQUIDITY_USD = 10000     # 最低流动性 $10k

    def __init__(self, client: BinanceSkillsClient, alert_engine: AlertAndActionEngine):
        self.client = client
        self.alert_engine = alert_engine

    def evaluate_token(self, token_address: str, token_symbol: str, chain: str = "bsc"):
        print(Fore.CYAN + Style.BRIGHT + f"\n{'='*60}")
        print(Fore.CYAN + Style.BRIGHT + f"  开始对 {token_symbol} 进行五维风控扫描")
        print(Fore.CYAN + Style.BRIGHT + f"  地址: {token_address}")
        print(Fore.CYAN + Style.BRIGHT + f"  链: {chain.upper()}")
        print(Fore.CYAN + Style.BRIGHT + f"{'='*60}\n")

        red_flags = []    # 红线列表
        warnings = []     # 警告列表
        info_lines = []   # 信息汇总

        # =====================================================
        # [1/5] 合约审计新鲜度与安全检查
        # =====================================================
        print(Fore.WHITE + Style.BRIGHT + "📋 [1/5] 合约安全审计 (GoPlus Security)")
        print(Fore.WHITE + "─" * 50)
        audit = self.client.get_token_contract_audit(token_address, chain)

        if not audit:
            print(Fore.YELLOW + "  ⚠️ 无法从 GoPlus 获取审计数据 (可能是新币或不支持的链)")
            warnings.append("无法获取链上审计数据")
        else:
            token_name = audit.get("token_name", "未知")
            token_sym = audit.get("token_symbol", token_symbol)
            if token_sym:
                token_symbol = token_sym  # 用真实 symbol

            # 基础信息
            print(Fore.WHITE + f"  代币名称: {token_name} ({token_symbol})")
            info_lines.append(f"代币: {token_name} ({token_symbol})")

            # 蜜罐检测
            is_honeypot = _is_risk(audit.get("is_honeypot"))
            hp_label = Fore.RED + "🔴 是 (貔貅盘!)" if is_honeypot else Fore.GREEN + "🟢 否"
            print(f"  蜜罐(Honeypot): {hp_label}")
            if is_honeypot:
                red_flags.append("合约被确认为貔貅盘(Honeypot)，无法卖出！")

            # 开源情况
            is_open_source = _is_safe(audit.get("is_open_source"))
            os_label = Fore.GREEN + "🟢 已开源" if is_open_source else Fore.YELLOW + "🟡 未开源"
            print(f"  合约开源: {os_label}")
            if not is_open_source:
                warnings.append("合约代码未开源，无法验证逻辑")

            # 代理合约
            is_proxy = _is_risk(audit.get("is_proxy"))
            proxy_label = Fore.YELLOW + "🟡 是 (可升级合约)" if is_proxy else Fore.GREEN + "🟢 否"
            print(f"  代理合约: {proxy_label}")
            if is_proxy:
                warnings.append("代理合约(可升级)，开发者可随时修改逻辑")

            # 可增发
            is_mintable = _is_risk(audit.get("is_mintable"))
            mint_label = Fore.RED + "🔴 是 (可无限增发!)" if is_mintable else Fore.GREEN + "🟢 否"
            print(f"  可增发: {mint_label}")
            if is_mintable:
                red_flags.append("合约允许无限增发代币，随时可稀释持仓")

            # 所有权
            can_take_ownership = _is_risk(audit.get("can_take_back_ownership"))
            owner_label = Fore.RED + "🔴 是" if can_take_ownership else Fore.GREEN + "🟢 否"
            print(f"  可夺回所有权: {owner_label}")
            if can_take_ownership:
                red_flags.append("开发者可夺回合约所有权")

            # 买卖税
            buy_tax = _pct(audit.get("buy_tax")) * 100
            sell_tax = _pct(audit.get("sell_tax")) * 100
            bt_color = Fore.RED if buy_tax > self.SELL_TAX_THRESHOLD else Fore.GREEN
            st_color = Fore.RED if sell_tax > self.SELL_TAX_THRESHOLD else Fore.GREEN
            print(f"  买入税: {bt_color}{buy_tax:.1f}%")
            print(f"  卖出税: {st_color}{sell_tax:.1f}%")
            if sell_tax > self.SELL_TAX_THRESHOLD:
                red_flags.append(f"卖出税高达 {sell_tax:.1f}%，大部分利润会被吃掉")
            if sell_tax >= 100:
                red_flags.append(f"卖出税 100%！完全无法卖出，与貔貅无异")

            # 不能卖出
            cannot_sell = _is_risk(audit.get("cannot_sell_all"))
            if cannot_sell:
                red_flags.append("合约限制：不能一次性卖出全部持仓")
                print(Fore.RED + "  全量卖出限制: 🔴 是")

            # 黑名单 / 白名单
            has_blacklist = _is_risk(audit.get("is_blacklisted"))
            if has_blacklist:
                warnings.append("合约含黑名单功能，开发者可冻结任意地址")
                print(Fore.YELLOW + "  黑名单功能: 🟡 有")

            # 交易暂停
            can_pause = _is_risk(audit.get("transfer_pausable"))
            if can_pause:
                warnings.append("合约可暂停所有交易")
                print(Fore.YELLOW + "  交易暂停: 🟡 可暂停")

        print()

        # =====================================================
        # [2/5] 早期持仓集中度
        # =====================================================
        print(Fore.WHITE + Style.BRIGHT + "👥 [2/5] 早期持仓集中度分析")
        print(Fore.WHITE + "─" * 50)

        holders = audit.get("holders", []) if audit else []
        lp_holders = audit.get("lp_holders", []) if audit else []
        holder_count = audit.get("holder_count", "未知") if audit else "未知"
        print(f"  持有人数: {holder_count}")

        if holders:
            top10_total = 0.0
            print(f"  {'排名':<4} {'地址':<20} {'占比':<10} {'是否锁仓':<8}")
            for i, h in enumerate(holders[:10], 1):
                addr = h.get("address", "???")
                pct = _pct(h.get("percent")) * 100
                is_locked = "🔒锁仓" if _is_safe(h.get("is_locked")) else ""
                is_contract = "📜合约" if _is_safe(h.get("is_contract")) else ""
                top10_total += pct
                short_addr = addr[:6] + "..." + addr[-4:]
                tag = f"{is_locked} {is_contract}".strip()
                color = Fore.YELLOW if pct > 10 else Fore.WHITE
                print(f"  {color}{i:<4} {short_addr:<20} {pct:.2f}%     {tag}")
            
            conc_color = Fore.RED if top10_total > self.HOLDER_CONCENTRATION_THRESHOLD else Fore.GREEN
            print(f"\n  {conc_color}Top 10 合计持仓: {top10_total:.2f}%")
            info_lines.append(f"Top10 持仓集中度: {top10_total:.2f}%")

            if top10_total > self.HOLDER_CONCENTRATION_THRESHOLD:
                red_flags.append(f"筹码高度集中！Top 10 地址持有 {top10_total:.2f}%，极易被砸盘收割")
        else:
            print(Fore.YELLOW + "  ⚠️ 无持仓分布数据")

        print()

        # =====================================================
        # [3/5] 流动性是否被操控
        # =====================================================
        print(Fore.WHITE + Style.BRIGHT + "💧 [3/5] 流动性健康度检查")
        print(Fore.WHITE + "─" * 50)

        # GoPlus LP 数据
        if lp_holders:
            for lp in lp_holders[:5]:
                lp_addr = lp.get("address", "???")
                lp_pct = _pct(lp.get("percent")) * 100
                lp_locked = _is_safe(lp.get("is_locked"))
                short_lp = lp_addr[:6] + "..." + lp_addr[-4:]
                lock_label = Fore.GREEN + "🔒已锁" if lp_locked else Fore.RED + "🔓未锁"
                print(f"  LP持有者: {short_lp}  占比: {lp_pct:.2f}%  {lock_label}")
                if lp_pct > 90 and not lp_locked:
                    red_flags.append(f"LP 池子 {lp_pct:.2f}% 由单一地址持有且 **未锁仓**，随时可以 Rug Pull!")

        # DexScreener 流动性
        print(Fore.WHITE + "\n  正在从 DexScreener 获取流动性数据...")
        dex_data = self.client.get_dexscreener_data(token_address)
        if dex_data:
            liq_usd = float(dex_data.get("liquidity", {}).get("usd", 0) or 0)
            vol_24h = float(dex_data.get("volume", {}).get("h24", 0) or 0)
            price_usd = dex_data.get("priceUsd", "N/A")
            pair_label = dex_data.get("baseToken", {}).get("symbol", "?") + "/" + dex_data.get("quoteToken", {}).get("symbol", "?")
            dex_name = dex_data.get("dexId", "未知DEX")
            price_change_5m = dex_data.get("priceChange", {}).get("m5", 0) or 0
            price_change_1h = dex_data.get("priceChange", {}).get("h1", 0) or 0
            price_change_24h = dex_data.get("priceChange", {}).get("h24", 0) or 0

            liq_color = Fore.RED if liq_usd < self.MIN_LIQUIDITY_USD else Fore.GREEN
            print(f"  交易对: {pair_label} ({dex_name})")
            print(f"  当前价格: ${price_usd}")
            print(f"  {liq_color}流动性: ${liq_usd:,.0f}")
            print(f"  24h 交易量: ${vol_24h:,.0f}")
            
            pc5_c = Fore.RED if float(price_change_5m) < -5 else Fore.GREEN
            pc1h_c = Fore.RED if float(price_change_1h) < -10 else Fore.GREEN
            pc24h_c = Fore.RED if float(price_change_24h) < -20 else Fore.GREEN
            print(f"  价格变动: {pc5_c}5m: {price_change_5m}%  {pc1h_c}1h: {price_change_1h}%  {pc24h_c}24h: {price_change_24h}%")

            info_lines.append(f"流动性: ${liq_usd:,.0f} | 24h量: ${vol_24h:,.0f}")

            if liq_usd < self.MIN_LIQUIDITY_USD:
                red_flags.append(f"流动性极低 (仅 ${liq_usd:,.0f})，极易被操控或无法卖出")
            if vol_24h > 0 and liq_usd > 0 and vol_24h / liq_usd > 50:
                warnings.append(f"成交量/流动性比率异常高 ({vol_24h/liq_usd:.0f}x)，可能存在刷量")
        else:
            print(Fore.YELLOW + "  ⚠️ DexScreener 未找到该代币的交易对数据")
            warnings.append("未找到 DEX 交易对数据")

        print()

        # =====================================================
        # [4/5] 社交热度是否被刷
        # =====================================================
        print(Fore.WHITE + Style.BRIGHT + "📣 [4/5] 社交热度分析")
        print(Fore.WHITE + "─" * 50)
        # 通过 DexScreener 的交易模式间接判断
        if dex_data:
            txns_5m = dex_data.get("txns", {}).get("m5", {})
            txns_1h = dex_data.get("txns", {}).get("h1", {})
            txns_24h = dex_data.get("txns", {}).get("h24", {})
            
            buys_5m = int(txns_5m.get("buys", 0) or 0)
            sells_5m = int(txns_5m.get("sells", 0) or 0)
            buys_1h = int(txns_1h.get("buys", 0) or 0)
            sells_1h = int(txns_1h.get("sells", 0) or 0)
            buys_24h = int(txns_24h.get("buys", 0) or 0)
            sells_24h = int(txns_24h.get("sells", 0) or 0)

            print(f"  5分钟交易: 买 {buys_5m} / 卖 {sells_5m}")
            print(f"  1小时交易: 买 {buys_1h} / 卖 {sells_1h}")
            print(f"  24小时交易: 买 {buys_24h} / 卖 {sells_24h}")

            # 判断是否有刷量嫌疑
            if buys_5m > 50 and sells_5m < 5:
                warnings.append(f"5分钟内大量买入({buys_5m}笔)几乎无卖出({sells_5m}笔)，疑似机器人刷量拉盘")
            if sells_1h > buys_1h * 3 and sells_1h > 20:
                warnings.append(f"1小时内卖出笔数({sells_1h})远超买入({buys_1h})，大户可能正在出货")
            if sells_24h > 0 and buys_24h > 0:
                ratio = buys_24h / sells_24h
                if ratio > 10:
                    warnings.append(f"24h买卖比异常 ({ratio:.1f}:1)，可能存在刷量行为")
        else:
            print(Fore.YELLOW + "  ⚠️ 无交易数据可供分析")

        print()

        # =====================================================
        # [5/5] 聪明钱动向 (通过卖出交易模式推断)
        # =====================================================
        print(Fore.WHITE + Style.BRIGHT + "🧠 [5/5] 链上聪明钱(Smart Money)动向推断")
        print(Fore.WHITE + "─" * 50)
        if dex_data:
            # 短期暴跌 + 大量卖出 = 聪明钱可能已出逃
            pc_1h = float(price_change_1h or 0)
            if sells_1h > buys_1h * 2 and pc_1h < -15:
                red_flags.append(f"聪明钱疑似已出逃: 1h 价格暴跌 {pc_1h:.1f}% 且卖出量远超买入")
                print(Fore.RED + f"  🔴 高风险信号: 1h 暴跌 {pc_1h:.1f}% + 卖出({sells_1h}) >> 买入({buys_1h})")
            elif sells_1h > buys_1h and pc_1h < -5:
                warnings.append(f"聪明钱可能正在撤退: 1h 下跌 {pc_1h:.1f}%，卖出笔数多于买入")
                print(Fore.YELLOW + f"  🟡 中风险信号: 1h 下跌 {pc_1h:.1f}%，卖多于买")
            else:
                print(Fore.GREEN + f"  🟢 暂无明显的聪明钱出逃迹象")
            
            # 检查创建者是否还持有
            if audit:
                creator_pct = _pct(audit.get("creator_percent")) * 100
                if creator_pct > 5:
                    print(Fore.YELLOW + f"  创建者仍持有 {creator_pct:.2f}%")
                    warnings.append(f"创建者仍持有 {creator_pct:.2f}%，有抛售风险")
                elif creator_pct == 0:
                    print(Fore.GREEN + f"  创建者已清仓或转移")
        else:
            print(Fore.YELLOW + "  ⚠️ 无市场数据可供推断")

        print()

        # =====================================================
        # 📊 综合评估报告
        # =====================================================
        print(Fore.CYAN + Style.BRIGHT + "=" * 60)
        print(Fore.CYAN + Style.BRIGHT + f"  📊 {token_symbol} 综合风控评估报告")
        print(Fore.CYAN + Style.BRIGHT + "=" * 60)

        # 红线
        if red_flags:
            print(Fore.RED + Style.BRIGHT + f"\n  🚨 严重风险 (红线) — 共 {len(red_flags)} 项:")
            for i, rf in enumerate(red_flags, 1):
                print(Fore.RED + f"    {i}. {rf}")

        # 警告
        if warnings:
            print(Fore.YELLOW + f"\n  ⚠️ 风险警告 — 共 {len(warnings)} 项:")
            for i, w in enumerate(warnings, 1):
                print(Fore.YELLOW + f"    {i}. {w}")

        # 信息摘要
        if info_lines:
            print(Fore.WHITE + f"\n  ℹ️ 关键数据:")
            for line in info_lines:
                print(Fore.WHITE + f"    • {line}")

        # 综合建议
        print()
        if red_flags:
            score_label = Fore.RED + Style.BRIGHT + "🔴 极高风险 — 强烈建议远离或立刻平仓！"
            print(f"  综合评级: {score_label}")
            print(Fore.RED + Style.BRIGHT + "\n  💡 建议: 该代币存在致命风险，切勿买入！若已持仓，建议立即全部卖出止损！")
            self.alert_engine.trigger_red_alert(
                "；".join(red_flags[:3]),
                token_symbol, self.client,
            )
        elif len(warnings) >= 3:
            score_label = Fore.YELLOW + Style.BRIGHT + "🟡 中等风险 — 请谨慎操作"
            print(f"  综合评级: {score_label}")
            print(Fore.YELLOW + "\n  💡 建议: 该代币存在多项风险警告，建议小仓位试水，设好止损，持续监控。")
        elif warnings:
            score_label = Fore.YELLOW + "🟡 低风险 — 注意风控"
            print(f"  综合评级: {score_label}")
            print(Fore.WHITE + "\n  💡 建议: 整体安全性尚可，但仍有部分风险点，建议做好止损管理。")
        else:
            score_label = Fore.GREEN + Style.BRIGHT + "🟢 低风险 — 暂未发现明显风控问题"
            print(f"  综合评级: {score_label}")
            print(Fore.GREEN + "\n  💡 建议: 基础安全检查通过，但请注意 DYOR (Do Your Own Research)，市场有风险。")

        print(Fore.CYAN + "\n" + "=" * 60 + "\n")
        time.sleep(0.5)
