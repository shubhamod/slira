import os
from flask import Flask, request, Response
from slackclient import SlackClient
import json
from jira.client import JIRA
import requests
import threading
from status import Status



jira_server = "https://slirahack.atlassian.net"
jira_user = "shubhamod97@gmail.com"
jira_password = "shubham123"

jira_server = {'server': jira_server}
jira = JIRA(options=jira_server, basic_auth=(jira_user, jira_password), async_=True)

SLACK_BOT_TOKEN='xoxb-2152601087-544487399811-2WsX8SD1xY5NCVXZ3nN5L86j'
slack_client = SlackClient(SLACK_BOT_TOKEN)

app = Flask(__name__)


def getButton(callback_id, name, color, style):
    return {
        "text": "",
        "callback_id": callback_id,
        "color": color,
        "attachment_type": "default",
        "actions": [
            {
                "name": name,
                "text": ":jira: {0}".format(name),
                "type": "button",
                "style": style,
                "value": callback_id
            }
        ]
    }

data_cache = {}




#########################################################################################
#
#                CREATE JIRA UTILS
#
#########################################################################################



def create_issue(project, summary, description ,issuetype, channel_id, user_id):
    new_issue = jira.create_issue(project=project, summary=summary,
                                  description=description, issuetype={'name': issuetype})
    new_issue_link = new_issue.permalink()
    print new_issue_link
    body = "New Jira created by user(<@{0}>) : {1}\n".format(user_id, new_issue_link) + \
           "> *Summary*\n> {0}\n> *Description*\n> {1}".format(summary, description)
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=body,
        attachments=[]
    )


projects_issuetypes = [
    {
        "label": "Choose Project",
        "type": "select",
        "name": "project",
        "placeholder": "Select a project",
        "options": [
            {
                "label": "Display",
                "value": "10002"
            },
            {
                "label": "CustomerBackone",
                "value": "10001"
            },
            {
                "label": "Personalisation",
                "value": "10004"
            },
            {
                "label": "SEO",
                "value": "10003"
            }
        ]
    },
    {
        "label": "Choose Issue Type",
        "type": "select",
        "name": "issuetype",
        "placeholder": "Select a IssueType",
        "options": [
            {
                "label": "Task",
                "value": "Task"
            },
            {
                "label": "Bug",
                "value": "Bug"
            }
        ]
    }

]

required_fields = [
    {
        "label": "Summary",
        "type": "text",
        "name": "summary",
        "placeholder": "type summary",
    },
    {
        "label": "Description",
        "type": "text",
        "name": "description",
        "placeholder": "type description",
    }
]


def create_jira_project_dialog(user_id, channel_id, trigger_id):
    slack_client.api_call("chat.postEphemeral", user=user_id, channel=channel_id,
                          text="Please wait..")
    open_dialog = slack_client.api_call(
        "dialog.open",
        trigger_id=trigger_id,
        dialog={
            "title": "CREATE JIRA",
            "submit_label": "Submit",
            "callback_id": "create_jira_show_req_fields_btn",
            "elements": projects_issuetypes
        }
    )


def create_jira_show_req_fields_btn(user_id, channel_id, project, issuetype):
    slack_client.api_call("chat.postEphemeral", user=user_id, channel=channel_id,
                          text=":jira: Project: {0}, Issue Type: {1}".format(project, issuetype),
                          attachments=[
                              getButton("create_jira_req_fields_dialog", "Add required fields", "#B22222", "primary")
                          ]
                          )


def create_jira_req_fields_dialog(trigger_id):
    open_dialog = slack_client.api_call(
        "dialog.open",
        trigger_id=trigger_id,
        dialog={
            "title": "Add Details to JIRA",
            "submit_label": "Submit",
            "callback_id": "create_jira_show_link",
            "elements": required_fields
        }
    )


def create_jira_show_link(user_id, channel_id, summary, description, project, issuetype):
    slack_client.api_call("chat.postEphemeral", user=user_id, channel=channel_id, text="Creating JIRA")
    thread = threading.Thread(target=create_issue,
                              args=(project, summary, description, issuetype, channel_id, user_id))
    thread.start()

