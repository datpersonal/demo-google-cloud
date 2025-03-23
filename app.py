from flask import Flask, request, render_template, redirect, url_for
from dotenv import load_dotenv
import mysql.connector
import os

app = Flask(__name__)
load_dotenv()

# Database credentials
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# Ensure MySQL user and database exist
def init_db():
    try:
        temp_conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        temp_cursor.execute("FLUSH PRIVILEGES;")
        temp_cursor.close()
        temp_conn.close()
    except mysql.connector.Error as err:
        print(f"Error initializing DB: {err}")

# Create table if it doesn't exist
def create_table():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                list_name VARCHAR(255) NOT NULL,
                content TEXT NOT NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error creating table: {err}")

# Run setup
init_db()
create_table()

# Home page to show all tasks and lists
@app.route('/')
def home():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT list_name FROM tasks")
    lists = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', lists=lists, tasks=[])

# View tasks in a specific list
@app.route('/<list_name>')
def view_list(list_name):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE list_name = %s", (list_name,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not tasks:
        return redirect(url_for('home'))  # Redirect if the list has no tasks
    
    return render_template('index.html', lists=[], tasks=tasks, list_name=list_name)

# Add a new task to a specific list
@app.route('/add', methods=['POST'])
def add_task():
    list_name = request.form['list_name']
    content = request.form['content']
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (list_name, content) VALUES (%s, %s)", (list_name, content))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('view_list', list_name=list_name))

# Delete a task from a specific list
@app.route('/delete/<int:task_id>/<list_name>', methods=['POST'])
def delete_task(task_id, list_name):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    
    # Check if there are remaining tasks in the list
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE list_name = %s", (list_name,))
    remaining_tasks = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    if remaining_tasks == 0:
        return redirect(url_for('home'))  # Redirect if no more tasks in the list
    
    return redirect(url_for('view_list', list_name=list_name))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
