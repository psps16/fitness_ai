# FitAI: AI-Powered Fitness Assistant

FitAI is an intelligent, personalized fitness assistant that helps users create and manage their workout and diet plans based on their individual goals and preferences.

## Features

- User authentication system with secure password hashing
- Personalized workout and diet plan generation based on user profile
- Natural language conversation with AI-powered fitness assistant using Gemini
- User profile management with MCQ-based onboarding
- Persistent memory of user data and conversation history
- Feature engineering (e.g., BMI calculation)
- Dynamic plan updates based on user feedback
- Special commands for accessing workout and diet plans
- Chat history retrieval from database
- Beautiful CLI interface with markdown rendering

## Setup

1. Clone this repository:
```bash
git clone 
cd fitness_ai
```

2. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
# Or using uv
uv sync
```

4. Create a `.env` file in the project root directory and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Running the Application

Run the main script:
```bash
python main.py
```

- Enter your username (new or existing) and password
- If you're a new user, you'll be guided through the onboarding process
- If you're a returning user, your existing profile and plans will be loaded
- Use the `/chat` command to start chatting with the AI assistant

## Commands

While in the application, you can use the following commands:
- `/chat`: Start or resume chatting with the AI assistant
- `/workout`: Display your current workout plan
- `/diet`: Display your current diet plan
- `/plans`: Display both your workout and diet plans
- `/load_from_memory`: Display your recent chat history
- `/help`: Show available commands
- `--exit`: End the conversation

## Chat Mode

When you enter `/chat` command, you'll enter chat mode where you can freely converse with the AI assistant. The assistant will:
- Remember your profile details (age, weight, height, BMI, etc.)
- Know your current workout and diet plans
- Ask follow-up questions when needed
- Provide personalized fitness advice

To exit chat mode, simply use any command starting with `/`.

## Chat History

The application automatically saves all conversations to the database. You can view your chat history at any time using the `/load_from_memory` command, which allows you to:
- Retrieve recent conversations
- Specify how many messages to display
- See timestamps for each message exchange

## Beautiful CLI Interface

FitAI features a modern, colorful CLI interface with:
- Fully rendered markdown in AI responses
- Syntax highlighting for code snippets
- Formatted tables and panels
- Loading animations
- Color-coded messages and commands
- Structured layout for improved readability

## Project Structure

- `main.py`: Main CLI application with user authentication
- `fitness_agent.py`: Core functionality for the fitness assistant
- `models/`: Directory containing data models and database functionality
  - `models.py`: Pydantic models for user data
  - `database.py`: Database operations for persistence
- `fitai_database.db`: SQLite database file (created on first run)
- `.env`: Environment variables (Gemini API key)

## Technical Details

- **AI Model**: Google's Gemini 2.5 Flash Lite Preview (gemini-2.5-flash-lite-preview-06-17)
- **Database**: SQLite for persistent storage
- **Authentication**: SHA-256 password hashing
- **Data Validation**: Pydantic models
- **State Management**: Per-user context loading for personalized conversations
- **UI Framework**: Rich library for terminal formatting and markdown rendering

## Future Enhancements

- **FastAPI Integration**: Implement a full FastAPI backend to expose the fitness assistant functionality as a RESTful API service, enabling web and mobile client development.

- **Structured Plan Output**: Enforce proper Pydantic models for workout and diet plans to store data in a structured format, enabling better analysis, visualization, and programmatic manipulation of fitness plans.

- **Advanced Authentication**: Integrate proper user authentication with JWT tokens, OAuth providers, and role-based access control for a more secure and scalable user management system.

- **Enhanced User Profiling**: Gather more comprehensive information beyond basic metrics (weight, height, age) such as:
  - Previous fitness experience
  - Specific fitness goals (e.g., marathon training, powerlifting)
  - Medical conditions or limitations
  - Available equipment
  - Time constraints
  - Sleep patterns and recovery metrics
  - Nutritional preferences and restrictions
  
This would allow for much more personalized and effective workout and diet plans tailored to each user's unique circumstances.
