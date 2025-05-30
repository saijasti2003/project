"""
Architecture Extractor

Performs semantic analysis and relationship extraction to identify C4 architecture components.
"""

from .relationship_extractor import RelationshipExtractor
from .component_classifier import ComponentClassifier
from .architecture_analyzer import ArchitectureAnalyzer
from .semantic_analyzer import SemanticAnalyzer

__all__ = [
    'RelationshipExtractor',
    'ComponentClassifier', 
    'ArchitectureAnalyzer',
    'SemanticAnalyzer'
]
