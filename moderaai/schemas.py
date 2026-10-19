"""The shape of a verdict. Gemini is asked to answer in exactly this shape (structured output)."""

from pydantic import BaseModel


class ModerationResult(BaseModel):
    flagged: bool
    category: str
    reasoning: str


class ImageModerationResult(ModerationResult):
    text_in_image: str  # any text the model could read in the image ("" if none)
