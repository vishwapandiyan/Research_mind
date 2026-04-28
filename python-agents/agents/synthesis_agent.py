"""
SynthesisAgent — cross-page synthesis using filesystem MCP tools.
Reads saved research notes and produces a unified summary.
"""
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from mcp_tools import get_tools

RESEARCH_DIR = str(Path.home() / "ResearchMind")

SYSTEM = f"""You are a research synthesis agent with access to a filesystem.
The research notes are stored in {RESEARCH_DIR}.

Steps:
1. Call list_directory with path="{RESEARCH_DIR}" to see all saved notes
2. Call read_file on the most recent 5-8 .md files
3. Synthesize everything into a comprehensive research summary

Respond ONLY with valid JSON:
{{
  "summary": "multi-paragraph synthesis connecting all sources",
  "key_themes": ["theme1", "theme2"],
  "contradictions": ["contradiction1"],
  "open_questions": ["question1"]
}}"""


async def run_synthesis_agent() -> dict:
    print("[SynthesisAgent] 🚀 Starting synthesis...")
    tools = await get_tools(server="filesystem")
    if not tools:
        print("[SynthesisAgent] ⚠️  Filesystem MCP not available, returning empty synthesis")
        return {
            "summary": "Filesystem MCP not available. Cannot read research notes.",
            "key_themes": [], "contradictions": [], "open_questions": []
        }

    llm = get_llm(temperature=0.3)
    agent = create_react_agent(llm, tools)

    try:
        print(f"[SynthesisAgent] 📂 Reading from: {RESEARCH_DIR}")
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=(
                f"You are a research synthesis agent. Follow these steps:\n"
                f"1. Call list_directory with path='{RESEARCH_DIR}'\n"
                f"2. Call read_file on the most recent 5 .md files you find\n"
                f"3. Synthesize all content and respond with JSON:\n"
                f'{{"summary": "...", "key_themes": [], "contradictions": [], "open_questions": []}}'
            ))]
        })
        last = result["messages"][-1].content
        print(f"[SynthesisAgent] 📝 Raw response: {last[:200]}...")
        last = re.sub(r"<think>.*?</think>", "", last, flags=re.DOTALL).strip()
        raw = re.sub(r"^```json\n?", "", last).rstrip("```").strip()
        try:
            parsed = json.loads(raw)
            print(f"[SynthesisAgent] ✅ Synthesis complete: {len(parsed.get('summary', ''))} chars")
            return parsed
        except Exception as e:
            print(f"[SynthesisAgent] ⚠️  JSON parse failed: {e}, returning raw text")
            return {
                "summary": last[:2000],
                "key_themes": [], "contradictions": [], "open_questions": []
            }
    except Exception as e:
        print(f"[SynthesisAgent] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "summary": f"Synthesis failed: {e}",
            "key_themes": [], "contradictions": [], "open_questions": []
        }