########################################################################################################




#######################################################################################################
#
#                    EVENT UTILS
#
#######################################################################################################

event_ts_cache={}

@app.route("/slack/events", methods=["POST"])
def events():
    payload = request.get_json()
    print payload
    if 'challenge' in payload:
        return Response(payload['challenge']), 200
    event = payload['event']
    if("hey" in event['text'] and event['ts'] not in event_ts_cache):
        event_ts_cache[event['ts']] = 1
        channel = event['channel']
        user = event['user']
        attachments = [
            getButton("create_jira_project_dialog", "Create Jira", "#7CFC00", "primary"),
            getButton("get_status_jira_button", "Get Status Jira", "#FFFF00", "warning"),
            getButton("delete_jira_button", "Delete Jira", "#B22222", "danger")
        ]
        slack_client.api_call(
            "chat.postEphemeral",
            user=user,
            channel=channel,
            text="Did you call me? Here's what you can do..",
            attachments= attachments
        )
    return Response(), 200



#########################################################################################################






#########################################################################################################
#
#
#                      STATUS UTILS
#
#########################################################################################################

status = Status(jira, slack_client)

###############################################################################
#
#           MESSAGE ACTIONS
#
#################################################################################

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # Parse the request payload
    print request.form
    message_action = json.loads(request.form["payload"])
    user_id = message_action["user"]["id"]
    callback_id = message_action["callback_id"]
    channel_id = message_action["channel"]["id"]
    if callback_id == "create_jira_project_dialog":
        trigger_id = message_action["trigger_id"]
        create_jira_project_dialog(user_id, channel_id, trigger_id)
    elif callback_id == "create_jira_show_req_fields_btn":
        project = message_action["submission"]["project"]
        issuetype = message_action["submission"]["issuetype"]
        data_cache[user_id] = {'project': project, 'issuetype': issuetype}
        create_jira_show_req_fields_btn(user_id, channel_id, project, issuetype)
    if callback_id == "create_jira_req_fields_dialog":
        trigger_id = message_action["trigger_id"]
        create_jira_req_fields_dialog(trigger_id)
    if callback_id == "create_jira_show_link":
        summary = message_action["submission"]["summary"]
        description = message_action["submission"]["description"]
        project = data_cache[user_id]['project']
        issuetype = data_cache[user_id]['issuetype']
        create_jira_show_link(user_id, channel_id, summary, description, project, issuetype)
    elif callback_id == "get_status_jira_button":
        status.get_status_options(message_action)
    elif callback_id == "all_projects":
        selected_project = message_action["submission"]["selected_project"]
        thread = threading.Thread(target=status.get_jira_of_project, args=(selected_project, channel_id))
        thread.start()
        slack_client.api_call("dialog.close")
    elif callback_id == "get_status_by_project":
        status.list_all_projects(message_action)
    elif callback_id == "get_status_by_user":
        status.list_all_users(message_action)
    elif callback_id == "all_users":
        selected_user = message_action["submission"]["selected_user"]
        thread = threading.Thread(target=status.get_jira_of_user, args=(selected_user, channel_id))
        thread.start()
    elif callback_id == "delete_jira_button":
        #delete
        message_ts = message_action['message_ts']
        slack_client.api_call(
            "chat.update",
            channel=channel_id,
            ts=message_ts,
            text="Deleting JIRA",
            attachments=[]
        )
        open_dialog = slack_client.api_call(
            "dialog.open",
            trigger_id=message_action["trigger_id"],
            dialog={
                "title": "DELETE JIRA",
                "submit_label": "Submit",
                "callback_id": "delete_jira_box",
                "elements": [
                    {
                        "label": "Coffee Type",
                        "type": "select",
                        "name": "meal_preferences",
                        "placeholder": "Select a drink",
                        "options": [
                            {
                                "label": "Cappuccino",
                                "value": "cappuccino"
                            },
                            {
                                "label": "Latte",
                                "value": "latte"
                            }
                        ]
                    }
                ]
            }
        )
    return Response(), 200


@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
