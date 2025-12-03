# Scholarsphere Python - University of Cebu Scholarship Portal

A complete Python Flask web application for managing university scholarships, converted from the original PHP version.

## Features

- **User Authentication**: Student, Provider, and Admin role-based access
- **Student Dashboard**: Profile management, credential uploads, scholarship applications
- **Provider Dashboard**: Scholarship management, application review, scheduling
- **Admin Dashboard**: User management, system oversight, analytics
- **Responsive Design**: Modern UI with mobile-friendly interface
- **Database Integration**: MySQL database with SQLAlchemy ORM

## Technology Stack

- **Backend**: Python 3.8+, Flask 2.3.3
- **Database**: MySQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Authentication**: Flask-Login with password hashing
- **Styling**: Custom CSS with Poppins font and Font Awesome icons

## Project Structure

```
scholarsphere_python/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── config.env            # Environment configuration
├── config/               # Configuration files
│   ├── __init__.py
│   └── database.py
├── auth/                 # Authentication module
│   ├── __init__.py
│   └── routes.py
├── admin/                # Admin dashboard module
│   ├── __init__.py
│   └── routes.py
├── students/             # Student dashboard module
│   ├── __init__.py
│   └── routes.py
├── provider/             # Provider dashboard module
│   ├── __init__.py
│   └── routes.py
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   └── auth/
│       ├── login.html
│       └── signup.html
└── static/               # Static assets
    ├── css/
    │   ├── main.css
    │   └── auth.css
    ├── js/
    │   ├── main.js
    │   └── auth.js
    └── images/
        └── uc-logo.png
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher
- pip (Python package manager)

### 1. Clone/Download the Project

```bash
# If you have the project files, navigate to the directory
cd scholarsphere_python
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

1. **Create MySQL Database**:
   ```sql
   CREATE DATABASE scholarsphere CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Update Database Configuration**:
   - Edit `config.env` file
   - Update database credentials:
     ```
     DB_HOST=127.0.0.1
     DB_USER=your_username
     DB_PASS=your_password
     DB_NAME=scholarsphere
     ```

### 5. Environment Configuration

1. **Copy and configure environment file**:
   ```bash
   cp config.env .env
   ```

2. **Update the configuration**:
   - Change `SECRET_KEY` to a secure random string
   - Update database credentials
   - Configure other settings as needed

### 6. Initialize Database

```bash
python app.py
```

The application will automatically create the necessary database tables on first run.

### 7. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

### Default Access

- **Home Page**: `http://localhost:5000`
- **Login**: `http://localhost:5000/auth/login`
- **Signup**: `http://localhost:5000/auth/signup`

### User Roles

1. **Students**: Can browse scholarships, manage profile, upload credentials, apply for scholarships
2. **Providers**: Can create scholarships, review applications, manage schedules
3. **Admins**: Can manage users, oversee system, view analytics

### Creating the Admin User

To create the default admin account, run the following script from your terminal:

```bash
python create_admin.py
```

This will create an admin user with the following credentials:
- **Email**: `admin@scholarsphere.com`
- **Password**: `admin123`

It is strongly recommended to change the password after the first login.

## Development

### Running in Development Mode

```bash
# Set environment variables
export FLASK_ENV=development
export FLASK_DEBUG=True

# Run the application
python app.py
```

### Database Migrations

The application uses SQLAlchemy for database management. Tables are created automatically on first run.

### Adding New Features

1. Create new routes in appropriate module files
2. Add corresponding templates in `templates/` directory
3. Update navigation and links as needed
4. Test thoroughly before deployment

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/signup` - User registration
- `GET /auth/logout` - User logout

### Student Routes
- `GET /students/dashboard` - Student dashboard
- `GET /students/profile` - Student profile
- `GET /students/credentials` - Student credentials
- `GET /students/applications` - Student applications
- `GET /students/scholarships` - Available scholarships

### Provider Routes
- `GET /provider/dashboard` - Provider dashboard
- `GET /provider/scholarships` - Manage scholarships
- `GET /provider/applications` - Review applications
- `GET /provider/schedules` - Manage schedules
- `GET /provider/documents` - Document management
- `GET /provider/remarks` - Review remarks
- `GET /provider/profile` - Organization profile

### Admin Routes
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - User management
- `GET /admin/providers` - Provider management
- `GET /admin/scholarships` - Scholarship oversight
- `GET /admin/applications` - Application management
- `GET /admin/reports` - Reports and analytics

## Security Features

- Password hashing using Werkzeug
- CSRF protection with Flask-WTF
- Session management with Flask-Login
- Input validation and sanitization
- SQL injection prevention with SQLAlchemy ORM

## Browser Support

- Chrome 70+
- Firefox 65+
- Safari 12+
- Edge 79+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## Changelog

### Version 1.0.0
- Initial Python conversion from PHP
- Complete authentication system
- Student, Provider, and Admin dashboards
- Responsive design implementation
- Database integration with SQLAlchemy

---

**Note**: This is a converted version of the original PHP Scholarsphere application. Make sure to update all configuration files and test thoroughly before deploying to production.
