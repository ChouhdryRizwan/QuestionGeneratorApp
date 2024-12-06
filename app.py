import streamlit as st
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
import csv
from io import StringIO

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
            st.experimental_rerun()  # Redirect to the main page after login
        else:
            st.error("Invalid username or password")

# Function to handle logout
def logout():
    st.session_state.authenticated = False
    st.session_state.generated_questions = []
    st.session_state.selected_questions = []
    st.success("Logged out successfully!")
    st.experimental_rerun()  # Redirect to the login page by rerunning the app

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
def generate_questions(subject, number, level, question_type):
    difficulty_mapping = {
        "Bronze": "basic",
        "Silver": "intermediate",
        "Gold": "advanced",
        "Platinum": "expert",
        "Diamond": "most difficult"
    }
    difficulty = difficulty_mapping.get(level, "basic")
    
    if question_type == "MCQ":
        prompt = f"Generate {number} multiple choice questions for the subject '{subject}' at a {difficulty} level in this format:\n\n" \
                 f"1. Question?\n" \
                 f"a) Option 1\n" \
                 f"b) Option 2\n" \
                 f"c) Option 3\n" \
                 f"d) Option 4\n\n" \
                 f"Correct Answer: [Option]\n\n"
    elif question_type == "True/False":
        prompt = f"Generate {number} true/false questions for the subject '{subject}' at a {difficulty} level in this format:\n\n" \
                 f"1. Question?\n" \
                 f"Correct Answer: [True/False]\n\n"
    elif question_type == "Multiple Correct Answers":
        prompt = f"Generate {number} questions with multiple correct answers for the subject '{subject}' at a {difficulty} level in this format:\n\n" \
                 f"1. Question?\n" \
                 f"a) Option 1\n" \
                 f"b) Option 2\n" \
                 f"c) Option 3\n" \
                 f"d) Option 4\n\n" \
                 f"Correct Answers: [Option1, Option2]\n\n"
    
    response = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
    return response.text.strip()

# Parsing function with refined output
def parse_questions(questions_text, question_type):
    if question_type == "MCQ":
        question_pattern = r'(\d+\..+?)\s*(a\).+?)\s*(b\).+?)\s*(c\).+?)\s*(d\).+?)\s*Correct Answer: \[([a-d])\]'
    elif question_type == "True/False":
        question_pattern = r'(\d+\..+?)\s*Correct Answer: \[(True|False)\]'
    elif question_type == "Multiple Correct Answers":
        question_pattern = r'(\d+\..+?)\s*(a\).+?)\s*(b\).+?)\s*(c\).+?)\s*(d\).+?)\s*Correct Answers: \[([a-d, ]+)\]'
    
    questions = []
    matches = re.findall(question_pattern, questions_text, re.DOTALL)

    for match in matches:
        if question_type == "MCQ":
            question_text, option_a, option_b, option_c, option_d, correct_answer = match
            clean_question = re.sub(r'^\d+\.\s*', '', question_text).strip()
            clean_option_a = re.sub(r'^a\)\s*', '', option_a).strip()
            clean_option_b = re.sub(r'^b\)\s*', '', option_b).strip()
            clean_option_c = re.sub(r'^c\)\s*', '', option_c).strip()
            clean_option_d = re.sub(r'^d\)\s*', '', option_d).strip()
            questions.append({
                "question": clean_question,
                "options": {
                    "a": clean_option_a,
                    "b": clean_option_b,
                    "c": clean_option_c,
                    "d": clean_option_d
                },
                "correct_answer": correct_answer.strip()
            })
        elif question_type == "True/False":
            question_text, correct_answer = match
            clean_question = re.sub(r'^\d+\.\s*', '', question_text).strip()
            questions.append({
                "question": clean_question,
                "correct_answer": correct_answer.strip()  # Store the correct answer
            })
        elif question_type == "Multiple Correct Answers":
            question_text, option_a, option_b, option_c, option_d, correct_answers = match
            clean_question = re.sub(r'^\d+\.\s*', '', question_text).strip()
            clean_option_a = re.sub(r'^a\)\s*', '', option_a).strip()
            clean_option_b = re.sub(r'^b\)\s*', '', option_b).strip()
            clean_option_c = re.sub(r'^c\)\s*', '', option_c).strip()
            clean_option_d = re.sub(r'^d\)\s*', '', option_d).strip()
            correct_answers_list = [ans.strip() for ans in correct_answers.split(',')]
            questions.append({
                "question": clean_question,
                "options": {
                    "a": clean_option_a,
                    "b": clean_option_b,
                    "c": clean_option_c,
                    "d": clean_option_d
                },
                "correct_answers": correct_answers_list
            })

    return questions


