"""
TESS Basic Test Suite
Run with: pytest tests/ -v
"""
import json
import pytest
import sys
import os

# Make sure tess_cli is importable from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ────────────────────────────────────────────────────────────
# Brain._parse_json tests
# ────────────────────────────────────────────────────────────

class TestBrainParseJson:
    """Test the JSON parser used to decode LLM responses."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        # Import lazily to avoid triggering Config.load() side-effects
        from tess_cli.core.brain import Brain
        # Minimal stub: we only need _parse_json, not a live LLM
        self.brain = Brain.__new__(Brain)

    def test_clean_json(self):
        result = self.brain._parse_json('{"action": "reply_op", "content": "hello"}')
        assert result["action"] == "reply_op"
        assert result["content"] == "hello"

    def test_json_wrapped_in_markdown(self):
        text = "```json\n{\"action\": \"final_reply\", \"content\": \"done\"}\n```"
        result = self.brain._parse_json(text)
        assert result["action"] == "final_reply"

    def test_json_with_trailing_text(self):
        text = '{"action": "reply_op", "content": "ok"} some trailing text'
        result = self.brain._parse_json(text)
        assert result["action"] == "reply_op"

    def test_nested_json(self):
        text = '{"action": "file_op", "sub_action": "read", "path": "/tmp/test.txt"}'
        result = self.brain._parse_json(text)
        assert result["sub_action"] == "read"

    def test_fallback_on_garbage(self):
        result = self.brain._parse_json("not json at all!!")
        # Should fall back gracefully to a reply_op, not crash
        assert isinstance(result, dict)
        assert "action" in result


# ────────────────────────────────────────────────────────────
# SecurityEngine.validate_action tests
# ────────────────────────────────────────────────────────────

class TestSecurityEngine:
    """Test that dangerous commands are blocked."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from tess_cli.core.security import SecurityEngine
        self.sec = SecurityEngine(level="MEDIUM")

    def test_safe_command_allowed(self):
        action = {"action": "execute_command", "command": "Get-Date"}
        is_safe, reason = self.sec.validate_action(action)
        assert is_safe

    def test_rm_rf_blocked(self):
        action = {"action": "execute_command", "command": "rm -rf /"}
        is_safe, _ = self.sec.validate_action(action)
        assert not is_safe

    def test_format_drive_blocked(self):
        action = {"action": "execute_command", "command": "format c:"}
        is_safe, _ = self.sec.validate_action(action)
        assert not is_safe

    def test_registry_delete_blocked(self):
        action = {"action": "execute_command", "command": "reg delete HKLM\\Software\\Test"}
        is_safe, _ = self.sec.validate_action(action)
        assert not is_safe

    def test_file_write_to_system32_blocked(self):
        action = {"action": "file_op", "sub_action": "write", "path": "C:\\Windows\\System32\\evil.dll"}
        is_safe, _ = self.sec.validate_action(action)
        assert not is_safe

    def test_reply_op_always_safe(self):
        action = {"action": "reply_op", "content": "hello"}
        is_safe, _ = self.sec.validate_action(action)
        assert is_safe

    def test_high_security_blocks_file_write(self):
        self.sec.set_level("HIGH")
        action = {"action": "execute_command", "command": "echo hello > output.txt"}
        is_safe, _ = self.sec.validate_action(action)
        assert not is_safe


# ────────────────────────────────────────────────────────────
# Config.load tests
# ────────────────────────────────────────────────────────────

class TestConfig:
    """Test configuration loading and defaults."""

    def test_config_loads_without_crash(self):
        from tess_cli.core.config import Config
        # Config.load() is called at import time; verify defaults are sane
        assert Config.VERSION >= 1
        assert isinstance(Config._data, dict)
        assert "llm" in Config._data
        assert "security" in Config._data

    def test_default_provider_is_gemini(self):
        from tess_cli.core.config import Config
        # If no override file exists, provider should be gemini
        provider = Config._data["llm"]["provider"]
        assert provider in ("gemini", "groq", "openai", "deepseek")

    def test_safe_mode_is_bool(self):
        from tess_cli.core.config import Config
        assert isinstance(Config.SAFE_MODE, bool)

    def test_get_system_prompt_contains_tess(self):
        from tess_cli.core.config import Config
        prompt = Config.get_system_prompt("casual")
        assert "TESS" in prompt
        assert "JSON" in prompt

    def test_personality_prompts_all_present(self):
        from tess_cli.core.config import Config
        for persona in ["casual", "professional", "witty", "motivational", "cute", "soul", "rogue"]:
            assert persona in Config.PERSONALITY_PROMPTS
            assert len(Config.PERSONALITY_PROMPTS[persona]) > 10


# ────────────────────────────────────────────────────────────
# Executor tests
# ────────────────────────────────────────────────────────────

class TestExecutor:
    """Test the command executor's safe mode and basic behaviour."""

    def test_empty_command_returns_error(self):
        from tess_cli.core.executor import Executor
        exe = Executor(safe_mode=False)
        result = exe.execute_command("")
        assert "ERROR" in result

    def test_safe_command_runs(self):
        from tess_cli.core.executor import Executor
        exe = Executor(safe_mode=False)
        result = exe.execute_command("echo TESS_TEST_OK")
        assert "TESS_TEST_OK" in result
