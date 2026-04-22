from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

class UserCreateDTO(BaseModel):
    name: str
    email: EmailStr

class UserUpdateDTO(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserDTO(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr

    class Config:
        from_attributes = True