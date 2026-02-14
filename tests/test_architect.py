
import pytest
import os
import shutil
from src.core.architect import Architect

@pytest.fixture
def architect():
    # Use a temp workspace for tests
    test_workspace = "test_workspace"
    arch = Architect(workspace_dir=test_workspace)
    yield arch
    # Cleanup
    if os.path.exists(test_workspace):
        shutil.rmtree(test_workspace)

def test_write_script(architect):
    filename = "hello_world.py"
    content = "print('Hello Test')"
    
    msg = architect.write_script(filename, content)
    
    assert "saved successfully" in msg
    assert os.path.exists(os.path.join(architect.scripts_dir, filename))
    
    with open(os.path.join(architect.scripts_dir, filename), 'r') as f:
        assert f.read() == content

def test_execute_script(architect):
    filename = "calc.py"
    content = "print(5 + 5)"
    architect.write_script(filename, content)
    
    output = architect.execute_script(filename)
    
    assert "10" in output
    assert "STDOUT" in output

def test_execute_script_error(architect):
    filename = "error.py"
    content = "print(1/0)"
    architect.write_script(filename, content)
    
    output = architect.execute_script(filename)
    
    assert "ZeroDivisionError" in output
    assert "STDERR" in output

def test_execute_missing_script(architect):
    output = architect.execute_script("non_existent.py")
    assert "not found" in output
