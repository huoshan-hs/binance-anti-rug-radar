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
 Binance 土狗防 Rug 雷达
 Binance Skills Hub 风控 + Smart Money + 持续监控 Demo
==============================================================
 命令:
   0x...                  分析单个代币合约
   chain bsc|eth|base|sol 切换默认链
   雷达 bsc                查看 BSC 观察名单快照
   监控 bsc                查看 BSC 观察名单快照
   help                   查看帮助
   exit / quit            退出
{Style.RESET_ALL}
"""

HELP_TEXT = """
示例
  0x55d398326f99059ff775485246999027b3197955
  帮我分析 eth 链上的 0xd44e2a841256a392d9f4c10eb7f9177eea3c4444
  雷达 bsc
  监控 bsc

说明
  - 单币分析会优先使用 Binance 官方审计、市场和 smart money 数据。
  - 输出重点不是“字段罗列”，而是：
    1. 是否值得继续看
    2. 最大风险点
    3. 下一步建议
  - “雷达 bsc” 会生成 BSC 新 meme 观察名单快照。
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
    print(Fore.WHITE + "  正在初始化雷达引擎...\n")

    agent = LLMAgent()
    default_chain = "bsc"

    print(Fore.WHITE + f"  当前默认链: {Fore.CYAN}{default_chain.upper()}{Style.RESET_ALL}")
    print(Fore.WHITE + "  请输入命令，或输入 'help' 查看帮助。\n")

    while True:
        try:
            command = input(Fore.GREEN + "radar > " + Style.RESET_ALL).strip()
            if not command:
                continue

            lower = command.lower()
            if lower in {"exit", "quit"}:
                print(Fore.MAGENTA + "\n正在退出 Binance 土狗防 Rug 雷达。\n")
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

            if "综合风险: 高风险" in report:
                speak_alert("警告，Binance 土狗防 Rug 雷达检测到高风险代币。")

        except KeyboardInterrupt:
            print(Fore.MAGENTA + "\n正在退出 Binance 土狗防 Rug 雷达。\n")
            break
        except Exception as exc:
            print(Fore.RED + f"  发生错误: {exc}")
            time.sleep(1)
