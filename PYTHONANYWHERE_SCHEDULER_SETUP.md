# Setting Up Scheduled Task for Semester Expirations on PythonAnywhere

This guide explains how to set up a scheduled task to run `process_semester_expirations.py` automatically on PythonAnywhere.

## Quick Reference

**Recommended Schedule:** Daily at 2:00 AM

**Command Template:**
```bash
cd /home/yourusername/scholarsphere_2 && /home/yourusername/.virtualenvs/yourvenv/bin/python process_semester_expirations.py
```

**Test First:**
```bash
cd /home/yourusername/scholarsphere_2
python3.10 test_semester_expirations.py
python3.10 process_semester_expirations.py
```

## Prerequisites

1. You must have a PythonAnywhere account (Paid account required for scheduled tasks)
2. The script `process_semester_expirations.py` must be uploaded to your PythonAnywhere account
3. All dependencies must be installed in your PythonAnywhere environment
4. Run `test_semester_expirations.py` first to verify everything is set up correctly

## Step-by-Step Instructions

### 1. Upload the Script

1. Log in to your PythonAnywhere account
2. Go to the **Files** tab
3. Navigate to your project directory (e.g., `/home/yourusername/scholarsphere_2/`)
4. Upload `process_semester_expirations.py` to this directory

### 2. Find Your Python Path

Before setting up the scheduled task, find the correct Python interpreter path:

1. Go to the **Tasks** tab in PythonAnywhere
2. Open a **Bash console**
3. Run:
   ```bash
   which python3.10
   ```
   or
   ```bash
   which python3
   ```
   
   This will show the full path to your Python interpreter (e.g., `/usr/bin/python3.10`)

4. If using a virtual environment, find the Python path in your venv:
   ```bash
   which python
   ```
   (Run this after activating your virtual environment)

### 3. Test the Script Manually First

Before setting up the scheduled task, test that the script works:

1. Go to the **Tasks** tab in PythonAnywhere
2. Click on **Bash console** or open a console
3. Navigate to your project directory:
   ```bash
   cd /home/yourusername/scholarsphere_2
   ```
4. **First, run the test script:**
   ```bash
   python3.10 test_semester_expirations.py
   ```
   This will verify your setup is correct.

5. **Then run the actual script:**
   ```bash
   python3.10 process_semester_expirations.py
   ```
   (Replace `python3.10` with your Python version if different)

6. Verify that it runs without errors and produces the expected output

### 4. Set Up the Scheduled Task

1. Go to the **Tasks** tab in PythonAnywhere
2. Click on **Create a new scheduled task**
3. Fill in the task details:

   **Command:**
   ```
   cd /home/yourusername/scholarsphere_2 && /home/yourusername/.virtualenvs/yourvenv/bin/python process_semester_expirations.py
   ```
   
   **Note:** Replace:
   - `yourusername` with your PythonAnywhere username
   - `yourvenv` with your virtual environment name (if you're using one)
   - If not using a virtual environment, use: `/usr/bin/python3.10` (or your Python version)

   **Alternative command (if using virtualenv):**
   ```
   cd /home/yourusername/scholarsphere_2 && source /home/yourusername/.virtualenvs/yourvenv/bin/activate && python process_semester_expirations.py
   ```

4. **Schedule:** Choose when to run the task
   - **Recommended:** Run daily at 2:00 AM (to process expirations early in the day)
   - Select "Every day" and set the time to `02:00`
   - Or choose a different schedule that fits your needs

5. **Description:** Add a description like:
   ```
   Process semester expirations and send notifications to students
   ```

6. Click **Create** to save the task

### 5. Verify the Task is Set Up Correctly

1. After creating the task, you should see it listed in the **Tasks** tab
2. The task will show:
   - The command that will be run
   - The schedule (when it will run)
   - The last run time (will be empty initially)
   - The next run time

### 6. Test the Scheduled Task (Optional)

You can test the scheduled task immediately:

1. In the **Tasks** tab, find your scheduled task
2. Click the **Run now** button (if available) or wait for the scheduled time
3. Check the output/logs to ensure it ran successfully

## Important Notes

### Environment Variables

If your script relies on environment variables (like database credentials), you may need to:

1. Set them in your PythonAnywhere **Web** app configuration, OR
2. Create a `.env` file in your project directory, OR
3. Add them to the scheduled task command:
   ```
   cd /home/yourusername/scholarsphere_2 && export DATABASE_URL="your_db_url" && python process_semester_expirations.py
   ```

### Virtual Environment

If you're using a virtual environment (recommended):

1. Make sure all dependencies are installed in your virtual environment:
   ```bash
   source /home/yourusername/.virtualenvs/yourvenv/bin/activate
   pip install -r requirements.txt
   ```

2. Use the full path to the Python interpreter in your virtual environment in the scheduled task command

### Database Connection

Ensure that:
- Your database is accessible from PythonAnywhere
- The database credentials in your `.env` or configuration are correct
- The database connection works from the PythonAnywhere environment

### Logging and Error Handling

The script prints output to stdout. To capture logs:

1. You can redirect output to a log file in the scheduled task command:
   ```
   cd /home/yourusername/scholarsphere_2 && python process_semester_expirations.py >> /home/yourusername/logs/semester_expirations.log 2>&1
   ```

2. Create the logs directory first:
   ```bash
   mkdir -p /home/yourusername/logs
   ```

## Example Scheduled Task Command

Here's a complete example command (adjust paths as needed):

```bash
cd /home/yourusername/scholarsphere_2 && /home/yourusername/.virtualenvs/scholarsphere_env/bin/python process_semester_expirations.py >> /home/yourusername/logs/semester_expirations.log 2>&1
```

## Troubleshooting

### Task Not Running

1. Check that you have a **Paid account** (scheduled tasks require a paid plan)
2. Verify the command path is correct
3. Check the Python version matches your environment
4. Look for error messages in the task logs

### Import Errors

1. Make sure all dependencies are installed in your virtual environment
2. Verify the script can find `app.py` and other modules
3. Check that the working directory is set correctly in the command

### Database Connection Errors

1. Verify database credentials are correct
2. Check that your database allows connections from PythonAnywhere IPs
3. Test the database connection manually in a console

### Email Not Sending

1. Verify email configuration in your `.env` file
2. Check that Flask-Mail is properly configured
3. Test email sending manually

## Monitoring

- Check the **Tasks** tab regularly to see:
  - Last run time
  - Next run time
  - Any error messages

- Review log files (if you set up logging) to monitor script execution

## Updating the Script

If you update `process_semester_expirations.py`:
1. Upload the new version to PythonAnywhere
2. The scheduled task will automatically use the updated script
3. No need to recreate the scheduled task

