from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/incident/alert', methods=['POST'])
def receive_incident():
    data = request.get_json()
    required_fields = ["incident_id", "type", "description", "severity"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    valid_severity = ["Low", "Medium", "High"]
    if data["severity"] not in valid_severity:
        return jsonify({"error": "Invalid severity value"}), 400
    print("Incident received:", data)
    return jsonify({"status": "Incident received successfully"}), 200

if __name__ == '__main__':
    app.run(port=5000)
