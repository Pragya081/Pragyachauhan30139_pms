# backend_pms.py

import psycopg2
from psycopg2 import sql

class PMSDatabase:
    def __init__(self, dbname, user, password, host, port):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.cursor = self.conn.cursor()
            return True
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()

    def create_tables(self):
        """CREATE: Creates the necessary database tables."""
        if not self.connect():
            return

        commands = (
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                is_manager BOOLEAN DEFAULT FALSE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS goals (
                goal_id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                manager_id INTEGER NOT NULL,
                goal_description TEXT NOT NULL,
                due_date DATE NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Draft',
                FOREIGN KEY (employee_id) REFERENCES users(user_id),
                FOREIGN KEY (manager_id) REFERENCES users(user_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id SERIAL PRIMARY KEY,
                goal_id INTEGER NOT NULL,
                task_description TEXT NOT NULL,
                is_approved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (goal_id) REFERENCES goals(goal_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id SERIAL PRIMARY KEY,
                goal_id INTEGER NOT NULL,
                feedback_text TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(goal_id)
            );
            """
        )
        try:
            for command in commands:
                self.cursor.execute(command)
            self.conn.commit()
            print("Tables created successfully.")
        except psycopg2.Error as e:
            print(f"Error creating tables: {e}")
        finally:
            self.close()
    
    # --- CRUD Operations ---

    def create_user(self, username, password, is_manager=False):
        """CREATE: Adds a new user to the database."""
        if not self.connect():
            return False
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password, is_manager) VALUES (%s, %s, %s) RETURNING user_id;",
                (username, password, is_manager)
            )
            user_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return user_id
        except psycopg2.IntegrityError:
            self.conn.rollback()
            return False
        finally:
            self.close()

    def read_user(self, username, password):
        """READ: Retrieves user information by username and password."""
        if not self.connect():
            return None
        try:
            self.cursor.execute(
                "SELECT user_id, username, is_manager FROM users WHERE username = %s AND password = %s;",
                (username, password)
            )
            user = self.cursor.fetchone()
            return user
        finally:
            self.close()

    def read_goals(self, employee_id=None, manager_id=None):
        """READ: Retrieves goals for a specific employee or manager."""
        if not self.connect():
            return []
        try:
            if employee_id:
                self.cursor.execute(
                    "SELECT goal_id, goal_description, due_date, status FROM goals WHERE employee_id = %s;",
                    (employee_id,)
                )
            elif manager_id:
                self.cursor.execute(
                    "SELECT goal_id, employee_id, goal_description, due_date, status FROM goals WHERE manager_id = %s;",
                    (manager_id,)
                )
            goals = self.cursor.fetchall()
            return goals
        finally:
            self.close()

    def update_goal_status(self, goal_id, new_status):
        """UPDATE: Allows a manager to update a goal's status."""
        if not self.connect():
            return False
        try:
            self.cursor.execute(
                "UPDATE goals SET status = %s WHERE goal_id = %s;",
                (new_status, goal_id)
            )
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            return False
        finally:
            self.close()

    def delete_goal(self, goal_id):
        """DELETE: Deletes a goal and its associated tasks and feedback."""
        if not self.connect():
            return False
        try:
            self.cursor.execute("DELETE FROM tasks WHERE goal_id = %s;", (goal_id,))
            self.cursor.execute("DELETE FROM feedback WHERE goal_id = %s;", (goal_id,))
            self.cursor.execute("DELETE FROM goals WHERE goal_id = %s;", (goal_id,))
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            self.conn.rollback()
            return False
        finally:
            self.close()

    # --- Business Insights Functions ---

    def count_goals_by_status(self):
        """Insights: Counts goals by their status."""
        if not self.connect():
            return []
        try:
            self.cursor.execute("SELECT status, COUNT(*) FROM goals GROUP BY status;")
            return self.cursor.fetchall()
        finally:
            self.close()
    
    def get_avg_goals_per_employee(self):
        """Insights: Calculates the average number of goals per employee."""
        if not self.connect():
            return None
        try:
            self.cursor.execute("SELECT AVG(goal_count) FROM (SELECT COUNT(*) AS goal_count FROM goals GROUP BY employee_id) AS subquery;")
            return self.cursor.fetchone()[0]
        finally:
            self.close()

    def get_longest_due_date_goal(self):
        """Insights: Finds the goal with the latest due date."""
        if not self.connect():
            return None
        try:
            self.cursor.execute("SELECT goal_description, due_date FROM goals ORDER BY due_date DESC LIMIT 1;")
            return self.cursor.fetchone()
        finally:
            self.close()
    
    def get_shortest_due_date_goal(self):
        """Insights: Finds the goal with the earliest due date."""
        if not self.connect():
            return None
        try:
            self.cursor.execute("SELECT goal_description, due_date FROM goals ORDER BY due_date ASC LIMIT 1;")
            return self.cursor.fetchone()
        finally:
            self.close()

    def get_most_tasks_goal(self):
        """Insights: Finds the goal with the most tasks."""
        if not self.connect():
            return None
        try:
            self.cursor.execute("SELECT g.goal_description, COUNT(t.task_id) FROM goals g JOIN tasks t ON g.goal_id = t.goal_id GROUP BY g.goal_id ORDER BY COUNT(t.task_id) DESC LIMIT 1;")
            return self.cursor.fetchone()
        finally:
            self.close()