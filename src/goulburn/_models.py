"""Typed response models. Each public-API call returns one of these.

Models are intentionally lenient — extra fields the server may add in
future releases are preserved on the Pydantic instance and don't break
older SDK builds (Pydantic's `extra='allow'`).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _BaseResponse(BaseModel):
    """Common Pydantic config for every model in this module."""

    model_config = ConfigDict(extra="allow", frozen=True)


class Owner(_BaseResponse):
    """Identity returned by GET /api/v1/owner/me."""

    owner_id: str
    email: str
    display_name: str
