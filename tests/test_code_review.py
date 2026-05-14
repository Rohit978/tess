import pytest
from tess_cli.skills.code_review_skill import CodeReviewSkill

class DummyBrain:
    def _parse_json(self, text):
        import json
        return json.loads(text)

def test_code_review_markdown_rendering():
    skill = CodeReviewSkill(brain=DummyBrain())
    
    mock_data = {
        "summary": "This code has some critical issues.",
        "bugs": [
            {"line": 42, "severity": "HIGH", "issue": "Missing None check", "fix": "Add if not user:"}
        ],
        "security": [
            {"line": 10, "severity": "CRITICAL", "issue": "Hardcoded API key", "fix": "Use os.getenv()"}
        ],
        "performance": [],
        "style": [
            {"line": 100, "issue": "Function is too long"}
        ]
    }
    
    md = skill._render_markdown(mock_data, "test.py")
    
    assert "🔍 TESS Code Review — test.py" in md
    assert "This code has some critical issues." in md
    assert "## 🐛 Bugs (1)" in md
    assert "Missing None check" in md
    assert "## 🔒 Security (1)" in md
    assert "Hardcoded API key" in md
    assert "## ⚡ Performance (0)" in md
    assert "Function is too long" in md
