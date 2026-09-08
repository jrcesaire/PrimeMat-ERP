"""
Moteur documentaire — génération de PDF.
"""
from app.core.documents.engine import DocumentEngine, TEMPLATE_DIR
from app.core.documents.context import ContextBuilder

__all__ = ["DocumentEngine", "TEMPLATE_DIR", "ContextBuilder"]
