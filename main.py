import threading
import time

import pyttsx3
from colorama import Fore, Style, init

from src.llm_agent import LLMAgent

init(autoreset=True)


def speak_alert(text: str) -> None:
    def run() -> None:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}
==============================================================
 Anti-FOMO 币安风控 Agent
 OpenClaw 风格技能包 + Binance Skills Hub 官方能力
==============================================================
 命令:
   0x...                  分析单个代币合约
   chain bsc|eth|base|sol 切换默认链
   热门 bsc               查看热门代币
   聪明钱流入 bsc         查看聪明钱流入榜
   meme 新币 bsc          查看 Meme 新币榜
   异动监控 bsc           查看链上异动
   square <文本>          发布到 Binance Square
   help                   查看帮助
   exit / quit            退出
{Style.RESET_ALL}
"""

HELP_TEXT = """
示例
  0x55d398326f99059ff775485246999027b3197955
  帮我分析 eth 链上的 0xd44e2a841256a392d9f4c10eb7f9177eea3c4444
  热门 bsc
  聪明钱流入 bsc
  meme 新币 bsc
  异动监控 bsc

说明
  - 风控、热门榜和异动监控优先使用 Binance 官方 Skills。
  - 只有官方字段缺失时，才会回退到 GoPlus 或 DexScreener。
  - 报告默认输出中文。
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


if __name__ == "__main__":
    print(BANNER)
    print(Fore.WHITE + "  正在初始化 Agent...\n")

    agent = LLMAgent()
    default_chain = "bsc"

    print(Fore.WHITE + f"  当前默认链: {Fore.CYAN}{default_chain.upper()}{Style.RESET_ALL}")
    print(Fore.WHITE + "  请输入命令，或输入 'help' 查看帮助。\n")

    while True:
        try:
            command = input(Fore.GREEN + "agent > " + Style.RESET_ALL).strip()
            if not command:
                continue

            lower = command.lower()
            if lower in {"exit", "quit"}:
                print(Fore.MAGENTA + "\n正在退出 Anti-FOMO 币安风控 Agent。\n")
                break

            if lower == "help":
                print(HELP_TEXT)
                continue

            if lower.startswith("chain "):
                chain_name = lower.split(" ", 1)[1].strip()
                if chain_name in CHAIN_ALIASES:
                    default_chain = CHAIN_ALIASES[chain_name]
                    print(Fore.GREEN + f"  默认链已切换为 {default_chain.upper()}。\n")
                else:
                    print(Fore.RED + f"  不支持的链: {chain_name}\n")
                continue

            report = agent.process(command, chain=default_chain)
            print(report)

            if "严重风险：" in report or "综合风险：高风险" in report:
                speak_alert("警告，Anti FOMO 币安风控 Agent 检测到高风险。")

        except KeyboardInterrupt:
            print(Fore.MAGENTA + "\n正在退出 Anti-FOMO 币安风控 Agent。\n")
            break
        except Exception as exc:
            print(Fore.RED + f"  发生错误: {exc}")
            time.sleep(1)
