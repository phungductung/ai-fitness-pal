"""Pydantic schemas for strict input validation on all LangChain tools.

Each schema enforces domain-specific constraints (e.g. positive weights,
realistic age ranges, valid enums) so that the LLM receives clear error
messages instead of silently computing nonsensical results.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ──────────────────────────────────────────────
# Fitness Formula Schemas
# ──────────────────────────────────────────────

class Calculate1RMInput(BaseModel):
    """Input schema for the 1-Rep Max calculator."""
    weight: float = Field(
        ...,
        description="Weight lifted in kg. Must be a positive number.",
        gt=0,
        le=1000,
    )
    reps: int = Field(
        ...,
        description="Number of repetitions performed. Must be between 1 and 100.",
        ge=1,
        le=100,
    )


class CalculateTDEEInput(BaseModel):
    """Input schema for TDEE (Total Daily Energy Expenditure) calculator."""
    weight_kg: float = Field(
        ...,
        description="Body weight in kilograms.",
        gt=0,
        le=500,
    )
    height_cm: float = Field(
        ...,
        description="Height in centimetres.",
        gt=0,
        le=300,
    )
    age: int = Field(
        ...,
        description="Age in years. Must be between 1 and 120.",
        ge=1,
        le=120,
    )
    gender: str = Field(
        ...,
        description="Biological gender: 'male' or 'female'.",
    )
    activity_multiplier: float = Field(
        ...,
        description=(
            "Activity multiplier. Common values: "
            "1.2 (sedentary), 1.375 (light), 1.55 (moderate), "
            "1.725 (active), 1.9 (extra active)."
        ),
        ge=1.0,
        le=3.0,
    )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        allowed = {"male", "female"}
        if v.strip().lower() not in allowed:
            raise ValueError(
                f"Gender must be 'male' or 'female', got '{v}'."
            )
        return v.strip().lower()


class SuggestMacrosInput(BaseModel):
    """Input schema for macro suggestion tool."""
    tdee: float = Field(
        ...,
        description="Total Daily Energy Expenditure in kcal. Must be positive.",
        gt=0,
        le=15000,
    )
    goal: str = Field(
        ...,
        description="Fitness goal: 'bulk', 'cut', or 'maintain'.",
    )

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        allowed = {"bulk", "cut", "maintain"}
        if v.strip().lower() not in allowed:
            raise ValueError(
                f"Goal must be one of {allowed}, got '{v}'."
            )
        return v.strip().lower()


# ──────────────────────────────────────────────
# Visualization Schema
# ──────────────────────────────────────────────

class VisualizeProgressInput(BaseModel):
    """Input schema for exercise progress visualization."""
    exercise: str = Field(
        ...,
        description="Name of the exercise to chart (e.g. 'Bench Press').",
        min_length=1,
        max_length=100,
    )


# ──────────────────────────────────────────────
# RAG / Research Schemas
# ──────────────────────────────────────────────

class QueryKnowledgeGraphInput(BaseModel):
    """Input schema for knowledge-graph queries."""
    topic: str = Field(
        ...,
        description="The specific name of the Supplement (e.g., 'Caffeine'), Goal (e.g., 'Recovery'), Food Source (e.g., 'Milk'), or Condition (e.g., 'Hypertension') you want to look up.",
        min_length=2,
        max_length=100,
    )
    topic_type: str = Field(
        ...,
        description="Must be one of: 'supplement', 'goal', 'side_effects', 'synergy', 'food_source', or 'condition'.",
    )

    @field_validator("topic_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"supplement", "goal", "side_effects", "synergy", "food_source", "condition"}
        if v.strip().lower() not in allowed:
            raise ValueError(f"topic_type must be one of {allowed}")
        return v.strip().lower()





class SearchLatestFitnessResearchInput(BaseModel):
    """Input schema for live Tavily internet search."""
    query: str = Field(
        ...,
        description="Search query for latest fitness studies or news.",
        min_length=2,
        max_length=500,
    )


# ──────────────────────────────────────────────
# MCP Data-Access Schemas
# ──────────────────────────────────────────────

class QueryFitnessDiaryInput(BaseModel):
    """Input schema for fitness diary queries."""
    limit: Optional[int] = Field(
        default=10,
        description="Number of entries to return (max 100).",
        ge=1,
        le=100,
    )
    order: Optional[str] = Field(
        default="desc",
        description="Sort order by date ('asc' or 'desc').",
    )


class AddPersonalRecordInput(BaseModel):
    """Input schema for logging a new personal record."""
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


class AddDiaryEntryInput(BaseModel):
    """Input schema for adding a daily fitness diary entry."""
    entry: str = Field(
        ...,
        description="Free-text description of the meal or activity.",
        min_length=1,
        max_length=1000,
    )
    calories: int = Field(
        ...,
        description="Calorie count for this entry. Must be non-negative.",
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
