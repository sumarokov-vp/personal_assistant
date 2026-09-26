from pydantic import BaseModel

from src.dropbox.models.move_plan import MovePlan


class MovePlanCardPress(BaseModel):
    plan: MovePlan
    chat_id: int
    message_id: int
