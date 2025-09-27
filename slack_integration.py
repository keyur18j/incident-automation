import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

try:
    slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
except KeyError:
    logging.error("SLACK_BOT_TOKEN environment variable not set. Please set it.")
    slack_client = None

def post_summary_to_slack(channel_id, incident_details):
    if not slack_client:
        logging.error("Slack client not initialized.")
        return

    severity = incident_details.get('determined_severity', 'Unknown')
    incident_id = incident_details.get('incident_id')
    description = incident_details.get('description')
    remediation = incident_details.get('remediation_step')

    try:
        result = slack_client.chat_postMessage(
            channel=channel_id,
            text=f"New Incident Alert: {description}",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"New Incident Alert: #{incident_id}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Severity:*\n*{severity}*"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{incident_details.get('type')}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{description}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested First Step:*\n`{remediation}`"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"A dedicated channel has been created: #incident-{incident_id}"
                        }
                    ]
                }
            ]
        )
        logging.info(f"Posted summary to channel {channel_id}: {result['ts']}")
    except SlackApiError as e:
        logging.error(f"Error posting message to Slack: {e.response['error']}")
        raise

def create_incident_channel(channel_name):
    if not slack_client:
        logging.error("Slack client not initialized.")
        return None
    
    try:
        response = slack_client.conversations_create(name=channel_name.lower(), is_private=False)
        channel_id = response["channel"]["id"]
        return channel_id
    except SlackApiError as e:
        if e.response["error"] == "name_taken":
            logging.warning(f"Channel #{channel_name} already exists.")
            response = slack_client.conversations_list()
            for ch in response['channels']:
                if ch['name'] == channel_name.lower():
                    return ch['id']
        else:
            logging.error(f"Error creating channel: {e.response['error']}")
            raise
    return None

def invite_users_to_channel(channel_id, user_ids):
    if not slack_client or not user_ids:
        logging.error("Slack client not initialized or no user IDs provided.")
        return

    try:
        response = slack_client.conversations_invite(channel=channel_id, users=user_ids)
        logging.info(f"Invited {user_ids} to channel {channel_id}")
    except SlackApiError as e:
        if e.response["error"] == 'already_in_channel':
            logging.warning(f"Some users were already in channel {channel_id}.")
        else:
            logging.error(f"Error inviting users: {e.response['error']}")
            raise