# Export to CSV function with refined output
def export_to_csv(selected_questions, subject, level):
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write header
    csv_writer.writerow([
        "Question Text", "Question Type", "Option 1", "Option 2",
        "Option 3", "Option 4", "isCorrectOption1", "isCorrectOption2",
        "isCorrectOption3", "isCorrectOption4", "Subject", "Level"
    ])

    # Write rows
    for question in selected_questions:
        if "correct_answers" in question:
            # Handle Multiple Correct Answers
            is_correct = {
                "a": "a" in question["correct_answers"],
                "b": "b" in question["correct_answers"],
                "c": "c" in question["correct_answers"],
                "d": "d" in question["correct_answers"]
            }
            csv_writer.writerow([
                question["question"],
                "Multiple Correct Answers",
                question["options"].get("a", ""),
                question["options"].get("b", ""),
                question["options"].get("c", ""),
                question["options"].get("d", ""),
                is_correct["a"],
                is_correct["b"],
                is_correct["c"],
                is_correct["d"],
                subject,
                level
            ])
        elif "options" in question:
            # Handle MCQ
            is_correct = {
                "a": question["correct_answer"] == "a",
                "b": question["correct_answer"] == "b",
                "c": question["correct_answer"] == "c",
                "d": question["correct_answer"] == "d"
            }
            csv_writer.writerow([
                question["question"],
                "MCQ",
                question["options"].get("a", ""),
                question["options"].get("b", ""),
                question["options"].get("c", ""),
                question["options"].get("d", ""),
                is_correct["a"],
                is_correct["b"],
                is_correct["c"],
                is_correct["d"],
                subject,
                level
            ])
        else:
            # Handle True/False
            is_correct = question["correct_answer"] == "True"
            csv_writer.writerow([
                question["question"],
                "True/False",
                "",  # No options for True/False
                "",  # No options for True/False
                "",  # No options for True/False
                "",  # No options for True/False
                is_correct,  # Only one correct answer
                "",  # No options for True/False
                "",  # No options for True/False
                "",  # No options for True/False
                subject,
                level
            ])

    csv_buffer.seek(0)
    return csv_buffer.getvalue()
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

    # Question Type Input
    question_type = st.selectbox("Select Question Type:", ["MCQ", "True/False", "Multiple Correct Answers"])

    # Subject Input with Dynamic Dropdown and Save
    selected_subject = st.selectbox("Subject (select or add new):", subjects + ["Add new..."])
    if selected_subject == "Add new...":
        new_subject = st.text_input("Enter new subject:", key="new_subject")
        if new_subject:
            if st.button("Save Subject", key="save_subject"):
                insert_subject(new_subject)
                st.success(f"Subject '{new_subject}' added successfully!")
                st.experimental_rerun()

    # Difficulty Level Input with Dynamic Dropdown and Save
    selected_level = st.selectbox("Difficulty Level (select or add new):", levels + ["Add new..."])
    if selected_level == "Add new...":
        new_level = st.text_input("Enter new difficulty level:", key="new_level")
        if new_level:
            if st.button("Save Difficulty Level", key="save_level"):
                insert_level(new_level)
                st.success(f"Difficulty level '{new_level}' added successfully!")
                st.experimental_rerun()

    # Static Input for Number of Questions
    number_of_questions = st.number_input("Number of Questions:", min_value=1, max_value=100, value=10)

    # Generate Questions Button
    if st.button("Generate Questions"):
        if selected_subject and selected_level:
            questions_text = generate_questions(selected_subject, number_of_questions, selected_level, question_type)
            if questions_text:
                st.session_state.generated_questions = parse_questions(questions_text, question_type)
            else:
                st.error("No questions generated. Please try again.")
        else:
            st.error("Please fill in both Subject and Difficulty Level.")

    # Updated display for refined questions
    if st.session_state.generated_questions:
        st.write("### Generated Questions:")
        for idx, question in enumerate(st.session_state.generated_questions):
            # Checkbox to select/unselect the question
            checkbox_key = f"gen_q_{idx}"
            if st.checkbox(f"{idx + 1} . {question['question']}", key=checkbox_key):
                if question not in st.session_state.selected_questions:
                    st.session_state.selected_questions.append(question)
            else:
                if question in st.session_state.selected_questions:
                    st.session_state.selected_questions.remove(question)

            # Display refined options for the generated question
            if "options" in question:
                for opt_key, option in question["options"].items():
                    st.text(f"{opt_key}. {option}")
            st.write(f"**Correct Answer: {question.get('correct_answer', question.get('correct_answers', []))}**")


    # Display Selected Questions and Export to CSV
    if st.session_state.selected_questions:
        st.write("### Selected Questions:")
        for idx, question in enumerate(st.session_state.selected_questions):
            st.write(f"**{idx + 1}. {question['question']}**")
            if "options" in question:
                for opt_key, option in question["options"].items():
                    st.text(f"{opt_key}. {option}")
                st.write(f"**Correct Answer: {question.get('correct_answer', question.get('correct_answers', []))}**")
            else:
                # Display correct answer for True/False
                st.write(f"**Correct Answer: {question['correct_answer']}**")  # Display the correct answer for True/False

        # Export to CSV Button
        csv_data = export_to_csv(st.session_state.selected_questions, selected_subject, selected_level)
        st.download_button(
            label="Export to CSV",
            data=csv_data,
            file_name="questions.csv",
            mime="text/csv"
            )