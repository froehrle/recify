#!/usr/bin/env python3
"""
Script to create Instagram session file for instaloader
"""

import instaloader
import os
from config import INSTAGRAM_SESSION_FILE

def create_instagram_session():
    """Create Instagram session file"""

    # Get credentials
    username = input("Enter Instagram username: ").strip()

    if not username:
        print("Username is required")
        return False

    # Create instaloader instance
    loader = instaloader.Instaloader()

    try:
        print(f"Logging in as {username}...")

        # Interactive login (will prompt for password and 2FA if needed)
        loader.interactive_login(username)

        # Save session
        session_filename = INSTAGRAM_SESSION_FILE or 'session'
        loader.save_session_to_file(username, session_filename)

        print(f"✅ Session saved successfully to '{session_filename}'")
        print(f"📁 Session file: {os.path.abspath(session_filename)}")

        # Test the session
        print("🔍 Testing session...")
        test_context = loader.context
        print(f"✅ Session is valid for user: {test_context.username}")

        return True

    except instaloader.exceptions.BadCredentialsException:
        print("❌ Invalid username or password")
        return False

    except instaloader.exceptions.TwoFactorAuthRequiredException:
        print("❌ Two-factor authentication required")
        print("💡 Please enable 2FA and try again")
        return False

    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False

def load_existing_session():
    """Test loading existing session"""

    username = input("Enter Instagram username for existing session: ").strip()

    if not username:
        print("Username is required")
        return False

    loader = instaloader.Instaloader()
    session_filename = INSTAGRAM_SESSION_FILE or 'session'

    try:
        loader.load_session_from_file(username, session_filename)
        print(f"✅ Successfully loaded session for {username}")
        return True

    except FileNotFoundError:
        print(f"❌ Session file not found: {session_filename}")
        return False

    except Exception as e:
        print(f"❌ Failed to load session: {e}")
        return False

def main():
    """Main function"""
    print("Instagram Session Manager")
    print("=" * 30)

    choice = input("""
Choose an option:
1. Create new session
2. Test existing session
3. Exit

Enter choice (1-3): """).strip()

    if choice == "1":
        create_instagram_session()
    elif choice == "2":
        load_existing_session()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()