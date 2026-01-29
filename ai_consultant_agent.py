import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from tavily import TavilyClient
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

genai.configure(api_key=API_KEY)
tavily_client = TavilyClient(TAVILY_API_KEY)

@dataclass
class MarketInsight:
    category: str
    finding: str
    confidence: float
    source: str

@dataclass
class StrategicRecommendation:
    category: str
    priority: str
    recommendation: str
    timeline: str
    action_items: List[str]

class ResponseValidator:
    @staticmethod
    def validate_response(text: str) -> bool:
        forbidden_topics = ['harmful', 'illegal', 'fraud', 'scam', 'money laundering']
        return not any(topic.lower() in text.lower() for topic in forbidden_topics)

    @staticmethod
    def sanitize_response(text: str) -> str:
        text = text.replace('```json', '').replace('```', '')
        return text.strip()

def tavily_search(query: str) -> Dict[str, Any]:
    try:
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
            max_results=10
        )
        return {
            "content": response.get("answer", ""),
            "sources": [result.get("url", "") for result in response.get("results", [])],
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}", "status": "error"}

def analyze_market_data(research_query: str, industry: str = "") -> Dict[str, Any]:
    insights = []
    
    if "startup" in research_query.lower():
        insights.extend([
            MarketInsight("Market Opportunity", "Growing market with moderate competition", 0.8, "Market Research"),
            MarketInsight("Risk Assessment", "Standard startup risks apply", 0.7, "Analysis")
        ])
    
    return {
        "query": research_query,
        "insights": [{"category": i.category, "finding": i.finding} for i in insights],
        "total_insights": len(insights)
    }

def generate_strategic_recommendations(analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    recommendations = []
    
    recommendations.append({
        "category": "Market Entry Strategy",
        "priority": "High",
        "recommendation": "Implement phased market entry with MVP testing",
        "timeline": "3-6 months",
        "action_items": [
            "Develop minimum viable product",
            "Identify target customer segment",
            "Conduct market validation tests"
        ]
    })
    
    return recommendations

SYSTEM_INSTRUCTIONS = """
You are a senior strategy consultant with experience at top-tier firms
such as McKinsey, Boston Consulting Group, Bain, EY, and Deloitte.

YOUR STYLE:
- Communicate like a management consultant writing a client-ready deck
- Use clear structure, short paragraphs, and crisp bullet points
- Be MECE (Mutually Exclusive, Collectively Exhaustive) in your breakdowns
- Focus on business impact, trade-offs, and prioritization

CORE PRINCIPLES:
- Always provide evidence-based, commercially sound recommendations
- Disclose limitations and assumptions clearly
- Avoid harmful or illegal business practices
- Respect data privacy and regulatory requirements
- Focus on ethical and sustainable business strategies

YOUR EXPERTISE:
- Corporate and business-unit strategy
- Go-to-market and commercial strategy
- Operational efficiency and cost optimization
- Digital / AI strategy and transformation
- Risk assessment and mitigation planning
- Market and competitive analysis using your knowledge and available tools

RESPONSE FORMAT (STRICTLY FOLLOW THIS STRUCTURE):
1. Executive Summary
   - 3–5 bullets with the key answer to the question
   - Focus on "So what?" and business impact

2. Situation Overview
   - Brief recap of the context, objectives, and constraints

3. Key Insights (MECE)
   - 3–7 structured bullets grouping insights into logical buckets
   - Clearly separate demand, supply/competition, economics, and risks where relevant

4. Strategic Recommendations
   - 3–7 specific recommendations
   - For each: include rationale, expected impact, and high-level owner

5. Implementation Roadmap
   - Phase the work into Near term (0–3 months), Mid term (3–12 months), Long term (12+ months)
   - 3–5 bullets per phase with concrete actions

6. Risks & Mitigations
   - 3–5 key risks with a clear mitigation for each

7. KPIs & Measurement
   - 5–10 metrics to track success, with a short note on target direction (↑/↓)

GENERAL GUIDELINES:
- Be concise but concrete; avoid generic advice
- Quantify impact where possible (ranges, orders of magnitude)
- Reference credible sources or market logic when available
- Call out key assumptions explicitly
"""

def get_gemini_response(prompt: str, context: str = "") -> str:
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp', system_instruction=SYSTEM_INSTRUCTIONS)
        
        full_prompt = f"""
{context}

User Query: {prompt}

Please provide a comprehensive business consultation response.
"""
        
        response = model.generate_content(full_prompt)
        
        if ResponseValidator.validate_response(response.text):
            return ResponseValidator.sanitize_response(response.text)
        else:
            return "I apologize, but I cannot provide advice on this topic. Please consult with a qualified professional."
            
    except Exception as e:
        return f"Error generating response: {str(e)}"

class AIConsultantAgent:
    def __init__(self):
        self.session_history = []
        
    def consult(self, user_query: str) -> str:
        try:
            self.session_history.append({"role": "user", "content": user_query})
            
            search_query = f"business consulting {user_query}"
            search_results = tavily_search(search_query)
            
            if search_results["status"] == "success":
                search_context = f"""
Recent Market Research:
{search_results['content']}

Sources: {', '.join(search_results['sources'][:3])}
"""
            else:
                search_context = "Unable to retrieve current market data. Proceeding with general analysis."
            
            analysis = analyze_market_data(user_query)
            recommendations = generate_strategic_recommendations(analysis)
            
            context = f"""
Market Analysis:
{json.dumps(analysis, indent=2)}

Strategic Recommendations:
{json.dumps(recommendations, indent=2)}

{search_context}
"""
            
            response = get_gemini_response(user_query, context)
            
            self.session_history.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            return f"Consultation error: {str(e)}"
    
    def get_session_summary(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.session_history),
            "last_topic": self.session_history[-1]["content"] if self.session_history else None
        }

def main():
    print("=== AI Business Consultant Agent ===")
    print("Using Gemini 2.0 Flash with Tavily Search")
    print("Type 'exit' to quit\n")
    
    agent = AIConsultantAgent()
    
    while True:
        try:
            user_input = input("\nYour business question: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("Session summary:", agent.get_session_summary())
                break
            
            if not user_input:
                continue
            
            print("\nConsulting...")
            response = agent.consult(user_input)
            print(f"\n{response}\n")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\nSession ended.")
            break

if __name__ == "__main__":
    main()