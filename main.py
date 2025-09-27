from flask import Flask, request, jsonify
import os
import logging
import requests

from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine('sqlite:///incidents.db', connect_args={'check_same_thread': False})
Base = declarative_base()

class Incident(Base):
    __tablename__ = 'incidents'
    incident_id = Column(String, primary_key=True)
    type = Column(String)
    description = Column(Text)
    severity = Column(String)
    remedy = Column(Text)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

from slack_integration import post_summary_to_slack, create_incident_channel, invite_users_to_channel
from knowledge_base import find_solution_and_severity

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

def save_incident(incident, severity, remedy):
    session = Session()
    record = Incident(
        incident_id=incident.get('incident_id'),
        type=incident.get('type'),
        description=incident.get('description'),
        severity=severity,
        remedy=remedy
    )
    session.merge(record)
    session.commit()
    session.close()
    logging.info(f"Incident {incident.get('incident_id')} saved to database.")

def create_github_issue(incident, severity, remedy):
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    REPO = 'keyur18j/incident-automation'
    if not GITHUB_TOKEN or not REPO:
        logging.warning("GITHUB_TOKEN or GITHUB_REPO not set. Skipping issue creation.")
        return None
        
    url = f'https://api.github.com/repos/{REPO}/issues'
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    title = f"[Incident {incident['incident_id']}] {incident['type']} | Severity: {severity}"
    body = (
        f"**Description:** {incident['description']}\n\n"
        f"**Determined Severity:** {severity}\n\n"
        f"**Suggested Remedy:** {remedy}\n"
    )
    data = {"title": title, "body": body, "labels": ["incident", severity.lower()]}
    
    try:
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        issue_url = resp.json()["html_url"]
        logging.info(f"Successfully created GitHub issue: {issue_url}")
        return issue_url
    except requests.RequestException as e:
        logging.error(f"Failed to create GitHub issue: {e.response.text if e.response else e}")
        return None

def process_incident(incident_data):
    incident_id = incident_data.get("incident_id")
    incident_description = incident_data.get("description")
    
    kb_result = find_solution_and_severity(incident_description)
    severity = kb_result.get("severity", "Unknown")
    remedy = kb_result.get("solution", "No suggestion available.")
    logging.info(f"Incident {incident_id} classified as {severity} with remedy: {remedy}")
    
    save_incident(incident_data, severity, remedy)
    
    full_incident_details = {**incident_data, "determined_severity": severity, "remediation_step": remedy}
    
    try:
        summary_channel_id = "C09HWJU73EV" 
        post_summary_to_slack(summary_channel_id, full_incident_details)
        new_channel_name = f"incident-{incident_id}"
        new_channel_id = create_incident_channel(new_channel_name)
        if new_channel_id:
            logging.info(f"Successfully created channel: #{new_channel_name} ({new_channel_id})")
            stakeholder_user_ids = ["U05M34FLJ04"] 
            invite_users_to_channel(new_channel_id, stakeholder_user_ids)
    except Exception as e:
        logging.error(f"Failed during Slack integration: {e}")

    github_issue_url = create_github_issue(incident_data, severity, remedy)
    
    return True, severity, remedy, github_issue_url

@app.route('/incident/alert', methods=['POST'])
def receive_incident_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_fields = ["incident_id", "type", "description"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    logging.info(f"Incident received: {data}")
    
    success, severity, remedy, github_issue_url = process_incident(data)
    
    if success:
        response_data = {
            "status": "Incident processed successfully",
            "incident_id": data.get("incident_id"),
            "classified_severity": severity,
            "suggested_remedy": remedy,
            "github_issue_url": github_issue_url
        }
        return jsonify(response_data), 200
    else:
        return jsonify({"status": "Incident received but failed during processing"}), 500

@app.route('/incident/list', methods=['GET'])
def list_incidents_route():
    session = Session()
    incidents = session.query(Incident).all()
    session.close()
    return jsonify([{
        "incident_id": i.incident_id, "type": i.type, "description": i.description,
        "severity": i.severity, "remedy": i.remedy
    } for i in incidents])

if __name__ == '__main__':
    app.run(port=5000, debug=True)