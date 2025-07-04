#!/usr/bin/env python3

import os
import uuid
from typing import Tuple
from dotenv import load_dotenv

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Import Rich components for console output
from rich.panel import Panel
from rich.box import ROUNDED
from rich.markdown import Markdown
from models.models import User, UserProfileData
# Constants for MCQ options
ACTIVITY_LEVELS = ["Sedentary", "Moderate", "Active"]
FITNESS_GOALS = ["Weight Loss", "Muscle Gain", "Endurance"]
DIETARY_PREFERENCES = ["Vegan", "Vegetarian", "Non-vegetarian"]

# Load API key from environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# We'll check for API key when needed, not at startup
# This allows new users to add their key during registration
if GEMINI_API_KEY:
    # Configure the Gemini API if key is available
    genai.configure(api_key=GEMINI_API_KEY)

def setup_llm(user: User):
    """
    Set up the LLM with user context and conversation memory using the latest LangChain API.
    """
    # Check if API key is available now (might have been added during registration)
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        load_dotenv()  # Reload environment variables
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set. Please create a .env file with your API key.")
        genai.configure(api_key=GEMINI_API_KEY)
    
    # Create a system prompt that includes the user profile and feature engineering
    system_prompt = f"""
    You are FitAI, an intelligent fitness assistant. You are helping a user named {user.profile_data.name}.
    
    USER PROFILE:
    - Age: {user.profile_data.age}
    - Height: {user.profile_data.height_cm} cm
    - Weight: {user.profile_data.weight_kg} kg
    - BMI: {user.profile_data.bmi} ({user.profile_data.bmi_category})
    - Activity Level: {user.profile_data.activity_level}
    - Fitness Goal: {user.profile_data.fitness_goal}
    - Dietary Preference: {user.profile_data.dietary_preference}
    """
    
    if user.workout_plan:
        system_prompt += f"\n\nCURRENT WORKOUT PLAN:\n{user.workout_plan.plan_text}\n"
    
    if user.diet_plan:
        system_prompt += f"\n\nCURRENT DIET PLAN:\n{user.diet_plan.plan_text}\n"
    
    system_prompt += """
    INSTRUCTIONS:
    1. Keep responses conversational, friendly, and encouraging.
    2. When a user asks about their workout or diet plan, provide the current plan from their profile.
    3. If the user wants to update any information (like weight, goals, etc.), ask follow-up questions to gather all the necessary information.
    4. When a user updates their profile, adjust workout and diet recommendations accordingly.
    5. If you notice missing information needed to provide good advice, ask clarifying questions.
    6. You can suggest modifications to plans based on new information from the user.
    7. Always be supportive and focus on healthy, sustainable fitness advice.
    """

    # Create the chat model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite-preview-06-17",
        temperature=0.7,
        google_api_key=GEMINI_API_KEY,
    )
    
    # Initialize conversation history
    chat_history = []
    
    # Add conversation history if it exists
    if user.conversation_history:
        # Only add the last 10 interactions to avoid token limits
        recent_history = user.conversation_history[-10:]
        for message in recent_history:
            chat_history.append(HumanMessage(content=message.user_message))
            chat_history.append(AIMessage(content=message.bot_reply))
    
    # Create a prompt template with system message and history
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # Create a chain using the new LangChain API
    chain = (
        {"input": RunnablePassthrough(), "chat_history": lambda _: chat_history}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # Create a wrapper class to maintain compatibility with the existing code
    class ConversationWrapper:
        def __init__(self, chain, chat_history):
            self.chain = chain
            self.chat_history = chat_history
        
        def predict(self, input):
            response = self.chain.invoke(input)
            # Update chat history
            self.chat_history.append(HumanMessage(content=input))
            self.chat_history.append(AIMessage(content=response))
            return response
    
    return ConversationWrapper(chain, chat_history)


def generate_workout_diet_plans(user: User) -> Tuple[str, str]:
    """
    Generate personalized workout and diet plans based on user profile.
    """
    # Check if API key is available now (might have been added during registration)
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        load_dotenv()  # Reload environment variables
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set. Please create a .env file with your API key.")
        genai.configure(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Based on the following user profile, generate both a personalized workout plan and diet plan.
    Make sure the plans are detailed, realistic, and tailored specifically to this individual.
    
    USER PROFILE:
    - Name: {user.profile_data.name}
    - Age: {user.profile_data.age}
    - Height: {user.profile_data.height_cm} cm
    - Weight: {user.profile_data.weight_kg} kg
    - BMI: {user.profile_data.bmi} ({user.profile_data.bmi_category})
    - Activity Level: {user.profile_data.activity_level}
    - Fitness Goal: {user.profile_data.fitness_goal}
    - Dietary Preference: {user.profile_data.dietary_preference}
    
    Format your response in two clearly labeled sections:
    1. WORKOUT PLAN: A weekly workout schedule with specific exercises, sets, reps, and rest periods.
    2. DIET PLAN: A daily meal plan with specific food recommendations and macronutrient targets.
    
    Make sure both plans are aligned with the user's fitness goals and take into account their BMI category.
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
    response = model.generate_content(prompt)
    
    result = response.text
    
    # Split the response into workout and diet sections
    sections = result.split("WORKOUT PLAN:")
    if len(sections) > 1:
        workout_and_diet = sections[1]
        parts = workout_and_diet.split("DIET PLAN:")
        if len(parts) > 1:
            workout_plan = "WORKOUT PLAN:" + parts[0].strip()
            diet_plan = "DIET PLAN:" + parts[1].strip()
            return workout_plan, diet_plan
    
    # Fallback in case the format isn't as expected
    return result.split("\n\n")[0], result.split("\n\n")[1]


def onboard_new_user(console=None) -> User:
    """
    Collect initial information for a new user through MCQs.
    
    Args:
        console: Optional Rich console for prettier output. If None, uses standard print.
    """
    if console:
        console.print(Panel.fit(
            "[header]WELCOME TO FITAI - YOUR PERSONALIZED FITNESS ASSISTANT![/header]", 
            border_style="cyan", 
            box=ROUNDED
        ))
        console.print("\n[info]Let's collect some information to create your personalized fitness plan.[/info]")
    else:
        print("\n" + "=" * 50)
        print("🏋️ Welcome to FitAI - Your Personalized Fitness Assistant! 🥗")
        print("=" * 50)
        print("\nLet's collect some information to create your personalized fitness plan.")
    
    # Get name
    if console:
        name = console.input("\n[info]What's your name?[/info] ")
    else:
        name = input("\nWhat's your name? ")
    
    # Get age with validation
    while True:
        try:
            if console:
                age = int(console.input("\n[info]What's your age?[/info] "))
            else:
                age = int(input("\nWhat's your age? "))
                
            if 12 <= age <= 120:
                break
                
            if console:
                console.print("[warning]Please enter a valid age between 12 and 120.[/warning]")
            else:
                print("Please enter a valid age between 12 and 120.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Get height with validation
    while True:
        try:
            if console:
                height = float(console.input("\n[info]What's your height in centimeters?[/info] "))
            else:
                height = float(input("\nWhat's your height in centimeters? "))
                
            if 100 <= height <= 250:
                break
                
            if console:
                console.print("[warning]Please enter a valid height between 100 and 250 cm.[/warning]")
            else:
                print("Please enter a valid height between 100 and 250 cm.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Get weight with validation
    while True:
        try:
            if console:
                weight = float(console.input("\n[info]What's your weight in kilograms?[/info] "))
            else:
                weight = float(input("\nWhat's your weight in kilograms? "))
                
            if 30 <= weight <= 300:
                break
                
            if console:
                console.print("[warning]Please enter a valid weight between 30 and 300 kg.[/warning]")
            else:
                print("Please enter a valid weight between 30 and 300 kg.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Blood group (optional)
    if console:
        blood_group = console.input("\n[info]What's your blood group? (optional, press Enter to skip)[/info] ")
    else:
        blood_group = input("\nWhat's your blood group? (optional, press Enter to skip) ")
        
    if blood_group.strip() == "":
        blood_group = None
    
    # Activity level selection
    if console:
        console.print("\n[info]What's your activity level?[/info]")
        for i, level in enumerate(ACTIVITY_LEVELS, 1):
            console.print(f"  {i}. [highlight]{level}[/highlight]")
    else:
        print("\nWhat's your activity level?")
        for i, level in enumerate(ACTIVITY_LEVELS, 1):
            print(f"{i}. {level}")
    
    while True:
        try:
            if console:
                activity_choice = int(console.input("\n[info]Enter the number of your choice:[/info] "))
            else:
                activity_choice = int(input("\nEnter the number of your choice: "))
                
            if 1 <= activity_choice <= len(ACTIVITY_LEVELS):
                activity_level = ACTIVITY_LEVELS[activity_choice - 1]
                break
                
            if console:
                console.print(f"[warning]Please enter a number between 1 and {len(ACTIVITY_LEVELS)}.[/warning]")
            else:
                print(f"Please enter a number between 1 and {len(ACTIVITY_LEVELS)}.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Fitness goal selection
    if console:
        console.print("\n[info]What's your primary fitness goal?[/info]")
        for i, goal in enumerate(FITNESS_GOALS, 1):
            console.print(f"  {i}. [highlight]{goal}[/highlight]")
    else:
        print("\nWhat's your primary fitness goal?")
        for i, goal in enumerate(FITNESS_GOALS, 1):
            print(f"{i}. {goal}")
    
    while True:
        try:
            if console:
                goal_choice = int(console.input("\n[info]Enter the number of your choice:[/info] "))
            else:
                goal_choice = int(input("\nEnter the number of your choice: "))
                
            if 1 <= goal_choice <= len(FITNESS_GOALS):
                fitness_goal = FITNESS_GOALS[goal_choice - 1]
                break
                
            if console:
                console.print(f"[warning]Please enter a number between 1 and {len(FITNESS_GOALS)}.[/warning]")
            else:
                print(f"Please enter a number between 1 and {len(FITNESS_GOALS)}.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Dietary preference selection
    if console:
        console.print("\n[info]What's your dietary preference?[/info]")
        for i, pref in enumerate(DIETARY_PREFERENCES, 1):
            console.print(f"  {i}. [highlight]{pref}[/highlight]")
    else:
        print("\nWhat's your dietary preference?")
        for i, pref in enumerate(DIETARY_PREFERENCES, 1):
            print(f"{i}. {pref}")
    
    while True:
        try:
            if console:
                pref_choice = int(console.input("\n[info]Enter the number of your choice:[/info] "))
            else:
                pref_choice = int(input("\nEnter the number of your choice: "))
                
            if 1 <= pref_choice <= len(DIETARY_PREFERENCES):
                dietary_preference = DIETARY_PREFERENCES[pref_choice - 1]
                break
                
            if console:
                console.print(f"[warning]Please enter a number between 1 and {len(DIETARY_PREFERENCES)}.[/warning]")
            else:
                print(f"Please enter a number between 1 and {len(DIETARY_PREFERENCES)}.")
        except ValueError:
            if console:
                console.print("[error]Please enter a valid number.[/error]")
            else:
                print("Please enter a valid number.")
    
    # Create user profile
    profile_data = UserProfileData(
        name=name,
        age=age,
        height_cm=height,
        weight_kg=weight,
        activity_level=activity_level,
        fitness_goal=fitness_goal,
        dietary_preference=dietary_preference,
        blood_group=blood_group
    )
    
    # Generate a unique user ID
    user_id = str(uuid.uuid4())
    
    # Create and return the new user
    return User(user_id=user_id, profile_data=profile_data)


def display_plans(user: User, console=None):
    """
    Display the user's current workout and diet plans.
    
    Args:
        user: User object containing the plans
        console: Optional Rich console for prettier output. If None, uses standard print.
    """
    if console:
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
    else:
        # Standard print version
        print("\n" + "=" * 50)
        print(f"FITNESS PLANS FOR {user.profile_data.name.upper()}")
        print("=" * 50)
        
        if user.workout_plan:
            print("\n" + "✓" * 50)
            print(user.workout_plan.plan_text)
            print("✓" * 50)
        else:
            print("\nNo workout plan generated yet.")
        
        if user.diet_plan:
            print("\n" + "✓" * 50)
            print(user.diet_plan.plan_text)
            print("✓" * 50)
        else:
            print("\nNo diet plan generated yet.") 