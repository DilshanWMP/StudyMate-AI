import os
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from dotenv import load_dotenv

from tools import create_schedule

load_dotenv()

# ---- State Definition ----
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    decision: str | None


# ---- LLM with Tool Bound ----
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.getenv("GROQ_API_KEY"),
)
llm_with_tools = llm.bind_tools([create_schedule])


# ---- Node: agent (calls the LLM) ----
def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# ---- Conditional Edge: did the LLM propose a tool call? ----
def check_tool_call(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "confirm"
    return END


# ---- Node: confirm (the HITL interrupt) ----
def confirm_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    decision = interrupt({
        "action": tool_call["name"],
        "args": tool_call["args"],
    })

    return {"decision": decision}


# ---- Conditional Edge: approve or reject? ----
def check_decision(state: AgentState):
    if state.get("decision") == "approve":
        return "execute_tool"
    return "discard"


# ---- Node: execute_tool (actually runs create_schedule) ----
def execute_tool_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    result = create_schedule.invoke(tool_call["args"])

    tool_message = ToolMessage(
        content=result,
        tool_call_id=tool_call["id"],
    )
    return {"messages": [tool_message]}


# ---- Node: discard (rejected, nothing saved) ----
def discard_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    tool_message = ToolMessage(
        content="Schedule request discarded by user.",
        tool_call_id=tool_call["id"],
    )
    return {"messages": [tool_message]}


# ---- Build the Graph ----
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("confirm", confirm_node)
    graph.add_node("execute_tool", execute_tool_node)
    graph.add_node("discard", discard_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges("agent", check_tool_call, {
        "confirm": "confirm",
        END: END,
    })

    graph.add_conditional_edges("confirm", check_decision, {
        "execute_tool": "execute_tool",
        "discard": "discard",
    })

    graph.add_edge("execute_tool", END)
    graph.add_edge("discard", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


app_graph = build_graph()