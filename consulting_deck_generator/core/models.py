import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class SlideBlueprint:
    """Step 1 Output: Structured slide blueprint"""
    slide_id: str
    title: str
    key_question: str
    core_insight: str
    visual_type: str  # bar_chart, line_chart, table, framework, pie_chart
    data_requirements: List[str]
    position_in_deck: int
    slide_template: str  # title_only, two_column, chart_main, framework

@dataclass
class SlideData:
    """Step 2 Output: Data and analytics for slides"""
    slide_id: str
    chart_data: Dict[str, Any]
    table_data: Optional[List[List[str]]] = None
    assumptions: List[str]
    sources: List[str]
    metrics: Dict[str, float]

@dataclass
class SlideContent:
    """Step 3 Output: Final slide content"""
    slide_id: str
    title: str
    bullets: List[str]  # Max 5 bullets per slide
    chart_caption: str
    so_what_takeaway: str
    call_to_action: Optional[str] = None
    visual_config: Dict[str, Any] = None

@dataclass
class DeckBlueprint:
    """Complete deck structure"""
    engagement_id: str
    client_name: str
    problem_statement: str
    slides: List[SlideBlueprint]
    hypothesis: str
    methodology: str

@dataclass
class GeneratedDeck:
    """Final output package"""
    blueprint: DeckBlueprint
    content_slides: List[SlideContent]
    data_slides: List[SlideData]
    metadata: Dict[str, Any]
    pptx_path: Optional[str] = None
    pdf_path: Optional[str] = None