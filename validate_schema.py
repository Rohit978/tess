
import json
from src.core.schemas import TessAction
from pydantic import TypeAdapter, ValidationError

def test_validation():
    # Test Converter Action (Correct)
    valid_data = {
        "action": "converter_op",
        "sub_action": "images_to_pdf",
        "source_paths": ["test.jpg"],
        "output_filename": "out.pdf"
    }
    
    # Test Research Action (Correct)
    valid_research = {
        "action": "research_op",
        "topic": "AI History",
        "depth": 3
    }

    # Test Converter Action (Wrong sub_action) -> Should fail
    invalid_data = {
        "action": "converter_op",
        "sub_action": "convert",  # Invalid
        "source_paths": "test.jpg"
    }
    
    adapter = TypeAdapter(TessAction)
    
    try:
        adapter.validate_python(valid_data)
        print("Valid Converter: PASS")
    except ValidationError as e:
        print(f"Valid Converter: FAIL - {e}")

    try:
        adapter.validate_python(valid_research)
        print("Valid Research: PASS")
    except ValidationError as e:
        print(f"Valid Research: FAIL - {e}")
        
    try:
        adapter.validate_python(invalid_data)
        print("Invalid Converter: FAIL (Should have raised error but didn't)")
    except ValidationError as e:
        print("Invalid Converter: PASS (Correctly raised error)")

if __name__ == "__main__":
    test_validation()
