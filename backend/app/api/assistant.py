from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.ml.intent import model_info
from app.models import User
from app.services import assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=400)


class Figure(BaseModel):
    label: str
    value: str


class Link(BaseModel):
    label: str
    to: str


class Alt(BaseModel):
    intent: str
    confidence: float


class AskResponse(BaseModel):
    intent: str
    confidence: float
    alternatives: list[Alt]
    entities: dict
    text: str
    figures: list[Figure]
    links: list[Link]
    assumptions: list[str]


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> AskResponse:
    a = assistant.ask(db, payload.question)
    return AskResponse(
        intent=a.intent, confidence=round(a.confidence, 3),
        alternatives=[Alt(intent=i, confidence=round(c, 3)) for i, c in a.alternatives], entities=a.entities, text=a.text,
        figures=[Figure(label=l, value=v) for l, v in a.figures], links=[Link(label=l, to=t) for l, t in a.links], assumptions=a.assumptions,
    )


@router.get("/info")
def info(_: User = Depends(get_current_user)) -> dict:
    return {"model": model_info(), "suggestions": assistant.SUGGESTIONS}
