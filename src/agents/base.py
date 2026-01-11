from abc import ABC, abstractmethod
from langchain_ollama import ChatOllama
from typing import List
from langchain.tools import BaseTool


class BaseAgent(ABC):
    def __init__(self, llm: ChatOllama, tools: List[BaseTool] = None):
        self.llm = llm
        self.tools = tools or []
        self.chain = self._build_chain()

    @abstractmethod
    def _build_chain(self):
        pass

    def act(self, task: str) -> str:
        if self.tools:
            bound_llm = self.llm.bind_tools(self.tools)
            return self.chain.invoke({"task": task, "llm": bound_llm})
        return self.chain.invoke({"task": task})
