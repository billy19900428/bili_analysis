#!/usr/bin/env python
import warnings
from datetime import datetime


warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

try:
    from crew import BiliAnalysis
except ImportError:
    print("请以模块方式运行：python -m src.bili_analysis.main")
    exit(1)

def run():
    # ① 优先拿命令行参数（你后续想改回命令行也能用）
    import sys
    if len(sys.argv) >= 2:
        topic = sys.argv[1]
    else:
        # ② PyCharm 运行时弹框输入
        topic = input("请输入搜索关键词（如：AI工作流）：").strip()
        if not topic:
            print("关键词不能为空！")
            exit(1)

    inputs = {
        'topic': topic,
        'current_year': str(datetime.now().year)
    }

    print(f"[INFO] 即将开始抓取，关键词：{inputs['topic']}")
    try:
        BiliAnalysis().crew().kickoff(inputs=inputs)
    except Exception as e:
        print(f"[ERROR] 运行 crew 时出错: {e}")
        exit(2)

if __name__ == "__main__":
    run()