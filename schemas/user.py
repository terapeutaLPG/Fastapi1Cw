from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str      = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email:    EmailStr
    password: str      = Field(min_length=8)

class UserOut(BaseModel):
    id:       int
    username: str
    email:    str
    role:     str

    model_config = {"from_attributes": True}

class PasswordChange(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=8)