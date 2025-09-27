from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Start of Classification & Remedy Logic ---

# Define keywords for severity classification
HIGH_SEVERITY_KEYWORDS = ["critical", "outage", "unresponsive", "security breach", "data loss", "down"]
MEDIUM_SEVERITY_KEYWORDS = ["slow", "degraded", "error", "warning", "intermittent", "failure"]

# Define a mapping of keywords to suggested remedies
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

    # 1. Find a specific remedy based on keywords
    for keyword, remedy in REMEDY_MAP.items():
        if keyword in search_text:
            return remedy

    # 2. If no specific keyword is found, provide a default remedy based on severity
    if severity == "High":
        return "Escalate to the on-call Level 2 engineer immediately. Open a war room/bridge call for coordination."
    if severity == "Medium":
        return "Assign to the relevant team for investigation within the next business hour. Monitor for further degradation."
    
    # Default for Low severity
    return "Create a ticket in the backlog for the responsible team. No immediate action required."

# --- End of Classification & Remedy Logic ---


@app.route('/incident/alert', methods=['POST'])
def receive_incident():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_fields = ["incident_id", "type", "description"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    
    # Step 1: Classify the incident's severity
    severity = classify_severity(data)
    
    # Step 2: Get a suggested remedy
    remedy = get_remedy(data, severity)

    print(f"Incident {data.get('incident_id')} classified as {severity}.")
    
    # Step 3: Build the full response object
    response_data = {
        "status": "Incident processed successfully",
        "incident_id": data.get("incident_id"),
        "classified_severity": severity,
        "suggested_remedy": remedy
    }
    
    # Return the full response with a 200 OK status
    return jsonify(response_data), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)