#!/usr/bin/env python3

import os
import getpass
from typing import Optional, Dict, Any, Tuple
import time
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich.text import Text
from rich.theme import Theme
from dotenv import load_dotenv, set_key

from models.database import (
    init_db, 
    get_user, 
    save_user, 
    get_all_user_ids,
    save_message,
    hash_password,
    register_user,
    authenticate_user
)
from models.models import User
from agent.fitness_agent import (
    onboard_new_user, 
    display_plans, 
    setup_llm,
    generate_workout_diet_plans,
    WorkoutPlan,
    DietPlan
)
from agent.tools import (
    parse_profile_update,
    update_user_profile,
    update_user_plans,
    handle_profile_updates,
    check_api_key,
    ACTIVITY_LEVELS,
    FITNESS_GOALS,
    DIETARY_PREFERENCES
)

# Set up rich console with custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold blue",
    "user": "bold white",
    "assistant": "green",
    "header": "bold cyan",
    "highlight": "bold magenta",
})

console = Console(theme=custom_theme)

def simple_login() -> Optional[User]:
    """Handle user login or registration with a simplified interface."""
    console.print(Panel.fit(
        "[header]FITAI - LOGIN / REGISTRATION[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    username = console.input("\n[info]Username (new or existing):[/info] ").strip()
    if not username:
        console.print("[error]Username cannot be empty.[/error]")
        return None
        
    password = getpass.getpass("Password: ")
    if not password:
        console.print("[error]Password cannot be empty.[/error]")
        return None
    
    # Show loading animation
    with console.status("[info]Authenticating...[/info]", spinner="dots"):
        time.sleep(0.5)  # Brief pause for effect
        # Try to authenticate as existing user
        user_id = authenticate_user(username, password)
    
    if user_id:
        # Existing user
        with console.status("[info]Loading your profile...[/info]", spinner="dots"):
            time.sleep(0.5)  # Brief pause for effect
            user = get_user(user_id)
            
        if user:
            console.print(f"\n[success]✅ Welcome back, {user.profile_data.name}![/success]")
            return user
        else:
            console.print("\n[error]❌ User profile not found. Please contact support.[/error]")
            return None
    else:
        # New user
        console.print(f"\n[highlight]Welcome {username}! Let's create your profile.[/highlight]")
        
        # Create a new user profile
        user = onboard_new_user(console)
        
        # Register the user
        with console.status("[info]Creating your account...[/info]", spinner="dots"):
            time.sleep(0.5)  # Brief pause for effect
            registration_success = register_user(username, password, user)
            
        if registration_success:
            console.print("\n[success]✅ Registration successful![/success]")
            
            # Generate initial workout and diet plans
            console.print("\n[info]Processing your information and generating personalized plans...[/info]")
            
            with console.status("[info]Creating personalized fitness plans...[/info]", spinner="dots"):
                workout_plan, diet_plan = generate_workout_diet_plans(user)
            
            # Update user with plans
            user.workout_plan = WorkoutPlan(plan_text=workout_plan)
            user.diet_plan = DietPlan(plan_text=diet_plan)
            
            # Save the user profile
            save_user(user)
            
            console.print("\n[success]✅ Your profile and initial plans have been created![/success]")
            return user
        else:
            console.print("\n[error]❌ Registration failed. Please try again.[/error]")
            return None

def display_chat_history(user: User, limit: int = 10, console: Console = console):
    """Display the most recent chat history for the user with markdown rendering."""
    if not user.conversation_history:
        console.print("\n[warning]No chat history found.[/warning]")
        return
    
    console.print(Panel.fit(
        "[header]RECENT CHAT HISTORY[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    # Get the most recent messages, limited by the limit parameter
    recent_messages = user.conversation_history[-limit:]
    
    for i, message in enumerate(recent_messages, 1):
        timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # User message in a panel
        console.print(Panel(
            Text(message.user_message, style="user"),
            title=f"You ({timestamp})",
            title_align="left",
            border_style="white",
            box=ROUNDED
        ))
        
        # AI response with markdown rendering
        console.print(Panel(
            Markdown(message.bot_reply),
            title="FitAI",
            title_align="left",
            border_style="green",
            box=ROUNDED
        ))
        
        if i < len(recent_messages):
            console.print()  # Add space between message pairs

def display_markdown_plans(user: User, console: Console = console):
    """Display the user's current workout and diet plans with markdown rendering."""
    console.print(Panel.fit(
        f"[header]FITNESS PLANS FOR {user.profile_data.name.upper()}[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    if user.workout_plan:
        console.print(Panel(
            Markdown(user.workout_plan.plan_text),
            title="[highlight]YOUR WORKOUT PLAN[/highlight]",
            title_align="center",
            border_style="magenta",
            box=ROUNDED
        ))
    else:
        console.print("\n[warning]No workout plan generated yet.[/warning]")
    
    if user.diet_plan:
        console.print(Panel(
            Markdown(user.diet_plan.plan_text),
            title="[highlight]YOUR DIET PLAN[/highlight]",
            title_align="center",
            border_style="magenta",
            box=ROUNDED
        ))
    else:
        console.print("\n[warning]No diet plan generated yet.[/warning]")

def display_commands():
    """Display available commands in a nicely formatted table."""
    table = Table(title="Available Commands", box=ROUNDED, border_style="blue")
    
    table.add_column("Command", style="command")
    table.add_column("Description", style="info")
    
    table.add_row("/chat", "Start or resume chatting with the AI assistant")
    table.add_row("/workout", "Display your current workout plan")
    table.add_row("/diet", "Display your current diet plan")
    table.add_row("/plans", "Display both your workout and diet plans")
    table.add_row("/profile", "View your current profile information")
    table.add_row("/update", "Update your profile information")
    table.add_row("/load_from_memory", "Display your recent chat history")
    table.add_row("/help", "Show this help message")
    table.add_row("--exit", "End the conversation")
    
    console.print(table)

def display_user_profile(user: User, console: Console = console):
    """Display the user's current profile information."""
    console.print(Panel.fit(
        f"[header]PROFILE INFORMATION FOR {user.profile_data.name.upper()}[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    profile_table = Table(box=ROUNDED, border_style="blue")
    profile_table.add_column("Attribute", style="info")
    profile_table.add_column("Value", style="highlight")
    
    profile_table.add_row("Name", user.profile_data.name)
    profile_table.add_row("Age", str(user.profile_data.age))
    profile_table.add_row("Height", f"{user.profile_data.height_cm} cm")
    profile_table.add_row("Weight", f"{user.profile_data.weight_kg} kg")
    profile_table.add_row("BMI", f"{user.profile_data.bmi} ({user.profile_data.bmi_category})")
    profile_table.add_row("Activity Level", user.profile_data.activity_level)
    profile_table.add_row("Fitness Goal", user.profile_data.fitness_goal)
    profile_table.add_row("Dietary Preference", user.profile_data.dietary_preference)
    
    if user.profile_data.blood_group:
        profile_table.add_row("Blood Group", user.profile_data.blood_group)
    
    console.print(profile_table)

def update_user_profile_interactive(user: User, console: Console = console) -> User:
    """Interactive function to update user profile."""
    console.print(Panel.fit(
        "[header]UPDATE YOUR PROFILE[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    console.print("[info]Enter new values or press Enter to keep current values.[/info]")
    
    # Weight update
    while True:
        try:
            current = user.profile_data.weight_kg
            weight_input = console.input(f"\n[info]Weight in kg (current: {current}):[/info] ").strip()
            
            if weight_input == "":
                break
                
            weight = float(weight_input)
            if 30 <= weight <= 300:
                user = update_user_profile(user, "weight_kg", weight)
                break
            else:
                console.print("[warning]Please enter a valid weight between 30 and 300 kg.[/warning]")
        except ValueError:
            console.print("[error]Please enter a valid number.[/error]")
    
    # Height update
    while True:
        try:
            current = user.profile_data.height_cm
            height_input = console.input(f"\n[info]Height in cm (current: {current}):[/info] ").strip()
            
            if height_input == "":
                break
                
            height = float(height_input)
            if 100 <= height <= 250:
                user = update_user_profile(user, "height_cm", height)
                break
            else:
                console.print("[warning]Please enter a valid height between 100 and 250 cm.[/warning]")
        except ValueError:
            console.print("[error]Please enter a valid number.[/error]")
    
    # Activity level update
    console.print("\n[info]Activity level:[/info]")
    for i, level in enumerate(ACTIVITY_LEVELS, 1):
        console.print(f"  {i}. [highlight]{level}[/highlight]")
    
    current_idx = ACTIVITY_LEVELS.index(user.profile_data.activity_level) + 1
    console.print(f"[info]Current: {user.profile_data.activity_level} ({current_idx})[/info]")
    
    activity_input = console.input("\n[info]Enter the number of your choice (or press Enter to keep current):[/info] ").strip()
    
    if activity_input:
        try:
            activity_choice = int(activity_input)
            if 1 <= activity_choice <= len(ACTIVITY_LEVELS):
                activity_level = ACTIVITY_LEVELS[activity_choice - 1]
                user = update_user_profile(user, "activity_level", activity_level)
        except ValueError:
            console.print("[error]Invalid choice. Keeping current activity level.[/error]")
    
    # Fitness goal update
    console.print("\n[info]Fitness goal:[/info]")
    for i, goal in enumerate(FITNESS_GOALS, 1):
        console.print(f"  {i}. [highlight]{goal}[/highlight]")
    
    current_idx = FITNESS_GOALS.index(user.profile_data.fitness_goal) + 1
    console.print(f"[info]Current: {user.profile_data.fitness_goal} ({current_idx})[/info]")
    
    goal_input = console.input("\n[info]Enter the number of your choice (or press Enter to keep current):[/info] ").strip()
    
    if goal_input:
        try:
            goal_choice = int(goal_input)
            if 1 <= goal_choice <= len(FITNESS_GOALS):
                fitness_goal = FITNESS_GOALS[goal_choice - 1]
                user = update_user_profile(user, "fitness_goal", fitness_goal)
        except ValueError:
            console.print("[error]Invalid choice. Keeping current fitness goal.[/error]")
    
    # Dietary preference update
    console.print("\n[info]Dietary preference:[/info]")
    for i, pref in enumerate(DIETARY_PREFERENCES, 1):
        console.print(f"  {i}. [highlight]{pref}[/highlight]")
    
    current_idx = DIETARY_PREFERENCES.index(user.profile_data.dietary_preference) + 1
    console.print(f"[info]Current: {user.profile_data.dietary_preference} ({current_idx})[/info]")
    
    pref_input = console.input("\n[info]Enter the number of your choice (or press Enter to keep current):[/info] ").strip()
    
    if pref_input:
        try:
            pref_choice = int(pref_input)
            if 1 <= pref_choice <= len(DIETARY_PREFERENCES):
                dietary_preference = DIETARY_PREFERENCES[pref_choice - 1]
                user = update_user_profile(user, "dietary_preference", dietary_preference)
        except ValueError:
            console.print("[error]Invalid choice. Keeping current dietary preference.[/error]")
    
    console.print("\n[success]✅ Your profile has been updated![/success]")
    
    # Ask if user wants to update plans
    update_plans = console.input("\n[info]Would you like to update your workout and diet plans based on your new information? (y/n)[/info] ").lower()
    
    if update_plans.startswith('y'):
        with console.status("[info]Generating new personalized plans...[/info]", spinner="dots"):
            workout_plan, diet_plan = update_user_plans(user)
        
        console.print("[success]✅ Your workout and diet plans have been updated![/success]")
    
    return user

def chat_loop(user: User):
    """Start the chat loop with the fitness assistant."""
    # For new users, display the plans automatically
    # For existing users, just show a welcome message
    if not user.conversation_history:
        # This is likely a new user who just created their plans
        display_markdown_plans(user)
    else:
        # This is an existing user, just show a welcome message
        console.print(Panel(
            f"[success]Welcome back, {user.profile_data.name}![/success]\n\n"
            "Your fitness data has been loaded.\n"
            "Use [command]/workout[/command] to see your workout plan or [command]/diet[/command] to see your diet plan.",
            border_style="green",
            box=ROUNDED
        ))
    
    # Set up the LLM for conversation
    with console.status("[info]Setting up your fitness assistant...[/info]", spinner="dots"):
        conversation = setup_llm(user)
    
    # Start conversation loop
    console.print(Panel.fit(
        "[header]CHAT WITH YOUR FITNESS ASSISTANT[/header]", 
        border_style="cyan", 
        box=ROUNDED
    ))
    
    console.print("\nType [command]--exit[/command] to end the conversation.")
    console.print("Type [command]/help[/command] to see available commands.")
    
    # Flag to track if we're in chat mode
    in_chat_mode = False
    
    # Track if any chat messages were exchanged in this session
    chat_session_active = False
    
    try:
        while True:
            # Get user input
            user_message = console.input("\n[user]You:[/user] ")
            
            # Check for commands
            if user_message.lower() == "--exit":
                console.print("\n[success]Thank you for using FitAI! Goodbye! 👋[/success]")
                break
                
            elif user_message.lower() == "/help":
                display_commands()
                continue
                
            elif user_message.lower() == "/chat":
                in_chat_mode = True
                console.print("\n[success]🤖 Chat mode activated. You can now chat freely with your fitness assistant.[/success]")
                console.print("[info]Use any command starting with '/' to exit chat mode.[/info]")
                continue
                
            elif user_message.lower() == "/workout":
                in_chat_mode = False
                if user.workout_plan:
                    console.print(Panel(
                        Markdown(user.workout_plan.plan_text),
                        title="[highlight]YOUR WORKOUT PLAN[/highlight]",
                        title_align="center",
                        border_style="magenta",
                        box=ROUNDED
                    ))
                else:
                    console.print("\n[warning]No workout plan generated yet.[/warning]")
                continue
                
            elif user_message.lower() == "/diet":
                in_chat_mode = False
                if user.diet_plan:
                    console.print(Panel(
                        Markdown(user.diet_plan.plan_text),
                        title="[highlight]YOUR DIET PLAN[/highlight]",
                        title_align="center",
                        border_style="magenta",
                        box=ROUNDED
                    ))
                else:
                    console.print("\n[warning]No diet plan generated yet.[/warning]")
                continue
                
            elif user_message.lower() == "/plans":
                in_chat_mode = False
                display_markdown_plans(user)
                continue
                
            elif user_message.lower() == "/profile":
                in_chat_mode = False
                display_user_profile(user)
                continue
                
            elif user_message.lower() == "/update":
                in_chat_mode = False
                user = update_user_profile_interactive(user)
                continue
                
            elif user_message.lower() == "/load_from_memory":
                in_chat_mode = False
                # Ask how many messages to display
                try:
                    limit_str = console.input("\n[info]How many recent messages would you like to see? (default: 10):[/info] ").strip()
                    limit = int(limit_str) if limit_str else 10
                    display_chat_history(user, limit)
                except ValueError:
                    console.print("\n[error]❌ Please enter a valid number. Showing the default of 10 messages.[/error]")
                    display_chat_history(user, 10)
                continue
                
            # If message starts with /, but is not a recognized command
            elif user_message.startswith("/"):
                in_chat_mode = False
                console.print("\n[error]❌ Unknown command. Type '/help' to see available commands.[/error]")
                continue
            
            # Process the message with the LLM if in chat mode or if message doesn't start with /
            if in_chat_mode or not user_message.startswith("/"):
                # Check for profile updates in the message using the tools module
                user, plans_updated = handle_profile_updates(user, user_message, console)
                
                # Display user message in a panel
                console.print(Panel(
                    Text(user_message, style="user"),
                    title="You",
                    title_align="left",
                    border_style="white",
                    box=ROUNDED
                ))
                
                # If plans were updated, we need to refresh the conversation with updated user info
                if plans_updated:
                    with console.status("[info]Updating your fitness assistant with new information...[/info]", spinner="dots"):
                        conversation = setup_llm(user)
                
                # Show thinking animation
                with console.status("[info]FitAI is thinking...[/info]", spinner="dots"):
                    response = conversation.predict(input=user_message)
                
                # Display AI response with markdown rendering
                console.print(Panel(
                    Markdown(response),
                    title="FitAI",
                    title_align="left",
                    border_style="green",
                    box=ROUNDED
                ))
                
                # Save the message pair to the database
                user.add_message(user_message=user_message, bot_reply=response)
                save_message(user.user_id, user_message, response)
                
                # Mark that we had chat activity in this session
                chat_session_active = True
            else:
                console.print("\n[error]❌ Unknown command. Type '/help' to see available commands.[/error]")
    
    finally:
        # If there was any chat activity, ensure it's saved to the database
        if chat_session_active:
            with console.status("[info]Saving chat history to database...[/info]", spinner="dots"):
                save_user(user)
                time.sleep(0.5)  # Brief pause for effect
            console.print("[success]Chat history saved![/success]")

def main():
    """Main function to run the CLI app."""
    # Initialize the database
    with console.status("[info]Initializing database...[/info]", spinner="dots"):
        init_db()
        time.sleep(0.5)  # Brief pause for effect
    
    # Welcome message
    console.print(Panel.fit(
        "[header]WELCOME TO FITAI - YOUR PERSONALIZED FITNESS ASSISTANT![/header]", 
        subtitle="[info]Powered by Gemini 2.5[/info]",
        border_style="cyan", 
        box=ROUNDED
    ))
    
    # Handle login or registration with simplified process
    user = simple_login()
    
    if user:
        # For all users (new and existing), check if API key is available
        # For new users, this is especially important
        if not check_api_key(console):
            console.print("\n[error]❌ API key is required to use FitAI. Please restart the application with a valid key.[/error]")
            return
            
        # Start the chat loop
        chat_loop(user)

if __name__ == "__main__":
    main() 