"""
Diagram Generator Module

This module provides comprehensive C4 diagram generation capabilities including:
- Context diagrams (highest level system overview)
- Container diagrams (application architecture)
- Component diagrams (detailed component relationships)
- Multiple output formats (PlantUML, Mermaid, SVG)
"""

from .c4_models import (
    C4Element,
    C4Person,
    C4System,
    C4Container,
    C4Component,
    C4Relationship,
    C4Diagram,
    DiagramType,
    ElementType,
    RelationshipType
)

from .diagram_formatters import (
    DiagramFormatter,
    PlantUMLFormatter,
    MermaidFormatter,
    SVGFormatter
)

from .c4_generator import (
    C4DiagramGenerator,
    DiagramGenerationConfig,
    DiagramTheme
)

from .diagram_optimizer import (
    DiagramOptimizer,
    OptimizationConfig,
    LayoutStrategy
)

__all__ = [
    # Core Models
    'C4Element',
    'C4Person',
    'C4System',
    'C4Container',
    'C4Component',
    'C4Relationship',
    'C4Diagram',
    'DiagramType',
    'ElementType',
    'RelationshipType',
    
    # Formatters
    'DiagramFormatter',
    'PlantUMLFormatter',
    'MermaidFormatter',
    'SVGFormatter',
    
    # Generator
    'C4DiagramGenerator',
    'DiagramGenerationConfig',
    'DiagramTheme',
    
    # Optimizer
    'DiagramOptimizer',
    'OptimizationConfig',
    'LayoutStrategy'
]
