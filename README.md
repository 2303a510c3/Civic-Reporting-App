# Civic Reporting App MVP

A simple Flask-based web application for crowdsourced civic issue reporting with admin dashboard and basic analytics.

## Features

- **Issue Submission**: Users can report civic issues with photos, descriptions, and location
- **Admin Dashboard**: Manage and track reported issues
- **Status Updates**: Update issue status (reported, in progress, resolved)
- **Basic Analytics**: View statistics and category breakdowns
- **Mobile-Friendly**: Responsive design for mobile devices

## Setup Instructions

### Prerequisites

1. **Python 3.7+** installed on your system
2. **MySQL Server** installed and running
3. **Git** (optional, for version control)

### Database Setup

1. **Install MySQL Server**:
   - Download from: https://dev.mysql.com/downloads/mysql/
   - Follow installation instructions for your OS
   - Note down your MySQL root password

2. **Create Database**:
   ```sql
   mysql -u root -p
   CREATE DATABASE civic_reporting;
   EXIT;
   ```

3. **Update Database Connection**:
   - Edit `app.py` line 12
   - Change: `'mysql+mysqlconnector://root:password@localhost/civic_reporting'`
   - Replace `password` with your MySQL root password

### Application Setup

1. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   ```

2. **Activate Virtual Environment**:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. **Access the Application**:
   - Open browser and go to: `http://localhost:5000`
   - Default admin login: username=`admin`, password=`admin123`

## Project Structure

```
Civic Reporting App/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── submit.html       # Issue submission form
│   ├── login.html        # Admin login
│   └── dashboard.html    # Admin dashboard
└── static/               # Static files
    ├── css/              # CSS files
    ├── js/               # JavaScript files
    └── uploads/          # Uploaded images
```

## Usage

### For Citizens (Public Users)

1. **Report Issues**:
   - Go to "Report Issue" page
   - Fill out the form with issue details
   - Upload a photo (optional)
   - Use "Use Current Location" button for GPS coordinates
   - Submit the report

2. **View Recent Issues**:
   - Check the home page for recently reported issues
   - See status updates and progress

### For Administrators

1. **Login**:
   - Go to "Login" page
   - Use admin credentials: `admin` / `admin123`

2. **Manage Issues**:
   - View all reported issues in the dashboard
   - Filter by status or category
   - Update issue status and assign departments
   - View analytics and statistics

3. **Update Issue Status**:
   - Click "View" on any issue
   - Change status: Reported → In Progress → Resolved
   - Assign to appropriate department

## API Endpoints

- `GET /api/issues` - Returns JSON list of all issues
- `POST /submit` - Submit new issue
- `POST /update_status/<id>` - Update issue status (admin only)

## Configuration

### Environment Variables (Optional)

Create a `.env` file for production:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+mysqlconnector://user:pass@localhost/civic_reporting
UPLOAD_FOLDER=static/uploads
```

### File Upload Settings

- Maximum file size: 16MB
- Allowed formats: JPG, PNG, JPEG, GIF
- Upload directory: `static/uploads/`

## Security Notes

⚠️ **Important for Production**:
1. Change the default admin password
2. Use a strong SECRET_KEY
3. Set up proper database credentials
4. Enable HTTPS
5. Configure proper file upload restrictions
6. Add input validation and sanitization

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Check MySQL is running
   - Verify database credentials in `app.py`
   - Ensure database `civic_reporting` exists

2. **File Upload Issues**:
   - Check `static/uploads/` directory exists
   - Verify file permissions
   - Check file size limits

3. **Import Errors**:
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility

### Getting Help

- Check Flask documentation: https://flask.palletsprojects.com/
- MySQL documentation: https://dev.mysql.com/doc/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/

## License

This project is open source and available under the MIT License.
