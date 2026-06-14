import os
import sys
import pytest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tess_cli.core.cognitive_brains import ReflexBrain
from tess_cli.core.event_bus import event_bus
from tess_cli.core.cognitive_layers import MemoryCentricCore, ProceduralLearner, CognitiveRouter
from tess_cli.core.brain import Brain

class TestReflexBrain:
    """Test deterministic fast-path cognition for obvious commands."""

    def test_open_chrome_routes_to_launch_app(self):
        result = ReflexBrain().generate_command("open chrome")
        assert result["action"] == "launch_app"
        assert result["app_name"] == "chrome"

    def test_screenshot_routes_without_llm(self):
        result = ReflexBrain().generate_command("screenshot")
        assert result["action"] == "system_control"
        assert result["sub_action"] == "screenshot"

    def test_unknown_command_falls_through(self):
        assert ReflexBrain().generate_command("plan my whole week in detail") is None


class TestEventBus:
    """Test Phase 2 — Event-Driven Cognition."""

    def test_event_bus_sync_delivery(self):
        received_events = []
        def handler(data):
            received_events.append(data)

        event_bus.subscribe("test_event", handler)
        event_bus.publish_sync("test_event", "hello")
        
        assert "hello" in received_events
        event_bus.unsubscribe("test_event", handler)

    def test_event_bus_async_delivery(self):
        received_events = []
        def handler(data):
            received_events.append(data)

        event_bus.subscribe("async_event", handler)
        event_bus.publish("async_event", "world")
        
        # Allow async queue to process
        time.sleep(0.1)
        
        assert "world" in received_events
        event_bus.unsubscribe("async_event", handler)


class TestCognitiveLayersAndRouter:
    """Test Phase 3 & 4 — Replace Static Prompting & Cognitive Layers."""

    @pytest.fixture
    def mock_brain(self):
        # Stub a basic Brain instance
        class MockBrain:
            def __init__(self):
                self.user_id = "test_user"
                self.personality = "casual"
                self.reflex_brain = ReflexBrain()
                self.history = [{"role": "system", "content": "base"}]
        return MockBrain()

    def test_cognitive_routing_classification(self, mock_brain):
        router = CognitiveRouter(mock_brain)
        
        # Should classify reflex queries
        assert router.route("open chrome") == "reflex"
        assert router.route("screenshot") == "reflex"
        
        # Should classify planner queries
        assert router.route("plan a weekend trip to Paris") == "planner"
        assert router.route("scaffold a new React application") == "planner"
        
        # Should fallback to reasoner
        assert router.route("who are you?") == "reasoner"

    def test_temporary_cognition_context(self, mock_brain):
        router = CognitiveRouter(mock_brain)
        
        reflex_ctx = router.get_temporary_cognition_context("reflex", "system_prompt")
        assert "REFLEX" in reflex_ctx
        assert "deterministic action" in reflex_ctx

        planner_ctx = router.get_temporary_cognition_context("planner", "system_prompt")
        assert "PLANNER" in planner_ctx
        assert "Structured decomposition" in planner_ctx


class TestMemoryAndProceduralLearning:
    """Test Phase 5 & 6 — Memory-Centric Architecture & Procedural Learning."""

    @pytest.fixture
    def clean_memory_core(self):
        core = MemoryCentricCore(user_id="test_suite_user")
        # Ensure clean state
        core.data = {
            "structured_memory": {},
            "procedural_memory": [],
            "episodic_memory": []
        }
        core.save()
        return core

    def test_structured_memory_facts(self, clean_memory_core):
        clean_memory_core.store_fact("favorite_color", "blue")
        
        # Reload to test persistence
        loaded_core = MemoryCentricCore(user_id="test_suite_user")
        assert loaded_core.get_fact("favorite_color") == "blue"

    def test_procedural_habit_compilation_and_execution(self, clean_memory_core):
        learner = ProceduralLearner(clean_memory_core)
        
        # Simulate repeating the same sequence 3 times (success episodes)
        query = "prepare release package"
        steps_run = [
            {"action": "execute_command", "command": "pytest"},
            {"action": "execute_command", "command": "python setup.py sdist"}
        ]
        
        for _ in range(3):
            learner.record_query(query)
            for step in steps_run:
                # Dispatch commands simulated via event_bus subscription
                event_bus.publish_sync("command_executed", step)
            learner.commit_episode(success=True)

        # Habit compilation should occur after 3 trials
        assert len(clean_memory_core.data["procedural_memory"]) == 1
        habit = learner.find_learned_workflow(query)
        assert habit is not None
        assert habit["trigger_phrases"] == [query.lower()]
        assert len(habit["steps"]) == 2
        assert habit["steps"][0]["command"] == "pytest"


