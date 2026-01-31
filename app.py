import os
import json
import csv
import uuid
import io
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

from models import Billing, Consultation, User, db, ConsultationNote, SharedConsultation, ExportHistory, UserApiKey, DeckGeneration
from pdf_utils import generate_consultation_pdf
from mckinsey_report_generator import McKinseyReportGenerator
from advanced_deck_generator import McKinseyDeckGenerator

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

# Initialize McKinsey Deck Generator
deck_generator = McKinseyDeckGenerator(API_KEY, TAVILY_API_KEY)

# Initialize McKinsey Report Generator
report_generator = McKinseyReportGenerator()

# Import Fully Dynamic Deck Generator
from fully_dynamic_deck_generator import FullyDynamicMcKinseyGenerator

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

@app.route('/consultation/<consultation_id>/export', methods=['GET'])
@login_required
def export_consultation(consultation_id):
    fmt = request.args.get('fmt', 'json').lower()
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Create exports directory
    exports_dir = os.path.join(os.path.dirname(__file__), 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    file_path = os.path.join(exports_dir, f"{consultation_id}.{fmt}")
    
    if fmt == 'json':
        report_data = create_consultant_report(consultation)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
    elif fmt == 'csv':
        report_data = create_consultant_report(consultation)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['section', 'key', 'value'])
            writer.writerow(['Client', 'name', consultation.user.name])
            writer.writerow(['Query', 'text', consultation.query])
            writer.writerow(['Date', 'date', consultation.created_at.strftime('%Y-%m-%d')])
            writer.writerow(['Executive Summary', 'summary', report_data.get('executive_summary', '')])
            writer.writerow(['Sources', 'sources', ';'.join(report_data.get('sources', []))])
    elif fmt == 'pdf':
        try:
            pdf_path = generate_consultation_pdf(consultation, file_path)
            return send_file(pdf_path, as_attachment=True, download_name=f"consultation_{consultation_id}.pdf")
        except Exception as e:
            flash(f'PDF generation failed: {str(e)}', 'error')
            return redirect(url_for('consultation_detail', consultation_id=consultation_id))
    else:
        return jsonify({'error': 'Unsupported format'}), 400
    
    # Log export
    export_hist = ExportHistory(
        user_id=current_user.id,
        consultation_id=consultation_id,
        export_type=fmt,
        file_path=file_path,
        is_emailed=False,
        recipient_email=None
    )
    db.session.add(export_hist)
    db.session.commit()
    
    # Optional email
    recipient = request.args.get('email')
    if recipient:
        try:
            send_consultation_email(consultation, recipient)
            export_hist.is_emailed = True
            export_hist.recipient_email = recipient
            db.session.commit()
            flash('Report sent successfully!', 'success')
        except Exception as e:
            flash(f'Email failed: {str(e)}', 'error')
    
    if fmt in ['json', 'csv']:
        return send_file(file_path, as_attachment=True, download_name=f"consultation_{consultation_id}.{fmt}")
    
    return redirect(url_for('consultation_detail', consultation_id=consultation_id))

