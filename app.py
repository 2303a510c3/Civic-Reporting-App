from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from datetime import datetime, timedelta
import uuid
import math
import requests
import base64
from sqlalchemy import or_, and_, func, case

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:Aman%40123@localhost:3306/civic_reporting'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grievance_id = db.Column(db.String(20), unique=True)  # GRIE-2024-001
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    voice_note_path = db.Column(db.String(200))  # Voice input
    photo_path = db.Column(db.String(200))
    location = db.Column(db.String(200))
    coordinates = db.Column(db.String(50))  # GPS coordinates
    status = db.Column(db.String(50), default='reported')  # reported, in_progress, resolved, escalated
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    category = db.Column(db.String(50))
    department = db.Column(db.String(100))
    escalation_level = db.Column(db.Integer, default=1)  # 1-5 levels
    duplicate_of = db.Column(db.Integer, db.ForeignKey('issue.id'))  # Duplicate handling
    resolution_time = db.Column(db.Integer)  # Hours to resolve
    citizen_satisfaction = db.Column(db.Integer)  # 1-5 rating
    feedback = db.Column(db.Text)  # Citizen feedback
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions for Enhanced Features

def generate_grievance_id():
    """Generate unique grievance ID"""
    today = datetime.now()
    year = today.year
    month = today.month
    
    # Count issues this month
    month_start = datetime(year, month, 1)
    count = Issue.query.filter(Issue.created_at >= month_start).count()
    
    return f"GRIE-{year}{month:02d}-{count+1:04d}"

def calculate_distance(loc1, loc2):
    """Calculate distance between two GPS coordinates"""
    try:
        lat1, lng1 = map(float, loc1.split(','))
        lat2, lng2 = map(float, loc2.split(','))
        
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng/2) * math.sin(dlng/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    except:
        return float('inf')

def detect_duplicate_issue(new_issue):
    """Detect if similar issue already exists"""
    # Find recent issues in same category (within 7 days)
    recent_issues = Issue.query.filter(
        Issue.category == new_issue.category,
        Issue.created_at >= datetime.utcnow() - timedelta(days=7),
        Issue.status.in_(['reported', 'in_progress'])
    ).all()
    
    for existing in recent_issues:
        if existing.coordinates and new_issue.coordinates:
            distance = calculate_distance(new_issue.coordinates, existing.coordinates)
            if distance < 0.1:  # Within 100 meters
                return existing
        else:
            # Fallback to text similarity
            if (new_issue.location.lower() in existing.location.lower() or 
                existing.location.lower() in new_issue.location.lower()):
                return existing
    
    return None

def auto_categorize_issue(title, description):
    """Automatically categorize issues based on keywords"""
    text = f"{title} {description}".lower()
    
    category_keywords = {
        'road': ['pothole', 'road', 'street', 'highway', 'asphalt', 'crack', 'traffic', 'signal'],
        'water': ['water', 'pipe', 'leak', 'supply', 'drain', 'sewer', 'flood', 'overflow'],
        'electricity': ['power', 'electricity', 'light', 'lamp', 'pole', 'outage', 'blackout'],
        'waste': ['garbage', 'waste', 'trash', 'dump', 'collection', 'bin', 'sanitation']
    }
    
    category_scores = {}
    for category, keywords in category_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text)
        category_scores[category] = score
    
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] > 0:
            return best_category
    
    return 'other'

def auto_assign_priority(title, description, category):
    """Automatically assign priority based on content analysis"""
    text = f"{title} {description}".lower()
    
    high_priority_keywords = ['emergency', 'urgent', 'dangerous', 'hazard', 'accident', 'safety', 'fire', 'flood']
    medium_priority_keywords = ['broken', 'damage', 'repair', 'problem', 'malfunction', 'slow']
    
    for keyword in high_priority_keywords:
        if keyword in text:
            return 'high'
    
    for keyword in medium_priority_keywords:
        if keyword in text:
            return 'medium'
    
    return 'low'

def categorize_with_openai(title, description):
    """Use OpenAI API for categorization (optional)"""
    try:
        # Simple fallback to keyword-based categorization
        return auto_categorize_issue(title, description)
    except:
        return auto_categorize_issue(title, description)

def check_escalation_needed(issue):
    """Check if issue needs escalation"""
    hours_since_created = (datetime.utcnow() - issue.created_at).total_seconds() / 3600
    
    # Escalate if high priority and no response in 24 hours
    if issue.priority == 'high' and hours_since_created > 24 and issue.status == 'reported':
        return True
    
    # Escalate if critical and no response in 6 hours
    if issue.priority == 'critical' and hours_since_created > 6 and issue.status == 'reported':
        return True
    
    # Escalate if in progress for more than 72 hours
    if issue.status == 'in_progress' and hours_since_created > 72:
        return True
    
    return False

