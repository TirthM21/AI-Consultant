import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import google.generativeai as genai
import wikipedia
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
    flash,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import Mail, Message
from tavily import TavilyClient

from models import Billing, Consultation, User, db
from pdf_utils import generate_consultation_pdf

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_HcYrtq5xh9em@ep-proud-mode-ah4gsusb-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@ai-consultant.com')

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if not email or not password or not name:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    consultations = (
        db.session.query(Consultation)
        .filter_by(user_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template('dashboard.html', consultations=consultations)

@app.route('/consult', methods=['POST'])
@login_required
def consult():
    query = request.form.get('query')
    
    if not query:
        flash('Please enter a query.', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.can_consult():
        flash('You have reached your consultation limit. Please upgrade to premium.', 'error')
        return redirect(url_for('billing'))
    
    try:
        # Wikipedia context
        wikipedia_summary = ""
        try:
            wikipedia_summary = wikipedia.summary(query, auto_suggest=True, sentences=5)
        except Exception:
            wikipedia_summary = ""

        search_query = f"business consulting {query}"
        search_response = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
            max_results=10
        )
        
        search_results = {
            "content": search_response.get("answer", ""),
            "sources": [result.get("url", "") for result in search_response.get("results", [])]
        }
        
        analysis = analyze_market_data(query)
        recommendations = generate_strategic_recommendations(analysis)
        
        context = f"""
Market Analysis:
{json.dumps(analysis, indent=2)}

Strategic Recommendations:
{json.dumps(recommendations, indent=2)}

Wikipedia Context:
{wikipedia_summary}

Recent Market Research:
{search_results['content']}

Sources: {', '.join(search_results['sources'][:3])}
"""
        
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=get_system_instructions())
        full_prompt = f"\nUser Query: {query}\n\nPlease provide a comprehensive business consultation response."
        response = model.generate_content(context + full_prompt)
        
        ai_response = sanitize_response(response.text)
        
        consultation = Consultation(
            user_id=current_user.id,
            query=query,
            response=ai_response,
            search_results=search_results,
            analysis=analysis,
            recommendations=recommendations
        )
        
        current_user.increment_usage()
        db.session.add(consultation)
        db.session.commit()
        
        flash('Consultation completed successfully!', 'success')
        return redirect(url_for('consultation_detail', consultation_id=consultation.id))
        
    except Exception as e:
        flash(f'Consultation error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/consultation/<consultation_id>')
@login_required
def consultation_detail(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    
    if consultation is None:
        abort(404)
    
    if consultation.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('consultation_detail.html', consultation=consultation)


@app.route('/consultation/<consultation_id>/pdf')
@login_required
def consultation_pdf(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)

    if consultation is None:
        abort(404)

    if consultation.user_id != current_user.id:
        abort(403)

    pdf_buffer = generate_consultation_pdf(consultation)
    filename = f"consultation_{consultation.id[:8]}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )

@app.route('/consultation/<consultation_id>/report')
@login_required
def generate_report(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    
    if consultation is None:
        abort(404)
    
    if consultation.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if consultation.report_generated:
        return jsonify(consultation.report_data)
    
    report_data = create_consultant_report(consultation)
    
    consultation.report_generated = True
    consultation.report_data = report_data
    db.session.commit()
    
    return jsonify(report_data)


@app.route('/consultation/<consultation_id>/export/json')
@login_required
def export_consultation_json(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)

    if consultation is None:
        abort(404)

    if consultation.user_id != current_user.id:
        abort(403)

    return jsonify(
        {
            "id": consultation.id,
            "query": consultation.query,
            "response": consultation.response,
            "analysis": consultation.analysis,
            "recommendations": consultation.recommendations,
            "search_results": consultation.search_results,
            "created_at": consultation.created_at.isoformat(),
        }
    )

@app.route('/consultation/<consultation_id>/email', methods=['POST'])
@login_required
def email_report(consultation_id):
    consultation = db.session.get(Consultation, consultation_id)
    
    if consultation is None:
        abort(404)
    
    if consultation.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    email = request.form.get('email', current_user.email)
    
    try:
        send_consultation_email(consultation, email)
        flash('Report sent successfully!', 'success')
    except Exception as e:
        flash(f'Failed to send email: {str(e)}', 'error')
    
    return redirect(url_for('consultation_detail', consultation_id=consultation_id))

@app.route('/billing')
@login_required
def billing():
    billing_history = Billing.query.filter_by(user_id=current_user.id).order_by(Billing.created_at.desc()).all()
    return render_template('billing.html', billing_history=billing_history)

@app.route('/billing/upgrade', methods=['POST'])
@login_required
def upgrade():
    amount = float(request.form.get('amount', '29.99'))
    payment_method = request.form.get('payment_method', 'credit_card')
    
    try:
        billing = Billing(
            user_id=current_user.id,
            amount=amount,
            payment_method=payment_method,
            status='completed',
            transaction_id=f'txn_{datetime.utcnow().timestamp()}'
        )
        
        db.session.add(billing)
        db.session.flush()
        
        current_user.is_premium = True
        current_user.billing_active = True
        current_user.subscription_end = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        flash('Successfully upgraded to premium!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Upgrade failed: {str(e)}', 'error')
    
    return redirect(url_for('billing'))

@app.route('/api/usage')
@login_required
def api_usage():
    return jsonify({
        'consultations_used': current_user.consultations_count,
        'consultations_remaining': current_user.remaining_consultations(),
        'is_premium': current_user.is_premium,
        'can_consult': current_user.can_consult()
    })

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

def get_system_instructions():
    return """
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

def sanitize_response(text: str) -> str:
    forbidden_topics = ['harmful', 'illegal', 'fraud', 'scam', 'money laundering']
    
    if any(topic.lower() in text.lower() for topic in forbidden_topics):
        return "I apologize, but I cannot provide advice on this topic. Please consult with a qualified professional."
    
    text = text.replace('```json', '').replace('```', '')
    return text.strip()

def create_consultant_report(consultation: Consultation) -> Dict[str, Any]:
    report = {
        "title": f"Business Consultation Report",
        "client": consultation.user.name,
        "date": consultation.created_at.strftime("%Y-%m-%d"),
        "query": consultation.query,
        "executive_summary": consultation.response[:500] + "...",
        "detailed_analysis": consultation.response,
        "market_insights": consultation.analysis.get("insights", []),
        "recommendations": consultation.recommendations,
        "sources": consultation.search_results.get("sources", [])[:5],
        "appendix": {
            "full_search_results": consultation.search_results.get("content", ""),
            "additional_notes": "Report generated by AI Consultant Agent"
        }
    }
    return report

def send_consultation_email(consultation: Consultation, recipient_email: str):
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        print("Email not configured. Skipping email sending.")
        return
    
    report_data = create_consultant_report(consultation)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; }}
            .content {{ background: #f9f9f9; padding: 20px; margin-top: 20px; border-radius: 10px; }}
            .section {{ margin: 20px 0; }}
            .query {{ font-style: italic; color: #666; }}
            .recommendations {{ background: #e8f4f8; padding: 15px; border-left: 4px solid #667eea; }}
            .footer {{ text-align: center; margin-top: 30px; color: #999; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Business Consultation Report</h1>
            <p>Date: {report_data['date']}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Your Query</h2>
                <p class="query">"{consultation.query}"</p>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <p>{report_data['executive_summary']}</p>
            </div>
            
            <div class="section">
                <h2>Strategic Recommendations</h2>
                <div class="recommendations">
                    {json.dumps(report_data['recommendations'], indent=2)}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by AI Consultant Agent</p>
            <p>This is an automated email. Please login to view the full report.</p>
        </div>
    </body>
    </html>
    """
    
    msg = Message(
        subject=f"Your Consultation Report - {datetime.now().strftime('%Y-%m-%d')}",
        recipients=[recipient_email],
        html=html_content
    )
    
    mail.send(msg)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        session['can_consult'] = current_user.can_consult()
        session['remaining'] = current_user.remaining_consultations()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)