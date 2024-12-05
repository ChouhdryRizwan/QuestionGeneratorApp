import streamlit as st
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

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
    prompt = f"Generate {number} multiple choice questions for the subject '{subject}' at a {difficulty} level with options and correct answers."
    response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
    return response.text

# Initialize database
init_db()

# Streamlit UI
st.title("Dynamic Question Generator")

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
            st.rerun()  # Update UI dynamically after saving

# Difficulty Level Input with Dynamic Dropdown and Save
selected_level = st.selectbox("Difficulty Level (select or add new):", levels + ["Add new..."])
if selected_level == "Add new...":
    new_level = st.text_input("Enter new difficulty level:", key="new_level")
    if new_level:
        if st.button("Save Difficulty Level", key="save_level"):
            insert_level(new_level)
            st.success(f"Difficulty level '{new_level}' added successfully!")
            st.rerun()  # Update UI dynamically after saving

# Static Input for Number of Questions
number_of_questions = st.number_input("Number of Questions:", min_value=1, max_value=100, value=10)

# Button to Generate Questions
if st.button("Generate Questions"):
    if selected_subject and selected_level:
        # Generate questions
        questions = generate_mcq(selected_subject, number_of_questions, selected_level)

        # Display the generated questions
        st.write("### Generated Questions:")
        st.write(questions)
    else:
        st.error("Please fill in both Subject and Difficulty Level.")
