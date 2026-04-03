from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_civic.db'  # Using SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Simple model - just one table
class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='reported')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    issues = Issue.query.order_by(Issue.created_at.desc()).all()
    return render_template('simple_index.html', issues=issues)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        
        issue = Issue(title=title, description=description, location=location)
        db.session.add(issue)
        db.session.commit()
        
        flash('Issue submitted successfully!')
        return redirect(url_for('index'))
    
    return render_template('simple_submit.html')

@app.route('/admin')
def admin():
    issues = Issue.query.all()
    return render_template('simple_admin.html', issues=issues)

@app.route('/update/<int:issue_id>')
def update_status(issue_id):
    issue = Issue.query.get(issue_id)
    if issue.status == 'reported':
        issue.status = 'in_progress'
    elif issue.status == 'in_progress':
        issue.status = 'resolved'
    
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