# Forms
class IssueForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10)])
    category = SelectField('Category', choices=[
        ('road', 'Road Issues'),
        ('water', 'Water Supply'),
        ('electricity', 'Electricity'),
        ('waste', 'Waste Management'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], default='medium')
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'])])
    voice_note = FileField('Voice Note', validators=[FileAllowed(['mp3', 'wav', 'ogg'])])
    location = StringField('Location', validators=[DataRequired()])
    coordinates = HiddenField('Coordinates')
    submit = SubmitField('Submit Issue')

class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent')
    ], validators=[DataRequired()])
    comment = TextAreaField('Additional Comments')
    submit = SubmitField('Submit Feedback')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StatusUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('reported', 'Reported'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved')
    ], validators=[DataRequired()])
    department = StringField('Department')
    submit = SubmitField('Update Status')

# Routes
@app.route('/')
def index():
    recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(5).all()
    return render_template('index.html', issues=recent_issues)

@app.route('/submit', methods=['GET', 'POST'])
def submit_issue():
    form = IssueForm()
    if form.validate_on_submit():
        
        # Auto-categorize and assign priority using AI
        auto_category = categorize_with_openai(form.title.data, form.description.data)
        auto_priority = auto_assign_priority(form.title.data, form.description.data, auto_category)
        
        # Use auto-categorized values if user didn't specify
        final_category = form.category.data if form.category.data != 'other' else auto_category
        final_priority = form.priority.data if form.priority.data != 'medium' else auto_priority
        
        # Handle photo upload
        photo_path = None
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            photo_path = unique_filename

        # Handle voice note upload
        voice_path = None
        if form.voice_note.data:
            voice_file = form.voice_note.data
            filename = secure_filename(voice_file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'voice', unique_filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            voice_file.save(file_path)
            voice_path = unique_filename

        # Determine department based on category
        department_mapping = {
            'road': 'Public Works Department',
            'water': 'Water Department',
            'electricity': 'Electricity Department',
            'waste': 'Sanitation Department',
            'other': 'General Administration'
        }
        department = department_mapping.get(final_category, 'General Administration')

        # Create new issue
        issue = Issue(
            grievance_id=generate_grievance_id(),
            title=form.title.data,
            description=form.description.data,
            photo_path=photo_path,
            voice_note_path=voice_path,
            location=form.location.data,
            coordinates=form.coordinates.data,
            category=final_category,
            priority=final_priority,
            department=department,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        # Check for duplicates
        duplicate = detect_duplicate_issue(issue)
        if duplicate:
            flash(f'Similar issue already reported (Grievance ID: {duplicate.grievance_id}). Please check if this is the same issue.', 'warning')
            return render_template('submit.html', form=form)
        
        db.session.add(issue)
        db.session.commit()
        
        flash(f'Issue submitted successfully! Your Grievance ID is: {issue.grievance_id}', 'success')
        return redirect(url_for('index'))
    
    return render_template('submit.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    
    # Build query
    query = Issue.query
    if status_filter != 'all':
        query = query.filter(Issue.status == status_filter)
    if category_filter != 'all':
        query = query.filter(Issue.category == category_filter)
    
    issues = query.order_by(Issue.created_at.desc()).all()
    
    # Analytics
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='resolved').count()
    in_progress_issues = Issue.query.filter_by(status='in_progress').count()
    
    # Category breakdown
    category_stats = db.session.query(
        Issue.category, 
        db.func.count(Issue.id)
    ).group_by(Issue.category).all()
    
    # Check for issues that need escalation
    escalated_issues = Issue.query.filter_by(status='escalated').count()
    
    # Check for overdue issues
    overdue_issues = Issue.query.filter(
        Issue.status == 'reported',
        Issue.created_at < datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    return render_template('dashboard.html', 
                         issues=issues, 
                         total_issues=total_issues,
                         resolved_issues=resolved_issues,
                         in_progress_issues=in_progress_issues,
                         escalated_issues=escalated_issues,
                         overdue_issues=overdue_issues,
                         category_stats=category_stats,
                         status_filter=status_filter,
                         category_filter=category_filter)

@app.route('/update_status/<int:issue_id>', methods=['POST'])
@login_required
def update_status(issue_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    issue = Issue.query.get_or_404(issue_id)
    new_status = request.form.get('status')
    
    issue.status = new_status
    issue.department = request.form.get('department', issue.department)
    issue.updated_at = datetime.utcnow()
    
    # Calculate resolution time if issue is resolved
    if new_status == 'resolved':
        time_diff = issue.updated_at - issue.created_at
        issue.resolution_time = int(time_diff.total_seconds() / 3600)  # Convert to hours
    
    db.session.commit()
    flash('Status updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Basic analytics
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='resolved').count()
    in_progress_issues = Issue.query.filter_by(status='in_progress').count()
    escalated_issues = Issue.query.filter_by(status='escalated').count()
    
    # Resolution rate
    resolution_rate = (resolved_issues / total_issues * 100) if total_issues > 0 else 0
    
    # Category breakdown
    category_stats = db.session.query(
        Issue.category,
        func.count(Issue.id).label('total'),
        func.sum(case((Issue.status == 'resolved', 1), else_=0)).label('resolved'),
        func.avg(case(
            (Issue.status == 'resolved', 
             (Issue.updated_at - Issue.created_at).cast(db.Float) / 3600),
            else_=None
        )).label('avg_response_time')
    ).group_by(Issue.category).all()
    
    # Department performance
    dept_stats = db.session.query(
        Issue.department,
        func.count(Issue.id).label('total'),
        func.sum(case((Issue.status == 'resolved', 1), else_=0)).label('resolved'),
        func.avg(case(
            (Issue.status == 'resolved', 
             (Issue.updated_at - Issue.created_at).cast(db.Float) / 3600),
            else_=None
        )).label('avg_response_time')
    ).group_by(Issue.department).all()
    
    # Priority analysis
    priority_stats = db.session.query(
        Issue.priority,
        func.count(Issue.id).label('count'),
        func.avg(case(
            (Issue.status == 'resolved', 
             (Issue.updated_at - Issue.created_at).cast(db.Float) / 3600),
            else_=None
        )).label('avg_response_time')
    ).group_by(Issue.priority).all()
    
    # Recent trends (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_trends = db.session.query(
        func.date(Issue.created_at).label('date'),
        func.count(Issue.id).label('issues_count'),
        func.sum(case((Issue.status == 'resolved', 1), else_=0)).label('resolved_count')
    ).filter(Issue.created_at >= thirty_days_ago).group_by(func.date(Issue.created_at)).order_by('date').all()
    
    # Satisfaction ratings
    avg_satisfaction = db.session.query(func.avg(Feedback.rating)).scalar() or 0
    total_feedback = Feedback.query.count()
    
    return render_template('analytics.html',
                         total_issues=total_issues,
                         resolved_issues=resolved_issues,
                         in_progress_issues=in_progress_issues,
                         escalated_issues=escalated_issues,
                         resolution_rate=round(resolution_rate, 2),
                         category_stats=category_stats,
                         dept_stats=dept_stats,
                         priority_stats=priority_stats,
                         recent_trends=recent_trends,
                         avg_satisfaction=round(avg_satisfaction, 2),
                         total_feedback=total_feedback)

@app.route('/issue/<int:issue_id>/feedback', methods=['GET', 'POST'])
def issue_feedback(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    form = FeedbackForm()
    
    if form.validate_on_submit():
        feedback = Feedback(
            issue_id=issue.id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        
        # Update issue satisfaction
        issue.citizen_satisfaction = form.rating.data
        issue.feedback = form.comment.data
        
        db.session.add(feedback)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('index'))
    
    return render_template('feedback.html', form=form, issue=issue)

@app.route('/issue/<int:issue_id>')
def view_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    feedback = Feedback.query.filter_by(issue_id=issue_id).first()
    return render_template('issue_detail.html', issue=issue, feedback=feedback)

@app.route('/api/escalate/<int:issue_id>', methods=['POST'])
@login_required
def escalate_issue(issue_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    issue = Issue.query.get_or_404(issue_id)
    
    if issue.escalation_level < 5:
        issue.escalation_level += 1
        issue.status = 'escalated'
        issue.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'escalation_level': issue.escalation_level,
            'message': f'Issue escalated to level {issue.escalation_level}'
        })
    
    return jsonify({'error': 'Issue already at maximum escalation level'}), 400

@app.route('/api/convert-voice', methods=['POST'])
def convert_voice():
    """Convert voice to text using browser speech recognition"""
    # This will be handled by frontend JavaScript
    return jsonify({'message': 'Voice conversion handled by frontend'})

@app.route('/api/issues')
def api_issues():
    issues = Issue.query.all()
    return jsonify([{
        'id': issue.id,
        'grievance_id': issue.grievance_id,
        'title': issue.title,
        'description': issue.description,
        'location': issue.location,
        'coordinates': issue.coordinates,
        'status': issue.status,
        'priority': issue.priority,
        'category': issue.category,
        'department': issue.department,
        'escalation_level': issue.escalation_level,
        'created_at': issue.created_at.isoformat(),
        'photo_path': issue.photo_path,
        'voice_note_path': issue.voice_note_path
    } for issue in issues])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
    
    app.run(debug=True)
