from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SignUpRequest(BaseModel):
    institution_name: str = Field(min_length=2, max_length=180)
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GenerationSession(BaseModel):
    subject: str = Field(min_length=1, max_length=160)
    faculty: str = Field(min_length=1, max_length=160)
    section: str = Field(min_length=1, max_length=80)
    students: int = Field(ge=1, le=1000)
    room_type: str = Field(default="classroom", min_length=1, max_length=24)
    unavailable: list[tuple[int, int]] = Field(default_factory=list)
    duration_periods: int = Field(default=1, ge=1, le=6)
    faculty_max_weekly_periods: int | None = Field(default=None, ge=1, le=100)
    session_key: str | None = None


class RoomOption(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    capacity: int = Field(ge=1, le=5000)
    room_type: str = Field(default="classroom", min_length=1, max_length=24)


class UserView(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    email_verified: bool = False
    email_verification_required: bool = False


class GenerateRequest(BaseModel):
    section: str = Field(min_length=1, max_length=80)
    sessions: list[GenerationSession] = Field(min_length=1, max_length=100)
    rooms: list[RoomOption] = Field(min_length=1, max_length=100)
    days: int = Field(default=5, ge=1, le=7)
    periods_per_day: int = Field(default=8, ge=1, le=14)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class EmailTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    term_id: UUID | None = None
    department_id: UUID | None = None


class AssistantConfirmRequest(BaseModel):
    action: Literal["generate_timetable"]
    term_id: UUID
    department_id: UUID
    name: str = Field(default="AI-assisted timetable", min_length=2, max_length=140)


class TeachingAssignmentCreate(BaseModel):
    subject_id: UUID
    section_id: UUID
    faculty_id: UUID
    sessions_per_week: int = Field(ge=1, le=20)
    duration_periods: int = Field(default=1, ge=1, le=6)


class StoredTimetableGenerateRequest(BaseModel):
    term_id: UUID
    department_id: UUID
    section_id: UUID | None = None
    name: str = Field(min_length=2, max_length=140)
    days: int = Field(default=5, ge=1, le=7)
    periods_per_day: int = Field(default=8, ge=1, le=14)
    weekdays: list[int] | None = Field(default=None, min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value):
        if value is not None and (len(set(value)) != len(value) or any(day < 0 or day > 6 for day in value)):
            raise ValueError("Choose unique weekdays from Monday through Sunday.")
        return value

    @model_validator(mode="after")
    def match_day_count(self):
        if self.weekdays is not None and len(self.weekdays) != self.days:
            raise ValueError("The number of selected weekdays must match the teaching day count.")
        return self


class TimetableEntryMove(BaseModel):
    day: int = Field(ge=0, le=6)
    period: int = Field(ge=0, le=13)
    room_id: UUID | None = None


class TimetableApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class UnavailableSlot(BaseModel):
    day: int = Field(ge=0, le=6)
    period: int = Field(ge=0, le=13)


class FacultyAvailabilityUpdate(BaseModel):
    unavailable: list[UnavailableSlot] = Field(max_length=98)





class InstitutionCalendarBreak(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def check_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("A break must end later than it starts on the same weekday.")
        return self
