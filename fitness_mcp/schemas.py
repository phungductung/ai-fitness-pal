"""Pydantic schemas for strict input validation on MCP server tools.

These schemas enforce domain-specific constraints directly at the
MCP tool boundary so that invalid data never reaches Supabase.
"""

from pydantic import BaseModel, Field, field_validator
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
    query: str = Field(
        default=None,
        description="Optional search/filter query for diary entries.",
        max_length=500,
    )


class AddDiaryEntryMCPInput(BaseModel):
    """Input schema for adding a diary entry via MCP."""
    entry: str = Field(
        ...,
        description="Free-text description of the meal or activity.",
        min_length=1,
        max_length=1000,
    )
    calories: int = Field(
        ...,
        description="Calorie count. Must be non-negative.",
        ge=0,
        le=20000,
    )
    protein: int = Field(
        ...,
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
