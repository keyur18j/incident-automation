from flask import Flask, request, jsonify
import os
import requests

from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine('sqlite:///incidents.db')
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


def create_github_issue(incident, severity, remedy):
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  
    REPO = 'keyur18j/incident-automation'        
    url = f'https://api.github.com/repos/{REPO}/issues'
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    title = f"[Incident {incident['incident_id']}] {incident['type']} | Severity: {severity}"
    body = (
        f"**Description:** {incident['description']}\n"
        f"**Severity:** {severity}\n"
        f"**Suggested Remedy:** {remedy}\n"
    )
    data = {"title": title, "body": body}
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 201:
        return resp.json()["html_url"]
    else:
        print("Failed to create GitHub issue:", resp.content)
        return None



app = Flask(__name__)


HIGH_SEVERITY_KEYWORDS = ["critical", "outage", "unresponsive", "security breach", "data loss", "down"]
MEDIUM_SEVERITY_KEYWORDS = ["slow", "degraded", "error", "warning", "intermittent", "failure"]

REMEDY_MAP = {
    "database": "Check database server status, logs, and running queries. Consider restarting the service or failing over to a replica.",
    "security breach": "IMMEDIATE ACTION: Isolate the affected system from the network. Initiate security incident response protocol. Reset all credentials.",
    "api": "Check the API gateway logs and the health of the underlying microservices. Review recent deployments for potential breaking changes.",
    "login": "Investigate the authentication service. Check for credential validation errors and service health.",
    "slow": "Analyze server CPU, memory, and I/O usage. Check for inefficient queries or resource-intensive processes.",
    "unresponsive": "Verify server connectivity and health. Attempt to SSH into the machine. If unreachable, a hard reboot may be required."
}

def classify_severity(incident_data):
    """
    Classifies incident severity based on keywords in its type and description.
    """
    search_text = (incident_data.get("type", "") + " " + incident_data.get("description", "")).lower()

    if any(keyword in search_text for keyword in HIGH_SEVERITY_KEYWORDS):
        return "High"
    
    if any(keyword in search_text for keyword in MEDIUM_SEVERITY_KEYWORDS):
        return "Medium"
        
    return "Low"

def get_remedy(incident_data, severity):
    """
    Suggests a remedy based on keywords and severity.
    """
    search_text = (incident_data.get("type", "") + " " + incident_data.get("description", "")).lower()

    for keyword, remedy in REMEDY_MAP.items():
        if keyword in search_text:
            return remedy

    if severity == "High":
        return "Escalate to the on-call Level 2 engineer immediately. Open a war room/bridge call for coordination."
    if severity == "Medium":
        return "Assign to the relevant team for investigation within the next business hour. Monitor for further degradation."
    
    return "Create a ticket in the backlog for the responsible team. No immediate action required."


@app.route('/incident/alert', methods=['POST'])
def receive_incident():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_fields = ["incident_id", "type", "description"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    severity = classify_severity(data)
    
    remedy = get_remedy(data, severity)

    print(f"Incident {data.get('incident_id')} classified as {severity}.")
    save_incident(data, severity, remedy)
    response_data = {
        "status": "Incident processed successfully",
        "incident_id": data.get("incident_id"),
        "classified_severity": severity,
        "suggested_remedy": remedy
    }
    
    github_issue_url = create_github_issue(data, severity, remedy)
    if github_issue_url:
        response_data["github_issue_url"] = github_issue_url
    else:
        response_data["github_issue_url"] = None

    return jsonify(response_data), 200

@app.route('/incident/list', methods=['GET'])
def list_incidents():
    session = Session()
    incidents = session.query(Incident).all()
    session.close()
    return jsonify([
        {
            "incident_id": i.incident_id,
            "type": i.type,
            "description": i.description,
            "severity": i.severity,
            "remedy": i.remedy,
        } for i in incidents
    ])


if __name__ == '__main__':
    app.run(port=5000, debug=True)