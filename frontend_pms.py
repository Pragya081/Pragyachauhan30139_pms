# frontend_pms.py

import streamlit as st
import pandas as pd
from backend_pms import PMSDatabase

# Database connection details (replace with your own)
DB_NAME = "pms_db"
DB_USER = "postgres"
DB_PASSWORD = "Pragya@123"
DB_HOST = "localhost"
DB_PORT = "5432"

# Initialize the database instance
db = PMSDatabase(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)

# --- Authentication and State Management ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'is_manager' not in st.session_state:
    st.session_state['is_manager'] = False

def login_form():
    st.title("Performance Management System/30139 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = db.read_user(username, password)
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user[0]
            st.session_state['is_manager'] = user[2]
            st.success(f"Welcome, {user[1]}!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password.")

    st.markdown("---")
    st.markdown("New user? Register below.")
    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    is_manager_checkbox = st.checkbox("Register as Manager")
    if st.button("Register"):
        if db.create_user(new_username, new_password, is_manager_checkbox):
            st.success("Registration successful! Please log in.")
        else:
            st.error("Username already exists.")

# --- Frontend Pages ---

def goal_and_task_setting():
    st.title("🎯 Goal & Task Setting")

    if st.session_state['is_manager']:
        st.subheader("Set a New Goal for an Employee")
        employee_id = st.number_input("Employee User ID", min_value=1)
        goal_description = st.text_area("Goal Description")
        due_date = st.date_input("Due Date")

        if st.button("Set Goal"):
            if db.connect():
                db.cursor.execute(
                    "INSERT INTO goals (employee_id, manager_id, goal_description, due_date) VALUES (%s, %s, %s, %s);",
                    (employee_id, st.session_state['user_id'], goal_description, due_date)
                )
                db.conn.commit()
                db.close()
                st.success("Goal set successfully!")
            else:
                st.error("Failed to connect to the database.")

        st.markdown("---")
        st.subheader("View Goals You've Set")
        goals = db.read_goals(manager_id=st.session_state['user_id'])
        if goals:
            df = pd.DataFrame(goals, columns=["Goal ID", "Employee ID", "Description", "Due Date", "Status"])
            st.dataframe(df)

    else: # Employee view
        st.subheader("Your Assigned Goals")
        goals = db.read_goals(employee_id=st.session_state['user_id'])
        if goals:
            df = pd.DataFrame(goals, columns=["Goal ID", "Description", "Due Date", "Status"])
            st.dataframe(df)

            st.markdown("---")
            st.subheader("Log a Task for a Goal")
            goal_id = st.selectbox("Select Goal ID", df["Goal ID"].tolist())
            task_description = st.text_area("Task Description")

            if st.button("Log Task"):
                if db.connect():
                    db.cursor.execute(
                        "INSERT INTO tasks (goal_id, task_description) VALUES (%s, %s);",
                        (goal_id, task_description)
                    )
                    db.conn.commit()
                    db.close()
                    st.success("Task logged successfully!")

def progress_tracking():
    st.title("📈 Progress Tracking")
    
    is_manager = st.session_state['is_manager']
    user_id = st.session_state['user_id']

    st.subheader("Current Goals & Progress")
    if is_manager:
        goals = db.read_goals(manager_id=user_id)
    else:
        goals = db.read_goals(employee_id=user_id)

    if goals:
        goals_df = pd.DataFrame(goals, columns=["Goal ID", "Employee/Manager ID", "Description", "Due Date", "Status"] if is_manager else ["Goal ID", "Description", "Due Date", "Status"])
        st.dataframe(goals_df)

        st.markdown("---")
        if is_manager:
            st.subheader("Update Goal Status")
            goal_id_to_update = st.selectbox("Select Goal ID to Update", goals_df["Goal ID"].tolist())
            new_status = st.selectbox("New Status", ['Draft', 'In Progress', 'Completed', 'Cancelled'])
            if st.button("Update Status"):
                if db.update_goal_status(goal_id_to_update, new_status):
                    st.success("Status updated successfully!")
                    st.experimental_rerun()
                else:
                    st.error("Failed to update status.")
        else:
            st.info("You can't update a goal's status. Only managers can.")

def feedback_page():
    st.title("📝 Feedback")
    if st.session_state['is_manager']:
        st.subheader("Provide Feedback on a Goal")
        goal_id = st.number_input("Goal ID", min_value=1)
        feedback_text = st.text_area("Your Feedback")

        if st.button("Submit Feedback"):
            if db.connect():
                db.cursor.execute(
                    "INSERT INTO feedback (goal_id, feedback_text) VALUES (%s, %s);",
                    (goal_id, feedback_text)
                )
                db.conn.commit()
                db.close()
                st.success("Feedback submitted!")

    st.subheader("View Feedback")
    if db.connect():
        if st.session_state['is_manager']:
            db.cursor.execute("SELECT g.goal_id, f.feedback_text FROM feedback f JOIN goals g ON f.goal_id = g.goal_id WHERE g.manager_id = %s;", (st.session_state['user_id'],))
        else:
            db.cursor.execute("SELECT g.goal_id, f.feedback_text FROM feedback f JOIN goals g ON f.goal_id = g.goal_id WHERE g.employee_id = %s;", (st.session_state['user_id'],))
        feedback_data = db.cursor.fetchall()
        db.close()
        
        if feedback_data:
            df = pd.DataFrame(feedback_data, columns=["Goal ID", "Feedback"])
            st.dataframe(df)
        else:
            st.info("No feedback available.")

def reporting_page():
    st.title("📊 Performance History & Reporting")

    user_id = st.session_state['user_id']
    is_manager = st.session_state['is_manager']

    if is_manager:
        st.subheader("Performance History for Your Team")
        if db.connect():
            query = """
            SELECT
                u.username AS employee_name,
                g.goal_description,
                g.due_date,
                g.status,
                f.feedback_text
            FROM goals g
            JOIN users u ON g.employee_id = u.user_id
            LEFT JOIN feedback f ON g.goal_id = f.goal_id
            WHERE g.manager_id = %s;
            """
            df = pd.read_sql(query, db.conn, params=(user_id,))
            db.close()
            st.dataframe(df)
    else:
        st.subheader("Your Performance History")
        if db.connect():
            query = """
            SELECT
                g.goal_description,
                g.due_date,
                g.status,
                f.feedback_text
            FROM goals g
            LEFT JOIN feedback f ON g.goal_id = f.goal_id
            WHERE g.employee_id = %s;
            """
            df = pd.read_sql(query, db.conn, params=(user_id,))
            db.close()
            st.dataframe(df)

def business_insights_page():
    st.title("💡 Business Insights")
    st.info("This section provides aggregate insights using COUNT, SUM, AVG, MIN, and MAX.")

    st.markdown("---")
    st.subheader("Goal Status Breakdown (COUNT)")
    status_counts = db.count_goals_by_status()
    if status_counts:
        df_status = pd.DataFrame(status_counts, columns=["Status", "Count"])
        st.bar_chart(df_status.set_index("Status"))
    else:
        st.info("No goal data to display.")

    st.markdown("---")
    st.subheader("Average Goals per Employee (AVG)")
    avg_goals = db.get_avg_goals_per_employee()
    if avg_goals is not None:
        st.metric(label="Average Goals per Employee", value=f"{avg_goals:.2f}")
    else:
        st.info("No goal data to calculate.")

    st.markdown("---")
    st.subheader("Goal with the Longest Timeline (MAX Due Date)")
    longest_goal = db.get_longest_due_date_goal()
    if longest_goal:
        st.info(f"Goal: '{longest_goal[0]}' due on {longest_goal[1]}")
    else:
        st.info("No goal data available.")

    st.markdown("---")
    st.subheader("Goal with the Shortest Timeline (MIN Due Date)")
    shortest_goal = db.get_shortest_due_date_goal()
    if shortest_goal:
        st.info(f"Goal: '{shortest_goal[0]}' due on {shortest_goal[1]}")
    else:
        st.info("No goal data available.")
    
    st.markdown("---")
    st.subheader("Goal with the Most Tasks (MAX Tasks)")
    most_tasks_goal = db.get_most_tasks_goal()
    if most_tasks_goal:
        st.info(f"Goal: '{most_tasks_goal[0]}' has {most_tasks_goal[1]} tasks logged.")
    else:
        st.info("No task data available.")


# --- Main Application Logic ---
if not st.session_state['logged_in']:
    login_form()
else:
    # Sidebar navigation
    st.sidebar.title(f"Welcome, User {st.session_state['user_id']}!")
    page = st.sidebar.radio("Navigation", ["Goal & Task Setting", "Progress Tracking", "Feedback", "Reporting", "Business Insights"])
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['is_manager'] = False
        st.experimental_rerun()

    # Create tables on first run
    db.create_tables()

    if page == "Goal & Task Setting":
        goal_and_task_setting()
    elif page == "Progress Tracking":
        progress_tracking()
    elif page == "Feedback":
        feedback_page()
    elif page == "Reporting":
        reporting_page()
    elif page == "Business Insights":
        business_insights_page()