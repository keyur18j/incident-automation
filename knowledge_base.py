import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_PATH = "kb.index"
DATA_PATH = "kb_data.pkl"

def build_kb():
    print("Building Knowledge Base with severity...")
    kb_entries = [
        {
            "problem": "Database connection error is causing API timeouts.",
            "solution": "Restart the primary database service (db-prod-01).",
            "severity": "High"
        },
        {
            "problem": "High CPU usage on web-server-03.",
            "solution": "Scale up the web server fleet by one instance.",
            "severity": "Medium"
        },
        {
            "problem": "Users are reporting slow page loads after the last deployment.",
            "solution": "Roll back the production deployment to the previous version.",
            "severity": "High"
        },
        {
            "problem": "The database is reporting 'disk full' errors.",
            "solution": "Check the disk space on the database server.",
            "severity": "Medium"
        },
        {
            "problem": "Credit card transactions are failing with a 500 error.",
            "solution": "The upstream payment gateway service is down. Escalate to the vendor.",
            "severity": "Critical"
        }
    ]
    
    problems = [entry["problem"] for entry in kb_entries]
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    problem_embeddings = model.encode(problems)
    
    index = faiss.IndexFlatL2(384)
    index.add(np.array(problem_embeddings, dtype=np.float32))
    
    faiss.write_index(index, INDEX_PATH)
    with open(DATA_PATH, "wb") as f:
        pickle.dump(kb_entries, f)
    
    print("Knowledge Base build complete!")
    return index, kb_entries

def load_kb():
    print("Loading existing Knowledge Base...")
    index = faiss.read_index(INDEX_PATH)
    with open(DATA_PATH, "rb") as f:
        kb_entries = pickle.load(f)
    return index, kb_entries

if os.path.exists(INDEX_PATH) and os.path.exists(DATA_PATH):
    try:
        faiss_index, kb_entries = load_kb()
        if not isinstance(kb_entries[0], dict):
             raise ValueError("Old KB format detected.")
    except (pickle.UnpicklingError, ValueError):
        print("Incompatible or old KB format detected. Rebuilding...")
        faiss_index, kb_entries = build_kb()
else:
    faiss_index, kb_entries = build_kb()

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def find_solution_and_severity(incident_description, k=1):
    query_vector = embedding_model.encode([incident_description])
    D, I = faiss_index.search(np.array(query_vector, dtype=np.float32), k)
    
    if not I.size:
        return {"solution": "No solution found.", "severity": "Unknown"}
        
    best_match_index = I[0][0]
    return kb_entries[best_match_index]