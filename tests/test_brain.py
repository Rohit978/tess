
import pytest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.brain import Brain
from src.core.schemas import TessAction

@pytest.fixture
def mock_brain():
    with patch('src.core.brain.Config') as MockConfig, \
         patch('src.core.brain.Groq') as MockGroq:
        
        MockConfig.GROQ_API_KEY = "dummy_key"
        MockConfig.LLM_PROVIDER = "groq"
        MockConfig.LLM_MODEL = "llama-3.3-70b"
        
        # Configure the MockGroq to return a specific mock instance when called
        mock_client_instance = MagicMock()
        MockGroq.return_value = mock_client_instance
        
        brain = Brain()
        # brain.client is now already mock_client_instance because Brain.__init__ called Groq()
        # Ensure we have a handle to it attached to the brain object for tests to configure
        brain.mock_groq_client = mock_client_instance 
        
        return brain

def test_generate_command_valid_json(mock_brain):
    """Test that valid JSON from LLM returns a valid ID"""
    
    # Mock LLM Response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "action": "launch_app",
        "app_name": "Calculator",
        "reason": "User asked for it"
    })
    mock_brain.mock_groq_client.chat.completions.create.return_value = mock_response
    
    result = mock_brain.generate_command("Open Calculator")
    
    # Assert
    assert result["action"] == "launch_app"
    assert result["app_name"] == "Calculator"
    assert result["is_dangerous"] is False # Default

def test_generate_command_invalid_json(mock_brain):
    """Test malformed JSON handling"""
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Not JSON"
    mock_brain.mock_groq_client.chat.completions.create.return_value = mock_response
    
    result = mock_brain.generate_command("Do something")
    
    assert result["action"] == "error"
    assert "Failed to parse" in result["reason"]

def test_generate_command_schema_violation(mock_brain):
    """Test valid JSON but invalid Schema (missing required field)"""
    
    mock_response = MagicMock()
    # Missing 'app_name' for launch_app
    mock_response.choices[0].message.content = json.dumps({
        "action": "launch_app",
        "reason": "Missing app name"
    })
    mock_brain.mock_groq_client.chat.completions.create.return_value = mock_response
    
    result = mock_brain.generate_command("Open something")
    
    # Brain catches Pydantic ValidationError and returns error action
    assert result["action"] == "error"
    assert "Validation Failed" in result["reason"]

def test_memory_context_injection(mock_brain):
    """Test that memory is searched and injected"""
    
    mock_knowledge = MagicMock()
    mock_knowledge.search_memory.return_value = "Past conversation about python"
    
    mock_brain.knowledge_db = mock_knowledge
    
    # Mock LLM
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({"action": "error", "reason": "test"})
    mock_brain.mock_groq_client.chat.completions.create.return_value = mock_response
    
    mock_brain.generate_command("Remember python?")
    
    # Check if search_memory was called
    mock_knowledge.search_memory.assert_called_once()
    
    # Check if context was added to system prompt
    call_args = mock_brain.mock_groq_client.chat.completions.create.call_args
    messages = call_args.kwargs['messages']
    system_msg = messages[0]['content']
    
    assert "Past conversation about python" in system_msg

def test_provider_switching(mock_brain):
    """Test that Brain switches to DeepSeek after exhausting Groq keys"""
    
    # Setup multiple keys
    mock_brain.api_keys = ["key1", "key2"]
    
    # Mock specific RateLimit error for Groq
    error_response = Exception("429 Rate Limit")
    mock_brain.mock_groq_client.chat.completions.create.side_effect = error_response
    
    # Setup DeepSeek mock
    mock_brain.deepseek_client = MagicMock()
    deepseek_response = MagicMock()
    deepseek_response.choices[0].message.content = json.dumps({
        "action": "launch_app", 
        "app_name": "Notepad",
        "reason": "Backup worked"
    })
    mock_brain.deepseek_client.chat.completions.create.return_value = deepseek_response
    
    # Run
    result = mock_brain.generate_command("Open Notepad")
    
    # Assert
    assert mock_brain.provider == "deepseek"
    assert result["action"] == "launch_app"
    # Should have called Groq twice (key1, key2) then DeepSeek
    assert mock_brain.mock_groq_client.chat.completions.create.call_count >= 2
    mock_brain.deepseek_client.chat.completions.create.assert_called_once()
