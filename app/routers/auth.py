from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from ..deps import SessionDep
from ..models import User
from ..security import issue_access_token
from ..services import otp as otp_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RequestOtpIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)


class RequestOtpOut(BaseModel):
    request_id: str


class VerifyOtpIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    otp: str = Field(min_length=4, max_length=8)
    name: str | None = Field(default=None, max_length=80)
    avatar: str | None = None


class UserOut(BaseModel):
    id: UUID
    phone: str
    name: str
    avatar: str | None
    created_at: datetime


class VerifyOtpOut(BaseModel):
    access_token: str
    user: UserOut


@router.post("/request-otp", response_model=RequestOtpOut)
def request_otp(payload: RequestOtpIn) -> RequestOtpOut:
    challenge = otp_service.request_otp(payload.phone)
    return RequestOtpOut(request_id=challenge.request_id)


@router.post("/verify-otp", response_model=VerifyOtpOut)
def verify_otp(payload: VerifyOtpIn, session: SessionDep) -> VerifyOtpOut:
    if not otp_service.verify_otp(payload.phone, payload.otp):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired OTP")

    user = session.exec(select(User).where(User.phone == payload.phone)).first()
    if user is None:
        user = User(
            phone=payload.phone,
            name=payload.name or _placeholder_name(payload.phone),
            avatar=payload.avatar,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    token = issue_access_token(user.id)
    return VerifyOtpOut(access_token=token, user=UserOut.model_validate(user, from_attributes=True))


def _placeholder_name(phone: str) -> str:
    tail = phone[-4:] if len(phone) >= 4 else phone
    return f"User {tail}"
