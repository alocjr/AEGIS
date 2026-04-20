import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aegis")

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

from app.config import settings
from app.database import db, init_indexes
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.course import router as course_router
from app.routes.maturity import router as maturity_router
from app.routes.progress import router as progress_router
from app.routes.quiz import router as quiz_router
from app.routes.public import router as public_router


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_VUE_DIST = BASE_DIR / "frontend-vue" / "dist"
FRONTEND_VUE_PUBLIC = BASE_DIR / "frontend-vue" / "public"
COURSE_FILE = BASE_DIR / "backend" / "data" / "course.json"

USE_VUE_UI = FRONTEND_VUE_DIST.exists() and (FRONTEND_VUE_DIST / "index.html").is_file()
# Landing page: lp.html (em dist após build, ou em public em dev)
LANDING_HTML = FRONTEND_VUE_DIST / "lp.html"
LANDING_HTML_DEV = FRONTEND_VUE_PUBLIC / "lp.html"

COURSE_SLUG = "trilha-ia-executiva"

# CORS: restrito às origens configuradas (evita allow_origins=["*"] com credentials)
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = ["http://localhost:5173"]

app = FastAPI(title="Valorian 4 Future API", version="1.0.0")


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Captura apenas exceções não tratadas; deixa HTTPException e ValidationError para o FastAPI."""
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_course_if_needed() -> None:
    if db.courses.find_one({"slug": COURSE_SLUG}):
        return
    course_data = json.loads(COURSE_FILE.read_text(encoding="utf-8"))
    db.courses.insert_one({"slug": COURSE_SLUG, **course_data})


@app.on_event("startup")
def startup() -> None:
    if not settings.mongodb_uri or not settings.jwt_secret_key:
        raise RuntimeError(
            "Configure MONGODB_URI e JWT_SECRET_KEY no ambiente ou no arquivo .env. "
            "Veja .env.example para referência."
        )
    init_indexes()
    seed_course_if_needed()
    logger.info("Application started")


@app.get("/api/health")
def health():
    """Health check para load balancer e monitoramento. Inclui checagem do MongoDB."""
    try:
        db.client.admin.command("ping")
        return {"status": "ok", "mongodb": "connected"}
    except Exception as e:
        logger.warning("Health check MongoDB failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "mongodb": "disconnected", "detail": str(e)},
        )


app.include_router(auth_router)
app.include_router(course_router)
app.include_router(progress_router)
app.include_router(maturity_router)
app.include_router(quiz_router)
app.include_router(admin_router)
app.include_router(public_router)

if USE_VUE_UI:
    app.mount("/assets", StaticFiles(directory=FRONTEND_VUE_DIST / "assets"), name="vue_assets")

    def _vue_index():
        return FileResponse(FRONTEND_VUE_DIST / "index.html", headers=NO_CACHE_HEADERS)

    def _landing():
        """Landing page: lp.html (aparência exata). Fallback para SPA se arquivo não existir."""
        if LANDING_HTML.exists():
            return FileResponse(LANDING_HTML, headers=NO_CACHE_HEADERS)
        if LANDING_HTML_DEV.exists():
            return FileResponse(LANDING_HTML_DEV, headers=NO_CACHE_HEADERS)
        return _vue_index()

    @app.get("/favicon.svg")
    def vue_favicon():
        return FileResponse(FRONTEND_VUE_DIST / "favicon.svg", headers=NO_CACHE_HEADERS)

    @app.get("/")
    def root():
        return _landing()

    @app.get("/index")
    @app.get("/index.html")
    def index_legacy():
        return RedirectResponse(url="/programa", status_code=302)

    @app.get("/programa")
    def programa_page():
        return _vue_index()

    @app.get("/ai-maturity")
    def ai_maturity_page():
        return _vue_index()

    @app.get("/admin")
    @app.get("/admin/trilhas")
    @app.get("/admin/usuarios")
    @app.get("/admin/alunos")
    @app.get("/admin/progresso")
    @app.get("/admin/quiz")
    def admin_pages():
        return _vue_index()

    @app.get("/quiz-respostas")
    def quiz_respostas_page():
        return _vue_index()

    @app.get("/agenda")
    def agenda_page():
        return _vue_index()

    @app.get("/login")
    def login_page():
        return _vue_index()

    @app.get("/quiz/{encontro_id:int}")
    def quiz_page(encontro_id: int):
        return _vue_index()

    @app.get("/trilhas")
    def trilhas_page():
        return _vue_index()

    @app.get("/trilhas/{slug:path}")
    def trilha_showcase_page(slug: str):
        return _vue_index()

    @app.get("/{full_path:path}")
    def vue_spa_fallback(full_path: str):
        """Fallback SPA: qualquer rota não API/static/assets retorna o index da Vue."""
        return _vue_index()

else:
    # Sem dist da Vue (ex.: só backend em dev): servir landing lp.html em / se existir
    if LANDING_HTML_DEV.exists():

        @app.get("/")
        def root_no_vue():
            return FileResponse(LANDING_HTML_DEV, headers=NO_CACHE_HEADERS)

        @app.get("/login")
        def login_no_vue():
            """Sem Vue UI: redireciona para a landing; o login exige o app Vue."""
            return RedirectResponse(url="/", status_code=302)
