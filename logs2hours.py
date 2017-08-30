""" logs2hours methods and script
"""

import os
import json

from datetime import datetime, timedelta

def filter_git_logs(repo_name, author_name,
                    start_date=datetime.now() - timedelta(1),
                    end_date=datetime.now()):
    """ Loads and filters, returning selection

    Args:
      log_path: name of repo, logs must reside in logs2hours/logs/git/
      author_name: name of author - str
      start_date: (optional) - datetime
        24 hours ago if unspecified
      end_date: (optional) - datetime
        current time if unspecified

    Returns:
      filtered_commits
    """
    # absolute path to this file
    my_abs_path = os.path.dirname(os.path.abspath(__file__))
    with open('{}/logs/git/{}.json'.format(my_abs_path, repo_name), 'r') as log_file:
        log_rec = json.load(log_file)

    filtered_commits = []

    for commit in log_rec:
        commit_date = datetime.fromtimestamp(commit['author']['date'])
        if start_date <= commit_date <= end_date:
            if commit['author']['name'] == author_name:
                filtered_commits.append(commit)

    return filtered_commits


def to_gantt_rec(commits, task_name,  commit_duration=30):
    """ Create and return the dataframe record expected by plotly's gantt plot

    Args:
      commits: list of commit records
      task_name: name of task to use, generally name of repo
      commit_duration: duration to give each commit - in minutes

    Returns:
      gantt_recs:
    """
    gantt_recs = []
    for commit in commits:
        commit_dt = datetime.fromtimestamp(commit['author']['date'])
        end_dt = commit_dt + timedelta(minutes=commit_duration)
        description = 'Message: {}'.format(commit['message'])
        tot_change = 0
        for file_change_rec in commit['changes']:
            description += '<br>   {}: +{}; -{}'.format(file_change_rec[2], file_change_rec[0], file_change_rec[1])
            # don't count notebook changes the same as code changes
            if file_change_rec[2].endswith('.ipynb'):
                # let's just give each notebook push an arbitrary 10 change units
                tot_change += 10
            else:
                tot_change += int(file_change_rec[0]) + int(file_change_rec[1])
        commit_rec = {
            'Task': task_name,
            'Start': "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                year=commit_dt.year, month=commit_dt.month, day=commit_dt.day,
                hour=commit_dt.hour, minute=commit_dt.minute, second=commit_dt.second
            ),
            'Finish': "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                year=end_dt.year, month=end_dt.month, day=end_dt.day,
                hour=end_dt.hour, minute=end_dt.minute, second=end_dt.second
            ),
            'Description': description,
            'TotalChanges': tot_change
        }
        gantt_recs.append(commit_rec)
    return gantt_recs
