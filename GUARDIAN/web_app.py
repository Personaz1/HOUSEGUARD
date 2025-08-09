"""
AI Superintelligent Family Architect Web Application
FastAPI web interface for the AI superintelligent family architect and family guardian
"""

import os
import json
import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid
from collections import deque
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn

# Импортируем кэш
from ai_client.utils.cache import system_cache

# Load environment variables
load_dotenv()

from ai_client.core.client import AIClient
from ai_client.autonomous import IntegrationHub, SystemAnalysisAgent, AutonomousSupervisor, GuardianPolicy
from ai_client.tools.home_tools import HomeTools
from ai_client.tools.vision_service import vision_service
from ai_client.tools.vision_tools import vision_tools
from ai_client.tools.audio_tools import AudioTools
from ai_client.core.response_processor import ResponseProcessor
from ai_client.tools.chat_summary_tools import ChatSummaryTools
from memory.user_profiles import UserProfile
from memory.conversation_history import conversation_history
from bridge.mqtt_bridge import MqttBridge
from bridge.topics import SIM_STEP, ACTUATOR_CMD


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# WebSocket connections list
websocket_connections = []
ACTIVE_STREAMS: Dict[str, str] = {}

class WebSocketLogHandler(logging.Handler):
    """Handler для отправки логов через WebSocket"""
    def emit(self, record):
        try:
            log_entry = self.format(record)
            # Отправляем всем подключенным WebSocket клиентам
            for websocket in websocket_connections[:]:  # Копируем список для безопасной итерации
                try:
                    asyncio.create_task(websocket.send_text(log_entry))
                except Exception as e:
                    # Удаляем отключенные WebSocket
                    websocket_connections.remove(websocket)
        except Exception as e:
            pass  # Игнорируем ошибки WebSocket

# Создаем WebSocket handler
websocket_handler = WebSocketLogHandler()
websocket_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Добавляем WebSocket handler только к основному логгеру
logger.addHandler(websocket_handler)

app = FastAPI(title="ΔΣ Guardian - Superintelligent Family Architect", version="1.0.0")
# Audio tools singleton
audio_tools = AudioTools()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Security
security = HTTPBasic()

# Session management
SESSIONS = {}  # In production, use Redis or database
SESSION_SECRET = secrets.token_urlsafe(32)

# Initialize components
ai_client = AIClient()
response_processor = ResponseProcessor(ai_client)
chat_summary_tools = ChatSummaryTools()
# Autonomous subsystems (background, no server control here)
integration_hub = IntegrationHub(ai_client)
system_agent = SystemAnalysisAgent(ai_client)
guardian_policy = GuardianPolicy()
autonomous_supervisor = AutonomousSupervisor(integration_hub, system_agent, interval_seconds=180, policy=guardian_policy)

# MQTT bridge for simulator controls
mqtt_bridge = MqttBridge(host=os.getenv("MQTT_HOST", "localhost"), port=int(os.getenv("MQTT_PORT", "1883")), client_id="web_app")

# HomeTools instance (SmartHouse REST)
SMARTHOUSE_BASE = os.getenv("SMARTHOUSE_BASE_URL", "http://localhost:8000")
home_tools = HomeTools(base_url=SMARTHOUSE_BASE, role=os.getenv("SMARTHOUSE_ROLE", "admin"))

# SmartHouse SSE events buffer
_smarthouse_events: "deque[Dict[str, Any]]" = deque(maxlen=200)
_sse_task: Optional[asyncio.Task] = None
_analysis_task: Optional[asyncio.Task] = None
# Track last authenticated user for background analysis
CURRENT_USER: Optional[str] = None

# In-memory store for background system tasks
system_tasks: Dict[str, Dict[str, Any]] = {}

# Presence snapshot cache to avoid hammering camera
_presence_cache: Dict[str, Any] = {"ts": None, "data": None}

