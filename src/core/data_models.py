# src/core/data_models.py

from typing import List, Optional
from pydantic import BaseModel, Field # Correct import

# --- Pydantic Models for the Data Extraction Outline ---

class DimensionPillarSummary(BaseModel):
    """Model for the summary table of dimensions and pillars."""
    dimension: str = Field(description="The broad category, e.g., 'Digital Foundation'.")
    pillar: str = Field(description="The specific area within the dimension, e.g., 'Institutions'.")
    value: int = Field(description="The score for the pillar.")
    rank: int = Field(description="The rank for the pillar.")

class SubPillar(BaseModel):
    """Model for individual indicators or sub-pillars within a main pillar."""
    name: str = Field(description="The name of the indicator or sub-pillar.")
    score: float = Field(description="The score of the indicator or sub-pillar.")

class PillarData(BaseModel):
    """Model for the detailed data of one of the nine pillars."""
    pillar_name: str = Field(description="The name of the pillar, e.g., 'First Pillar: Institutions'.")
    total_pillar_score: float = Field(description="The total score for this pillar.")
    sub_pillars: List[SubPillar] = Field(description="A list of all sub-pillars and their scores.")

class CountryData(BaseModel):
    """The root model to hold all extracted data for a single country."""
    country_name: str = Field(description="The name of the country being analyzed.")
    overall_adei_score: int = Field(description="The overall ADEI score for the country.")
    overall_adei_rank: int = Field(description="The overall ADEI rank for the country.")
    dimension_summary: List[DimensionPillarSummary] = Field(description="The country's dimension and pillar summary table.")
    detailed_pillars: List[PillarData] = Field(description="A list containing the detailed data for all nine pillars.")
