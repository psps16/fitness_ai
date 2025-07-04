# models/database.py

import sqlite3
import hashlib
import json
from typing import Optional, List
from datetime import datetime

from .models import User, Message

DB_FILE = "fitai_database.db"

def init_db():
    """
    Initializes the database. Creates tables for users and conversation history.
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL
            )
        """)
        
        # Create conversation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_reply TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create table for workout plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_plans (
                user_id TEXT PRIMARY KEY,
                last_updated TEXT NOT NULL,
                plan_text TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create table for diet plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diet_plans (
                user_id TEXT PRIMARY KEY,
                last_updated TEXT NOT NULL,
                plan_text TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create authentication table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                user_id TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
    print("Database initialized successfully with all required tables.")


def save_user(user: User):
    """Saves or updates a user's complete profile in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        # Save user profile
        profile_json = user.model_dump_json(indent=2)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, profile_json) VALUES (?, ?)",
            (user.user_id, profile_json)
        )
        
        # Save workout plan if exists
        if user.workout_plan:
            cursor.execute(
                """INSERT OR REPLACE INTO workout_plans 
                   (user_id, last_updated, plan_text) VALUES (?, ?, ?)""",
                (user.user_id, user.workout_plan.last_updated.isoformat(),
                 user.workout_plan.plan_text)
            )
            
        # Save diet plan if exists
        if user.diet_plan:
            cursor.execute(
                """INSERT OR REPLACE INTO diet_plans 
                   (user_id, last_updated, plan_text) VALUES (?, ?, ?)""",
                (user.user_id, user.diet_plan.last_updated.isoformat(),
                 user.diet_plan.plan_text)
            )
            
        # Save any new conversation messages
        for message in user.conversation_history:
            cursor.execute(
                """INSERT INTO conversation_history 
                   (user_id, timestamp, user_message, bot_reply) 
                   VALUES (?, ?, ?, ?)""",
                (user.user_id, message.timestamp.isoformat(),
                 message.user_message, message.bot_reply)
            )
            
        conn.commit()


def get_user(user_id: str) -> Optional[User]:
    """Retrieves a user's complete profile from the database using their unique user_id."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get user profile data
        cursor.execute("SELECT profile_json FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return None
            
        # Create user object from profile data
        user = User.model_validate_json(user_row['profile_json'])
        
        # Get workout plan if exists
        cursor.execute("""SELECT last_updated, plan_text 
                          FROM workout_plans WHERE user_id = ?""", 
                       (user_id,))
        workout_row = cursor.fetchone()
        if workout_row:
            from .models import WorkoutPlan
            user.workout_plan = WorkoutPlan(
                last_updated=datetime.fromisoformat(workout_row['last_updated']),
                plan_text=workout_row['plan_text']
            )
            
        # Get diet plan if exists
        cursor.execute("""SELECT last_updated, plan_text 
                          FROM diet_plans WHERE user_id = ?""", 
                       (user_id,))
        diet_row = cursor.fetchone()
        if diet_row:
            from .models import DietPlan
            user.diet_plan = DietPlan(
                last_updated=datetime.fromisoformat(diet_row['last_updated']),
                plan_text=diet_row['plan_text']
            )
            
        # Get conversation history
        cursor.execute("""SELECT timestamp, user_message, bot_reply 
                          FROM conversation_history 
                          WHERE user_id = ? 
                          ORDER BY timestamp ASC""", 
                       (user_id,))
        messages = cursor.fetchall()
        
        # Add messages to user object
        from .models import Message
        user.conversation_history = [
            Message(
                timestamp=datetime.fromisoformat(msg['timestamp']),
                user_message=msg['user_message'],
                bot_reply=msg['bot_reply']
            ) for msg in messages
        ]
        
        return user


def save_message(user_id: str, user_message: str, bot_reply: str):
    """
    Saves a new message pair to the conversation history.
    This can be called directly without loading the full user profile.
    """
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO conversation_history 
               (user_id, timestamp, user_message, bot_reply) 
               VALUES (?, ?, ?, ?)""",
            (user_id, timestamp, user_message, bot_reply)
        )
        conn.commit()


def get_all_user_ids() -> List[str]:
    """Returns a list of all registered user IDs."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str, user: User) -> bool:
    """Register a new user with username and password."""
    password_hash = hash_password(password)
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Check if username already exists
            cursor.execute("SELECT username FROM auth WHERE username = ?", (username,))
            if cursor.fetchone():
                print("\n❌ Username already exists. Please choose another one.")
                return False
                
            # Save the authentication details
            cursor.execute(
                "INSERT INTO auth (username, password_hash, user_id) VALUES (?, ?, ?)",
                (username, password_hash, user.user_id)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False


def authenticate_user(username: str, password: str) -> Optional[str]:
    """Authenticate a user and return their user_id if successful."""
    password_hash = hash_password(password)
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM auth WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return None