# Presence feature toggle and camera allowlist
VISION_PRESENCE_ENABLED: bool = os.getenv("VISION_PRESENCE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
_allowed_ids_env = os.getenv("VISION_ALLOWED_IDS", "").strip()
VISION_ALLOWED_IDS: List[str] = [s.strip() for s in _allowed_ids_env.split(",") if s.strip()] if _allowed_ids_env else []

def _get_model_status() -> Dict[str, Any]:
    try:
        return ai_client.get_model_status()
    except Exception as e:
        return {"error": str(e)}

def _get_presence_snapshot() -> Dict[str, Any]:
    try:
        if not VISION_PRESENCE_ENABLED:
            return {"disabled": True}
        # Throttle to once per 120s
        now = datetime.now()
        ts = _presence_cache.get("ts")
        if ts and (now - ts).total_seconds() < 120 and _presence_cache.get("data") is not None:
            return _presence_cache["data"]
        # Pick camera id: env VISION_CAMERA_ID, constrained by allowlist if present
        configured_id = os.getenv("VISION_CAMERA_ID", "0")
        camera_id = configured_id
        if VISION_ALLOWED_IDS:
            if configured_id not in VISION_ALLOWED_IDS:
                camera_id = VISION_ALLOWED_IDS[0]
        presence_raw = vision_tools.estimate_presence(camera_id)
        try:
            presence_parsed = json.loads(presence_raw)
        except Exception:
            presence_parsed = {"raw": presence_raw}
        _presence_cache["ts"] = now
        _presence_cache["data"] = presence_parsed
        return presence_parsed
    except Exception:
        return _presence_cache.get("data") or {"error": "presence_unavailable"}

# --- Vision settings API ---
@app.get("/api/vision/settings")
async def get_vision_settings(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "success": True,
        "settings": {
            "presence_enabled": VISION_PRESENCE_ENABLED,
            "allowed_ids": VISION_ALLOWED_IDS,
            "default_camera_id": os.getenv("VISION_CAMERA_ID", "0"),
        }
    }

@app.post("/api/vision/settings")
async def update_vision_settings(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = await request.json()
    except Exception:
        data = {}
    global VISION_PRESENCE_ENABLED, VISION_ALLOWED_IDS
    # enabled
    if "presence_enabled" in data:
        VISION_PRESENCE_ENABLED = bool(data.get("presence_enabled"))
    # allowed_ids can be list or csv string
    if "allowed_ids" in data:
        aid = data.get("allowed_ids")
        if isinstance(aid, str):
            VISION_ALLOWED_IDS = [s.strip() for s in aid.split(",") if s.strip()]
        elif isinstance(aid, list):
            VISION_ALLOWED_IDS = [str(s).strip() for s in aid if str(s).strip()]
    # default camera id
    if "default_camera_id" in data:
        os.environ["VISION_CAMERA_ID"] = str(data.get("default_camera_id"))
    # reset presence cache
    _presence_cache["ts"] = None
    _presence_cache["data"] = None
    return {"success": True, "message": "Vision settings updated", "settings": {
        "presence_enabled": VISION_PRESENCE_ENABLED,
        "allowed_ids": VISION_ALLOWED_IDS,
        "default_camera_id": os.getenv("VISION_CAMERA_ID", "0"),
    }}

# --- Vision settings page ---
@app.get("/vision", response_class=HTMLResponse)
async def vision_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("vision.html", {"request": request, "username": username})

async def _consume_smarthouse_sse(base_url: str):
    import httpx
    url = base_url.rstrip('/') + "/ui/stream"
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, headers={"Accept": "text/event-stream"}) as resp:
                    resp.raise_for_status()
                    event_type = "message"
                    data_lines: List[str] = []
                    async for raw_chunk in resp.aiter_lines():
                        if raw_chunk is None:
                            continue
                        line = raw_chunk.strip()
                        if not line:
                            # dispatch event
                            if data_lines:
                                data_str = "\n".join(data_lines)
                                try:
                                    payload = json.loads(data_str)
                                except Exception:
                                    payload = {"raw": data_str}
                                _smarthouse_events.append({"type": event_type, "data": payload, "ts": datetime.now().isoformat()})
                            # reset
                            event_type = "message"
                            data_lines = []
                            continue
                        if line.startswith("event:"):
                            event_type = line[len("event:"):].strip() or "message"
                        elif line.startswith("data:"):
                            data_lines.append(line[len("data:"):].strip())
                        # ignore other fields
        except Exception as e:
            logger.warning(f"SSE reconnect in 3s due to: {e}")
            await asyncio.sleep(3)


async def _compute_system_analysis(username: Optional[str]):
    """Heavy LLM system analysis computation in background; stores result in cache."""
    try:
        # Build user context
        if username:
            user_profile = UserProfile(username)
            profile_data = user_profile.get_profile()
            recent_messages = conversation_history.get_recent_history(limit=666)
            context = f"""
User Profile:\n- Name: {profile_data.get('full_name', username)}\n- Bio: {profile_data.get('profile', 'N/A')}\n\nRecent Conversation ({len(recent_messages)} messages):\n{chr(10).join([f"- {msg.get('message', 'N/A')}" for msg in recent_messages]) if recent_messages else "No recent messages"}
"""
        else:
            profile_data = {}
            context = """
System Status:\n- No authenticated user\n- Basic system analysis mode\n- Guardian AI is operational\n- All core functions available
"""

        # Snapshot SmartHouse and events
        try:
            smarthouse_state = home_tools.get_state()
        except Exception:
            smarthouse_state = {"error": "unavailable"}
        recent_events = list(_smarthouse_events)[-20:]

        # System health and vision status
        recent_changes = get_recent_file_changes()
        system_health = ai_client.system.diagnose_system_health()
        vision_status = vision_tools.get_camera_status("default")
        # Presence estimation (THROTTLED) from camera (prefer source 1), SMART method
        try:
            # Throttle presence checks and prefer non-Continuity cameras by default
            cam_env = os.getenv("VISION_CAMERA_ID", "0")
            # basic throttle: only once per 120s
            THROTTLE_KEY = "presence_last_ts"
            now_ts = datetime.now().timestamp()
            last_ts = getattr(globals(), THROTTLE_KEY, 0)
            if now_ts - last_ts >= float(os.getenv("VISION_PRESENCE_THROTTLE_S", "120")):
                globals()[THROTTLE_KEY] = now_ts
                presence_smart_raw = vision_tools.estimate_presence_smart(cam_env)
            else:
                presence_smart_raw = json.dumps({
                    "presence": "cached",
                    "note": "throttled",
                })
            try:
                if isinstance(presence_smart_raw, str) and "Presence:" in presence_smart_raw:
                    json_part = presence_smart_raw.split("Presence:", 1)[1].strip()
                    presence_parsed = json.loads(json_part)
                else:
                    presence_parsed = _get_presence_snapshot()
            except Exception:
                presence_parsed = _get_presence_snapshot()
        except Exception:
            presence_parsed = _get_presence_snapshot()

        additional_prompt = """
Ты — системный наблюдатель-диспетчер дома. Всегда действуй по циклу:
PERCEIVE → THINK → TEST WITH TOOLS → INTEGRATE RESULTS → DECIDE → ACT → NEXT CHECKS.

1) В разделе Tool Plan спланируй конкретные вызовы инструментов (VisionTools/HomeTools), минимум:
   - VisionTools.get_camera_status("default")
   - VisionTools.estimate_presence("default")
   - При сомнениях: VisionTools.capture_image("default") и VisionTools.analyze_image(<последний снимок>)

2) В разделе Tool Results кратко перепиши факты: presence, faces, события, время суток.

3) Decisions & Actions: presence_status (home/away/unknown) с обоснованием, безопасные действия, Next Checks.

JSON:
{
  "system_status": "строка",
  "insights": ["факты"],
  "presence": {"status": "home|away|unknown", "faces": int, "confidence": float},
  "recommended_actions": ["..."],
  "tool_plan": ["VisionTools.estimate_presence(\"default\")", "..."]
}
"""

        # Use placeholder tags to avoid f-string formatting issues inside braces
        analysis_message = (
            "You are Guardian's system analyst. Produce a short, human-readable status first, then a compact JSON.\n\n"
            f"User Context: {context}\n"
            f"Recent Changes: {recent_changes[:500]}\n"
            f"System Health: {system_health[:500]}\n"
            f"Vision Status: {vision_status[:500]}\n"
            f"Presence Snapshot: {json.dumps(presence_parsed)[:400]}\n"
            f"SmartHouse Snapshot (truncated): {json.dumps(smarthouse_state)[:800]}\n"
            f"Recent House Events: {json.dumps(recent_events)[:800]}\n\n"
            "Output format:\n"
            "1) STATUS: one paragraph in natural language (<=80 words), mention user, presence (home/away/unknown), and any actions planned.\n"
            "2) JSON: {{ 'system_status': '...', 'insights': [...], 'presence': {{...}}, 'recommended_actions': [...], 'tool_plan': [...], 'next_checks': [...] }}"
        )

        analysis_response = ai_client.chat(
            message=analysis_message,
            user_profile=profile_data,
            conversation_context=context,
            additional_prompt=additional_prompt,
        )

        # Parse JSON if possible
        try:
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # Удаляем только управляющие символы, НЕ срезая Unicode (кириллицу)
                json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
                analysis_data = json.loads(json_str)
            else:
                # Fallback: показываем только нормализованный текст, без сырого кода и полей raw
                status_text = "System analysis updated."
                analysis_data = {"system_status": status_text, "presence": presence_parsed}
        except Exception:
            analysis_data = {"system_status": "System analysis updated.", "presence": presence_parsed}

        # Сохраняем без параметров, чтобы клиенты без username тоже видели кэш
        system_cache.set("system_analysis", analysis_data, params=None, ttl_seconds=600)
        # И дублируем с параметрами пользователя, если он есть
        if username:
            system_cache.set("system_analysis", analysis_data, params={"username": username, "has_user": True}, ttl_seconds=600)
        logger.info("💾 SYSTEM ANALYSIS: Background result cached")
    except Exception as e:
        logger.error(f"❌ Background system analysis error: {e}")


@app.on_event("startup")
async def _startup_autonomous():
    try:
        await integration_hub.start()
        await autonomous_supervisor.start()
        # Connect MQTT bridge (non-blocking, tolerate absence)
        mqtt_bridge.connect()
        # Start SmartHouse SSE listener
        global _sse_task
        if _sse_task is None:
            _sse_task = asyncio.create_task(_consume_smarthouse_sse(SMARTHOUSE_BASE), name="smarthouse_sse")
        # Start background system analysis loop
        async def _loop():
            # prefer last authenticated user if available
            user = globals().get("CURRENT_USER")
            while True:
                try:
                    # refresh chosen user if changed
                    user = globals().get("CURRENT_USER") or user
                    await _compute_system_analysis(user)
                except Exception as e:
                    logger.warning(f"Background analysis tick error: {e}")
                await asyncio.sleep(30)  # чаще обновляем
        global _analysis_task
        if _analysis_task is None:
            _analysis_task = asyncio.create_task(_loop(), name="system_analysis_loop")
    except Exception as e:
        logger.warning(f"Autonomous startup warning: {e}")


@app.on_event("shutdown")
async def _shutdown_autonomous():
    try:
        await autonomous_supervisor.stop()
        await integration_hub.stop()
        # Stop SSE task
        global _sse_task
        if _sse_task is not None:
            _sse_task.cancel()
            _sse_task = None
        # Stop analysis task
        global _analysis_task
        if _analysis_task is not None:
            _analysis_task.cancel()
            _analysis_task = None
    except Exception as e:
        logger.warning(f"Autonomous shutdown warning: {e}")
# conversation_history = ConversationHistory() # This line is removed

def get_recent_file_changes() -> str:
    """Get recent file changes for system analysis"""
    try:
        import os
        from datetime import datetime, timedelta
        
        changes = []
        changes.append("## RECENT FILE CHANGES")
        
        # Check for recently modified files
        current_time = datetime.now()
        recent_files = []
        
        # Key directories to monitor
        key_dirs = ["", "ai_client.py", "web_app.py", "memory", "templates", "static", "guardian_sandbox"]
        
        for item in key_dirs:
            if os.path.exists(item):
                if os.path.isfile(item):
                    # Single file
                    mtime = datetime.fromtimestamp(os.path.getmtime(item))
                    if current_time - mtime < timedelta(hours=24):
                        recent_files.append((item, mtime))
                else:
                    # Directory
                    for root, dirs, files in os.walk(item):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                                if current_time - mtime < timedelta(hours=24):
                                    recent_files.append((file_path, mtime))
                            except:
                                continue
        
        # Sort by modification time
        recent_files.sort(key=lambda x: x[1], reverse=True)
        
        if recent_files:
            changes.append("Recently modified files (last 24 hours):")
            for file_path, mtime in recent_files[:10]:  # Show top 10
                changes.append(f"- {file_path} (modified: {mtime.strftime('%H:%M:%S')})")
        else:
            changes.append("No recent file changes detected.")
        
        # Check for new files in sandbox
        sandbox_path = "guardian_sandbox"
        if os.path.exists(sandbox_path):
            sandbox_files = []
            for root, dirs, files in os.walk(sandbox_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        ctime = datetime.fromtimestamp(os.path.getctime(file_path))
                        if current_time - ctime < timedelta(hours=24):
                            sandbox_files.append((file_path, ctime))
                    except:
                        continue
            
            if sandbox_files:
                changes.append("\nNew files in sandbox (last 24 hours):")
                for file_path, ctime in sandbox_files[:5]:
                    changes.append(f"- {file_path} (created: {ctime.strftime('%H:%M:%S')})")
        
        return "\n".join(changes)
        
    except Exception as e:
        logger.error(f"Error getting recent file changes: {e}")
        return "Error retrieving recent file changes"

def create_session(username: str) -> str:
    """Create a new session for user"""
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(days=30)  # 30 дней вместо 24 часов
    }
    # Сохраняем сессии в файл
    _save_sessions()
    return session_id

def _save_sessions():
    """Сохранить сессии в файл"""
    try:
        sessions_file = os.path.join(os.path.dirname(__file__), 'sessions.json')
        sessions_data = {}
        for session_id, session in SESSIONS.items():
            sessions_data[session_id] = {
                "username": session["username"],
                "created_at": session["created_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat()
            }
        with open(sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving sessions: {e}")

def _load_sessions():
    """Загрузить сессии из файла"""
    try:
        sessions_file = os.path.join(os.path.dirname(__file__), 'sessions.json')
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
            for session_id, session in sessions_data.items():
                SESSIONS[session_id] = {
                    "username": session["username"],
                    "created_at": datetime.fromisoformat(session["created_at"]),
                    "expires_at": datetime.fromisoformat(session["expires_at"])
                }
    except Exception as e:
        logger.error(f"Error loading sessions: {e}")

# Загружаем сессии при запуске
_load_sessions()

def get_session(session_id: str) -> Optional[Dict]:
    """Get session data"""
    if session_id not in SESSIONS:
        return None
    
    session = SESSIONS[session_id]
    if datetime.now() > session["expires_at"]:
        del SESSIONS[session_id]
        _save_sessions() # Сохраняем после удаления
        return None
    
    return session

def verify_session(request: Request) -> Optional[str]:
    """Verify session and return username"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    
    session = get_session(session_id)
    if not session:
        return None
    
    return session["username"]

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials - fallback for API calls"""
    username = credentials.username
    password = credentials.password
    
    # Load credentials from environment variables
    valid_credentials = {}
    credentials_str = os.getenv('USER_CREDENTIALS', '')
    if credentials_str:
        try:
            # Format: "user1:pass1,user2:pass2"
            for pair in credentials_str.split(','):
                if ':' in pair:
                    user, pwd = pair.strip().split(':', 1)
                    valid_credentials[user] = pwd
        except Exception as e:
            logger.error(f"Error parsing credentials: {e}")
    
    # Simple authentication - in production, use proper password hashing
    if username in valid_credentials and password == valid_credentials[username]:
        return username
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session or query params"""
    # Try session first
    username = verify_session(request)
    if username:
        try:
            globals()["CURRENT_USER"] = username
        except Exception:
            pass
        return username
    
    # Fallback to query params for backward compatibility
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    
    # Check credentials from environment variables
    if username and password:
        valid_credentials = {}
        credentials_str = os.getenv('USER_CREDENTIALS', '')
        if credentials_str:
            try:
                for pair in credentials_str.split(','):
                    if ':' in pair:
                        user, pwd = pair.strip().split(':', 1)
                        valid_credentials[user] = pwd
                if username in valid_credentials and password == valid_credentials[username]:
                    try:
                        globals()["CURRENT_USER"] = username
                    except Exception:
                        pass
                    return username
            except Exception as e:
                logger.error(f"Error parsing credentials: {e}")
    
    return None

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """Handle login and create session"""
    # Load credentials from environment variables
    valid_credentials = {}
    credentials_str = os.getenv('USER_CREDENTIALS', '')
    if credentials_str:
        try:
            # Format: "user1:pass1,user2:pass2"
            for pair in credentials_str.split(','):
                if ':' in pair:
                    user, pwd = pair.strip().split(':', 1)
                    valid_credentials[user] = pwd
        except Exception as e:
            logger.error(f"Error parsing credentials: {e}")
    
    # Fallback to default if no env credentials
    if not valid_credentials:
        logger.warning("No credentials found in environment variables")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Authentication not configured"
        })
    
    # Debug logging (безопасно)
    logger.info(f"Login attempt - Username: '{username}'")
    logger.info(f"Username in valid_credentials: {username in valid_credentials}")
    if username in valid_credentials:
        logger.info(f"Password matches: {password == valid_credentials[username]}")
    
    if username in valid_credentials and password == valid_credentials[username]:
        logger.info(f"Login successful for user: {username}")
        try:
            globals()["CURRENT_USER"] = username
        except Exception:
            pass
        session_id = create_session(username)
        response = RedirectResponse(url="/app", status_code=302)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400  # 24 hours
        )
        # Kick immediate analysis for this user (non-blocking)
        try:
            asyncio.create_task(_compute_system_analysis(username))
        except Exception:
            pass
        return response
    else:
        logger.info(f"Login failed for user: {username}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })



@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Redirect legacy chat to new SPA"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    # Ensure session exists
    if not verify_session(request):
        _ = create_session(username)
    return RedirectResponse(url="/app", status_code=302)

@app.get("/app", response_class=HTMLResponse)
async def app_spa(request: Request):
    """Serve new SPA shell"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("app.html", {"request": request, "username": username})

# ===== Audio trigger UI and API =====
@app.get("/audio", response_class=HTMLResponse)
async def audio_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    html = """
    <!DOCTYPE html>
    <html><head><meta charset='utf-8'><title>Audio Trigger</title>
    <link rel="stylesheet" href="/static/css/guardian.css" />
    </head><body style="padding:24px">
    <h2>Audio Trigger</h2>
    <button id="btn" style="padding:10px 16px">🎤 Listen 5s</button>
    <pre id="out" style="white-space:pre-wrap;margin-top:16px"></pre>
    <script>
    document.getElementById('btn').onclick = async ()=>{
      const fd = new FormData(); fd.append('seconds','5');
      const r = await fetch('/api/audio/listen', {method:'POST', body:fd, credentials:'include'});
      const j = await r.json();
      document.getElementById('out').textContent = JSON.stringify(j, null, 2);
    };
    </script>
    </body></html>
    """
    return HTMLResponse(html)

@app.post("/api/audio/listen")
async def api_audio_listen(request: Request, seconds: int = Form(5), language: str = Form("ru-RU")):
    try:
        res = audio_tools.listen(seconds=seconds, language=language)
        data = json.loads(res)
        return JSONResponse({"success": True, "result": data})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/chat/stream")
async def chat_stream_endpoint(
    request: Request,
    message: str = Form(...)
):
    """Handle chat messages with streaming response"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Create session if user came via URL
    if not verify_session(request) and request.query_params.get("username"):
        session_id = create_session(username)
        # Note: Can't set cookie in streaming response, but session is created
    
    async def generate_stream():
        """Agentic streaming with iterative tool execution until convergence.
        - Streams each LLM step as one chunk
        - Executes detected tool calls sequentially and streams results
        - Feeds tool results back and continues until no more tool calls or step budget
        """
        try:
            import uuid as _uuid
            stream_id = str(_uuid.uuid4())
            # Mark current active stream for user
            ACTIVE_STREAMS[username] = stream_id
            # Send initial status with stream_id so client can de-dup
            yield f"data: {json.dumps({'type': 'status', 'message': 'stream-start', 'stream_id': stream_id})}\n\n"
            # Profile/context
            user_profile = UserProfile(username)
            user_profile_dict = user_profile.get_profile()
            user_profile_dict['username'] = username

            recent_messages = conversation_history.get_recent_history(limit=666)
            base_context = ""
            if recent_messages:
                base_context += "Recent conversation:\n"
                for msg in recent_messages:
                    base_context += f"- User: {msg.get('message', '')}\n"
                    base_context += f"- AI: {msg.get('ai_response', '')}\n"
            recent_changes = get_recent_file_changes()
            if recent_changes:
                base_context += f"\n**SYSTEM CONTEXT:**\n{recent_changes}\n"

            # Settings
            import os as _os
            max_steps = int(_os.getenv("AGENT_MAX_STEPS", "20"))
            tools_per_step = int(_os.getenv("AGENT_TOOLS_PER_STEP", "5"))

            # Accumulators
            full_response = ""
            tool_trace_lines: list[str] = []
            step = 0
            current_message = message

            while step < max_steps:
                step += 1
                # Compose dynamic context with tool results so far
                tool_context = ("\n**TOOL RESULTS SO FAR:**\n" + "\n".join(tool_trace_lines) + "\n") if tool_trace_lines else ""
                dynamic_context = base_context + tool_context

                # If новый стрим уже активен, переводим текущий шаг в фоновую системную задачу и выходим
                if ACTIVE_STREAMS.get(username) != stream_id:
                    try:
                        desc = f"Continue previous chat task: {current_message}"
                        import uuid as _uuid
                        task_id = str(_uuid.uuid4())
                        system_tasks[task_id] = {"id": task_id, "description": desc, "status": "queued"}
                        asyncio.create_task(_run_system_task(task_id, desc, username))
                        yield f"data: {json.dumps({'type': 'status', 'message': 'handed-to-background', 'task_id': task_id, 'stream_id': stream_id})}\n\n"
                    except Exception:
                        pass
                    break
                # Single-step generation with streaming chunks
                step_text = ""
                model_stream = ai_client.generate_streaming_response(
                    user_message=current_message,
                    context=dynamic_context,
                    user_profile=user_profile_dict
                )
                async for step_chunk in model_stream:
                    if ACTIVE_STREAMS.get(username) != stream_id:
                        try:
                            desc = f"Continue previous chat task: {current_message}"
                            import uuid as _uuid
                            task_id = str(_uuid.uuid4())
                            system_tasks[task_id] = {"id": task_id, "description": desc, "status": "queued"}
                            asyncio.create_task(_run_system_task(task_id, desc, username))
                            yield f"data: {json.dumps({'type': 'status', 'message': 'handed-to-background', 'task_id': task_id, 'stream_id': stream_id})}\n\n"
                        except Exception:
                            pass
                        break
                    if step_chunk:
                        step_text += step_chunk
                        full_response += step_chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'content': step_chunk, 'stream_id': stream_id})}\n\n"

                # Extract and execute tool calls found in this step
                tool_calls = response_processor.tool_extractor.extract_tool_calls(step_text or "")
                if not tool_calls:
                    break

                executed = 0
                for tool_call in tool_calls:
                    if executed >= tools_per_step:
                        break
                    try:
                        result = response_processor.tool_executor.execute_tool_call(tool_call, context={'user_profile': user_profile_dict})
                    except Exception as exec_err:
                        result = {"success": False, "error": str(exec_err)}

                    if result.get('success'):
                        out = f"✅ {result.get('result', '')}"
                    else:
                        out = f"❌ Error: {result.get('error', '')}"
                    # Stream tool result as a structured event
                    full_response += "\n" + out
                    yield f"data: {json.dumps({'type': 'tool_result', 'content': out, 'stream_id': stream_id})}\n\n"

                    # Add to trace for the next iteration (short line)
                    fn = getattr(tool_call, 'function_name', 'tool')
                    summary = out
                    if len(summary) > 240:
                        summary = summary[:240] + "…"
                    tool_trace_lines.append(f"- {fn}: {summary}")
                    executed += 1

                # Ask the model to continue planning/actions using the latest tool results
                current_message = "CONTINUE. Integrate the TOOL RESULTS SO FAR and proceed. If task is solved, provide the final concise answer."

            # Completed loop
            yield f"data: {json.dumps({'type': 'message_complete', 'stream_id': stream_id})}\n\n"

            # Persist
            conversation_history.add_message(username, message, full_response)
            cache_key = f"conversation_history_{username}_20"
            system_cache.delete(cache_key)
            cache_key_5 = f"conversation_history_{username}_5"
            system_cache.delete(cache_key_5)
            logger.info(f"🗑️ CONVERSATION CACHE: Cleared cache for {username} after new message")

            # Provide final summary event for UI (SSE v2)
            try:
                final_summary = full_response.strip()
                if len(final_summary) > 2000:
                    final_summary = final_summary[:2000] + "…"
                yield f"data: {json.dumps({'type': 'final_summary', 'content': final_summary, 'stream_id': stream_id})}\n\n"
            except Exception:
                pass

            # Clear only if still current
            if ACTIVE_STREAMS.get(username) == stream_id:
                ACTIVE_STREAMS.pop(username, None)
            yield f"data: {json.dumps({'type': 'complete', 'timestamp': datetime.now().isoformat(), 'stream_id': stream_id})}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming chat: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'stream_id': ACTIVE_STREAMS.get(username)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/chat")
async def chat_endpoint(
    request: Request,
    message: str = Form(...)
):
    """Handle chat messages with regular response"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get user profile
        user_profile = UserProfile(username)
        user_profile_dict = user_profile.get_profile()
        user_profile_dict['username'] = username
        
        # Get conversation context
        recent_messages = conversation_history.get_recent_history(limit=666)
        
        # Build full context
        full_context = ""
        if recent_messages:
            full_context += "Recent conversation:\n"
            for msg in recent_messages:
                full_context += f"- User: {msg.get('message', '')}\n"
                full_context += f"- AI: {msg.get('ai_response', '')}\n"
        
        # Add system context (recent file changes)
        recent_changes = get_recent_file_changes()
        if recent_changes:
            full_context += f"\n**SYSTEM CONTEXT:**\n{recent_changes}\n"
        
        # Generate AI response
        ai_response = ai_client.chat(
            message=message,
            user_profile=user_profile_dict,
            conversation_context=full_context
        )
        
        # ОБРАБОТКА TOOL CALLS ЧЕРЕЗ ResponseProcessor
        logger.info(f"🔧 CHAT: Processing response through ResponseProcessor...")
        
        # Обрабатываем через ResponseProcessor с контекстом
        context = {'user_profile': user_profile_dict}
        processed_response = await response_processor.process_complete_response(ai_response, context)
        
        # Используем форматированный ответ
        ai_response = processed_response.formatted_text
        
        logger.info(f"🔧 CHAT: Response processing completed")
        
        # Save to conversation history
        conversation_history.add_message(username, message, ai_response)
        
        # Clear conversation history cache to force refresh
        cache_key = f"conversation_history_{username}_20"
        system_cache.delete(cache_key)
        cache_key_5 = f"conversation_history_{username}_5"
        system_cache.delete(cache_key_5)
        logger.info(f"🗑️ CONVERSATION CACHE: Cleared cache for {username} after new message")
        
        return JSONResponse({
            "success": True,
            "response": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# ========= System Task API (background agent with tools) =========

async def _run_system_task(task_id: str, description: str, username: Optional[str]) -> None:
    """Run an agentic background task with iterative tool use until completion or limits."""
    try:
        import os as _os
        max_steps = int(_os.getenv("SYSTEM_TASK_MAX_STEPS", "50"))
        tools_per_step = int(_os.getenv("SYSTEM_TASK_TOOLS_PER_STEP", "10"))

        # Prepare user context
        user_profile_dict: Dict[str, Any] = {}
        if username:
            try:
                user_profile = UserProfile(username)
                user_profile_dict = user_profile.get_profile()
                user_profile_dict['username'] = username
            except Exception:
                user_profile_dict = {"username": username}

        recent_messages = conversation_history.get_recent_history(limit=40)
        base_context = ""
        if recent_messages:
            base_context += "Recent conversation:\n"
            for msg in recent_messages:
                base_context += f"- User: {msg.get('message', '')}\n"
                base_context += f"- AI: {msg.get('ai_response', '')}\n"
        try:
            recent_changes = get_recent_file_changes()
            if recent_changes:
                base_context += f"\n**SYSTEM CONTEXT:**\n{recent_changes}\n"
        except Exception:
            pass

        # Init task record
        system_tasks[task_id].update({
            "status": "running",
            "steps": [],
            "started_at": datetime.now().isoformat()
        })

        current_message = f"TASK: {description}. Think step-by-step and use tools when needed."
        step = 0
        while step < max_steps:
            step += 1
            trace = system_tasks.get(task_id, {})
            tool_lines = trace.get("tool_lines", [])
            tool_context = ("\n**TOOL RESULTS SO FAR:**\n" + "\n".join(tool_lines) + "\n") if tool_lines else ""
            dynamic_context = base_context + tool_context

            # Generate one step
            ai_text = ai_client.chat(
                message=current_message,
                user_profile=user_profile_dict,
                conversation_context=dynamic_context
            )

            step_rec = {"step": step, "text": ai_text}
            system_tasks[task_id]["steps"].append(step_rec)
            system_tasks[task_id]["last_update"] = datetime.now().isoformat()

            # Extract and execute tools
            tool_calls = response_processor.tool_extractor.extract_tool_calls(ai_text or "")
            if not tool_calls:
                # Heuristic: stop if model declares done
                if ai_text and ("DONE" in ai_text or "Готово" in ai_text or "Завершено" in ai_text):
                    break
                # Otherwise continue planning briefly
                current_message = "CONTINUE. If task is solved, output final summary and mark DONE."
                continue

            executed = 0
            for tool_call in tool_calls:
                if executed >= tools_per_step:
                    break
                try:
                    result = response_processor.tool_executor.execute_tool_call(tool_call, context={"user_profile": user_profile_dict})
                except Exception as exec_err:
                    result = {"success": False, "error": str(exec_err)}

                if result.get("success"):
                    out = f"✅ {result.get('result', '')}"
                else:
                    out = f"❌ Error: {result.get('error', '')}"
                tool_lines.append(f"- {getattr(tool_call, 'function_name', 'tool')}: {out[:240]}")
                system_tasks[task_id]["steps"].append({"tool": getattr(tool_call, 'function_name', 'tool'), "result": out})
                system_tasks[task_id]["last_update"] = datetime.now().isoformat()
                executed += 1

            current_message = "CONTINUE. Integrate the TOOL RESULTS SO FAR and proceed. When finished, output DONE and the final concise answer."

        system_tasks[task_id]["status"] = "done"
        system_tasks[task_id]["finished_at"] = datetime.now().isoformat()
    except Exception as e:
        system_tasks[task_id]["status"] = "error"
        system_tasks[task_id]["error"] = str(e)
        system_tasks[task_id]["last_update"] = datetime.now().isoformat()


@app.post("/api/system-task/submit")
async def submit_system_task(request: Request, description: str = Form(...)):
    """Submit a background system task; returns task_id."""
    try:
        username = get_current_user(request)
        task_id = str(uuid.uuid4())
        system_tasks[task_id] = {"id": task_id, "description": description, "status": "queued"}
        asyncio.create_task(_run_system_task(task_id, description, username))
        return JSONResponse({"success": True, "task_id": task_id})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/system-task/submit-json")
async def submit_system_task_json(request: Request):
    """Submit system task using JSON body: {"description":"..."}."""
    try:
        data = await request.json()
        description = str(data.get("description", "")).strip()
        if not description:
            return JSONResponse({"success": False, "error": "description required"}, status_code=400)
        username = get_current_user(request)
        task_id = str(uuid.uuid4())
        system_tasks[task_id] = {"id": task_id, "description": description, "status": "queued"}
        asyncio.create_task(_run_system_task(task_id, description, username))
        return JSONResponse({"success": True, "task_id": task_id})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/system-task/{task_id}")
async def get_system_task(task_id: str):
    rec = system_tasks.get(task_id)
    if not rec:
        return JSONResponse({"success": False, "error": "task not found"}, status_code=404)
    return JSONResponse({"success": True, "task": rec})

@app.get("/api/profile")
async def get_profile(request: Request):
    """Get current user's profile"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_profile = UserProfile(username)
        profile_data = user_profile.get_profile()
        profile_data['username'] = username  # Add username to profile data
        
        return JSONResponse({
            "success": True,
            "profile": profile_data
        })
        
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/model-status")
async def api_model_status():
    return JSONResponse({"success": True, "model": _get_model_status()})

@app.post("/api/model/switch")
async def api_model_switch(request: Request):
    try:
        data = await request.json()
        name = data.get("model")
        if not name:
            return JSONResponse({"success": False, "error": "model required"}, status_code=400)
        ok = ai_client.switch_to_model(str(name))
        return JSONResponse({"success": ok})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# --- New lightweight API for SPA ---

@app.get("/api/system-task")
async def list_system_tasks():
    """List all system tasks (shallow)."""
    try:
        return JSONResponse({
            "success": True,
            "tasks": list(system_tasks.values())
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/system-task/{task_id}/cancel")
async def cancel_system_task(task_id: str):
    rec = system_tasks.get(task_id)
    if not rec:
        return JSONResponse({"success": False, "error": "task not found"}, status_code=404)
    rec["status"] = "cancelled"
    rec["cancel_requested"] = True
    rec["last_update"] = datetime.now().isoformat()
    return JSONResponse({"success": True, "task": rec})

@app.get("/api/house/events")
async def get_house_events(limit: int = 50):
    try:
        ev = list(_smarthouse_events)[-abs(limit):]
        return JSONResponse({"success": True, "events": ev})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/house/events/stream")
async def stream_house_events():
    """Server-Sent Events for house events aggregated from SmartHouse /ui/stream."""
    async def event_generator():
        last_len = 0
        # On connect: replay recent tail
        try:
            snapshot = list(_smarthouse_events)
            last_len = len(snapshot)
            tail = snapshot[-20:]
            for ev in tail:
                yield f"data: {json.dumps(ev)}\n\n"
        except Exception:
            pass
        # Live loop
        while True:
            try:
                cur = list(_smarthouse_events)
                if len(cur) > last_len:
                    new_items = cur[last_len:]
                    last_len = len(cur)
                    for ev in new_items:
                        yield f"data: {json.dumps(ev)}\n\n"
                else:
                    # heartbeat
                    yield "event: ping\n" + f"data: {json.dumps({'ts': datetime.now().isoformat()})}\n\n"
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/api/presence")
async def api_presence():
    try:
        return JSONResponse({"success": True, "presence": _get_presence_snapshot()})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/home/state")
async def api_home_state():
    try:
        state = home_tools.get_state()
        return JSONResponse({"success": True, "state": state})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/home/devices")
async def api_home_devices():
    try:
        return JSONResponse({"success": True, "devices": home_tools.list_devices()})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post("/api/home/action")
async def api_home_action(request: Request):
    """Safe wrapper for a subset of actions from HomeTools (light/lock/thermostat)."""
    try:
        data = await request.json()
        action = str(data.get("action", "")).strip()
        device_id = str(data.get("device_id", "")).strip()
        if not device_id:
            return JSONResponse({"success": False, "error": "device_id required"}, status_code=400)

        if action in {"switch_on", "switch_off", "lock_door", "unlock_door"}:
            fn = getattr(home_tools, action, None)
            if not fn:
                return JSONResponse({"success": False, "error": "unsupported"}, status_code=400)
            msg = fn(device_id)
            return JSONResponse({"success": True, "message": msg})

        if action == "set_thermostat":
            temperature = data.get("temperature")
            if temperature is None:
                return JSONResponse({"success": False, "error": "temperature required"}, status_code=400)
            msg = home_tools.set_thermostat(device_id, float(temperature))
            return JSONResponse({"success": True, "message": msg})

        if action == "control_light":
            state = bool(data.get("state", True))
            brightness = data.get("brightness")
            msg = home_tools.control_light(device_id, state, int(brightness) if brightness is not None else None)
            return JSONResponse({"success": True, "message": msg})

        return JSONResponse({"success": False, "error": "action not allowed"}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/profile/{username}")
async def get_profile_by_username(request: Request, username: str):
    """Get profile by username (for avatar loading)"""
    # Only allow getting profiles for meranda and stepan
    if username not in ["meranda", "stepan"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        user_profile = UserProfile(username)
        profile_data = user_profile.get_profile()
        
        return JSONResponse({
            "success": True,
            "profile": profile_data
        })
        
    except Exception as e:
        logger.error(f"Error getting profile for {username}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/avatar/{username}")
async def get_user_avatar(request: Request, username: str):
    """Get user avatar URL without authentication (for display purposes)"""
    # Only allow getting avatars for meranda and stepan
    if username not in ["meranda", "stepan"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        user_profile = UserProfile(username)
        profile_data = user_profile.get_profile()
        
        return JSONResponse({
            "success": True,
            "avatar_url": profile_data.get('avatar_url', ''),
            "username": username
        })
        
    except Exception as e:
        logger.error(f"Error getting avatar for {username}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/profile/update")
async def update_profile_full(request: Request):
    """Update user profile"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        form_data = await request.form()
        
        # Get current profile to preserve existing data
        user_profile = UserProfile(username)
        current_profile = user_profile.get_profile()
        
        # Extract profile data from form, preserving existing data
        profile_data = {
                       'full_name': form_data.get('full_name', current_profile.get('full_name', '')),
                       'age': form_data.get('age', current_profile.get('age', '')),
                       'location': form_data.get('location', current_profile.get('location', '')),
                       'email': form_data.get('email', current_profile.get('email', '')),
           
                       'profile': form_data.get('bio', current_profile.get('profile', '')),  # bio field maps to profile
                       'interests': form_data.get('interests', current_profile.get('interests', '')),
                       'goals': form_data.get('goals', current_profile.get('goals', '')),
                       'challenges': form_data.get('challenges', current_profile.get('challenges', '')),
                       'preferences': form_data.get('preferences', current_profile.get('preferences', '')),
                       'show_feelings': form_data.get('show_feelings') == 'on',
                       'avatar_url': current_profile.get('avatar_url', ''),  # Preserve avatar URL
                       'last_updated': datetime.now().isoformat()
                   }
        
        # Handle password change if provided
        new_password = form_data.get('new_password')
        confirm_password = form_data.get('confirm_password')
        current_password = form_data.get('current_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                return JSONResponse({
                    "success": False,
                    "error": "Passwords do not match"
                }, status_code=400)
            
            # In production, validate current password and hash new password
            if current_password == 'musser':  # Simple validation for demo
                profile_data['password'] = new_password
            else:
                return JSONResponse({
                    "success": False,
                    "error": "Incorrect current password"
                }, status_code=400)
        
        # Update profile
        user_profile._save_profile(profile_data)
        
        return JSONResponse({
            "success": True,
            "message": "Profile updated successfully",
            "profile": profile_data
        })
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/profile/feeling")
async def update_feeling(
    request: Request,
    feeling: str = Form(...),
    context: str = Form("")
):
    """Update user's current feeling"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_profile = UserProfile(username)
        
        
        return JSONResponse({
            "success": True,
            "message": f"Profile updated",
            "feeling": feeling
        })
        
    except Exception as e:
        logger.error(f"Error updating feeling: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/conversation-history")
async def get_conversation_history(
    request: Request,
    limit: int = 20
):
    """Get conversation history - optimized for speed"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Create session if user came via URL
    if not verify_session(request) and request.query_params.get("username"):
        session_id = create_session(username)
        response = JSONResponse({
            "success": True,
            "history": [],
            "count": 0
        })
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400
        )
        return response
    
    try:
        # Проверяем кэш для истории чата (только если нет принудительного обновления)
        force_refresh = request.query_params.get("_t") is not None
        cache_key = f"conversation_history_{username}_{limit}"
        cached_history = system_cache.get(cache_key) if not force_refresh else None
        
        if cached_history and not force_refresh:
            logger.info(f"✅ CONVERSATION HISTORY: Returning cached result for {username}")
            return JSONResponse({
                "success": True,
                "history": cached_history,
                "count": len(cached_history),
                "cached": True
            })
        
        # Для гостя используем отдельную историю
        if username == "guest":
            try:
                with open("memory/guest_conversation_history.json", "r", encoding="utf-8") as f:
                    guest_history = json.load(f)
                logger.info(f"👤 GUEST HISTORY: Loaded {len(guest_history)} messages for guest")
                system_cache.set(cache_key, guest_history, ttl_seconds=120)
                return JSONResponse({
                    "success": True,
                    "history": guest_history,
                    "count": len(guest_history),
                    "cached": False
                })
            except FileNotFoundError:
                logger.info("👤 GUEST HISTORY: No guest history file found, returning empty")
                system_cache.set(cache_key, [], ttl_seconds=300)
                return JSONResponse({
                    "success": True,
                    "history": [],
                    "count": 0,
                    "cached": False
                })
        
        # FAST PATH: Если история пустая, возвращаем сразу
        if not conversation_history.history:
            logger.info(f"⚡ CONVERSATION HISTORY: Empty history - fast return for {username}")
            # Кэшируем пустой результат на 5 минут
            system_cache.set(cache_key, [], ttl_seconds=300)
            return JSONResponse({
                "success": True,
                "history": [],
                "count": 0,
                "cached": False
            })
        
        # Optimize limit for faster loading
        optimized_limit = min(limit, 50)
        logger.info(f"🔄 CONVERSATION HISTORY: Fetching fresh data for {username}")
        history = conversation_history.get_recent_history(limit=optimized_limit)
        
        # Кэшируем результат на 10 секунд для мгновенного обновления
        system_cache.set(cache_key, history, ttl_seconds=10)
        
        logger.info(f"✅ CONVERSATION HISTORY: Loaded {len(history)} messages for {username}")
        
        return JSONResponse({
            "success": True,
            "history": history,
            "count": len(history),
            "cached": False
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "history": [],
            "count": 0
        }, status_code=500)

@app.post("/api/conversation-clear")
async def clear_conversation_history(request: Request):
    """Clear conversation history"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        conversation_history.clear_history()
        
        return JSONResponse({
            "success": True,
            "message": "Conversation history cleared"
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/conversation-history/clear")
async def clear_conversation_history(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        conversation_history.clear_history()
        # clear caches
        system_cache.delete(f"conversation_history_{username}_20")
        system_cache.delete(f"conversation_history_{username}_5")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/conversation-archive")
async def get_conversation_archive(request: Request):
    """Get conversation archive"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Create session if user came via URL
    if not verify_session(request) and request.query_params.get("username"):
        session_id = create_session(username)
        response = JSONResponse({
            "success": True,
            "archive": conversation_history.get_archive_entries(),
            "count": len(conversation_history.get_archive_entries())
        })
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400
        )
        return response
    
    try:
        archive = conversation_history.get_archive_entries()
        
        return JSONResponse({
            "success": True,
            "archive": archive,
            "count": len(archive)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation archive: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.put("/api/conversation-archive/{archive_id}")
async def edit_conversation_archive(
    request: Request,
    archive_id: str,
    summary: str = Form(...)
):
    """Edit conversation archive summary"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        success = conversation_history.edit_archive_entry(archive_id, summary)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Archive summary updated"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Archive not found"
            }, status_code=404)
        
    except Exception as e:
        logger.error(f"Error editing conversation archive: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)



@app.get("/api/files/list")
async def list_files(
    request: Request,
    directory: str = ""
):
    """List files in directory"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Security: only allow listing files in safe directories
        safe_directories = ["memory", "static", "templates"]
        
        if directory and directory not in safe_directories:
            return JSONResponse({
                "success": False,
                "error": "Access denied to this directory"
            }, status_code=403)
        
        target_dir = directory if directory else "."
        files = []
        
        if os.path.exists(target_dir):
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                files.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
                })
        
        return JSONResponse({
            "success": True,
            "files": files,
            "directory": directory
        })
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/files/search")
async def search_files(
    request: Request,
    query: str
):
    """Search files by name"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Security: only search in safe directories
        safe_directories = ["memory", "static", "templates"]
        results = []
        
        for directory in safe_directories:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if query.lower() in file.lower():
                            file_path = os.path.join(root, file)
                            results.append({
                                "name": file,
                                "path": file_path,
                                "size": os.path.getsize(file_path)
                            })
        
        return JSONResponse({
            "success": True,
            "results": results,
            "query": query,
            "count": len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Temporary endpoint to prevent 404 errors from cached frontend
@app.get("/api/hidden-profile")
async def get_hidden_profile_stub(request: Request):
    """Temporary stub for hidden profile - returns empty data"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"success": True, "hidden_profile": "", "username": username, "last_updated": ""}

@app.put("/api/hidden-profile")
async def update_hidden_profile_stub(
    request: Request,
    hidden_profile_text: str = Form(...)
):
    """Temporary stub for hidden profile update"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"success": True, "message": "Hidden profile functionality removed"}

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Serve profile page"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    
    # If user came via URL with credentials, create session
    if not verify_session(request) and request.query_params.get("username"):
        session_id = create_session(username)
        response = templates.TemplateResponse("profile.html", {
            "request": request, 
            "username": username,
            "profile": get_profile_data(username)
        })
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400
        )
        return response
    
    try:
        profile_data = get_profile_data(username)
        return templates.TemplateResponse("profile.html", {
            "request": request, 
            "username": username,
            "profile": profile_data
        })
            
    except Exception as e:
        logger.error(f"Error loading profile page: {e}")
        raise HTTPException(status_code=500, detail="Error loading profile")

def get_profile_data(username: str) -> Dict:
    """Get profile data for user"""
    user_profile = UserProfile(username)
    profile_data = user_profile.get_profile()
    
    # Add default values for new fields
    profile_data.setdefault('email', '')
    profile_data.setdefault('full_name', '')
    profile_data.setdefault('age', '')
    profile_data.setdefault('location', '')

    profile_data.setdefault('show_feelings', True)

    return profile_data

@app.post("/api/profile/avatar")
async def upload_avatar(request: Request):
    """Upload user avatar"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        form_data = await request.form()
        avatar_file = form_data.get('avatar')
        
        if not avatar_file:
            return JSONResponse({"success": False, "error": "No file provided"})
        
        # Create avatars directory if it doesn't exist
        avatar_dir = "static/avatars"
        os.makedirs(avatar_dir, exist_ok=True)
        
        # Save avatar file
        avatar_path = f"{avatar_dir}/{username}_avatar.jpg"
        
        # Read file content properly
        file_content = await avatar_file.read()
        with open(avatar_path, "wb") as f:
            f.write(file_content)
        
        # Update profile with avatar path
        user_profile = UserProfile(username)
        profile_data = user_profile.get_profile()
        profile_data['avatar_url'] = f"/static/avatars/{username}_avatar.jpg"
        user_profile._save_profile(profile_data)
        
        return JSONResponse({
            "success": True, 
            "avatar_url": profile_data['avatar_url'],
            "message": "Avatar uploaded successfully"
        })
        
    except Exception as e:
        logger.error(f"Error uploading avatar: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.delete("/api/profile/delete")
async def delete_account(request: Request):
    """Delete user account"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # In production, implement proper account deletion with data cleanup
        # For now, just return success
        return JSONResponse({"success": True, "message": "Account deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/logout")
async def logout(response: Response):
    """Handle logout and clear session"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")
    return response

@app.get("/api/model-status")
async def get_model_status(request: Request):
    """Get AI model status and quota information - internal agent endpoint, no auth required"""
    
    try:
        # Проверяем кэш
        cached_status = system_cache.get("model_status")
        if cached_status:
            logger.info("✅ MODEL STATUS: Returning cached result")
            return JSONResponse({
                "success": True,
                "status": cached_status,
                "timestamp": datetime.now().isoformat(),
                "cached": True
            })
        
        # Получаем свежие данные
        logger.info("🔄 MODEL STATUS: Fetching fresh data")
        status = ai_client.get_model_status()
        
        # Кэшируем результат на 5 минут
        system_cache.set("model_status", status, ttl_seconds=300)
        
        return JSONResponse({
            "success": True,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "cached": False
        })
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/system-analysis/clear-cache")
async def clear_system_analysis_cache(request: Request):
    """Clear system analysis cache"""
    try:
        username = get_current_user(request)
        # Invalidate any variants (legacy keyed + unified key)
        cache_params = {"username": username, "has_user": bool(username)}
        system_cache.invalidate("system_analysis", cache_params)
        system_cache.invalidate("system_analysis")
        logger.info("🗑️ SYSTEM ANALYSIS: Cache cleared (all variants)")
        
        return JSONResponse({
            "success": True,
            "message": "Cache cleared successfully",
            "smarthouse_events": len(_smarthouse_events)
        })
    except Exception as e:
        logger.error(f"❌ Error clearing cache: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/model-status/clear-cache")
async def clear_model_status_cache(request: Request):
    """Clear model status cache"""
    try:
        system_cache.invalidate("model_status")
        logger.info("🗑️ MODEL STATUS: Cache cleared")
        
        return JSONResponse({
            "success": True,
            "message": "Model status cache cleared successfully"
        })
    except Exception as e:
        logger.error(f"❌ Error clearing model status cache: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/login-greeting")
async def login_greeting(request: Request):
    """Generate personalized greeting for user login"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get user profile
        user_profile = UserProfile(username)
        user_profile_dict = user_profile.get_profile()
        user_profile_dict['username'] = username
        
        # Get conversation context
        recent_messages = conversation_history.get_recent_history(limit=5)
        
        # Build context for greeting
        greeting_context = f"""
        User: {username}
        Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Recent messages: {len(recent_messages)} messages in history
        """
        
        # Generate greeting
        greeting_response = ai_client.chat(
            message="Generate a brief, personalized greeting for the user login. Keep it under 100 words.",
            conversation_context=greeting_context,
            user_profile=user_profile_dict,
            additional_prompt="You are welcoming the user back to the system. Be warm, brief, and acknowledge their return."
        )
        
        return JSONResponse({
            "success": True,
            "greeting": greeting_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating login greeting: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/system-analysis")
async def get_system_analysis(request: Request):
    """Get system analysis - internal agent endpoint, no auth required"""
    
    try:
        # Get current user if available, but don't require it
        username = get_current_user(request)
        
        # Быстрый ответ из кэша (бэкграунд его поддерживает актуальным)
        cache_params = {"username": username, "has_user": bool(username)}
        cached_result = system_cache.get("system_analysis", cache_params, ttl_seconds=600) or system_cache.get("system_analysis", ttl_seconds=600)
        
        if cached_result:
            logger.info("✅ SYSTEM ANALYSIS: Returning cached result")
            # Always return unified shape: { success, analysis: { llm_analysis, live_analysis }, timestamp }
            try:
                from ai_client.autonomous import SystemAnalysisAgent  # local import to avoid top-cycle
                live = globals().get("system_agent").get_last() if globals().get("system_agent") else None
            except Exception:
                live = None
            # If cached_result already looks merged, keep it; else wrap into llm_analysis
            if isinstance(cached_result, dict) and "llm_analysis" in cached_result and "live_analysis" in cached_result:
                merged = cached_result
            else:
                merged = {"llm_analysis": cached_result, "live_analysis": live or {}}
            # Enrich live_analysis with quick presence snapshot and current user if available
            try:
                merged.setdefault("live_analysis", {})["presence"] = _get_presence_snapshot()
            except Exception:
                pass
            try:
                user_hint = username or globals().get("CURRENT_USER")
                if user_hint:
                    merged.setdefault("live_analysis", {})["user"] = user_hint
            except Exception:
                pass
            return JSONResponse({"success": True, "analysis": merged, "timestamp": datetime.now().isoformat()})
        
        # Если кэша нет, запускаем фоновую задачу и возвращаем заглушку
        logger.info("🔧 SYSTEM ANALYSIS: No cached result – kicking background analysis and returning placeholder")
        try:
            asyncio.create_task(_compute_system_analysis(username))
        except Exception:
            pass
        # If live background snapshot is available, return it instead of generic placeholder
        live = globals().get("system_agent").get_last() if globals().get("system_agent") else None
        if live:
            return JSONResponse({"success": True, "analysis": {"llm_analysis": live, "live_analysis": {}}, "timestamp": datetime.now().isoformat()})
        placeholder = {"success": True, "analysis": {"llm_analysis": {"system_status": "Analyzing... (background)", "timestamp": datetime.now().isoformat()}, "live_analysis": {}}, "timestamp": datetime.now().isoformat()}
        return JSONResponse(content=placeholder)
        
        if username:
            # If user is authenticated, get their profile and context
            user_profile = UserProfile(username)
            profile_data = user_profile.get_profile()
            
            # Get conversation history
            recent_messages = conversation_history.get_recent_history(limit=666)
            

            

            

            
            # Build context for LLM - ПОЛНЫЕ ДАННЫЕ ДЛЯ АНАЛИЗА
            context = f"""
User Profile:
- Name: {profile_data.get('full_name', username)}

- Bio: {profile_data.get('profile', 'N/A')}



Recent Conversation ({len(recent_messages)} messages):
{chr(10).join([f"- {msg.get('message', 'N/A')}" for msg in recent_messages]) if recent_messages else "No recent messages"}




"""
        else:
            # If no user authenticated, provide basic system analysis
            context = """
System Status:
- No authenticated user
- Basic system analysis mode
- Guardian AI is operational
- All core functions available
"""

        
        # Get SmartHouse snapshot and recent events
        try:
            smarthouse_state = home_tools.get_state()
        except Exception:
            smarthouse_state = {"error": "unavailable"}
        recent_events = list(_smarthouse_events)[-20:]

        # Get recent file changes and system status + vision status
        recent_changes = get_recent_file_changes()
        system_health = ai_client.system.diagnose_system_health()
        vision_status = vision_tools.get_camera_status("default")
        
        # Generate system analysis using AI — с обязательным циклом инструментов
        additional_prompt = """
Ты — системный наблюдатель-диспетчер дома. Всегда действуй по циклу:
PERCEIVE → THINK → TEST WITH TOOLS → INTEGRATE RESULTS → DECIDE → ACT → NEXT CHECKS.

1) В разделе Tool Plan спланируй конкретные вызовы инструментов (VisionTools/HomeTools), минимум:
   - VisionTools.get_camera_status("default")
   - VisionTools.estimate_presence("default")
   - При сомнениях: VisionTools.capture_image("default") и VisionTools.analyze_image(<последний снимок>)

2) Выполни план (исполняющая среда выполнит вызовы). В разделе Tool Results кратко перепиши факты:
   presence: true/false, faces, события, время суток.

