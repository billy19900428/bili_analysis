from crewai import Agent, Crew, Process, Task,LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from tools.search_tool import BilibiliSearchTool
import os

# 创建工具实例
bilibili_tool = BilibiliSearchTool()

# 创建大模型
# 配置千问模型
qwen_llm = LLM(
    model="qwen-plus",  # 可选：qwen-turbo, qwen-max, qwen2.5-coder 等
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    custom_llm_provider="openai"
)

@CrewBase
class BiliAnalysis():
    """BiliAnalysis crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def data_crawling_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['data_crawling_engineer'], # type: ignore[index]
            tools=[bilibili_tool],
            llm=qwen_llm,
            verbose=True
        )

    @agent
    def data_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['data_analyst'], # type: ignore[index]
            llm=qwen_llm,
            verbose=True
        )


    @task
    def data_collection_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_collection_task'], # type: ignore[index]

        )

    @task
    def analyst_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyst_task'], # type: ignore[index]
            output_file='report1.md'
        )

    @task
    def competitive_account_production_task(self) -> Task:
        return Task(
            config=self.tasks_config['competitive_account_production_task'],  # type: ignore[index]
            output_file='report2.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the BiliAnalysis crew"""


        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )

# ===================== 供 Streamlit 调用的入口 =====================
def run_crew(keyword: str):
    """
    纯函数入口，避免再启子进程
    """
    from datetime import datetime
    from crew import BiliAnalysis          # 同文件里直接再导入就行

    inputs = {
        'topic': keyword,
        'current_year': str(datetime.now().year)
    }
    BiliAnalysis().crew().kickoff(inputs=inputs)