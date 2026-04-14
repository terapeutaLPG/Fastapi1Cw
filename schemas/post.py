from pydantic import BaseModel, Field


class AuthorBasic(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = False
    tag_ids: list[int] = []


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    published: bool | None = None
    tag_ids: list[int] | None = None


class PostOut(BaseModel):
    id: int
    title: str
    content: str
    published: bool
    author: AuthorBasic
    tags: list[TagOut] = []

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[PostOut]
