import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tess_cli.core.config import Config
from tess_cli.core.brain import Brain
from tess_cli.core.skill_loader import SkillLoader
from tess_cli.core.agent_loop import AgenticLoop
from tess_cli.core.orchestrator import ActionDispatcher

brain = Brain()
loader = SkillLoader(brain)
registry = loader.load_skills()
comps = {'skill_registry': registry}

print("Running AgenticLoop trace on user input...")
query = r'index file at "C:\Users\01roh\Downloads\Dharmansh Dixit.docx"'

# Let's run it step-by-step to see exactly what goes back to the LLM
response = brain.generate_command(query)
print(f"Step 1 Response: {response}")

dispatcher = ActionDispatcher(comps, brain, output_handler=None, skill_registry=registry)
res = dispatcher.dispatch(response)
print(f"Step 1 Execution Result: {res}")

next_query = f"Result of {response.get('action')}: {res}. Next?"
print(f"\nSending back to LLM: {next_query}")
response2 = brain.generate_command(next_query)
print(f"Step 2 Response: {response2}")
