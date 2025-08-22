from __future__ import annotations

from pydantic import BaseModel


class SomeExampleType(BaseModel):
    property: str
