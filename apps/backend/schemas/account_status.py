"""Account activation contract; status changes never expose credentials."""
from pydantic import BaseModel, ConfigDict, StrictBool


class AccountStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: StrictBool


class AccountStatusOut(BaseModel):
    account_id: str
    email: str
    username: str
    role: str
    is_active: bool
