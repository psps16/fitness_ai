# models/models.py

from pydantic import BaseModel, Field, computed_field
from typing import Literal, Annotated, List, Dict, Optional
from datetime import datetime

# Define Literal types for our Multiple-Choice Questions (MCQs)
# This provides strong typing and automatic validation.
ActivityLevel = Literal["Sedentary", "Moderate", "Active"]
FitnessGoal = Literal["Weight Loss", "Muscle Gain", "Endurance"]
BMICategory = Literal["Underweight", "Normal", "Overweight", "Obese"]
DietaryPreference = Literal["Vegan", "Vegetarian", "Non-vegetarian"]


class UserProfileData(BaseModel):
    """
    Stores the raw user information and dynamically computes derived features.
    The core fields are now required, ensuring a complete profile.
    """
    # --- Required User Inputs (Free-form and MCQs) ---
    name: Annotated[str, Field(description="The user's first name.", examples=["Luffy"])]
    age: Annotated[int, Field(description="The user's age in years.", examples=[21])]
    height_cm: Annotated[float, Field(description="The user's height in centimeters.", examples=[175])]
    weight_kg: Annotated[float, Field(description="The user's weight in kilograms.", examples=[75])]
    activity_level: Annotated[ActivityLevel, Field(description="The user's selected activity level.")]
    fitness_goal: Annotated[FitnessGoal, Field(description="The user's selected primary fitness goal.")]
    dietary_preference: Annotated[DietaryPreference, Field(description="The user's dietary preference.")]
    blood_group: Optional[str] = Field(None, description="The user's blood group (optional).")

    # --- Automatically Computed Features ---
    @computed_field
    @property
    def bmi(self) -> float:
        """
        Calculates the Body Mass Index (BMI). 
        Since height and weight are now required fields, this will always return a float.
        """
        # No need to check for None, as Pydantic enforces the presence of these fields.
        height_in_meters = self.height_cm / 100
        calculated_bmi = self.weight_kg / (height_in_meters ** 2)
        return round(calculated_bmi, 2)

    @computed_field
    @property
    def bmi_category(self) -> BMICategory:
        """
        Determines the BMI category. 
        This is also guaranteed to return a valid category string.
        """
        # We can directly use self.bmi without checking for None.
        if self.bmi < 18.5:
            return "Underweight"
        elif 18.5 <= self.bmi < 25:
            return "Normal"
        elif 25 <= self.bmi < 30:
            return "Overweight"
        else:  # self.bmi >= 30
            return "Obese"


class Message(BaseModel):
    """
    Represents a single message in the conversation history.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    user_message: str
    bot_reply: str


class Plan(BaseModel):
    """
    Base class for workout and diet plans
    """
    last_updated: datetime = Field(default_factory=datetime.now)
    plan_text: str


class WorkoutPlan(Plan):
    """
    Represents the user's workout plan
    """
    pass


class DietPlan(Plan):
    """
    Represents the user's diet plan
    """
    pass


class User(BaseModel):
    """
    The main user model that ties everything together.
    """
    user_id: str = Field(description="A unique identifier for the user (e.g., their username).")
    profile_data: UserProfileData
    workout_plan: Optional[WorkoutPlan] = None
    diet_plan: Optional[DietPlan] = None
    conversation_history: List[Message] = Field(default_factory=list)
    
    def add_message(self, user_message: str, bot_reply: str):
        """
        Adds a new message pair to the conversation history
        """
        self.conversation_history.append(
            Message(user_message=user_message, bot_reply=bot_reply)
        )