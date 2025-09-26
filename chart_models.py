from typing import List, Optional
from pydantic import BaseModel, Field

class ChartDataPoint(BaseModel):
    """Represents a single data point for a chart (e.g., one bar)."""
    label: str = Field(description="The label for the data point (e.g., a country name).")
    value: float = Field(description="The numerical value for the data point (e.g., a score).")

class ChartData(BaseModel):
    """
    A model to hold data extracted from text that is suitable for plotting a chart.
    If the text does not contain chartable data, the 'chartable' field should be False.
    """
    chartable: bool = Field(description="Set to True if the text contains data suitable for a chart, otherwise False.")
    title: str = Field(description="A descriptive title for the chart (e.g., 'Top 5 Countries by Innovation Score').")
    data: List[ChartDataPoint] = Field(description="A list of data points to be plotted.")

