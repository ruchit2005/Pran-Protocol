
import sys
import pkg_resources

print(f"Python executable: {sys.executable}")
print(f"Python paths: {sys.path}")

try:
    import langchain_experimental
    print(f"langchain_experimental file: {langchain_experimental.__file__}")
    from langchain_experimental import text_splitter
    print(f"text_splitter location: {text_splitter}")
    from langchain_experimental.text_splitter import SemanticChunker
    print("Successfully imported SemanticChunker")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")

try:
    version = pkg_resources.get_distribution("langchain-experimental").version
    print(f"langchain-experimental version: {version}")
except Exception as e:
    print(f"Could not get version: {e}")
