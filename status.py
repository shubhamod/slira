import os
from flask import Flask, request, Response
import json
from attachments import *

class Status:
    def __init__(self, jira, slack_client):
        self.jira = jira
        self.slack_client = slack_client
        self.all_projects = [(project.name, project.key) for project in jira.projects()]#jira.projects is a API
        self.all_users = [(user.displayName, user.key) for user in jira.search_users("%")]

    def get_status_options(self, message_action):
        response = "Hello. What kind of status you want?"
        attachments = [get_status_by_project, get_status_by_user]
        channel_id = message_action["channel"]["id"]
        self.slack_client.api_call("chat.postMessage", channel=channel_id, text=response, attachments=attachments)

    def list_all_projects(self, message_action):
        projects_by_label_value = [{"label": str(label), "value": str(value).lower()} for (label, value) in self.all_projects]
        trigger_id = message_action["trigger_id"]
        dialog = {
                    "title": "Select Project",
                    "submit_label": "Submit",
                    "callback_id": "all_projects",
                    "elements": [
                        {
                            "label": "Projects",
                            "type": "select",
                            "name": "selected_project",
                            "placeholder": "Select Project",
                            "options": projects_by_label_value
                        }
                    ]
                }
        open_dialog = self.slack_client.api_call("dialog.open", trigger_id=trigger_id, dialog=dialog)

    def list_all_users(self, message_action):
        users_by_label_value = [{"label": str(label), "value": str(value).lower()} for (label, value) in self.all_users]
        trigger_id = message_action["trigger_id"]
        dialog = {
                    "title": "Select User",
                    "submit_label": "Submit",
                    "callback_id": "all_users",
                    "elements": [
                        {
                            "label": "Users",
                            "type": "select",
                            "name": "selected_user",
                            "placeholder": "Select User",
                            "options": users_by_label_value
                        }
                    ]
                }
        open_dialog = self.slack_client.api_call("dialog.open", trigger_id=trigger_id, dialog=dialog)

    def get_jira_of_project(self, selected_project, channel_id):
        issues = ["{0}\n> {1}".format(issue.key, issue.fields.summary) for issue in self.jira.search_issues('project=%s'%(selected_project))]
        self.slack_client.api_call("chat.postMessage", channel=channel_id, text=str("\n".join(issues)), attachments=[])

    def get_jira_of_user(self, selected_user, channel_id):
        issues = ["{0}\n> {1}".format(issue.key, issue.fields.summary) for issue in self.jira.search_issues('assignee = %s order by priority desc'%(selected_user), maxResults=5)]
        self.slack_client.api_call("chat.postMessage", channel=channel_id, text=str("\n".join(issues)), attachments=[])