3) В разделе Decisions & Actions:
   - Дай presence_status: home/away/unknown и основание.
   - Предложи безопасные действия (≤30% свет, уведомления).
   - Опиши Next Checks: когда перепроверить и чем.

JSON-формат ответа:
{
  "system_status": "строка",
  "insights": ["факты"],
  "presence": {"status": "home|away|unknown", "faces": int, "confidence": float},
  "recommended_actions": ["..."],
  "tool_plan": ["VisionTools.estimate_presence(\"default\")", "..."]
}
"""

        # Log system analysis start
        logger.info("🔧 SYSTEM ANALYSIS: Starting autonomous analysis...")
        logger.info(f"🔧 SYSTEM ANALYSIS: User context available: {bool(username)}")
        logger.info(f"🔧 SYSTEM ANALYSIS: Recent changes: {len(recent_changes.split())} words")
        logger.info(f"🔧 SYSTEM ANALYSIS: System health: {len(system_health.split())} words")
        
        # Детальное логирование для отладки
        try:
            if username:
                logger.info(f"🔧 SYSTEM ANALYSIS: recent_messages type: {type(recent_messages)}")

            else:
                logger.info("🔧 SYSTEM ANALYSIS: No user context available")
        except NameError:
            logger.info("🔧 SYSTEM ANALYSIS: Variables not initialized (no user context)")
        except Exception as e:
            logger.error(f"🔧 SYSTEM ANALYSIS: Error in debug logging: {e}")

        # Generate analysis
        analysis_message = f"""Analyze the system and take autonomous actions based on this context:

