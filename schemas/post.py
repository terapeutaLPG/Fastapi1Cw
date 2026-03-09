from pydantic import BaseModel

class AuthorBasic(BaseModel):
    id:       int
    username: str

    model_config = {"from_attributes": True}

class TagOut(BaseModel):
    id:   int
    name: str

    model_config = {"from_attributes": True}

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