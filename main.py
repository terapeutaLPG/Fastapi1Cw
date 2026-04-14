import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from models import comment, post, tag, task, user
from routers import auth, calculator, comments, posts, tags, tasks, users
from exceptions import register_exception_handlers

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog API",
    version="1.2",
    description="REST API z autoryzacją JWT i kontrolą dostępu",
)

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

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(tags.router)
app.include_router(tasks.router)
app.include_router(calculator.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