class TestRAGSessionEngine:
    """Test RAG and Daily Journaling & Preference Extraction on shutdown."""

    def test_session_events_initialization_and_logging(self):
        # Initialize Brain
        brain = Brain(user_id="test_suite_rag_user")
        assert hasattr(brain, "session_events")
        assert isinstance(brain.session_events, list)

        # Trigger user queries and actions
        brain.update_history("user", "Hello Tess, I love programming in Python!")
        brain.update_history("assistant", '{"action": "code_op", "sub_action": "write"}')
        brain.update_history("system", "Result of code_op: file written successfully")

        # Verify tracking
        assert len(brain.session_events) == 3
        assert "User Query: Hello Tess, I love programming in Python!" in brain.session_events
        assert "TESS Action: code_op" in brain.session_events
        assert "System: Result of code_op: file written successfully" in brain.session_events

    def test_summarize_and_save_session(self, monkeypatch):
        brain = Brain(user_id="test_suite_rag_user")
        brain.session_events = [
            "User Query: I prefer dark theme",
            "TESS Action: sysadmin_op"
        ]

        summary_called = False
        facts_called = False

        def mock_request_completion(messages, json_mode=False, temperature=0.7):
            nonlocal summary_called, facts_called
            prompt_content = messages[-1]["content"]
            if "meta-cognition analyzer" in prompt_content:
                summary_called = True
                return "The user expressed preference for dark theme and asked for sysadmin tasks."
            elif "extract any concrete facts" in prompt_content:
                facts_called = True
                return '["prefers dark theme"]'
            return None

        monkeypatch.setattr(brain, "request_completion", mock_request_completion)

        # Mock knowledge_db store_memory
        class MockKB:
            def __init__(self):
                self.memories = []
            def store_memory(self, text, metadata=None):
                self.memories.append((text, metadata))
                return True

        brain.knowledge_db = MockKB()

        # Run summarization
        brain.summarize_and_save_session()

        assert summary_called
        assert facts_called
        assert len(brain.knowledge_db.memories) == 1
        assert "user activities: The user expressed preference for dark theme" in brain.knowledge_db.memories[0][0]

        # Verify fact is learned in UserProfile
        from tess_cli.core.user_profile import UserProfile
        profile = UserProfile()
        assert any("prefers dark theme" in f["text"] for f in profile.data["facts"])


class TestVisualTimelineAndClipboard:
    """Test Visual Timeline (Temporal RAG) and Clipboard Synchronization."""

    def test_visual_timeline_indexing(self, monkeypatch):
        from tess_cli.core.visual_timeline import VisualTimelineTracker
        
        # Setup mocks
        def mock_active_app(self):
            tracker.running = False
            return "TestApp"
        monkeypatch.setattr("tess_cli.core.desktop_vision.DesktopVisionController.active_app", mock_active_app)
        
        class MockWindow:
            def descendants(self):
                class MockCtrl:
                    def window_text(self):
                        return "Mock UIA element text content"
                return [MockCtrl()]

        # Mock UIA window lookup
        monkeypatch.setattr("tess_cli.core.os_controller.OSController._get_window", lambda self, app=None: MockWindow())

        class MockKB:
            def __init__(self):
                self.entries = []
            def store_memory(self, text, metadata=None):
                self.entries.append((text, metadata))
                return True

        brain = Brain(user_id="test_suite_timeline_user")
        kb = MockKB()
        
        # Test tracker
        tracker = VisualTimelineTracker(brain, kb, interval_sec=1)
        tracker.running = True
        
        # Run one loop iteration manually
        try:
            tracker._run_loop()
        except TypeError:
            # Catch time.sleep mock if triggered (though running flag set to True and loop ends after manual run if we stop it inside callback or manually, but tracker uses a simple while loop which might keep running unless we set tracker.running = False during UIA)
            pass

        assert len(kb.entries) == 1
        assert "Active Window: TestApp" in kb.entries[0][0]
        assert "Content: Mock UIA element text content" in kb.entries[0][0]
        assert kb.entries[0][1]["type"] == "screen_snapshot"
        assert kb.entries[0][1]["active_window"] == "TestApp"

    def test_clipboard_sync_monitor(self, monkeypatch):
        from tess_cli.core.clipboard_sync import ClipboardSyncMonitor
        import subprocess

        clipboard_text = "Hello from PC clipboard"
        set_text = ""

        # Mock subprocess.run for Get-Clipboard and Set-Clipboard
        def mock_run(cmd, capture_output=False, text=False, timeout=5, creationflags=0, check=False):
            nonlocal set_text
            class MockResult:
                def __init__(self, stdout):
                    self.stdout = stdout
            # Check command
            if "Get-Clipboard" in cmd:
                return MockResult(clipboard_text)
            elif "Set-Clipboard" in cmd[-1]:  # script is the last argument
                # Extract text base64 encoded
                import base64
                b64_part = cmd[-1].split("'")[1]
                set_text = base64.b64decode(b64_part.encode('utf-8')).decode('utf-8')
                return MockResult("")
            return MockResult("")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Callbacks
        received_text = ""
        def on_change(text):
            nonlocal received_text
            received_text = text

        # Mock sys.platform to be win32 to test Windows path
        monkeypatch.setattr("sys.platform", "win32")

        monitor = ClipboardSyncMonitor(on_change)
        
        # Verify get_clipboard
        assert monitor.get_clipboard() == clipboard_text

        # Verify set_clipboard
        monitor.set_clipboard("Updated Clipboard Content")
        assert set_text == "Updated Clipboard Content"

        # Verify run_loop checks for changes
        monitor.running = True
        
        # Modify loop so it runs exactly once
        def stop_after_one_run(text):
            on_change(text)
            monitor.running = False
            
        monitor.on_change_callback = stop_after_one_run
        monitor._run_loop() # Manual run of single iteration
        
        # Since last_clipboard is different from clipboard_text, callback should trigger
        assert received_text == clipboard_text


