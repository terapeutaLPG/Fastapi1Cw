import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, text

from database import engine, Base
from models import comment, note, post, tag, task, user
from routers import auth, calculator, comments, notes, posts, tags, tasks, users
from exceptions import register_exception_handlers

def ensure_tasks_owner_column() -> None:
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "owner_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tasks ADD COLUMN owner_id INTEGER"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_tasks_owner_id ON tasks (owner_id)"))

ensure_tasks_owner_column()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog API",
    version="1.2",
    description=(
        "REST API z autoryzacją JWT i kontrolą dostępu.\n\n"
        "[Powrót do strony nawigacyjnej](/)"
    ),
)
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Process-Time"] = str(duration)
    print(f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms)")
    return response

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/notes")
def notes_page(request: Request):
    return templates.TemplateResponse("notes.html", {"request": request})

@app.get("/todo/login")
def todo_login_page(request: Request):
    return templates.TemplateResponse("todo_login.html", {"request": request})

@app.get("/todo")
def todo_page(request: Request):
    return templates.TemplateResponse("todo_app.html", {"request": request})

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(tags.router)
app.include_router(tasks.router)
app.include_router(calculator.router)
app.include_router(notes.router)
