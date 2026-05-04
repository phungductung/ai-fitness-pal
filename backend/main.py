from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.types import Command
import json
import os
import datetime
import uuid
from typing import List, Optional
from dotenv import load_dotenv

# Import our agents and tools (assuming they are in backend/app)
from app.agents.orchestrator import create_fitness_graph
from app.utils.mcp_client import get_mcp_client
from app.utils.logger import logger, thread_id_var

from fastapi.staticfiles import StaticFiles

load_dotenv()


# Ensure static directory exists
if not os.path.exists("static"):
    os.makedirs("static")

app = FastAPI(title="AI Fitness Architect API")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  # If None, a new thread is created
    history: List[dict] = []  # Kept for backwards-compat but no longer required
    file_path: Optional[str] = None


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool  # True = proceed, False = cancel


# --- Compile graph once at module level ---
graph = create_fitness_graph()


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Streaming endpoint for multi-agent conversation.
    Uses LangGraph checkpointer for persistent threads —
    the frontend only needs to send the latest message + thread_id."""

    # Resolve or create a thread_id
    thread_id = request.thread_id or str(uuid.uuid4())
    thread_id_var.set(thread_id)
    config = {
        "configurable": {"thread_id": thread_id},
        "tags": ["chat_endpoint", "fitness_app"],
        "metadata": {
            "session_id": thread_id,
            "user_id": "default_user",
            "endpoint": "/chat",
        },
    }

    async def event_generator():
        # Send the thread_id first so the frontend can track it
        yield f"event: thread\ndata: {json.dumps({'thread_id': thread_id})}\n\n"

        # Build input messages.  On the first turn we include the system prompt;
        # on subsequent turns the checkpointer already has it.
        current_state = await graph.aget_state(config)
        is_new_thread = not current_state.values.get("messages")

        input_messages = []
        if is_new_thread:
            input_messages.append(
                SystemMessage(
                    content="You are AI Fitness Pal, a comprehensive health and fitness architect. "
                    "You help users with workouts, nutrition, and progress tracking "
                    "using your specialized coach and nutrition agents."
                )
            )
            # Include any legacy history for backwards-compat on the first message
            for msg in request.history:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    input_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    input_messages.append(AIMessage(content=content))

        # Add the new user message
        input_messages.append(HumanMessage(content=request.message))

        inputs = {
            "messages": input_messages,
            "data_context": {"file_path": request.file_path}
            if request.file_path
            else {},
            "intermediate_outputs": [],
        }

        # Track the active node to associate tokens with a sender
        current_node = "assistant"

        logger.info(f"Starting stream for: {request.message[:50]}...")

        try:
            async for event in graph.astream_events(
                inputs, version="v2", config=config
            ):
                kind = event["event"]
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")

                # Only stream tokens from specific nodes to avoid bleeding internal LLM thoughts
                streamable_nodes = ["aggregator"]
                user_facing_nodes = ["aggregator", "safety_guard", "fallback"]
                if kind == "on_chain_start" and node_name in streamable_nodes:
                    current_node = "assistant"
                    logger.debug(f"Entering agent node: {node_name}")
                elif (
                    kind == "on_chain_start"
                    and node_name
                    and not node_name.startswith("__")
                ):
                    current_node = None

                if kind == "on_chat_model_stream" and current_node == "assistant":
                    content = event["data"]["chunk"].content
                    if content:
                        data = json.dumps(
                            {"sender": current_node, "token": content, "type": "text"}
                        )
                        yield f"event: token\ndata: {data}\n\n"

                elif kind == "on_chain_end" and node_name in user_facing_nodes:
                    output = event["data"].get("output")
                    if output and "messages" in output:
                        last_msg = output["messages"][-1]
                        content = ""
                        if hasattr(last_msg, "content"):
                            content = last_msg.content
                        elif isinstance(last_msg, dict):
                            content = last_msg.get("content", "")

                        if isinstance(content, str) and content.strip():
                            sender_name = (
                                "assistant" if node_name == "aggregator" else node_name
                            )
                            data = json.dumps(
                                {
                                    "sender": sender_name,
                                    "content": content,
                                    "type": "text",
                                }
                            )
                            yield f"event: message\ndata: {data}\n\n"
                            logger.debug(f"Finished agent node: {node_name}")

            # --- After streaming finishes, check for an interrupt ---
            final_state = await graph.aget_state(config)
            if final_state.next:  # Graph is paused at an interrupt
                # The interrupt payload contains the confirmation question
                interrupt_data = None
                if final_state.tasks:
                    for task in final_state.tasks:
                        if hasattr(task, "interrupts") and task.interrupts:
                            interrupt_data = task.interrupts[0].value
                            break

                confirmation = interrupt_data or {
                    "question": "A destructive action is pending. Do you approve?"
                }
                data = json.dumps(
                    {
                        "type": "interrupt",
                        "thread_id": thread_id,
                        "question": confirmation.get("question", str(confirmation)),
                        "tool_calls": confirmation.get("tool_calls", []),
                    }
                )
                yield f"event: interrupt\ndata: {data}\n\n"
                logger.info("Interrupted — awaiting human approval")

        except Exception as e:
            logger.error(f"Error in event_generator: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

        yield "event: done\ndata: end\n\n"

    from fastapi.responses import StreamingResponse

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chat/resume")
async def resume_chat(request: ResumeRequest):
    """Resume a paused graph after human-in-the-loop interrupt."""
    thread_id_var.set(request.thread_id)
    config = {
        "configurable": {"thread_id": request.thread_id},
        "tags": ["resume_chat", "fitness_app"],
        "metadata": {
            "session_id": request.thread_id,
            "user_id": "default_user",
            "endpoint": "/chat/resume",
            "approved": request.approved,
        },
    }
    resume_value = "yes" if request.approved else "no"

    async def event_generator():
        current_node = None

        try:
            async for event in graph.astream_events(
                Command(resume=resume_value), version="v2", config=config
            ):
                kind = event["event"]
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")

                streamable_nodes = ["aggregator", "human_review"]
                user_facing_nodes = [
                    "aggregator",
                    "safety_guard",
                    "human_review",
                    "fallback",
                ]
                if kind == "on_chain_start" and node_name in streamable_nodes:
                    current_node = "assistant"
                elif (
                    kind == "on_chain_start"
                    and node_name
                    and not node_name.startswith("__")
                ):
                    current_node = None

                if kind == "on_chat_model_stream" and current_node == "assistant":
                    content = event["data"]["chunk"].content
                    if content:
                        data = json.dumps(
                            {"sender": "assistant", "token": content, "type": "text"}
                        )
                        yield f"event: token\ndata: {data}\n\n"

                elif kind == "on_chain_end" and node_name in user_facing_nodes:
                    output = event["data"].get("output")
                    if output and "messages" in output:
                        last_msg = output["messages"][-1]
                        content = (
                            last_msg.content if hasattr(last_msg, "content") else ""
                        )
                        if isinstance(content, str) and content.strip():
                            data = json.dumps(
                                {
                                    "sender": "assistant",
                                    "content": content,
                                    "type": "text",
                                }
                            )
                            yield f"event: message\ndata: {data}\n\n"

        except Exception as e:
            logger.error(f"Error in resume_chat: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

        yield "event: done\ndata: end\n\n"

    from fastapi.responses import StreamingResponse

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chat/new")
async def new_chat():
    """Create a fresh thread_id for a new conversation."""
    return {"thread_id": str(uuid.uuid4())}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), type: str = Form(...)):
    """Handle image and PDF uploads for GPT-4o analysis."""
    file_path = f"static/temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Logic to send to GPT-4o Vision would go here
    # For now, return a success message
    return {
        "status": "success",
        "filename": file_path,
        "message": "File received for analysis",
    }


@app.get("/morning-briefing")
async def morning_briefing():
    """Generate a daily morning briefing audio using OpenAI TTS."""
    logger.info("Received request for morning briefing")
    from app.utils.tts import MorningBriefing
    # from app.utils.mcp_client import get_local_data # Assuming this helper exists (commented out as it doesn't exist yet)

    api_key = os.getenv("OPENAI_API_KEY")
    briefing_tool = MorningBriefing(api_key)

    # Mocking data for now
    pr_data = [{"Exercise": "Deadlift", "Weight": 180}]
    nutrition_summary = {"calories": 2800, "protein_g": 200}

    script = briefing_tool.compose_briefing_text(pr_data, nutrition_summary)
    audio_path = briefing_tool.generate_briefing_audio(
        script, output_path="static/briefing.mp3"
    )

    return {"status": "success", "audio_url": audio_path, "script": script}


@app.get("/dashboard-data")
async def get_dashboard_data():
    """Fetch real data for the dashboard from MCP."""
    client = get_mcp_client()

    # Get PRs
    prs_json = await client.get_prs()
    try:
        prs = (
            json.loads(prs_json)
            if not prs_json.startswith("Error")
            and not prs_json == "No PR records found."
            else []
        )
    except Exception:
        prs = []

    # Get Diary (last 7 entries)
    diary_json = await client.query_diary(limit=7, order="desc")
    try:
        diary = json.loads(diary_json) if not diary_json.startswith("Error") else []
        # Sort back to ascending for the chart
        diary.sort(key=lambda x: x.get("date", ""))
    except Exception:
        diary = []

    # Format data for the chart - Real-time last 30 days with gap filling
    unique_days = {entry["date"]: entry["weight"] for entry in diary if entry.get("weight") is not None}
    
    weight_progress = []
    today = datetime.date.today()
    
    # We'll fill gaps by looking for the last known weight
    last_known_weight = None
    
    # First, find the oldest weight if we don't have one for the start of our 30-day window
    # Sort all dates we have to find the most recent weight before our window if needed
    all_dates_with_weight = sorted(unique_days.keys())
    
    for i in range(6, -1, -1):
        target_date = today - datetime.timedelta(days=i)
        date_str = target_date.isoformat()
        
        current_weight = unique_days.get(date_str)
        
        if current_weight is not None:
            last_known_weight = current_weight
        elif last_known_weight is None:
            # If we don't have a weight yet for this period, look back in our 100 entries
            # to find the most recent weight before this 7-day window
            older_weights = [unique_days[d] for d in all_dates_with_weight if d < date_str]
            if older_weights:
                last_known_weight = older_weights[-1]
            else:
                # Fallback if absolutely no weight data exists yet
                last_known_weight = 0 
        
        weight_progress.append({
            "date": target_date.strftime("%a"),
            "weight": last_known_weight,
            "full_date": date_str
        })

    # Get today's stats
    today_stats = {"calories": 0, "protein": 0, "weight": 0, "recovery": 88}
    if diary:
        latest = diary[-1]  # Now it's the latest because we sorted it ASC
        today_stats["calories"] = latest.get("calories", 0)
        today_stats["protein"] = latest.get("protein", 0)
        today_stats["weight"] = latest.get("weight", 0)

        # Calculate recovery score
        sleep = latest.get("sleep_hours", 8.0)
        fatigue = latest.get("fatigue", 3)
        # Recovery = (Sleep % of 8 hours) - (Fatigue impact)
        recovery_score = int((sleep / 8.0) * 100 - (fatigue * 5))
        today_stats["recovery"] = max(0, min(100, recovery_score))

    return {"prs": prs, "weight_progress": weight_progress, "today_stats": today_stats}


# --- Cache Management Endpoints ---
@app.get("/cache/stats")
async def cache_stats():
    """Return LLM cache statistics (number of cached entries)."""
    import sqlite3

    cache_path = os.path.join(os.path.dirname(__file__), ".cache", "llm_cache.db")
    if not os.path.exists(cache_path):
        return {"enabled": True, "entries": 0, "size_kb": 0}
    try:
        conn = sqlite3.connect(cache_path)
        cursor = conn.execute("SELECT COUNT(*) FROM full_llm_cache")
        count = cursor.fetchone()[0]
        conn.close()
        size_kb = round(os.path.getsize(cache_path) / 1024, 1)
        return {"enabled": True, "entries": count, "size_kb": size_kb}
    except Exception as e:
        return {"enabled": True, "entries": "unknown", "error": str(e)}


@app.delete("/cache/clear")
async def cache_clear():
    """Clear the entire LLM cache."""
    import sqlite3

    cache_path = os.path.join(os.path.dirname(__file__), ".cache", "llm_cache.db")
    if not os.path.exists(cache_path):
        return {"status": "ok", "message": "Cache already empty"}
    try:
        conn = sqlite3.connect(cache_path)
        conn.execute("DELETE FROM full_llm_cache")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Cache cleared successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
