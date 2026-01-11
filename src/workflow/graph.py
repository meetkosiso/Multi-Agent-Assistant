from enum import Enum
from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.exceptions import OutputParserException
import src.core.prompts as prompts
from src.agents.researcher import ResearcherAgent
from src.agents.developer import DeveloperAgent
from src.agents.tester import TesterAgent
from src.mcp.client import MCPClient
import logging

# Module-level logger for observability
logger = logging.getLogger(__name__)


class Agent(str, Enum):
    """Enum for agent types in the workflow."""
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    TESTER = "tester"
    FINISH = "finish"


class AgentState(TypedDict):
    """State for the agent workflow graph."""
    query: str
    steps: List[str]
    current_task: str
    result: str


class Workflow:
    """Multi-agent workflow using LangGraph.

    This class orchestrates a supervisor-driven loop with specialized agents
    for research, development, and testing. It includes error handling,
    logging, cycle detection, and structured routing for reliability.
    """
    SUPERVISOR_NODE = "supervisor"
    MAX_ITERATIONS = 20  # Prevent infinite loops

    def __init__(self, llm: ChatOllama, mcp_client: MCPClient):
        self.llm = llm
        self.mcp_client = mcp_client
        self.tools = mcp_client.get_tools()
        self.researcher = ResearcherAgent(llm, self.tools)
        self.developer = DeveloperAgent(llm, self.tools)
        self.tester = TesterAgent(llm, self.tools)
        self.graph = self._build_graph()

    def _supervisor_node(self, state: AgentState) -> Dict[str, Any]:
        """Supervisor node: decides the next agent or to finish.

        Uses the LLM to route based on query and history. Includes
        fallback to researcher on parsing errors.
        """
        try:
            prompt = ChatPromptTemplate.from_template(
                prompts.SUPERVISOR_PROMPT)
            chain = prompt | self.llm | StrOutputParser()
            raw_next_agent = chain.invoke(
                {"query": state["query"], "state": "\n".join(state["steps"])}
            ).strip().lower()

            # More robust matching with logging
            if "researcher" in raw_next_agent:
                next_agent = Agent.RESEARCHER.value
            elif "developer" in raw_next_agent:
                next_agent = Agent.DEVELOPER.value
            elif "tester" in raw_next_agent:
                next_agent = Agent.TESTER.value
            elif "finish" in raw_next_agent:
                next_agent = Agent.FINISH.value
            else:
                logger.warning(
                    "Supervisor output did not match known agent: %s. Falling back to researcher.",
                    raw_next_agent
                )
                next_agent = Agent.RESEARCHER.value

            updated_steps = state["steps"] + [f"Routed to {next_agent}"]
            return {"current_task": next_agent, "steps": updated_steps}

        except OutputParserException as e:
            logger.error("Output parser error in supervisor: %s", e)
            return {
                "current_task": Agent.RESEARCHER.value,
                "steps": state["steps"] + ["Fallback to researcher due to parsing error"]
            }
        except Exception as e:
            logger.exception("Unexpected error in supervisor node: %s", e)
            raise

    def _agent_node(self, agent, name: str):
        """Factory for agent nodes.

        Wraps agent execution with error handling and logging.
        """
        def node(state: AgentState) -> Dict[str, Any]:
            try:
                result = agent.act(state["query"])
                truncated_result = result[:100] + \
                    "..." if len(result) > 100 else result
                updated_steps = state["steps"] + \
                    [f"{name} result: {truncated_result}"]
                return {"result": result, "steps": updated_steps}
            except Exception as e:
                logger.exception("Error in %s agent: %s", name, e)
                error_msg = f"Error in {name}: {str(e)}"
                return {
                    "result": error_msg,
                    "steps": state["steps"] + [error_msg]
                }

        return node

    def _build_graph(self) -> StateGraph:
        """Builds the LangGraph workflow graph.

        Includes agents, edges, conditional routing, and entry point.
        """
        graph = StateGraph(AgentState)

        graph.add_node(self.SUPERVISOR_NODE, self._supervisor_node)

        agents = [
            (Agent.RESEARCHER, self.researcher),
            (Agent.DEVELOPER, self.developer),
            (Agent.TESTER, self.tester),
        ]

        path_map: Dict[str, str] = {
            agent_enum.value: agent_enum.value for agent_enum, _ in agents
        }
        path_map[Agent.FINISH.value] = END

        for agent_enum, agent_inst in agents:
            name = agent_enum.value
            graph.add_node(name, self._agent_node(agent_inst, name))
            graph.add_edge(name, self.SUPERVISOR_NODE)

        def route(state: AgentState) -> str:
            """Conditional router based on current task."""
            task = state["current_task"]
            if task == Agent.FINISH.value:
                return END
            if len(state["steps"]) > self.MAX_ITERATIONS:
                logger.warning(
                    "Max iterations reached for query: %s", state["query"])
                return END
            return path_map.get(task, Agent.RESEARCHER.value)  # Fallback

        graph.add_conditional_edges(
            self.SUPERVISOR_NODE,
            route,
            path_map,
        )

        graph.set_entry_point(self.SUPERVISOR_NODE)
        return graph.compile()

    def run(self, query: str) -> str:
        """Runs the workflow for a given query.

        Initializes state and invokes the graph. Handles top-level errors.
        """
        initial_state: AgentState = {
            "query": query,
            "steps": [],
            "current_task": "",
            "result": ""
        }
        try:
            logger.info("Starting workflow for query: %s", query)
            result_state = self.graph.invoke(initial_state)
            final_result = result_state.get(
                "result", "Workflow completed without result")
            logger.info("Workflow completed for query: %s", query)
            return final_result
        except Exception as e:
            logger.exception("Workflow execution failed for query: %s", query)
            return f"Error during workflow execution: {str(e)}"
