## AI-Powered Incident Alert System Automation

- This project provides an automated incident response system built with Python and Flask. 
- It listens for incoming incident alerts, uses a knowledge base to determine severity and suggest remedies. 
- It then undertakes a bunch of alert processes like creating dedicated Slack channels, notifying stakeholders, and generating GitHub issues for tracking. 
- It also adds the response in a sqlite db.

<br>

<img src="images/architecture.jpg" alt="Incident Automation System Architecture" width="400">

<br>

# Knowledge Base Pipeline
Uses a sentence-transformer model and a FAISS vector index to intelligently find similar past incidents and determine the severity and a suggested remedy.
- The incident's description is passed to the Knowledge Base, which encodes it into a vector.
- FAISS performs a high-speed similarity search on the vector index to find the closest historical incident.
- The system retrieves the severity and remedy from the best match found in the knowledge base.