User Context: {context}
Recent Changes: {recent_changes[:500]}
System Health: {system_health[:500]}
Vision Status: {vision_status[:500]}
SmartHouse Snapshot (truncated): {json.dumps(smarthouse_state)[:800]}
Recent House Events: {json.dumps(recent_events)[:800]}"""

        analysis_response = ai_client.chat(
            message=analysis_message,
            user_profile=profile_data if username else {},
            conversation_context=context,
            additional_prompt=additional_prompt
        )

        # Log system analysis completion
        logger.info(f"✅ SYSTEM ANALYSIS: Completed - {len(analysis_response.split())} words generated")
        logger.info(f"✅ SYSTEM ANALYSIS: Response preview: {analysis_response[:100]}...")
        
        # Try to parse JSON response - УЛУЧШЕННАЯ ОБРАБОТКА
        try:
            import re
            # Extract JSON from response - более точный поиск
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # Очищаем JSON от лишних символов
                json_str = re.sub(r'[^\x20-\x7E]', '', json_str)  # Убираем непечатаемые символы
                analysis_data = json.loads(json_str)
                logger.info("✅ SYSTEM ANALYSIS: JSON parsed successfully")
            else:
                # Fallback if no JSON found
                logger.warning("⚠️ SYSTEM ANALYSIS: No JSON found in response")
                analysis_data = {
                    "system_status": analysis_response,
                    "status": analysis_response,
                    "capabilities": "System is operational"
                }
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            logger.error(f"❌ SYSTEM ANALYSIS: JSON parsing failed: {e}")
            analysis_data = {
                "system_status": analysis_response,
                "status": analysis_response,
                "capabilities": "System is operational"
            }
        except Exception as e:
            # General fallback
            logger.error(f"❌ SYSTEM ANALYSIS: General parsing error: {e}")
            analysis_data = {
                "system_status": "System analysis completed",
                "status": "System analysis completed",
                "capabilities": "System is operational"
            }
        
        # Сохраняем в кэш только если нет ошибок (для совместимости пути sync)
        if "❌ Error: 429" not in analysis_response and "❌ Error:" not in analysis_response:
            system_cache.set("system_analysis", analysis_data, cache_params, ttl_seconds=600)
            logger.info("💾 SYSTEM ANALYSIS: Result cached for 10 minutes")
        else:
            logger.warning("⚠️ SYSTEM ANALYSIS: Not caching error response")
            system_cache.invalidate("system_analysis", cache_params)
        
        # Merge on-demand LLM analysis with live background snapshot
        try:
            from ai_client.autonomous import SystemAnalysisAgent  # local import to avoid top-cycle
            # use already initialized system_agent if available
            live = globals().get("system_agent").get_last() if globals().get("system_agent") else None
        except Exception:
            live = None

        merged = {"llm_analysis": analysis_data, "live_analysis": live or {}}
        return JSONResponse({"success": True, "analysis": merged, "timestamp": datetime.now().isoformat()})
        
    except Exception as e:
        logger.error(f"❌ System analysis error: {e}")
        
        # Пробуем вернуть кэшированный результат при ошибке
        try:
            cached_result = system_cache.get("system_analysis", cache_params, ttl_seconds=3600)  # 1 час для fallback
            if cached_result:
                logger.info("✅ SYSTEM ANALYSIS: Returning cached fallback result")
                return JSONResponse(content=cached_result)
        except:
            pass
        
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# Guardian Profile API endpoints


@app.get("/sw.js")
async def service_worker(request: Request):
    """Service Worker for PWA functionality"""
    return FileResponse("static/sw.js", media_type="application/javascript")

# File upload and management endpoints
@app.post("/api/upload-file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload file to sandbox or images directory"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Determine upload directory based on file type
        if file.content_type and file.content_type.startswith('image/'):
            # Images go to static/images for analysis
            upload_dir = "static/images"
            file_path = f"/static/images/{file.filename}"
        else:
            # Other files go to sandbox
            upload_dir = "guardian_sandbox/uploads"
            file_path = f"/guardian_sandbox/uploads/{file.filename}"
        
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return JSONResponse({
            "success": True,
            "file_path": file_path,
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": len(content)
        })
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/analyze-image")
async def analyze_image(request: Request):
    """Analyze uploaded image using AI"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        file_path = data.get("file_path")
        file_name = data.get("file_name")
        user_context = data.get("user_context", "")
        
        if not file_path or not file_name:
            return JSONResponse({
                "success": False,
                "error": "Missing file path or name"
            })
        
        # Remove leading slash for file system path
        fs_path = file_path.lstrip('/')
        
        if not os.path.exists(fs_path):
            return JSONResponse({
                "success": False,
                "error": "File not found"
            })
        
        # Use the new integrated image analysis
        analysis = ai_client.system.analyze_image(fs_path, user_context)
        
        return JSONResponse({
            "success": True,
            "analysis": analysis,
            "model_used": ai_client.models[ai_client.current_model_index]['name'],
            "vision_api_available": ai_client.gemini_client.vision_client is not None
        })
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/delete-file")
async def delete_file(request: Request):
    """Delete uploaded file"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        file_path = data.get("file_path")
        
        if not file_path:
            return JSONResponse({
                "success": False,
                "error": "Missing file path"
            })
        
        # Remove leading slash for file system path
        fs_path = file_path.lstrip('/')
        
        if not os.path.exists(fs_path):
            return JSONResponse({
                "success": False,
                "error": "File not found"
            })
        
        # Delete file
        os.remove(fs_path)
        
        return JSONResponse({
            "success": True,
            "message": "File deleted successfully"
        })
    except Exception as e:
        logger.error(f"File deletion error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

# ========== Vision Online Analyzer ==========
@app.get("/api/vision/status")
async def get_vision_status():
    return JSONResponse({"success": True, "status": vision_service.get_status()})


@app.post("/api/vision/analyze-frame")
async def analyze_frame(request: Request):
    try:
        # Simple rate limit: per-IP allow at most 1 request every 3s
        ip = request.client.host if request.client else "unknown"
        key = f"vision_rl_{ip}"
        last = system_cache.get(key, ttl_seconds=3)
        if last is not None:
            return JSONResponse({"success": False, "error": "Too many requests"}, status_code=429)
        system_cache.set(key, {"ip": ip, "ts": datetime.now().isoformat()}, ttl_seconds=3)

        body = await request.body()
        content_type = request.headers.get("content-type", "")
        use_google = request.query_params.get("google", "false").lower() == "true"
        image_bytes: bytes
        if "application/json" in content_type:
            data = await request.json()
            b64 = data.get("image_base64", "")
            import base64
            image_bytes = base64.b64decode(b64)
        else:
            image_bytes = body
        result = vision_service.analyze_frame(image_bytes, use_google=use_google)
        return JSONResponse({"success": True, "result": result})
    except Exception as e:
        logger.error(f"Vision analyze error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

@app.get("/api/download/{file_path:path}")
async def download_file(request: Request, file_path: str):
    """Download file from sandbox"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Construct full path
        full_path = os.path.join("guardian_sandbox", file_path)
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file for download
        return FileResponse(
            path=full_path,
            filename=os.path.basename(full_path),
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"File download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Message editing endpoints
@app.post("/api/message/edit")
async def edit_message(request: Request):
    """Edit a message in conversation history"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        message_id = data.get("message_id")
        new_content = data.get("new_content")
        
        if not message_id or new_content is None:
            return JSONResponse({
                "success": False,
                "error": "Missing message_id or new_content"
            })
        
        # Edit message in conversation history
        success = conversation_history.edit_message(message_id, new_content)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Message edited successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to edit message"
            })
        
    except Exception as e:
        logger.error(f"Message edit error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/message/delete")
async def delete_message(request: Request):
    """Delete a message from conversation history"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        data = await request.json()
        message_id = data.get("message_id")
        
        if not message_id:
            return JSONResponse({
                "success": False,
                "error": "Missing message_id"
            })
        
        # Delete message from conversation history
        success = conversation_history.delete_message(message_id)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Message deleted successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to delete message"
            })
        
    except Exception as e:
        logger.error(f"Message deletion error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/conversation/archive")
