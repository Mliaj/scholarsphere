# This script generates a password hash using the Werkzeug library,
# which is the same library used by the Scholarsphere application.

# To use this script:
# 1. Make sure you have the project's dependencies installed (pip install -r requirements.txt)
# 2. Run this script from your terminal: python generate_hash.py
# 3. The script will print a password hash.
# 4. Copy the entire hash string and provide it to me.

from werkzeug.security import generate_password_hash

# The password to hash
password_to_hash = 'admin123'

# Generate the hash
hashed_password = generate_password_hash(password_to_hash)

# Print the hash
print(f"The hashed password for '{password_to_hash}' is:")
print(hashed_password)