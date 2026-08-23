import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        missing = []
        if len(value) < 8:
            missing.append("at least 8 characters")
        if not any(c.isupper() for c in value):
            missing.append("an uppercase letter")
        if not any(c.islower() for c in value):
            missing.append("a lowercase letter")
        if not any(c.isdigit() for c in value):
            missing.append("a digit")
        if not any(not c.isalnum() for c in value):
            missing.append("a special character")
        if missing:
            raise ValueError("Password must contain " + ", ".join(missing))
        return value


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: Role
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: EmailStr
    role: Role