async def archive_conversation(request: Request):
    """Manually archive current conversation"""
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Archive current conversation
        conversation_history._archive_old_messages()
        
        return JSONResponse({
            "success": True,
            "message": "Conversation archived successfully"
        })
        
    except Exception as e:
        logger.error(f"Conversation archive error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/image-analyzer/status")
async def get_image_analyzer_status(request: Request):
    """Get image analyzer status"""
    try:
        # Image analysis is now integrated into ai_client
        status = ai_client.get_model_status()
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"Error getting image analyzer status: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/model/switch")
async def switch_model(request: Request):
    """Switch to a different AI model"""
    try:
        data = await request.json()
        model_name = data.get('model_name')
        
        if not model_name:
            return {"success": False, "error": "Model name is required"}
        
        # Use global AI client instance
        success = ai_client.switch_to_model(model_name)
        
        if success:
            current_model = ai_client.get_model_status()
            return {
                "success": True, 
                "message": f"Switched to {model_name}",
                "current_model": current_model
            }
        else:
            return {"success": False, "error": f"Failed to switch to {model_name}"}
            
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        return {"success": False, "error": str(e)}

@app.get("/roadmap", response_class=HTMLResponse)
async def roadmap_page(request: Request):
    """Development roadmap page"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("roadmap.html", {
        "request": request,
        "username": username
    })

@app.get("/models", response_class=HTMLResponse)
async def models_page(request: Request):
    """AI Models management page"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("models.html", {
        "request": request,
        "username": username
    })

