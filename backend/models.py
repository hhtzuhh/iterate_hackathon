from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class InsuranceRequest(BaseModel):
    insurance_number: str
