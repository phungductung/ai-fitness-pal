"""Pydantic schemas for strict input validation on MCP server tools.

These schemas enforce domain-specific constraints directly at the
MCP tool boundary so that invalid data never reaches Supabase.
"""

from pydantic import BaseModel, Field
from typing import Optional


class AddPersonalRecordMCPInput(BaseModel):
    """Input schema for the add_personal_record MCP tool."""
    exercise: str = Field(
        ...,
        description="Name of the exercise (e.g. 'Squat', 'Bench Press').",
        min_length=1,
        max_length=100,
    )
    weight: float = Field(
        ...,
        description="Weight lifted in kg. Must be positive.",
        gt=0,
        le=1000,
    )
    reps: int = Field(
        ...,
        description="Number of reps performed. Must be between 1 and 100.",
        ge=1,
        le=100,
    )


class QueryFitnessDiaryMCPInput(BaseModel):
    """Input schema for the query_fitness_diary MCP tool."""
    limit: Optional[int] = Field(
        default=10,
        description="Number of entries to return.",
        ge=1,
        le=1000,
    )
    order: Optional[str] = Field(
        default="desc",
        description="Order of entries by date (asc or desc).",
        pattern="^(asc|desc)$",
    )


class AddDiaryEntryMCPInput(BaseModel):
    """Input schema for adding a diary entry via MCP."""
    entry: str = Field(
        default="Weight update",
        description="Free-text description of the meal or activity.",
        max_length=1000,
    )
    calories: int = Field(
        default=0,
        description="Calorie count. Must be non-negative.",
        ge=0,
        le=20000,
    )
    protein: int = Field(
        default=0,
        description="Protein intake in grams. Must be non-negative.",
        ge=0,
        le=2000,
    )
    weight: Optional[float] = Field(
        default=None,
        description="Current body weight in kg (optional).",
        ge=20,
        le=500,
    )
    sleep_hours: float = Field(
        default=8.0,
        description="Hours of sleep (0-24).",
        ge=0,
        le=24,
    )
    fatigue: int = Field(
        default=3,
        description="Fatigue level on a 1-5 scale.",
        ge=1,
        le=5,
    )


class DeletePersonalRecordMCPInput(BaseModel):
    """Input schema for deleting a personal record via MCP."""
    record_id: str = Field(
        ...,
        description="The unique ID of the personal record to delete (UUID).",
    )
