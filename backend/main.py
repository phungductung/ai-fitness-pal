from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
import json
import os
import datetime
from typing import List, Optional
from dotenv import load_dotenv

# Import our agents and tools (assuming they are in backend/app)
from app.agents.orchestrator import create_fitness_graph
from app.utils.multimodal import pdf_to_base64_images, encode_image
from app.utils.mcp_client import get_mcp_client

load_dotenv()

from fastapi.staticfiles import StaticFiles
import os

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
    history: List[dict] = []
    file_path: Optional[str] = None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Streaming endpoint for multi-agent conversation using astream_events."""
    graph = create_fitness_graph()
    
    async def event_generator():
        # Convert history to LangGraph message format
        history_messages = [SystemMessage(content="You are AI Fitness Pal, a comprehensive health and fitness architect. You help users with workouts, nutrition, and progress tracking using your specialized coach and nutrition agents.")]
        for msg in request.history:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                history_messages.append(AIMessage(content=content))
        
        # Add the new message
        history_messages.append(HumanMessage(content=request.message))
        
        # Pass file path into the state if provided
        inputs = {
            "messages": history_messages,
            "data_context": {"file_path": request.file_path} if request.file_path else {},
            "intermediate_outputs": []
        }

        
        # Track the active node to associate tokens with a sender
        current_node = "assistant"
        
        print(f"Starting stream for message: {request.message[:50]}...")
        
        try:
            async for event in graph.astream_events(inputs, version="v2"):
                kind = event["event"]
                metadata = event.get("metadata", {})
                node_name = metadata.get("langgraph_node")
                
                # Only set current_node when entering a user-facing agent node
                # This acts as a 'gatekeeper' for the UI
                # Only set current_node for the aggregator to ensure a single blended response
                user_facing_nodes = ["aggregator"]
                if kind == "on_chain_start" and node_name in user_facing_nodes:
                    current_node = "assistant" # Group all blended output under 'assistant'
                    print(f"Entering agent node: {node_name}")


                elif kind == "on_chain_start" and node_name and not node_name.startswith("__"):
                    # For all other nodes (orchestrator, tools, etc.), set current_node to None
                    # to prevent any tokens from leaking to the UI
                    current_node = None

                # Only stream tokens if we are currently inside a user-facing node
                # Only stream tokens from the aggregator
                if kind == "on_chat_model_stream" and current_node == "assistant":


                    content = event["data"]["chunk"].content
                    if content:
                        data = json.dumps({
                            "sender": current_node,
                            "token": content,
                            "type": "text"
                        })
                        yield f"event: token\ndata: {data}\n\n"
                        
                elif kind == "on_chain_end" and node_name in user_facing_nodes:
                    # When a user-facing node finishes, send its final output messages
                    output = event["data"].get("output")
                    if output and "messages" in output:
                        last_msg = output["messages"][-1]
                        content = ""
                        if hasattr(last_msg, "content"):
                            content = last_msg.content
                        elif isinstance(last_msg, dict):
                            content = last_msg.get("content", "")
                        
                        if isinstance(content, str) and content.strip():
                            data = json.dumps({
                                "sender": node_name,
                                "content": content,
                                "type": "text"
                            })
                            yield f"event: message\ndata: {data}\n\n"
                            print(f"Finished agent node: {node_name}")
        except Exception as e:
            print(f"Error in event_generator: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"
        
        yield "event: done\ndata: end\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), type: str = Form(...)):
    """Handle image and PDF uploads for GPT-4o analysis."""
    file_path = f"static/temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Logic to send to GPT-4o Vision would go here
    # For now, return a success message
    return {"status": "success", "filename": file_path, "message": "File received for analysis"}

@app.get("/morning-briefing")
async def morning_briefing():
    """Generate a daily morning briefing audio using OpenAI TTS."""
    print("Received request for morning briefing")
    from app.utils.tts import MorningBriefing
    # from app.utils.mcp_client import get_local_data # Assuming this helper exists (commented out as it doesn't exist yet)
    
    api_key = os.getenv("OPENAI_API_KEY")
    briefing_tool = MorningBriefing(api_key)
    
    # Mocking data for now
    pr_data = [{"Exercise": "Deadlift", "Weight": 180}]
    nutrition_summary = {"calories": 2800, "protein_g": 200}
    
    script = briefing_tool.compose_briefing_text(pr_data, nutrition_summary)
    audio_path = briefing_tool.generate_briefing_audio(script, output_path="static/briefing.mp3")
    
    return {"status": "success", "audio_url": "/static/briefing.mp3", "script": script}

@app.get("/dashboard-data")
async def get_dashboard_data():
    """Fetch real data for the dashboard from MCP."""
    client = get_mcp_client()
    
    # Get PRs
    prs_json = await client.get_prs()
    try:
        prs = json.loads(prs_json) if not prs_json.startswith("Error") and not prs_json == "No PR records found." else []
    except:
        prs = []
    
    # Get Diary (last 7 entries)
    diary_json = await client.query_diary("SELECT * FROM diary ORDER BY date DESC LIMIT 7")
    try:
        diary = json.loads(diary_json) if not diary_json.startswith("Error") else []
        # Sort back to ascending for the chart
        diary.sort(key=lambda x: x.get("date", ""))
    except:
        diary = []
    
    # Format data for the chart
    weight_progress = []
    for entry in diary:
        if entry.get("weight") is not None:
            # Format date to Mon, Tue, etc.
            try:
                dt = datetime.datetime.strptime(entry["date"], "%Y-%m-%d")
                day_name = dt.strftime("%a")
                weight_progress.append({"date": day_name, "weight": entry["weight"], "full_date": entry["date"]})
            except:
                weight_progress.append({"date": entry["date"], "weight": entry["weight"]})

    # Get today's stats
    today_stats = {"calories": 0, "protein": 0, "weight": 0, "recovery": 88}
    if diary:
        latest = diary[-1] # Now it's the latest because we sorted it ASC
        today_stats["calories"] = latest.get("calories", 0)
        today_stats["protein"] = latest.get("protein", 0)
        today_stats["weight"] = latest.get("weight", 0)
        
        # Calculate recovery score
        sleep = latest.get("sleep_hours", 8.0)
        fatigue = latest.get("fatigue", 3)
        # Recovery = (Sleep % of 8 hours) - (Fatigue impact)
        recovery_score = int((sleep / 8.0) * 100 - (fatigue * 5))
        today_stats["recovery"] = max(0, min(100, recovery_score))

    return {
        "prs": prs,
        "weight_progress": weight_progress,
        "today_stats": today_stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
