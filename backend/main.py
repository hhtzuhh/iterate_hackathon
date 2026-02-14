"""FastAPI application with SSE chat endpoint"""
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from .agent import root_agent
from .adk_sse_wrapper import run_agent_sse
from .config import settings
from .models import ChatRequest
from google.adk.runners import InMemoryRunner

app = FastAPI(
    title="Blaxel Hello World Agent",
    description="Hello World SSE agent powered by Claude via Google ADK",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "blaxel-agent", "version": "1.0.0"}


@app.get("/api/sandbox/run")
async def sandbox_run():
    """Connect to Blaxel sandbox and run 2+2 inside it."""
    import os
    os.environ.setdefault("BL_WORKSPACE", settings.bl_workspace)
    os.environ.setdefault("BL_API_KEY", settings.bl_api_key)

    from blaxel.core import SandboxInstance

    sandbox = await SandboxInstance.get(settings.sandbox_name)
    result = await sandbox.process.exec({
        "command": "python3 -c \"print(2+2)\"",
        "wait_for_completion": True,
        "timeout": 15000,
    })
    return {
        "command": result.command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "status": result.status,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    runner = InMemoryRunner(agent=root_agent, app_name=settings.app_name)
    session = await runner.session_service.create_session(
        app_name=settings.app_name,
        user_id="web_user",
    )

    async def sse_generator():
        async for payload in run_agent_sse(
            runner=runner,
            session_id=session.id,
            user_id="web_user",
            message=req.message,
        ):
            yield {"data": payload}

    return EventSourceResponse(sse_generator())


# Static files must be mounted last so API routes take priority
if settings.frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(settings.frontend_dir), html=True),
        name="frontend",
    )
