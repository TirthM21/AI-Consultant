# 🤖 AI Business Consultant Agent

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Framework-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_2.0_Flash-4285F4?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Tavily](https://img.shields.io/badge/Search-Tavily_API-teal?style=for-the-badge&logo=google-cloud)](https://tavily.com/)

> **A sophisticated AI-driven business intelligence platform that combines real-time market research with strategic consulting to deliver actionable insights and professional reports.**

---

## ✨ Core Capabilities

### 🔍 Real-Time Intelligence
*   **Deep Web Research**: Leverages the **Tavily Search API** to pull up-to-the-minute market data, competitor analysis, and industry trends.
*   **Context-Aware Analysis**: Processes live search results to ground AI responses in current reality, avoiding hallucinations.

### 🧠 Strategic Consultation
*   **Gemini 2.0 Flash Integration**: Powered by Google's latest model for high-speed, high-reasoning business advice.
*   **Market Insights**: Automatically extracts key findings, confidence scores, and risk assessments.
*   **Actionable Roadmaps**: Generates structured recommendations with priorities, timelines, and specific action items.

### 📄 Professional Artifacts
*   **Report Generation**: Creates comprehensive consultant-style reports including executive summaries and detailed appendices.
*   **Email Delivery**: Integration with SMTP to send professional reports directly to stakeholders' inboxes.

### 💎 Enterprise-Ready Platform
*   **Secure Auth**: Full user authentication system with encrypted credentials.
*   **Usage Control**: Tiered system (Free vs. Premium) with monthly consultation limits.
*   **Modern UI**: A glassmorphism-inspired, responsive interface built for executive-level presentation.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, Flask, Flask-SQLAlchemy, Flask-Login |
| **AI Engine** | Google Gemini 2.0 Flash-exp |
| **Search API** | Tavily AI (Advanced Depth) |
| **Database** | PostgreSQL (Hosted on Neon) |
| **Frontend** | HTML5, CSS3 (Modern Glassmorphism), Bootstrap 5, JS |
| **Security** | BCrypt, Session-based Auth, CSRF Protection |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- API Keys for Google Gemini and Tavily

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd AI-CONSULTANT

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:

```env
SECRET_KEY=your_secure_secret_key

# Email Settings (for sending reports)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=AI Consultant <noreply@yourdomain.com>

# Database (Optional: Defaults to Neon PostgreSQL)
# SQLALCHEMY_DATABASE_URI=your_db_connection_string
```

### 4. Launching the App
The application initializes the database automatically on the first run.

```bash
python app.py
```
Visit `http://localhost:5000` to start your first consultation.

---

## 📁 Project Structure

```text
AI-CONSULTANT/
├── app.py                # Main Flask application & routes
├── ai_consultant_agent.py # Core logic for the AI Agent & Tavily integration
├── models.py             # Database schemas (User, Consultation, Billing)
├── static/               # CSS, JS, and Images
├── templates/            # Jinja2 HTML templates
│   ├── home.html         # Premium Landing Page
│   ├── dashboard.html    # User Workspace
│   └── consultation_detail.html # Result Visualization
└── requirements.txt      # Project dependencies
```

---

## 🔒 Security & Performance
- **Data Integrity**: Uses SQLAlchemy ORM for SQL injection prevention.
- **Async Efficiency**: Gemini 2.0 Flash provides near-instantaneous complex reasoning.
- **Privacy**: User consultations are isolated and secured with industry-standard session management.

---

## 💳 Billing & Tiers
- **Free Tier**: 3 Consultations per month.
- **Premium Tier**: Unlimited consultations, priority processing, and advanced reports ($29.99/mo).

---

## 📝 License
Copyright © 2024. All rights reserved.

---

<div align="center">
  <p>Built with ❤️ using Flask & Google Generative AI</p>
</div># AI-Consultant
