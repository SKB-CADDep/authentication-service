from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenValidationRequest(BaseModel):
    token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    groups: list[str] = Field(default_factory=list)
    message: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
