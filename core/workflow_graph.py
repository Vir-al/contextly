from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import  BaseMessage,AIMessage,HumanMessage # <-- ADD IMPORTS

import sqlite3

import operator
from typing import Annotated, TypedDict, Union

from agents.contextly_agent import ContextlyAgent

REASON_NODE = "reason_node"
ACT_NODE = "act_node"

class AgentState(TypedDict):
    input: str
    agent_outcome: Union[AgentAction, AgentFinish, None]
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    chat_history: Annotated[list[BaseMessage], operator.add]
    


class ContextlyWorkflowV2:
    def __init__(self, contextly_agent: ContextlyAgent):
        self.contextly_agent = contextly_agent
        self.workflow = self._build_workflow()
        sqlite_conn = sqlite3.connect("checkpoint.sqlite", check_same_thread=False)
        memory = SqliteSaver(sqlite_conn)
        self.agent_graph = self.workflow.compile(checkpointer=memory)

    def reason_node(self, state: AgentState):
        agent_output = self.contextly_agent.agent_executor.invoke({
            "chat_history": state.get("chat_history", []), # Pass history here
            "intermediate_steps": state.get("intermediate_steps", [])
        })
        # Handle direct AgentAction or AgentFinish objects
        if isinstance(agent_output, AgentAction) or isinstance(agent_output, AgentFinish):
            return {"agent_outcome": agent_output}

        if isinstance(agent_output, str):
            return {"agent_outcome": AgentFinish(return_values={"output": agent_output}, log="LLM returned a plain response.")}

      
        if isinstance(agent_output, dict):
            if "agent_outcome" in agent_output:
                return {"agent_outcome": agent_output["agent_outcome"]}
            elif "output" in agent_output:
                return {"agent_outcome": AgentFinish(return_values={"output": agent_output["output"]}, log="")}

        raise ValueError(f"Invalid output format from agent: {agent_output}")
    
    def end_node(self, state: AgentState):
       return state['agent_outcome']

    def act_node(self, state: AgentState):
        agent_action = state["agent_outcome"]
        previous_steps = state.get("intermediate_steps", [])

        if isinstance(agent_action, AgentFinish):
            return {"intermediate_steps": previous_steps}

        tool_name = agent_action.tool
        tool_input = agent_action.tool_input

        tool_function = next((t for t in self.contextly_agent.get_tools() if t.name == tool_name), None)

        if tool_function:
            try:
                output = tool_function.invoke(tool_input) if not isinstance(tool_input, dict) else tool_function.invoke(**tool_input)
            except Exception as e:
                output = f"Error invoking tool {tool_name}: {e}"
        else:
            output = f"Tool '{tool_name}' not found"

        return {"intermediate_steps": previous_steps + [(agent_action, str(output))]}
    
    def should_continue(self, state: AgentState) -> str:
         return END if isinstance(state["agent_outcome"], AgentFinish) else ACT_NODE

    def _build_workflow(self) -> StateGraph:
        builder = StateGraph(AgentState)
        builder.add_node(REASON_NODE, self.reason_node)
        builder.add_node(ACT_NODE, self.act_node)
        # builder.add_node(END, self.end_node)

        builder.set_entry_point(REASON_NODE)
        builder.add_conditional_edges(REASON_NODE, self.should_continue)
        builder.add_edge(ACT_NODE, REASON_NODE)

        return builder

    async def invoke(self, query: str, thread_ts: str):
        config = {"configurable": {"thread_id": thread_ts}}
        initial_state = {
            "chat_history": [HumanMessage(content=query)],
            "agent_outcome": None,
            "intermediate_steps": []
        }
        result = self.agent_graph.invoke(initial_state, config)
        # Fix for END node: return plain output instead of trying to await dict
        if isinstance(result, dict) and "agent_outcome" in result:
            outcome = result["agent_outcome"]
            if isinstance(outcome, AgentFinish):
                output = outcome.return_values["output"]
                ai_message = AIMessage(content=output)
                self.agent_graph.update_state(config, {"chat_history": [ai_message]})
                return output
        return result