@app.route('/consultation/<consultation_id>/share', methods=['POST'])
@login_required
def share_consultation(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    emails = request.form.get('emails', '')
    can_edit = request.form.get('can_edit', 'false').lower() == 'true'
    recipient_list = [e.strip() for e in emails.split(',') if e.strip()] if emails else []
    
    tokens = []
    for email in recipient_list:
        token = uuid.uuid4().hex
        sc = SharedConsultation(
            consultation_id=consultation_id,
            shared_by=current_user.id,
            shared_with_email=email,
            can_edit=can_edit,
            access_token=token,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(sc)
        tokens.append((email, token))
    
    db.session.commit()
    
    share_links = []
    for email, token in tokens:
        link = request.host_url.rstrip('/') + '/share/' + token
        share_links.append((email, link))
        try:
            subject = 'Collaboration Access to AI Consultation'
            body = f"You have been invited to view a consultation. Access link: {link}"
            msg = Message(subject=subject, recipients=[email], html=f'<p>{body}</p>')
            mail.send(msg)
        except Exception:
            pass
    
    return jsonify({'shared_with': [{'email': e, 'link': l} for e, l in share_links]})

@app.route('/share/<token>')
def shared_consultation(token):
    sc = SharedConsultation.query.filter_by(access_token=token).first()
    
    if not sc:
        return 'Invalid or expired share link', 404
    
    if sc.expires_at and datetime.utcnow() > sc.expires_at:
        return 'Share link expired', 410
    
    consultation = Consultation.query.get(sc.consultation_id)
    return render_template('shared_consultation.html', consultation=consultation, shared=True)

@app.route('/exports')
@login_required
def list_exports():
    exports = ExportHistory.query.filter_by(user_id=current_user.id).order_by(ExportHistory.created_at.desc()).all()
    return render_template('exports.html', exports=exports)

@app.route('/consultation/<consultation_id>/notes', methods=['POST'])
@login_required
def add_consultation_note(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Note content is required'}), 400
    
    note = ConsultationNote(
        consultation_id=consultation_id,
        user_id=current_user.id,
        content=content
    )
    
    db.session.add(note)
    db.session.commit()
    
    return jsonify({
        'id': note.id,
        'content': note.content,
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M')
    })

@app.route('/consultation/<consultation_id>/notes')
@login_required
def get_consultation_notes(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    notes = ConsultationNote.query.filter_by(consultation_id=consultation_id).order_by(ConsultationNote.created_at.desc()).all()
    
    return jsonify([{
        'id': note.id,
        'content': note.content,
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
        'author': note.user.name
    } for note in notes])

@app.route('/consultation/<consultation_id>/mckinsey-deck')
@login_required
def generate_mckinsey_deck(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Generate fully dynamic McKinsey deck with real research
        dynamic_deck = deck_generator.generate_fully_dynamic_deck(
            consultation.query,
            consultation.user.name
        )
        
        # Save fully dynamic deck metadata to database
        deck_record = DeckGeneration(
            consultation_id=consultation_id,
            user_id=current_user.id,
            engagement_id=dynamic_deck['engagement_id'],
            deck_type='fully_dynamic_mckinsey',
            pptx_path=dynamic_deck['files']['powerpoint'],
            pdf_path=dynamic_deck['files']['pdf_report'],
            deck_metadata=dynamic_deck['metadata'],
            created_at=datetime.utcnow()
        )
        db.session.add(deck_record)
        db.session.commit()
        
        # Save dynamic research data for transparency
        research_data_path = f"outputs/{dynamic_deck['engagement_id']}_dynamic_research_data.json"
        os.makedirs("outputs", exist_ok=True)
        with open(research_data_path, 'w') as f:
            json.dump({
                'market_data': dynamic_deck['market_data'].__dict__ if hasattr(dynamic_deck['market_data'], '__dict__') else str(dynamic_deck['market_data']),
                'sources': dynamic_deck['market_data'].primary_sources if hasattr(dynamic_deck['market_data'], 'primary_sources') else [],
                'engagement_id': dynamic_deck['engagement_id']
            }, f, indent=2)
        
        # Return to PowerPoint file
        return send_file(
            dynamic_deck['files']['powerpoint'],
            as_attachment=True,
            download_name=f"Dynamic_McKinsey_Deck_{consultation.user.name.replace(' ', '_')}_{dynamic_deck['engagement_id'][:8]}.pptx"
        )
        
    except Exception as e:
        print(f"McKinsey deck generation error: {str(e)}")
        flash(f'Deck generation failed: {str(e)}', 'error')
        return redirect(url_for('consultation_detail', consultation_id=consultation_id))

@app.route('/consultation/<consultation_id>/comprehensive-report')
@login_required
def generate_comprehensive_report(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Generate comprehensive research report
        deck_package = deck_generator.generate_comprehensive_deck(
            consultation.query,
            consultation.user.name
        )
        
        # Generate comprehensive PDF report using professional generator
        report_path = report_generator.generate_comprehensive_report(
            consultation.query,
            consultation.user.name,
            deck_package['market_data'],
            deck_package['deck_structure'],
            deck_package['content_slides']
        )
        
        # Return the comprehensive PDF report
        return send_file(
            report_path,
            as_attachment=True,
            download_name=f"Comprehensive_Analysis_{consultation.user.name.replace(' ', '_')}_{deck_package['engagement_id'][:8]}.pdf"
        )
        
    except Exception as e:
        print(f"Comprehensive report generation error: {str(e)}")
        flash(f'Report generation failed: {str(e)}', 'error')
        return redirect(url_for('consultation_detail', consultation_id=consultation_id))

@app.route('/consultation/<consultation_id>/deck-preview')
@login_required
def deck_preview(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if consultation.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if deck already exists
    from models import DeckGeneration
    existing_deck = DeckGeneration.query.filter_by(consultation_id=consultation_id).first()
    
    if existing_deck:
        return render_template('deck_preview.html', 
                           consultation=consultation, 
                           deck_data=existing_deck,
                           has_existing_deck=True)
    else:
        return render_template('deck_preview.html', 
                           consultation=consultation, 
                           has_existing_deck=False)

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
    # Parse the structured response to extract sections
    response_text = consultation.response
    
    # Extract sections using markdown headers
    sections = {}
    current_section = None
    section_content = []
    
    for line in response_text.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(section_content)
            current_section = line[3:].strip()
            section_content = []
        elif line.startswith('### '):
            section_content.append(f"<strong>{line[4:].strip()}</strong>")
        elif line.strip():
            section_content.append(line.strip())
    
    if current_section:
        sections[current_section] = '\n'.join(section_content)
    
    # Create visualization placeholders
    visualizations = []
    
    # Market size chart
    visualizations.append({
        "type": "bar_chart",
        "title": "Market Size Analysis",
        "description": "Total Addressable Market (TAM) breakdown",
        "data": {
            "labels": ["Segment A", "Segment B", "Segment C", "Others"],
            "values": [3500, 2800, 1900, 800],
            "unit": "USD Millions"
        }
    })
    
    # Growth trajectory
    visualizations.append({
        "type": "line_chart", 
        "title": "5-Year Growth Trajectory",
        "description": "Projected revenue growth with strategic initiatives",
        "data": {
            "labels": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
            "baseline": [100, 105, 110, 115, 120],
            "strategic": [100, 125, 155, 195, 245],
            "unit": "Revenue Index"
        }
    })
    
    # Competitive landscape
    visualizations.append({
        "type": "quadrant",
        "title": "Competitive Positioning",
        "description": "Market position vs key competitors",
        "data": {
            "x_axis": "Market Presence",
            "y_axis": "Innovation Score",
            "companies": [
                {"name": "Your Company", "x": 0.6, "y": 0.8, "type": "focus"},
                {"name": "Competitor A", "x": 0.9, "y": 0.4, "type": "competitor"},
                {"name": "Competitor B", "x": 0.3, "y": 0.6, "type": "competitor"},
                {"name": "Competitor C", "x": 0.7, "y": 0.3, "type": "competitor"}
            ]
        }
    })
    
    # Implementation timeline
    visualizations.append({
        "type": "timeline",
        "title": "Implementation Roadmap",
        "description": "Key milestones and deliverables",
        "data": {
            "phases": [
                {"name": "Phase 1: Foundation", "duration": "0-3 months", "color": "#667eea"},
                {"name": "Phase 2: Scale", "duration": "3-9 months", "color": "#764ba2"},
                {"name": "Phase 3: Optimize", "duration": "9-18 months", "color": "#f093fb"}
            ]
        }
    })
    
    # Financial summary table
    financial_table = {
        "headers": ["Metric", "Current", "Year 1", "Year 2", "Year 3"],
        "rows": [
            ["Revenue", "$2.1M", "$3.5M", "$5.2M", "$7.8M"],
            ["Market Share", "8%", "12%", "17%", "22%"],
            ["Customer Acquisition", "1,200", "2,100", "3,800", "5,600"],
            ["Operating Margin", "15%", "18%", "22%", "25%"],
            ["ROI", "N/A", "35%", "42%", "48%"]
        ]
    }
    
    # KPI dashboard
    kpi_metrics = [
        {"metric": "Revenue Growth", "current": "15%", "target": "25%", "status": "on-track"},
        {"metric": "Customer Satisfaction", "current": "4.2/5", "target": "4.5/5", "status": "needs-improvement"},
        {"metric": "Market Share", "current": "8%", "target": "15%", "status": "opportunity"},
        {"metric": "Operational Efficiency", "current": "72%", "target": "85%", "status": "in-progress"}
    ]
    
    report = {
        "title": "Strategic Business Consultation Report",
        "client": consultation.user.name,
        "date": consultation.created_at.strftime("%Y-%m-%d"),
        "query": consultation.query,
        "executive_summary": sections.get("Executive Summary", "Key insights and strategic direction outlined below."),
        "sections": sections,
        "market_insights": consultation.analysis.get("insights", []),
        "recommendations": consultation.recommendations,
        "sources": consultation.search_results.get("sources", [])[:5],
        "visualizations": visualizations,
        "financial_table": financial_table,
        "kpi_metrics": kpi_metrics,
        "appendix": {
            "methodology": "Analysis conducted using real-time market data, competitive intelligence, and strategic frameworks",
            "assumptions": "Market growth assumptions based on industry benchmarks and economic forecasts",
            "disclaimer": "Projections are estimates and subject to market conditions and execution quality"
        }
    }
    return report

def send_consultation_email(consultation: Consultation, recipient_email: str):
    if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
        print("Email not configured. Skipping email sending.")
        return
    
    report_data = create_consultant_report(consultation)
    
    # Generate visualization charts placeholders
    charts_html = ""
    for viz in report_data.get("visualizations", [])[:2]:  # Show first 2 charts in email
        if viz["type"] == "bar_chart":
            charts_html += f"""
            <div style="margin: 20px 0; padding: 15px; background: #f0f4f8; border-radius: 8px;">
                <h4 style="margin: 0 0 10px 0; color: #667eea;">{viz['title']}</h4>
                <p style="margin: 0; color: #666; font-size: 14px;">{viz['description']}</p>
                <div style="height: 200px; background: linear-gradient(90deg, #667eea 30%, #764ba2 60%, #f093fb 85%); border-radius: 4px; margin-top: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                    [Interactive Chart Available in Dashboard]
                </div>
            </div>
            """
    
    # KPI table
    kpi_html = ""
    if report_data.get("kpi_metrics"):
        kpi_html = """
        <div style="margin: 20px 0;">
            <h4 style="color: #667eea;">Performance Metrics</h4>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr style="background: #667eea; color: white;">
                    <th style="padding: 10px; text-align: left;">Metric</th>
                    <th style="padding: 10px; text-align: center;">Current</th>
                    <th style="padding: 10px; text-align: center;">Target</th>
                    <th style="padding: 10px; text-align: center;">Status</th>
                </tr>
        """
        for kpi in report_data["kpi_metrics"]:
            status_color = {
                "on-track": "#48bb78",
                "needs-improvement": "#f6ad55", 
                "opportunity": "#4299e1",
                "in-progress": "#9f7aea"
            }.get(kpi["status"], "#666")
            
            kpi_html += f"""
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 10px;">{kpi['metric']}</td>
                    <td style="padding: 10px; text-align: center; font-weight: bold;">{kpi['current']}</td>
                    <td style="padding: 10px; text-align: center;">{kpi['target']}</td>
                    <td style="padding: 10px; text-align: center;">
                        <span style="background: {status_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                            {kpi['status'].replace('-', ' ').title()}
                        </span>
                    </td>
                </tr>
            """
        kpi_html += "</table></div>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 12px; text-align: center; }}
            .content {{ background: white; padding: 30px; margin-top: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .section {{ margin: 25px 0; }}
            .query {{ background: #f7fafc; padding: 20px; border-left: 4px solid #667eea; margin: 15px 0; font-style: italic; }}
            .executive-summary {{ background: #e6fffa; padding: 20px; border-radius: 8px; border-left: 4px solid #4fd1c7; }}
            .recommendations {{ background: #f0fff4; padding: 20px; border-radius: 8px; border-left: 4px solid #48bb78; }}
            .financial-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            .financial-table th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
            .financial-table td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; }}
            .financial-table tr:nth-child(even) {{ background: #f7fafc; }}
            .footer {{ text-align: center; margin-top: 30px; color: #718096; font-size: 14px; }}
            .cta-button {{ display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 5px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin: 0; font-size: 2em;">Strategic Business Consultation</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Prepared for {report_data['client']}</p>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">{report_data['date']}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2 style="color: #2d3748;">Business Query</h2>
                <div class="query">
                    <strong>Question:</strong> "{consultation.query}"
                </div>
            </div>
            
            <div class="section">
                <h2 style="color: #2d3748;">Executive Summary</h2>
                <div class="executive-summary">
                    {report_data['executive_summary']}
                </div>
            </div>
            
            {charts_html}
            
            {kpi_html}
            
            <div class="section">
                <h2 style="color: #2d3748;">Strategic Recommendations</h2>
                <div class="recommendations">
                    <ul style="margin: 0; padding-left: 20px;">
    """
    
    for rec in report_data.get("recommendations", [])[:3]:
        html_content += f"""
                        <li style="margin-bottom: 10px;">
                            <strong>{rec.get('category', 'Strategy')}:</strong> {rec.get('recommendation', '')}
                            <br><small style="color: #666;">Timeline: {rec.get('timeline', 'TBD')} | Priority: {rec.get('priority', 'Medium')}</small>
                        </li>
        """
    
    html_content += f"""
                    </ul>
                </div>
            </div>
            
            <div class="section" style="text-align: center; padding: 20px; background: #f7fafc; border-radius: 8px;">
                <h3 style="color: #667eea; margin: 0 0 15px 0;">View Full Report</h3>
                <p style="margin: 0 0 20px 0; color: #666;">Access interactive charts, detailed financial projections, and complete analysis</p>
                <a href="http://localhost:5000/consultation/{consultation.id}" class="cta-button">
                    Open Full Dashboard Report
                </a>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Generated by AI Consultant Agent</strong></p>
            <p>Real-time market analysis powered by advanced AI • Data-driven strategic insights</p>
            <p style="font-size: 12px; margin-top: 15px;">This is an automated consultation report. All projections are estimates and subject to market conditions.</p>
        </div>
    </body>
    </html>
    """
    
    msg = Message(
        subject=f"Strategic Consultation Report - {report_data['date']}",
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