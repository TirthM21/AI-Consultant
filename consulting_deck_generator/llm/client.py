import os
import json
import google.generativeai as genai
from typing import Dict, Any, List
from ..core.models import SlideBlueprint, SlideData, SlideContent

class LLMClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def _generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=4000,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"LLM generation failed: {str(e)}")
    
    def step1_engagement_structuring(self, problem_statement: str) -> Dict[str, Any]:
        """Step 1: Generate slide blueprint"""
        prompt = f"""
You are a senior McKinsey engagement manager. Given this client problem, design a 10-slide deck blueprint.

PROBLEM: {problem_statement}

RULES:
- Each slide must answer ONE business question
- Apply Pyramid Principle: main insight at top, supporting details below
- Use hypothesis-driven approach
- Titles must be action-oriented, not descriptive
- Visuals must drive insights, not decorate

Return EXACT JSON structure:
{{
    "hypothesis": "Single sentence articulating the core hypothesis",
    "methodology": "Brief description of analytical approach",
    "slides": [
        {{
            "slide_id": "slide_01",
            "title": "Action-oriented title (max 8 words)",
            "key_question": "What single question does this slide answer?",
            "core_insight": "One sentence with the main finding",
            "visual_type": "bar_chart|line_chart|pie_chart|table|framework|process_flow",
            "data_requirements": ["Specific data needed for visual"],
            "position_in_deck": 1,
            "slide_template": "title_only|two_column|chart_main|framework"
        }}
    ]
}}

COVER SLIDES (use these exact types):
1. Title & situation overview (title_only)
2. Problem definition (two_column)
3. Hypothesis (framework)
4. Market analysis (chart_main + bar_chart)
5. Competitive landscape (framework)
6. Financial impact (table)
7. Growth opportunity (line_chart)
8. Implementation roadmap (process_flow)
9. Risk & mitigation (framework)
10. Recommendations & next steps (two_column)

OUTPUT ONLY RAW JSON. NO EXPLANATIONS.
"""
        
        response = self._generate_response(prompt, temperature=0.3)
        
        try:
            # Parse JSON response
            parsed = json.loads(response)
            return parsed
        except json.JSONDecodeError:
            # Fallback: extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            raise Exception("Failed to parse LLM response as JSON")
    
    def step2_data_generation(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Generate data and analytics"""
        prompt = f"""
You are a McKinsey analytics lead. Generate realistic data for this deck blueprint.

BLUEPRINT: {json.dumps(blueprint, indent=2)}

RULES:
- Generate chart-ready datasets in specified format
- Create tables with realistic business metrics
- Explicitly state all assumptions
- No formatting language, only data
- All numbers must be plausible for the business context

For each slide, return:

{{
    "slide_data": {{
        "slide_id": {{
            "chart_data": {{
                "type": "bar|line|pie|scatter",
                "labels": ["Category A", "Category B", "Category C"],
                "datasets": [
                    {{
                        "label": "Series 1",
                        "data": [100, 150, 80],
                        "color": "#667eea"
                    }}
                ]
            }},
            "table_data": [
                ["Header 1", "Header 2", "Header 3"],
                ["Value 1", "Value 2", "Value 3"],
                ["Value 4", "Value 5", "Value 6"]
            ],
            "assumptions": [
                "Assumption 1: Market grows at X% annually",
                "Assumption 2: Y% market share achievable"
            ],
            "sources": [
                "Source: Internal company data",
                "Source: Industry reports 2024"
            ],
            "metrics": {{
                "total_market_size": 5000,
                "growth_rate": 12.5,
                "market_share_target": 15.0
            }}
        }}
    }}
}}

DATA GUIDELINES:
- Market size: $500M - $10B ranges
- Growth rates: 5% - 25% annually
- Competitors: Real company names or realistic placeholders
- Financials: Reasonable margins and multiples

OUTPUT ONLY RAW JSON. NO EXPLANATIONS.
"""
        
        response = self._generate_response(prompt, temperature=0.2)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            raise Exception("Failed to parse data generation response")
    
    def step3_content_generation(self, blueprint: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Generate final slide content"""
        prompt = f"""
You are a McKinsey content specialist. Write consulting-quality slide content.

BLUEPRINT: {json.dumps(blueprint, indent=2)}
DATA: {json.dumps(data, indent=2)}

CONTENT RULES:
- Max 5 bullet points per slide
- Each bullet must start with strong action verb
- Chart captions explain the insight, not describe the chart
- "So what?" takeaways are provocative and actionable
- Use consulting language (e.g., "proprietary insights", "strategic advantage")

Return for each slide:

{{
    "slide_content": {{
        "slide_id": {{
            "title": "Exact same title from blueprint",
            "bullets": [
                "Bullet 1: Action verb + what + impact",
                "Bullet 2: Supporting evidence",
                "Bullet 3: Quantified outcome"
            ],
            "chart_caption": "Insight-based caption for visual (1 sentence)",
            "so_what_takeaway": "So what? Strategic implication",
            "call_to_action": "Next step for client",
            "visual_config": {{
                "chart_title": "Clear, benefit-oriented title",
                "subtitle": "Key metric or time period"
            }}
        }}
    }}
}}

STYLE GUIDELINES:
- Be direct and confident
- Quantify whenever possible
- Focus on "what this means for the client"
- Avoid generic business school language
- Use McKinsey tone: authoritative, precise, impactful

OUTPUT ONLY RAW JSON. NO EXPLANATIONS.
"""
        
        response = self._generate_response(prompt, temperature=0.1)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(response[start:end])
            raise Exception("Failed to parse content generation response")