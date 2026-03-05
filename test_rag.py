import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tess_cli.core.config import Config
from tess_cli.core.brain import Brain
from tess_cli.core.skill_loader import SkillLoader

# 1. Initialize Brain 
brain = Brain()

# 2. Load skills
loader = SkillLoader(brain)
loader.load_skills()

# 3. Find RAG Skill
rag_skill = loader.skills.get("Local Document Whisperer (RAG)")

if not rag_skill:
    print("Failed to load RAG Skill.")
    sys.exit(1)

print("RAG Skill loaded successfully.")

# 4. Mock Action: Index the document
index_action = {
    "action": "rag_op",
    "sub_action": "index",
    "path": "mock_document.txt"
}

print(f"\n--- Indexing ---")
print(rag_skill.execute(index_action, {}))

# 5. Mock Action: Query the document
query_action = {
    "action": "rag_op",
    "sub_action": "query",
    "query": "What is the secret password to the coffee lab?"
}

print(f"\n--- Querying ---")
print(rag_skill.execute(query_action, {}))
