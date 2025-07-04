#!/usr/bin/env python3

import re
from typing import Dict, Any, Tuple
import os
from dotenv import load_dotenv, set_key

from models.models import User, WorkoutPlan, DietPlan
from models.database import save_user

# Constants for MCQ options (copied from fitness_agent.py for reference)
ACTIVITY_LEVELS = ["Sedentary", "Moderate", "Active"]
FITNESS_GOALS = ["Weight Loss", "Muscle Gain", "Endurance"]
DIETARY_PREFERENCES = ["Vegan", "Vegetarian", "Non-vegetarian"]

def parse_profile_update(message: str) -> Dict[str, Any]:
    """
    Parse a user message to detect profile update requests.
    
    Args:
        message: User message to parse
        
    Returns:
        Dictionary of field:value pairs to update, or empty dict if no updates found
    """
    updates = {}
    
    # Check for weight updates
    weight_patterns = [
        r"my weight is (?:now |currently )?(\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"i (?:now )?weigh (\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"i've lost (\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"i've gained (\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"my weight (?:has )?changed to (\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"update my weight to (\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
        r"i am (?:now |currently )?(\d+\.?\d*)\s*(?:kg|kilos|kilograms)",
    ]
    
    for pattern in weight_patterns:
        match = re.search(pattern, message.lower())
        if match:
            try:
                weight = float(match.group(1))
                if 30 <= weight <= 300:  # Basic validation
                    updates["weight_kg"] = weight
                break
            except ValueError:
                pass
    
    # Check for height updates
    height_patterns = [
        r"my height is (?:now |currently )?(\d+\.?\d*)\s*(?:cm|centimeters)",
        r"i am (?:now )?(\d+\.?\d*)\s*(?:cm|centimeters) tall",
        r"update my height to (\d+\.?\d*)\s*(?:cm|centimeters)",
    ]
    
    for pattern in height_patterns:
        match = re.search(pattern, message.lower())
        if match:
            try:
                height = float(match.group(1))
                if 100 <= height <= 250:  # Basic validation
                    updates["height_cm"] = height
                break
            except ValueError:
                pass
    
    # Check for age updates
    age_patterns = [
        r"my age is (?:now |currently )?(\d+)",
        r"i am (?:now )?(\d+) years old",
        r"update my age to (\d+)",
        r"i turned (\d+)",
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, message.lower())
        if match:
            try:
                age = int(match.group(1))
                if 12 <= age <= 120:  # Basic validation
                    updates["age"] = age
                break
            except ValueError:
                pass
    
    # Check for activity level updates
    activity_patterns = [
        r"my activity level is (?:now |currently )?(\w+)",
        r"i am (?:now )?(\w+)ly active",
        r"update my activity level to (\w+)",
    ]
    
    for pattern in activity_patterns:
        match = re.search(pattern, message.lower())
        if match:
            activity = match.group(1).capitalize()
            if activity in ACTIVITY_LEVELS:
                updates["activity_level"] = activity
                break
    
    # Check for fitness goal updates
    if "weight loss" in message.lower() or "lose weight" in message.lower() or "losing weight" in message.lower():
        updates["fitness_goal"] = "Weight Loss"
    elif "muscle gain" in message.lower() or "build muscle" in message.lower() or "gaining muscle" in message.lower():
        updates["fitness_goal"] = "Muscle Gain"
    elif "endurance" in message.lower() or "stamina" in message.lower() or "cardiovascular" in message.lower():
        updates["fitness_goal"] = "Endurance"
    
    # Check for dietary preference updates
    if "vegan" in message.lower() or "plant-based" in message.lower():
        updates["dietary_preference"] = "Vegan"
    elif "vegetarian" in message.lower():
        updates["dietary_preference"] = "Vegetarian"
    elif "non-vegetarian" in message.lower() or "meat" in message.lower() or "omnivore" in message.lower():
        updates["dietary_preference"] = "Non-vegetarian"
    
    return updates

def update_user_profile(user: User, field: str, new_value: Any) -> User:
    """
    Update a specific field in the user's profile data.
    
    Args:
        user: User object to update
        field: Field name to update
        new_value: New value for the field
        
    Returns:
        Updated User object
    """
    # Check if the field exists in the profile data
    if hasattr(user.profile_data, field):
        # Update the field
        setattr(user.profile_data, field, new_value)
        
        # BMI is automatically recalculated by the model's computed_field properties
        # No need to manually recalculate it
        
        # Save the updated user
        save_user(user)
        
        return user
    else:
        raise ValueError(f"Field '{field}' not found in user profile data")

def generate_workout_diet_plans(user: User) -> Tuple[str, str]:
    """
    Generate personalized workout and diet plans based on user profile.
    Import this function from fitness_agent to avoid duplication.
    """
    # Import here to avoid circular imports
    from agent.fitness_agent import generate_workout_diet_plans as gen_plans
    return gen_plans(user)

def update_user_plans(user: User) -> Tuple[str, str]:
    """
    Regenerate workout and diet plans based on updated user profile.
    
    Args:
        user: User object with updated profile
        
    Returns:
        Tuple of (workout_plan, diet_plan) as strings
    """
    # Generate new plans
    workout_plan, diet_plan = generate_workout_diet_plans(user)
    
    # Update user with new plans
    user.workout_plan = WorkoutPlan(plan_text=workout_plan)
    user.diet_plan = DietPlan(plan_text=diet_plan)
    
    # Save the updated user
    save_user(user)
    
    return workout_plan, diet_plan

def check_api_key(console=None) -> bool:
    """
    Check if the API key is present, ask for it if not.
    
    Args:
        console: Optional Rich console for prettier output
        
    Returns:
        True if API key is valid, False otherwise
    """
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        if console:
            console.print("\n[warning]No Google Gemini API key found.[/warning]")
            console.print("[info]To use FitAI, you need a Google Gemini API key.[/info]")
            console.print("[info]You can get one from https://aistudio.google.com/app/apikey[/info]")
        else:
            print("\nNo Google Gemini API key found.")
            print("To use FitAI, you need a Google Gemini API key.")
            print("You can get one from https://aistudio.google.com/app/apikey")
        
        # Give the user up to 3 attempts to enter a valid key
        for attempt in range(3):
            if attempt > 0:
                if console:
                    console.print(f"\n[warning]Attempt {attempt+1}/3 to enter a valid API key.[/warning]")
                else:
                    print(f"\nAttempt {attempt+1}/3 to enter a valid API key.")
                
            if console:
                api_key = console.input("\n[info]Please enter your Google Gemini API key:[/info] ").strip()
            else:
                api_key = input("\nPlease enter your Google Gemini API key: ").strip()
                
            if not api_key:
                if attempt < 2:
                    if console:
                        console.print("[error]API key cannot be empty. Please try again.[/error]")
                    else:
                        print("API key cannot be empty. Please try again.")
                    continue
                else:
                    if console:
                        console.print("[error]API key cannot be empty. You can restart the application later with a valid key.[/error]")
                    else:
                        print("API key cannot be empty. You can restart the application later with a valid key.")
                    return False
            
            # Save API key to .env file
            try:
                # Check if .env file exists, create if not
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
                if not os.path.exists(env_path):
                    with open(env_path, 'w') as f:
                        f.write(f"GEMINI_API_KEY={api_key}\n")
                else:
                    # Update existing .env file
                    set_key(env_path, "GEMINI_API_KEY", api_key)
                
                # Reload environment variables
                load_dotenv(override=True)
                
                # Try to validate the API key by making a simple API call
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
                    response = model.generate_content("Hello")
                    
                    if console:
                        console.print("[success]✅ API key validated and saved successfully![/success]")
                    else:
                        print("✅ API key validated and saved successfully!")
                    return True
                except Exception as e:
                    if attempt < 2:
                        if console:
                            console.print(f"[error]❌ Invalid API key: {str(e)}[/error]")
                        else:
                            print(f"❌ Invalid API key: {str(e)}")
                        continue
                    else:
                        if console:
                            console.print(f"[error]❌ Invalid API key: {str(e)}[/error]")
                            console.print("[warning]You can restart the application later with a valid key.[/warning]")
                        else:
                            print(f"❌ Invalid API key: {str(e)}")
                            print("You can restart the application later with a valid key.")
                        return False
                    
            except Exception as e:
                if attempt < 2:
                    if console:
                        console.print(f"[error]❌ Failed to save API key: {str(e)}[/error]")
                    else:
                        print(f"❌ Failed to save API key: {str(e)}")
                    continue
                else:
                    if console:
                        console.print(f"[error]❌ Failed to save API key: {str(e)}[/error]")
                        console.print("[warning]You can manually add your API key to the .env file.[/warning]")
                    else:
                        print(f"❌ Failed to save API key: {str(e)}")
                        print("You can manually add your API key to the .env file.")
                    return False
    
    return True

def handle_profile_updates(user: User, message: str, console=None) -> Tuple[User, bool]:
    """
    Handle potential profile updates in a user message.
    
    Args:
        user: Current user object
        message: User message to parse
        console: Optional Rich console for output
        
    Returns:
        Tuple of (updated_user, plans_updated)
    """
    updates = parse_profile_update(message)
    plans_updated = False
    
    if updates:
        # Show what's being updated
        if console:
            console.print("\n[info]Detected profile updates:[/info]")
            for field, value in updates.items():
                console.print(f"[info]- {field}: {value}[/info]")
        else:
            print("\nDetected profile updates:")
            for field, value in updates.items():
                print(f"- {field}: {value}")
        
        # Apply updates
        for field, value in updates.items():
            try:
                user = update_user_profile(user, field, value)
            except ValueError as e:
                if console:
                    console.print(f"[error]Error updating {field}: {str(e)}[/error]")
                else:
                    print(f"Error updating {field}: {str(e)}")
        
        if console:
            console.print("[success]✅ Your profile has been updated![/success]")
            
            # Ask if user wants to update plans
            update_plans = console.input("\n[info]Would you like to update your workout and diet plans based on your new information? (y/n)[/info] ").lower()
            
            if update_plans.startswith('y'):
                workout_plan, diet_plan = update_user_plans(user)
                console.print("[success]✅ Your workout and diet plans have been updated![/success]")
                plans_updated = True
        else:
            print("✅ Your profile has been updated!")
            
            # Ask if user wants to update plans
            update_plans = input("\nWould you like to update your workout and diet plans based on your new information? (y/n) ").lower()
            
            if update_plans.startswith('y'):
                workout_plan, diet_plan = update_user_plans(user)
                print("✅ Your workout and diet plans have been updated!")
                plans_updated = True
    
    return user, plans_updated 