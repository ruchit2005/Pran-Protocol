
import os
import sys
import importlib.util

print(f"Python: {sys.executable}")

try:
    import langchain_experimental
    print(f"langchain_experimental path: {langchain_experimental.__file__}")
    
    # helper to find module
    spec = importlib.util.find_spec("langchain_experimental.text_splitter")
    if spec:
        print(f"text_splitter found: {spec.origin}")
    else:
        print("text_splitter submodule NOT found via find_spec")

    from langchain_experimental import text_splitter
    if hasattr(text_splitter, 'SemanticChunker'):
        print("SemanticChunker FOUND in text_splitter")
    else:
        print("SemanticChunker NOT FOUND in text_splitter")
        print(f"Available attributes: {dir(text_splitter)}")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
