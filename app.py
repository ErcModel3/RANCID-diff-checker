from flask import Flask, render_template, request
from datetime import datetime, timedelta
from dotenv import load_dotenv
import subprocess
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure the repo path from environment variable
REPO_PATH = os.getenv('REPO_PATH', os.getcwd())

def get_friday_weeks(num_weeks=12):
    """Generate a list of Friday dates going back num_weeks"""
    today = datetime.now()
    # Find the most recent Friday
    days_since_friday = (today.weekday() - 4) % 7
    last_friday = today - timedelta(days=days_since_friday)

    weeks = []
    for i in range(num_weeks):
        friday = last_friday - timedelta(weeks=i)
        weeks.append(friday)

    return weeks

def get_week_range(friday_date):
    """Get the date range for a week starting on Friday"""
    start = friday_date
    end = friday_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end

def get_git_diff(start_date, end_date):
    """Get git diff for commits in the date range"""
    try:
        # Format dates for git log
        since = start_date.strftime('%Y-%m-%d %H:%M:%S')
        until = end_date.strftime('%Y-%m-%d %H:%M:%S')

        # Get commits in range
        commits_cmd = [
            'git', '-C', REPO_PATH, 'log',
            f'--since={since}',
            f'--until={until}',
            '--pretty=format:%H|%an|%ad|%s',
            '--date=format:%Y-%m-%d %H:%M:%S'
        ]

        commits_output = subprocess.run(commits_cmd, capture_output=True, text=True)

        if commits_output.returncode != 0:
            return None, "Error fetching commits"

        commits = []
        for line in commits_output.stdout.strip().split('\n'):
            if line:
                hash, author, date, message = line.split('|', 3)
                commits.append({
                    'hash': hash,
                    'author': author,
                    'date': date,
                    'message': message
                })

        # Get diff for the entire range
        if commits:
            first_commit = commits[-1]['hash']
            last_commit = commits[0]['hash']

            diff_cmd = [
                'git', '-C', REPO_PATH, 'diff',
                f'{first_commit}^..{last_commit}'
            ]

            diff_output = subprocess.run(diff_cmd, capture_output=True, text=True)

            if diff_output.returncode != 0:
                return commits, "Error fetching diff"

            return commits, diff_output.stdout
        else:
            return [], "No commits in this week"

    except Exception as e:
        return None, f"Error: {str(e)}"

@app.route('/')
def index():
    weeks = get_friday_weeks()
    selected_week = request.args.get('week')

    commits = None
    diff = None
    week_start = None
    week_end = None

    if selected_week:
        try:
            friday = datetime.strptime(selected_week, '%Y-%m-%d')
            week_start, week_end = get_week_range(friday)
            commits, diff = get_git_diff(week_start, week_end)
        except ValueError:
            diff = "Invalid date format"

    return render_template('index.html',
                         weeks=weeks,
                         selected_week=selected_week,
                         commits=commits,
                         diff=diff,
                         week_start=week_start,
                         week_end=week_end)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