@app.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    """SmartHouse dashboard page"""
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username
    })

@app.get("/simulator", response_class=HTMLResponse)
async def simulator_page(request: Request):
    username = get_current_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("simulator.html", {"request": request, "username": username})

@app.post("/api/sim/step")
async def api_sim_step(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = await request.json()
        step = int(data.get("step", 1))
        ok = mqtt_bridge.publish_json(SIM_STEP, {"dt": 0.05, "sync": True, "step": step})
        return {"success": ok, "published_step": step}
    except Exception as e:
        logger.error(f"/api/sim/step error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/sim/door/open")
async def api_sim_door_open(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        topic = ACTUATOR_CMD.format(device_type="door", device_id="door_1")
        ok = mqtt_bridge.publish_json(topic, {"action": "open"})
        return {"success": ok}
    except Exception as e:
        logger.error(f"/api/sim/door/open error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/sim/health")
async def api_sim_health():
    return {"success": True, "mqtt_connected": mqtt_bridge.is_connected()}

# SmartHouse passthrough endpoints (optional quick control from Guardian UI)
@app.get("/api/home/state")
async def api_home_state(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return {"success": True, "state": home_tools.get_state()}
    except Exception as e:
        logger.error(f"/api/home/state error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/home/events")
async def api_home_events(request: Request, limit: int = 50):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        items = list(_smarthouse_events)[-max(1, min(limit, 200)) :]
        return {"success": True, "events": items, "count": len(items)}
    except Exception as e:
        logger.error(f"/api/home/events error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/home/control_light")
async def api_home_control_light(request: Request):
    username = get_current_user(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = await request.json()
    try:
        text = home_tools.control_light(data.get("device_id"), bool(data.get("state", True)), data.get("brightness"))
        return {"success": True, "result": text}
    except Exception as e:
        logger.error(f"/api/home/control_light error: {e}")
        return {"success": False, "error": str(e)}

# Vision endpoints
@app.get("/api/vision/cameras")
async def list_cameras(request: Request):
    """Get list of available cameras"""
    try:
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.list_cameras()
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error listing cameras: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/vision/presence/{camera_id}")
async def presence_estimation(request: Request, camera_id: str):
    """Estimate human presence from a single frame"""
    try:
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.estimate_presence(camera_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error estimating presence: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/vision/camera/{camera_id}/status")
async def get_camera_status(request: Request, camera_id: str):
    """Get status of specific camera"""
    try:
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.get_camera_status(camera_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/vision/capture")
async def capture_image(request: Request):
    """Capture image from camera"""
    try:
        data = await request.json()
        camera_id = data.get('camera_id', 'default')
        
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.capture_image(camera_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error capturing image: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/vision/analyze")
async def analyze_image(request: Request):
    """Analyze captured image"""
    try:
        data = await request.json()
        image_path = data.get('image_path')
        
        if not image_path:
            return {"success": False, "error": "Image path is required"}
        
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.analyze_image(image_path)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/vision/motion")
async def detect_motion(request: Request):
    """Detect motion from camera"""
    try:
        data = await request.json()
        camera_id = data.get('camera_id', 'default')
        threshold = data.get('threshold', 25.0)
        
        from ai_client.tools.vision_tools import vision_tools
        result = vision_tools.detect_motion(camera_id, threshold)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Error detecting motion: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/chat/generate-title")
async def generate_chat_title(request: Request):
    """Generate title for a chat based on messages"""
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
        title = chat_summary_tools.generate_chat_title(messages)
        return {"success": True, "title": title}
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        return {"success": False, "error": str(e)}

# WebSocket endpoint для real-time логов
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Простой стриминг логов
        last_position = 0
        
        while True:
            try:
                # Читаем лог файл
                with open('app.log', 'r', encoding='utf-8') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    
                    if new_lines:
                        # Отправляем только новые строки
                        for line in new_lines:
                            if line.strip():
                                await websocket.send_text(line.strip())
                        
                        # Обновляем позицию
                        last_position = f.tell()
                
                # Ждем 1 секунду
                await asyncio.sleep(1)
                
            except FileNotFoundError:
                await websocket.send_text("Log file not found")
                break
            except Exception as e:
                await websocket.send_text(f"Log error: {e}")
                break
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 