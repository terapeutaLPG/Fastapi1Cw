from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class TaskUpdate(BaseModel):
    done: bool


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    done: bool
    created_at: datetime

    model_config = {"from_attributes": True}
