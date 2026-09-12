from db.client import db_client


def seed_demo_user():
    email = "candidate@hiremind.ai"
    password = "devpass"
    full_name = "Dev Candidate"
    role = "candidate"
    try:
        user = db_client.sign_up(email=email, password=password, full_name=full_name, role=role)
        print(f"✓ Seeded demo user: {email}")
        return user
    except ValueError:
        print(f"• Demo user {email} already exists.")
        return None


if __name__ == "__main__":
    seed_demo_user()
