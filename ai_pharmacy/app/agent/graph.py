import json
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.nodes import TOOLS, call_model
from app.agent.state import AgentState
from app.config import MEMORY_DB_PATH

_graph_cache = {}

PRODUCT_LOOKUP_TOOLS = {
    "search_products_tool",
    "compare_products_tool",
    "find_cheapest_tool",
    "filter_products_tool",
}

NO_RESULTS_MESSAGE = (
    "Uzr, ushbu so'rov bo'yicha ulangan dorixonalarda (OXYmed, PharmaClick, "
    "Europharm) hech qanday mahsulot topilmadi. Mahsulot nomini tekshirib "
    "qayta yozib ko'ring yoki boshqacha nom bilan (masalan, brend nomisiz) "
    "qidirib ko'ring."
)


def _parse_tool_content(content):
    try:
        return json.loads(content) if isinstance(content, str) else content
    except (TypeError, ValueError):
        return None


def _is_empty_tool_result(content) -> bool:
    data = _parse_tool_content(content)
    if data is None:
        return True
    if isinstance(data, list):
        return len(data) == 0
    if isinstance(data, dict):
        if "count" in data:
            return data["count"] == 0
        if "comparison_table" in data:
            return len(data["comparison_table"]) == 0
    return False


def _fmt_price(p: dict) -> str:
    price = p.get("price")
    price_str = f"{price:,.0f}".replace(",", " ") if price is not None else "narxi noma'lum"
    brand = f" [{p['brand']}]" if p.get("brand") else ""
    stock = "" if p.get("in_stock", True) else " (sotuvda yo'q)"
    return f"{p.get('name')}{brand} — {price_str} {p.get('currency', 'UZS')}, {p.get('store')}{stock}"


def _format_product_list(products: list[dict], limit: int = 10) -> str:
    lines = [f"{i}. {_fmt_price(p)}" for i, p in enumerate(products[:limit], 1)]
    return "\n".join(lines)


def _format_lookup_result(tool_name: str, data) -> str | None:
    if tool_name in ("search_products_tool", "filter_products_tool"):
        if not isinstance(data, list) or not data:
            return None
        return f"Topilgan mahsulotlar:\n{_format_product_list(data)}"

    if tool_name == "compare_products_tool":
        table = data.get("comparison_table") if isinstance(data, dict) else None
        if not table:
            return None
        text = f"Narxlar taqqoslash jadvali:\n{_format_product_list(table)}"
        cheapest = data.get("cheapest")
        if cheapest:
            text += f"\n\nEng arzoni: {_fmt_price(cheapest)}"
        return text

    if tool_name == "find_cheapest_tool":
        if not isinstance(data, dict) or not data:
            return None
        return f"Eng arzon variant: {_fmt_price(data)}"

    if tool_name == "product_details_tool":
        if not isinstance(data, dict) or not data:
            return None
        parts = [f"**{data.get('name')}**"]
        for label, key in [
            ("Brend", "brand"),
            ("Ishlab chiqaruvchi", "manufacturer"),
            ("Doza", "dosage"),
            ("Qadoq soni", "package_size"),
            ("Tavsif", "description"),
            ("Qo'llash bo'yicha ko'rsatma", "usage_instructions"),
            ("Saqlash shartlari", "storage_conditions"),
        ]:
            if data.get(key):
                parts.append(f"{label}: {data[key]}")
        return "\n".join(parts)

    return None


def _build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    return builder


def get_agent():
    """Return a compiled LangGraph agent with SQLite-backed conversation memory."""
    if "agent" in _graph_cache:
        return _graph_cache["agent"]

    Path(MEMORY_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MEMORY_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    graph = _build_graph().compile(checkpointer=checkpointer)
    _graph_cache["agent"] = graph
    return graph


def run_agent(thread_id: str, user_message: str) -> dict:
    """Run one turn of the agent for a given conversation thread. Returns the
    final answer text plus a log of tool calls made during this turn."""
    agent = get_agent()
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke({"messages": [HumanMessage(content=user_message)]}, config=config)

    messages = result["messages"]
    tool_log = []
    final_answer = ""

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                tool_log.append({"tool": call["name"], "args": call["args"]})
        if isinstance(msg, AIMessage) and msg.content:
            final_answer = msg.content

    # Keep only tool calls/results produced during this turn (after the new HumanMessage).
    recent_tool_results = [
        {"tool": m.name, "result": m.content}
        for m in messages[-(len(tool_log) * 2 + 2) :]
        if isinstance(m, ToolMessage)
    ]

    # Grounding safeguard: small local LLMs are not reliable narrators of tool
    # output — they sometimes drop real results or invent extra ones on top of
    # them. So facts (names/prices/stores) are never taken from the model's
    # free text: whenever a product-lookup tool was called this turn, the
    # answer is rebuilt deterministically straight from that tool's JSON.
    lookup_results = [r for r in recent_tool_results if r["tool"] in PRODUCT_LOOKUP_TOOLS]

    if lookup_results:
        if all(_is_empty_tool_result(r["result"]) for r in lookup_results):
            final_answer = NO_RESULTS_MESSAGE
        else:
            seen = set()
            sections = []
            for r in lookup_results:
                key = (r["tool"], r["result"])
                if key in seen:
                    continue
                seen.add(key)
                formatted = _format_lookup_result(r["tool"], _parse_tool_content(r["result"]))
                if formatted:
                    sections.append(formatted)
            if sections:
                final_answer = "\n\n".join(sections)

    return {
        "answer": final_answer,
        "tool_calls": tool_log,
        "tool_results": recent_tool_results,
    }
