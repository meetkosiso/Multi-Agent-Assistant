from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.core.prompts import RESEARCHER_PROMPT
from src.agents.base import BaseAgent


class ResearcherAgent(BaseAgent):
    def _build_chain(self):
        prompt = ChatPromptTemplate.from_template(RESEARCHER_PROMPT)
        return prompt | self.llm | StrOutputParser()
