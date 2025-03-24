import os
import sqlalchemy
from flask import Flask, request, render_template, redirect, url_for, Response
from flask_cors import CORS
from dotenv import load_dotenv
from connect_connector import connect_with_connector  # Only using this method
from connect_unix import connect_unix_socket
app = Flask(__name__)
CORS(app)
load_dotenv()

def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    # use a TCP socket when INSTANCE_HOST (e.g. 127.0.0.1) is defined
    if os.environ.get("DB_HOST"):
        return connect_unix_socket()

    # use the connector when INSTANCE_CONNECTION_NAME (e.g. project:region:instance) is defined
    if os.environ.get("INSTANCE_UNIX_SOCKET"):
        # Either a DB_USER or a DB_IAM_USER should be defined. If both are
        # defined, DB_IAM_USER takes precedence.
        return connect_with_connector()

    raise ValueError(
        "Missing database connection type. Please define one of INSTANCE_HOST, INSTANCE_UNIX_SOCKET, or INSTANCE_CONNECTION_NAME"
    )
# Initialize database connection
def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    """Creates the `tasks` table if it doesn't exist."""
    with db.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    list_name VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
        )
        conn.commit()

db = None
@app.before_request
def init_db() -> None:
    """Initiates connection to the database and ensures table exists."""
    global db
    if db is None:
        db = init_connection_pool()
        migrate_db(db)

@app.route('/')
def home():
    try:
        with db.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT DISTINCT list_name FROM tasks"))
            lists = result.fetchall()
        return render_template('index.html', lists=lists, tasks=[])
    except Exception as err:
        print(f"Error occurred while fetching task lists: {err}")
        
        # Optionally, re-throw the exception if you want it handled elsewhere
        # You can raise a custom exception here or re-raise the current one
        raise
        
        # Return a fallback response
        return render_template('index.html', lists=[], tasks=[])
@app.route('/<list_name>')
def view_list(list_name):
    try:
        with db.connect() as conn:
            result = conn.execute(
                sqlalchemy.text("SELECT * FROM tasks WHERE list_name = :list_name"),
                {"list_name": list_name}
            )
            tasks = result.fetchall()

        if not tasks:
            return redirect(url_for('home'))

        return render_template('index.html', lists=[], tasks=tasks, list_name=list_name)
    except Exception as err:
        return redirect(url_for('home'))

@app.route('/add', methods=['POST'])
def add_task():
    list_name = request.form.get("list_name", "")
    content = request.form.get("content", "")
    try:
        with db.connect() as conn:
            conn.execute(
                sqlalchemy.text("INSERT INTO tasks (list_name, content) VALUES (:list_name, :content)"),
                {"list_name": list_name, "content": content}
            )
            conn.commit()
        return redirect(url_for('view_list', list_name=list_name))
    except Exception as err:
        return redirect(url_for('home'))

@app.route('/delete/<int:task_id>/<list_name>', methods=['POST'])
def delete_task(task_id, list_name):
    try:
        with db.connect() as conn:
            conn.execute(
                sqlalchemy.text("DELETE FROM tasks WHERE id = :task_id"),
                {"task_id": task_id}
            )
            conn.commit()

            result = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM tasks WHERE list_name = :list_name"),
                {"list_name": list_name}
            )
            remaining_tasks = result.scalar()

        if remaining_tasks == 0:
            return redirect(url_for('home'))

        return redirect(url_for('view_list', list_name=list_name))
    except Exception as err:
        return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

