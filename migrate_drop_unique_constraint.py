import os
import pymysql
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

# Database connection details from environment variables
db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_pass = os.environ.get('DB_PASS')
db_name = os.environ.get('DB_NAME')

def drop_unique_constraint():
    """
    Connects to the MySQL database and drops the unique constraint `unique_user_scholarship`
    from the `scholarship_applications` table.
    """
    try:
        # Establish a database connection
        connection = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Successfully connected to the database.")

        with connection.cursor() as cursor:
            # SQL command to drop the unique constraint
            # Note: The constraint name must be correct
            sql_command = "ALTER TABLE scholarship_applications DROP CONSTRAINT unique_user_scholarship;"
            
            # Execute the command
            cursor.execute(sql_command)
            print("Successfully executed the command to drop the unique constraint.")

        # Commit the changes
        connection.commit()
        print("The changes have been committed to the database.")

    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL or executing command: {e}")
        # If the error is that the constraint does not exist, it's not a failure
        if e.args[0] == 1091: # Error code for "Can't DROP '...'; check that column/key exists"
            print("Constraint likely did not exist, which is acceptable.")
        else:
            # For other errors, you might want to handle them differently
            print("An unexpected database error occurred.")
            
    finally:
        # Close the connection
        if 'connection' in locals() and connection.open:
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    drop_unique_constraint()
