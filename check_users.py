from app import app, db, User

def list_users():
    with app.app_context():
        users = User.query.all()
        print(f"{'ID':<5} {'Name':<30} {'Email/ID':<35} {'Role':<10} {'Active':<10}")
        print("-" * 90)
        for user in users:
            identifier = user.student_id if user.student_id else user.email
            print(f"{user.id:<5} {user.get_full_name():<30} {identifier:<35} {user.role:<10} {user.is_active!s:<10}")

if __name__ == "__main__":
    list_users()
