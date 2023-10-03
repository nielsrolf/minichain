from typing import List, Optional

from pydantic import BaseModel, Field


class DefaultResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")


class Done(BaseModel):
    success: bool = Field(
        ...,
        description="Always set this to true to indicate that you are done with this function.",
    )


class ReferencesToOriginalMessages(BaseModel):
    original_message_id: Optional[int] = Field(
        None, description="The id of the original message that you want to keep."
    )
    summary: Optional[str] = Field(
        None,
        description="A summary of one or more messages that you want to keep instead of the original message.",
    )


class ShortenedHistory(BaseModel):
    messages: List[ReferencesToOriginalMessages] = Field(
        ...,
        description="The messages you want to keep from the original history. You can either pass message ids - those messages will be kept and not summarized - or no id but a text summary to insert into the history.",
    )


class BashQuery(BaseModel):
    commands: List[str] = Field(..., description="A list of bash commands.")
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")


class MultiModalResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")
    generated_files: List[str] = Field(
        ..., description="Media files that have been generated."
    )
