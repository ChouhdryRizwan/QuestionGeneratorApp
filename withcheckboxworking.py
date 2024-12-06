import streamlit as st
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "selected_questions" not in st.session_state:
    st.session_state.selected_questions = []

if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []


# Function to handle login
def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.authenticated = True
            st.success("Logged in successfully!")
            st.rerun()  # Redirect to the main page after login
        else:
            st.error("Invalid username or password")


# Function to handle logout
def logout():
    st.session_state.authenticated = False
    st.session_state.generated_questions = []
    st.session_state.selected_questions = []
    st.success("Logged out successfully!")
    st.rerun()  # Redirect to the login page by rerunning the app


# Database setup
def init_db():
    conn = sqlite3.connect("questions_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS difficulty_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()


def insert_subject(subject):
    conn = sqlite3.connect("questions_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO topics (subject) VALUES (?)
    """, (subject,))
    conn.commit()
    conn.close()


def insert_level(level):
    conn = sqlite3.connect("questions_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO difficulty_levels (level) VALUES (?)
    """, (level,))
    conn.commit()
    conn.close()


def fetch_subjects():
    conn = sqlite3.connect("questions_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject FROM topics")
    subjects = [row[0] for row in cursor.fetchall()]
    conn.close()
    return subjects


def fetch_levels():
    conn = sqlite3.connect("questions_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT level FROM difficulty_levels")
    levels = [row[0] for row in cursor.fetchall()]
    conn.close()
    return levels


# Function to generate questions
def generate_mcq(subject, number, level):
    difficulty_mapping = {
        "Bronze": "basic",
        "Silver": "intermediate",
        "Gold": "advanced",
        "Platinum": "expert",
        "Diamond": "most difficult"
    }
    difficulty = difficulty_mapping.get(level, "basic")
    prompt = f"Generate {number} multiple choice questions for the subject '{subject}' at a {difficulty} level in this format:\n\n" \
             f"1. Question?\n" \
             f"a) Option 1\n" \
             f"b) Option 2\n" \
             f"c) Option 3\n" \
             f"d) Option 4\n\n" \
             f"Correct Answer: [Option]\n\n"
    response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
    return response.text.strip()


# Improved parsing function using regex
def parse_questions(questions_text):
    question_pattern = r'(\d+\..+?)\s*(a\).+?)\s*(b\).+?)\s*(c\).+?)\s*(d\).+?)\s*Correct Answer: \[([a-d])\]'
    questions = []
    matches = re.findall(question_pattern, questions_text, re.DOTALL)

    for match in matches:
        question_text, option_a, option_b, option_c, option_d, correct_answer = match
        questions.append({
            "question": question_text.strip(),
            "options": {
                "a": option_a.strip(),
                "b": option_b.strip(),
                "c": option_c.strip(),
                "d": option_d.strip()
            },
            "correct_answer": correct_answer.strip()
        })

    return questions


# Initialize database
init_db()

# Main App
if not st.session_state.authenticated:
    login()
else:
    # Logout button
    if st.button("Logout"):
        logout()

    # Main application
    st.title("Question's Generator")

    # Fetch existing data
    subjects = fetch_subjects()
    levels = fetch_levels()

    # Subject Input with Dynamic Dropdown and Save
    selected_subject = st.selectbox("Subject (select or add new):", subjects + ["Add new..."])
    if selected_subject == "Add new...":
        new_subject = st.text_input("Enter new subject:", key="new_subject")
        if new_subject:
            if st.button("Save Subject", key="save_subject"):
                insert_subject(new_subject)
                st.success(f"Subject '{new_subject}' added successfully!")
                st.rerun()

    # Difficulty Level Input with Dynamic Dropdown and Save
    selected_level = st.selectbox("Difficulty Level (select or add new):", levels + ["Add new..."])
    if selected_level == "Add new...":
        new_level = st.text_input("Enter new difficulty level:", key="new_level")
        if new_level:
            if st.button("Save Difficulty Level", key="save_level"):
                insert_level(new_level)
                st.success(f"Difficulty level '{new_level}' added successfully!")
                st.rerun()

    # Static Input for Number of Questions
    number_of_questions = st.number_input("Number of Questions:", min_value=1, max_value=100, value=10)

    # Generate Questions Button
    if st.button("Generate Questions"):
        if selected_subject and selected_level:
            questions_text = generate_mcq(selected_subject, number_of_questions, selected_level)
            if questions_text:
                st.session_state.generated_questions = parse_questions(questions_text)
            else:
                st.error("No questions generated. Please try again.")
        else:
            st.error("Please fill in both Subject and Difficulty Level.")

   # Display Generated Questions
    st.write("### Generated Questions:")
    for idx, question in enumerate(st.session_state.generated_questions):
        # Checkbox to select/unselect the question
        checkbox_key = f"gen_q_{idx}"
        if st.checkbox(f"{question['question']}", key=checkbox_key):
            if question not in st.session_state.selected_questions:
                st.session_state.selected_questions.append(question)
        else:
            if question in st.session_state.selected_questions:
                st.session_state.selected_questions.remove(question)

        # Display options for the generated question
        for opt_key, option in question["options"].items():
            st.text(f"{option}")
        st.text(f"Correct Answer: {question['correct_answer']}")

    # Display Selected Questions
    st.write("### Selected Questions:")
    for idx, question in enumerate(st.session_state.selected_questions):
        st.write(f"**{idx + 1}. {question['question']}**")
        for opt_key, option in question["options"].items():
            st.text(f"{option}")
        st.text(f"Correct Answer: {question['correct_answer']}")

