""" logs2hours methods and script
"""

import os
import json

import numpy as np

import plotly.figure_factory as ff

from datetime import datetime, timedelta
from warnings import warn

# horribly incomplete of file extensions of programming language source files
# you should add the extension of all files whose lines you want to be counted
CODE_FILE_EXTENSIONS = ['py', 'c', 'h', 'tex']

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


def git_to_gantt_rec(commits, task_name,  commit_duration=30):
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
            dot_split = file_change_rec[2].split('.')
            if len(dot_split) > 0:
                extension = dot_split[-1]
            else:
                extension = ''
            # don't count notebook changes the same as code changes
            if extension == 'ipynb':
                # let's just give each notebook push an arbitrary 10 change units
                tot_change += 10
            elif extension in CODE_FILE_EXTENSIONS:
                tot_change += int(file_change_rec[0]) + int(file_change_rec[1])
            else:
                warn("Don't know what to do about file extension '{}'; ignoring".format(extension))
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

def extract_user_messages_from_slack_rec(user_id,
                                         start_date=datetime.now() - timedelta(1),
                                         end_date=datetime.now()):
    """ Extracts all messages authored by user from the slack dump
    Slack dump must be in logs2hours/slack/

    Args:
      user_id: id of desired user, not their name - str
        look in the dumps to find this
      start_date: (optional) - datetime
        24 hours ago if unspecified
      end_date: (optional) - datetime
        current time if unspecified

    Returns:
      authored_messages: list of all messages ever authored by the user
       elements are message records (dictionaries )that have at least these keys:
         - ts
         - type
         - user

    """
    # absolute path to this file
    my_abs_path = os.path.dirname(os.path.abspath(__file__))

    authored_messages = []
    log_path = '{}/logs/slack'.format(my_abs_path)
    for channel_name in os.listdir(log_path):
        channel_path = log_path + '/' + channel_name
        # there are some top level jsons to ignore
        if not os.path.isdir(channel_path):
            continue
        for day_rec_name in os.listdir(channel_path):
            rec_path = channel_path + '/' + day_rec_name
            with open(rec_path, 'r') as rec_file:
                day_rec = json.load(rec_file)
                for atomic_rec in day_rec:
                    atomic_rec['channel'] = channel_name
                    rec_time = datetime.fromtimestamp(float(atomic_rec['ts']))
                    if start_date <= rec_time <= end_date:
                        if atomic_rec['type'] == 'message':
                            if 'subtype' not in atomic_rec:
                                if atomic_rec['user'] == user_id:
                                    authored_messages.append(atomic_rec)
                            elif atomic_rec['subtype'] == 'file_comment':
                                if atomic_rec['comment']['user'] == user_id:
                                    authored_messages.append(atomic_rec)
                            else:
                                # bot_message subtypes don't have a user
                                if 'user' in atomic_rec:
                                    if atomic_rec['user'] == user_id:
                                        authored_messages.append(atomic_rec)
    return authored_messages

def slack_to_gantt_rec(slack_recs, message_duration=1):
    """ Create and return the dataframe record expected by plotly's gantt plot

    Args:
      slack_recs: list of message records
      message_duration: duration to give each message - in minutes

    Returns:
      gantt_recs
    """
    gantt_recs = []
    for message_rec in slack_recs:
        message_dt = datetime.fromtimestamp(float(message_rec['ts']))
        end_dt = message_dt + timedelta(minutes=message_duration)
        description = message_rec['text']
        gantt_rec = {
            'Task': message_rec['channel'],
            'Start': "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                year=message_dt.year, month=message_dt.month, day=message_dt.day,
                hour=message_dt.hour, minute=message_dt.minute, second=message_dt.second
            ),
            'Finish': "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                year=end_dt.year, month=end_dt.month, day=end_dt.day,
                hour=end_dt.hour, minute=end_dt.minute, second=end_dt.second
            ),
            'Description': description,
            'TotalChanges': 0
        }
        gantt_recs.append(gantt_rec)
    return gantt_recs

def make_gantt_figure(start_date, end_date, work_spec, estimate_hours=True):
    """ Run everything and return the plotly gantt figure

    Args:
      start_date: datetime start
      end_date: datetime end
      work_spec: spec as returned by make_spec
      estimate_hours: if True, also estimated hours and plot sessions

    Returns:
      gantt_figure: pass to iplot
    """
    commit_recs = []
    raw_commits = []
    for repo in work_spec['repos']:
        commits = filter_git_logs(repo,
                                  work_spec['author_name'],
                                  start_date=start_date,
                                  end_date=end_date
        )
        raw_commits.extend(commits)
        commit_recs.extend(git_to_gantt_rec(commits, repo, 1))


    authored_messages = extract_user_messages_from_slack_rec(
        work_spec['slack_uid'], start_date=start_date, end_date=end_date
    )
    slack_gantt_recs = slack_to_gantt_rec(authored_messages)
    all_recs = commit_recs + slack_gantt_recs

    if estimate_hours:
        # collect timestamps into single list
        timestamps = []
        for commit in raw_commits:
            timestamps.append(datetime.fromtimestamp(commit['author']['date']))

        for message in authored_messages:
            timestamps.append(datetime.fromtimestamp(float(message['ts'])))

        tot_hours, sessions = calc_estimated_hours(timestamps)
        session_recs = []
        for session in sessions:
            session_recs.append({
                'Task': 'Sessions',
                'Start':  "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                    year=session[0].year, month=session[0].month, day=session[0].day,
                    hour=session[0].hour, minute=session[0].minute, second=session[0].second
                ),
                'Finish': "{year}-{month:0>2d}-{day:0>2d} {hour}:{minute:0>2d}:{second:0>2d}".format(
                    year=session[1].year, month=session[1].month, day=session[1].day,
                    hour=session[1].hour, minute=session[1].minute, second=session[1].second
                ),
                'Description': 'Session',
                'TotalChanges': 0
            })
        all_recs += session_recs

    gantt_fig = ff.create_gantt(all_recs, group_tasks=True, index_col='TotalChanges', show_colorbar=True)


    gantt_fig['layout']['title'] = "{year1}/{month1:0>2d}/{day1:0>2d} - {year2}/{month2:0>2d}/{day2:0>2d}".format(
        year1=start_date.year, month1=start_date.month, day1=start_date.day,
        year2=end_date.year, month2=end_date.month, day2=end_date.day
    )
    if estimate_hours:
        gantt_fig['layout']['title'] += '<br> Total estimated hours >= {}'.format(tot_hours)


    return gantt_fig

