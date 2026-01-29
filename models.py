from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    consultations_count = db.Column(db.Integer, default=0)
    monthly_limit = db.Column(db.Integer, default=3)
    billing_active = db.Column(db.Boolean, default=False)
    subscription_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    consultations = db.relationship('Consultation', backref='user', lazy=True, cascade='all, delete-orphan')
    billing_history = db.relationship('Billing', backref='user', lazy=True, cascade='all, delete-orphan')
    api_keys = db.relationship('UserApiKey', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def increment_usage(self):
        self.consultations_count += 1
        db.session.commit()
    
    def can_consult(self):
        if self.is_premium and self.billing_active:
            if self.subscription_end and datetime.utcnow() > self.subscription_end:
                return False
            return True
        return self.consultations_count < self.monthly_limit
    
    def remaining_consultations(self):
        if self.is_premium and self.billing_active:
            if self.subscription_end:
                days_left = (self.subscription_end - datetime.utcnow()).days
                return f"Unlimited (expires in {days_left} days)"
            return "Unlimited"
        return max(0, self.monthly_limit - self.consultations_count)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Consultation(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    search_results = db.Column(db.JSON, nullable=True)
    analysis = db.Column(db.JSON, nullable=True)
    recommendations = db.Column(db.JSON, nullable=True)
    report_generated = db.Column(db.Boolean, default=False)
    report_data = db.Column(db.JSON, nullable=True)
    is_shared = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(36), nullable=True)
    email_preference = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    notes = db.relationship('ConsultationNote', backref='consultation', lazy=True, cascade='all, delete-orphan')
    shared_with = db.relationship('SharedConsultation', backref='consultation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Consultation {self.id[:8]}...>'

class ConsultationNote(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id = db.Column(db.String(36), db.ForeignKey('consultation.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notes')
    
    def __repr__(self):
        return f'<ConsultationNote {self.id[:8]}...>'

class SharedConsultation(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id = db.Column(db.String(36), db.ForeignKey('consultation.id'), nullable=False)
    shared_by = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    shared_with_email = db.Column(db.String(120), nullable=False)
    can_edit = db.Column(db.Boolean, default=False)
    access_token = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    shared_by_user = db.relationship('User', foreign_keys=[shared_by], backref='shared_consultations')
    
    def __repr__(self):
        return f'<SharedConsultation {self.id[:8]}...>'

class Billing(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Billing {self.id[:8]}... ${self.amount}>'

class UserApiKey(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<UserApiKey {self.name}>'

class ExportHistory(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    consultation_id = db.Column(db.String(36), db.ForeignKey('consultation.id'), nullable=True)
    export_type = db.Column(db.String(20), nullable=False)  # PDF, JSON, CSV
    file_path = db.Column(db.String(500), nullable=True)
    is_emailed = db.Column(db.Boolean, default=False)
    recipient_email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExportHistory {self.export_type}>'