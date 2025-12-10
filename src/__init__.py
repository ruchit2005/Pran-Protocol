"""
Healthcare Multi-Agent Workflow
"""

# Lazy imports to avoid loading heavy dependencies when not needed
# This allows ingest.py and other scripts to import submodules without
# loading the full workflow (which requires OpenAI, Tavily, etc.)

__version__ = "1.0.0"

def __getattr__(name):
    """Lazy load heavy imports only when accessed"""
    if name == "HealthcareWorkflow":
        from .workflow import HealthcareWorkflow
        return HealthcareWorkflow
    elif name == "HealthcareConfig":
        from .config import HealthcareConfig
        return HealthcareConfig
    elif name == "ClassificationSchema":
        from .schemas import ClassificationSchema
        return ClassificationSchema
    elif name == "SymptomCheckerSchema":
        from .schemas import SymptomCheckerSchema
        return SymptomCheckerSchema
    elif name == "GovernmentSchemeSchema":
        from .schemas import GovernmentSchemeSchema
        return GovernmentSchemeSchema
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'HealthcareWorkflow',
    'ClassificationSchema',
    'SymptomCheckerSchema',
    'GovernmentSchemeSchema',
    'HealthcareConfig'
]