def summarize_day(year, month, day, work_spec):
    """ Summarize the days events
    Days go from 4am-4am.
    Returns a gantt fig rec

    Args:
      year
      month
      day
      work_spec: spec as returned by make_spec

    Returns:
      gantt_fig
    """
    start_date = datetime(year, month, day, 4)
    end_date = start_date + timedelta(1)

    # keyed by repo
    commit_recs = {}
    for repo in work_spec['repos']:
        commits = filter_git_logs(repo,
                                  work_spec['author_name'],
                                  start_date=start_date,
                                  end_date=end_date
        )
        commit_recs[repo] = commits

    authored_messages = extract_user_messages_from_slack_rec(
        work_spec['slack_uid'], start_date=start_date, end_date=end_date
    )

    # keyed by channel
    slack_messages = {}
    for message in authored_messages:
        channel = message['channel']
        if channel in slack_messages:
            slack_messages[channel].append(message)
        else:
            slack_messages[channel] = [message]

    # find first and last events
    first_commit = datetime.now()
    last_commit = datetime(2015, 1, 1)

    first_message = datetime.now()
    last_message = datetime(2015, 1, 1)

    for commits in commit_recs.values():
        for commit in commits:
            commit_dt = datetime.fromtimestamp(commit['author']['date'])
            if commit_dt < first_commit:
                first_commit = commit_dt
            if last_commit < commit_dt:
                last_commit = commit_dt

    for messages in slack_messages.values():
        for message in messages:
            message_dt = datetime.fromtimestamp(float(message['ts']))
            if message_dt < first_message:
                first_message = message_dt
            if last_message <  message_dt:
                last_message = message_dt

    print("First commit: {hour:0>2d}:{minute:0>2d}".format(
        hour=first_commit.hour, minute=first_commit.minute
    ))
    print("Last commit: {hour:0>2d}:{minute:0>2d}".format(
        hour=last_commit.hour, minute=last_commit.minute
    ))
    print()
    print("First message: {hour:0>2d}:{minute:0>2d}".format(
        hour=first_message.hour, minute=first_message.minute
    ))
    print("Last message: {hour:0>2d}:{minute:0>2d}".format(
        hour=last_message.hour, minute=last_message.minute
    ))
    print()
    print('='*80)
    print()
    print("Event summary:")
    print("  Repos:")
    for repo, commits in commit_recs.items():
        if len(commits) > 0:
            print("    {}: {} commits".format(repo, len(commits)))
    print("  Messages:")
    for channel, messages in slack_messages.items():
        if len(messages):
            print("    {}: {} messages".format(channel, len(messages)))


    return make_gantt_figure(start_date, end_date, work_spec)

def calc_estimated_hours(timestamps, sess_sep=2, sess_extra=0.5):
    """ Estimate hours from list of commits

    Args:
      timestamps: list of datetime objects
        not assumed to be sorted
      sess_sep: commits closer together this are considered part of the same session - in hours
      sess_extra: extra time to add to beginning of session - in hours

    Returns:
      total_hours: estimated total hours - float
      sessions: List of computed session partitions [[start_datetime, end_datetime], ...]
    """
    # [N]
    timestamps = sorted(timestamps)
    # time deltas between adjacent events
    # [N - 1]
    time_diffs = -np.diff(timestamps)
    max_sep = timedelta(hours=sess_sep)

    if len(timestamps > 0):
        # calculate sessions
        sessions = [[timestamps[0], None]]
        for timestamp, delta_t in zip(timestamps[1:], time_diffs):
            if delta_t < max_sep:
                sessions[-1][1] = timestamp
            else:
                sessions.append([timestamp, None])
        sessions[-1][1] = timestamps[-1]

        # offset left edge of sessons by sess_extra
        fudge_offset = timedelta(hours=sess_extra)
        sessions = [[sess[0] - fudge_offset, sess[1]] for sess in sessions]
    else:
        sessions = []

    # sum hours
    tot_hours = 0
    for session in sessions:
        tot_hours += (session[1] - session[0]).total_seconds() / 3600

    return tot_hours, sessions


def make_spec(repos, slack_user_id, author_name):
    """ Format and return spec specifying what to analyze
    Convenience method: spec used by several other methods here

    Args:
      repos: list of repo names, which should have their logs jumped to json already in logs2hours/logs/git
      start_date: datetime start
      end_date: datetime end
      slack_user_id: id of desired user, not their name - str
        look in the dumps to find this
      author_name: git author name

    Returns:
      spec
    """
    spec = {
        'repos': repos,
        'slack_uid': slack_user_id,
        'author_name': author_name
    }
    return spec
