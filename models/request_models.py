from pydantic import BaseModel, Field

class Question(BaseModel):
    """
    Pydantic model representing a standard question request.
    """

    text: str = Field(
        min_length=3,
        max_length=1000,
        description="The content of the question."
    )

class ChatQuestion(Question):
    """
    Pydantic model representing a chat question request with session tracking.
    """
    session_id: str = Field(
        description="Unique identifier for the chat session."
    )