"""Data models for Symentic MCP Server."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Consent(BaseModel):
    """User consent information."""
    given: bool
    method: str
    timestamp: str


class SlackProfile(BaseModel):
    """Slack profile information."""
    displayName: str = Field(alias="display_name")
    isAdmin: bool = Field(alias="is_admin")
    isOwner: bool = Field(alias="is_owner")
    profilePictureUrl: Optional[str] = Field(None, alias="profile_picture_url")
    realName: str = Field(alias="real_name")
    slackUserId: str = Field(alias="slack_user_id")
    statusText: str = Field(default="", alias="status_text")
    timezone: Optional[str] = None
    title: str = Field(default="")


class Enrichment(BaseModel):
    """Enrichment data from various agents."""
    agent: str
    date: str
    detail: str


class UserProfile(BaseModel):
    """Main user profile model."""
    PK: str  # Partition Key - format: "symentic_{business_id}"
    SK: str  # Sort Key - format: "USER#{user_id}"
    businessId: str = Field(alias="business_id")
    consent: Optional[Consent] = None
    description: Optional[str] = None
    email: Optional[str] = None
    enrichments: List[Enrichment] = Field(default_factory=list)
    expertise: List[str] = Field(default_factory=list)
    firstSeen: str = Field(alias="first_seen")
    GSI1PK: Optional[str] = None  # Global Secondary Index 1 Partition Key
    GSI1SK: Optional[str] = None  # Global Secondary Index 1 Sort Key
    id: str
    interactionCount: int = Field(0, alias="interaction_count")
    interactions: int = 0
    lastInteraction: Optional[str] = Field(None, alias="last_interaction")
    lastUpdated: str = Field(alias="last_updated")
    name: str
    role: Optional[str] = None
    slackProfile: Optional[SlackProfile] = Field(None, alias="slack_profile")
    source: str = "slack"
    tags: List[str] = Field(default_factory=list)
    userId: str = Field(alias="user_id")
    userType: str = Field(alias="user_type")  # internal or external

    class Config:
        populate_by_name = True


class UserProfileUpdate(BaseModel):
    """Model for updating user profile fields."""
    description: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    tags: Optional[List[str]] = None
    expertise: Optional[List[str]] = None


class EnrichmentInput(BaseModel):
    """Model for adding new enrichments."""
    agent: str
    detail: str
    date: Optional[str] = None  # Will default to today if not provided