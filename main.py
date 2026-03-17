from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from models import user, post, tag, comment
from routers import auth, users, posts, comments, tags
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

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(tags.router)