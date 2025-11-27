# Deployment Guide for Scholarsphere

This guide covers two common ways to deploy your Flask application: using a Platform as a Service (PaaS) like Render.com, and using a traditional Linux VPS (Ubuntu).

## Prerequisites for Production

1.  **Gunicorn**: We have added `gunicorn` to your `requirements.txt`. This is the production WSGI server that will serve your Python application.
2.  **Procfile**: A `Procfile` has been created for PaaS deployments.
3.  **Database**: You will need a MySQL database accessible from your production environment.

---

## Option 1: Deploy to Render.com (Easiest)

Render is a modern cloud platform that makes deployment very simple.

1.  **Push to GitHub/GitLab**: Ensure your project is pushed to a remote repository.
2.  **Create a Web Service**:
    *   Go to [Render Dashboard](https://dashboard.render.com/).
    *   Click "New +" -> "Web Service".
    *   Connect your repository.
3.  **Configure Service**:
    *   **Runtime**: Python 3
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn app:app` (Render might auto-detect this from the `Procfile`)
4.  **Environment Variables**:
    *   Scroll down to the "Environment" section.
    *   Add the keys from your `config.env` file (e.g., `SECRET_KEY`, `DB_HOST`, `DB_USER`, etc.).
    *   **Important**: For `DB_HOST`, you cannot use `127.0.0.1` or `localhost`. You need a hosted database.
5.  **Database**:
    *   You can create a managed MySQL database on Render (New + -> MySQL) or use another provider (e.g., PlanetScale, AWS RDS).
    *   Update the `DB_*` environment variables in your Web Service to point to this new database.

---

## Option 2: Deploy to Ubuntu VPS (DigitalOcean, AWS EC2, Linode)

This gives you full control but requires more setup.

### 1. Server Setup
SSH into your server and update packages:
```bash
sudo apt update
sudo apt upgrade
```

### 2. Install Dependencies
Install Python, pip, and MySQL client dependencies:
```bash
sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
sudo apt install libmysqlclient-dev pkg-config
```

### 3. Set up the Project
Clone your repository and set up the virtual environment:
```bash
git clone <your-repo-url>
cd scholarsphere_2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Gunicorn (Systemd Service)
Create a systemd service file to keep your app running:
`sudo nano /etc/systemd/system/scholarsphere.service`

Paste the following (adjust paths/user):
```ini
[Unit]
Description=Gunicorn instance to serve Scholarsphere
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/scholarsphere_2
Environment="PATH=/home/ubuntu/scholarsphere_2/venv/bin"
EnvironmentFile=/home/ubuntu/scholarsphere_2/.env
ExecStart=/home/ubuntu/scholarsphere_2/venv/bin/gunicorn --workers 3 --bind unix:scholarsphere.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl start scholarsphere
sudo systemctl enable scholarsphere
```

### 5. Configure Nginx
Install Nginx:
```bash
sudo apt install nginx
```

Create a server block:
`sudo nano /etc/nginx/sites-available/scholarsphere`

```nginx
server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/scholarsphere_2/scholarsphere.sock;
    }

    location /static {
        alias /home/ubuntu/scholarsphere_2/static;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/scholarsphere /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Database Setup
Install MySQL Server (if running locally on the VPS):
```bash
sudo apt install mysql-server
sudo mysql_secure_installation
```
Create the database and user as per the project requirements.
