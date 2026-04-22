from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class TaskUpdate(BaseModel):
    done: bool


class TaskPut(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    done: bool


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    done: bool | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    done: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[TaskOut]
