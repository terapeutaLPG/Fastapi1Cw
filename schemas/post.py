from pydantic import BaseModel, Field

class AuthorBasic(BaseModel):
    id:       int
    username: str

    model_config = {"from_attributes": True}

class TagOut(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class PostCreate(BaseModel):
    title:     str
    content:   str
    published: bool      = False
    tag_ids:   list[int] = []

class PostOut(BaseModel):
    id:        int
    title:     str
    content:   str
    published: bool
    author:    AuthorBasic
    tags:      list[TagOut] = []

    model_config = {"from_attributes": True}