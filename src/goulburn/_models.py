"""Typed response models for the goulburn SDK.

Each public-API call returns one of these. Models use Pydantic's
`extra='allow'` so server-side additions of new fields don't break
older SDK builds — your code keeps working, the new field just isn't
typed until you upgrade.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _BaseResponse(BaseModel):
    """Common Pydantic config for every model in this module."""

    model_config = ConfigDict(extra="allow", frozen=True)


class Owner(_BaseResponse):
    """Identity returned by GET /api/v1/owner/me."""

    owner_id: str
    email: str
    display_name: str


class Agent(_BaseResponse):
    """Agent record returned by GET /api/v1/agents/mine and /agents/{name}.

    Only the most-used fields are typed explicitly. Anything else the
    server returns (status, endpoint_url, scores, capability_tags,
    etc.) is preserved on the instance and accessible via attribute
    access or .model_dump() — extra='allow' on the parent class.
    """

    name: str
    description: str = ""


class AgentList(_BaseResponse):
    """Wrapper for paginated list endpoints — /api/v1/agents/mine."""

    data: list[Agent]
    next_cursor: str | None = None
    has_more: bool = False


class ProbeRunResult(_BaseResponse):
    """Result of POST /api/v1/agents/{name}/probe/run.

    Shape varies by probe kind; the SDK exposes the raw fields via
    .model_dump() and lets callers branch on specific keys.
    """


class TrustProfile(_BaseResponse):
    """Trust profile returned by GET /api/v1/trust/profile/{agent_name}.

    Includes the 5-layer breakdown (identity, capability, track_record,
    social, compliance). Each layer's full evidence is preserved on
    the instance under `layers`.
    """

    agent: str
    tier: str
    overall_score: int
    layers: dict[str, Any]
