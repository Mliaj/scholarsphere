# Deploying to PythonAnywhere (Free Tier)

This guide assumes you have a GitHub account and have pushed your code there.

## Phase 1: Prepare and Push Code
1.  Create a new repository on GitHub.
2.  Push your local code to this repository:
    ```bash
    git init
    git add .
    git commit -m "Ready for deployment"
    git branch -M main
    git remote add origin https://github.com/<your-username>/<your-repo-name>.git
    git push -u origin main
    ```

## Phase 2: PythonAnywhere Setup
1.  **Sign Up/Log In** to [PythonAnywhere](https://www.pythonanywhere.com/).
2.  **Open a Bash Console**: Go to the "Consoles" tab and start a "Bash" console.
3.  **Clone your Code**:
    ```bash
    git clone https://github.com/<your-username>/<your-repo-name>.git mysite
    cd mysite
    ```
    *(Note: replacing `mysite` with a different name is fine, but you'll need to adjust paths later).*

4.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Phase 3: Database Setup
1.  Go to the **Databases** tab in PythonAnywhere.
2.  Under "Create a Database", set a password (remember this!) and click **Initialize MySQL**.
3.  Once created, note down:
    *   **Database Host**: (usually `<username>.mysql.pythonanywhere-services.com`)
    *   **Username**: (usually `<username>`)
    *   **Database Name**: (usually `<username>$default`)

## Phase 4: Configure Secrets
1.  Back in the **Bash Console** (inside `~/mysite`):
2.  Create your production configuration file:
    ```bash
    nano config.env
    ```
3.  Paste your production details (use the DB info from Phase 3):
    ```env
    SECRET_KEY=super-secret-random-string
    
    # Database Config
    DB_HOST=<your-username>.mysql.pythonanywhere-services.com
    DB_USER=<your-username>
    DB_PASS=<your-db-password>
    DB_NAME=<your-username>$default
    DB_PORT=3306
    
    # Mail Config (Free tier blocks most ports, but 587 often works for Gmail)
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USE_TLS=true
    MAIL_USERNAME=your-email@gmail.com
    MAIL_PASSWORD=your-app-password
    ```
4.  Press `Ctrl+X`, then `Y`, then `Enter` to save.

## Phase 5: Web App Configuration
1.  Go to the **Web** tab.
2.  Click **Add a new web app**.
3.  Select **Manual Configuration** (Select Python 3.10 or the version matching your local env). -> *Do NOT select "Flask" from the wizard, as it creates a dummy app. Manual gives you more control.*
4.  **Virtualenv**:
    *   Scroll down to "Virtualenv".
    *   Enter the path: `/home/<your-username>/mysite/venv`
5.  **WSGI Configuration File**:
    *   Click the link to edit the WSGI configuration file (usually `/var/www/<username>_pythonanywhere_com_wsgi.py`).
    *   Delete everything and replace it with:
    ```python
    import sys
    import os
    
    # Add your project directory to the sys.path
    project_home = '/home/<your-username>/mysite'
    if project_home not in sys.path:
        sys.path = [project_home] + sys.path
    
    # Set environment variables here if config.env fails, 
    # but your app loads config.env, so just ensure we are in the right dir.
    os.chdir(project_home)
    
    # Import the flask app
    from app import app as application
    ```
6.  **Static Files** (Optional but Recommended):
    *   Although `whitenoise` is installed, PythonAnywhere serves static files faster if you map them here.
    *   **URL**: `/static/`
    *   **Directory**: `/home/<your-username>/mysite/static`

## Phase 6: Finalize
1.  Click the big green **Reload** button at the top of the Web tab.
2.  Click the link to your site (e.g., `https://<username>.pythonanywhere.com`).
3.  The database tables will be auto-created when the app first starts (due to the code in `app.py`).

## Troubleshooting
*   **Error Log**: If the site shows "Something went wrong", check the **Error Log** link in the Web tab.
*   **Database Errors**: Ensure your `config.env` has the exact DB credentials from the Databases tab.
