from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.core.prompts import TESTER_PROMPT
from src.agents.base import BaseAgent


class TesterAgent(BaseAgent):
    def _build_chain(self):
        prompt = ChatPromptTemplate.from_template(TESTER_PROMPT)
        return prompt | self.llm | StrOutputParser()
