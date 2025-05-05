from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()

class Execution(database.Model):
    id = database.Column(database.String, primary_key=True)
    repo_title = database.Column(database.String, nullable=False)
    pr_name = database.Column(database.String, nullable=True)
    timestamp = database.Column(database.DateTime, nullable=False)
    status = database.Column(database.String, nullable=False)
    logs = database.Column(database.Text, nullable=True)
    active_stage = database.Column(database.String, nullable=True)
    is_paused = database.Column(database.Boolean, default=False)