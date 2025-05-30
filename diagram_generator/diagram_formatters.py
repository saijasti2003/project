"""
Diagram Formatters

This module provides formatters for generating C4 diagrams in different output formats:
- PlantUML for detailed architectural diagrams
- Mermaid for web-friendly interactive diagrams
- SVG for high-quality vector graphics
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .c4_models import C4Diagram, C4Element, C4Relationship, ElementType, RelationshipType, DiagramType
import xml.etree.ElementTree as ET


@dataclass
class FormatterConfig:
    """Configuration for diagram formatters"""
    theme: str = "default"
    show_technology: bool = True
    show_descriptions: bool = True
    max_label_length: int = 30
    include_metadata: bool = True
    custom_styles: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_styles is None:
            self.custom_styles = {}


class DiagramFormatter(ABC):
    """Abstract base class for diagram formatters"""
    
    def __init__(self, config: FormatterConfig = None):
        self.config = config or FormatterConfig()
    
    @abstractmethod
    def format_diagram(self, diagram: C4Diagram) -> str:
        """Format a C4 diagram to the target format"""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this format"""
        pass
    
    def _truncate_text(self, text: str, max_length: int = None) -> str:
        """Truncate text to specified length"""
        max_length = max_length or self.config.max_label_length
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _escape_text(self, text: str) -> str:
        """Escape special characters for the target format"""
        return text


class PlantUMLFormatter(DiagramFormatter):
    """Formatter for PlantUML C4 diagrams"""
    
    def __init__(self, config: FormatterConfig = None):
        super().__init__(config)
        self.element_styles = {
            ElementType.PERSON: "Person",
            ElementType.SYSTEM: "System",
            ElementType.EXTERNAL_SYSTEM: "System_Ext",
            ElementType.CONTAINER: "Container",
            ElementType.COMPONENT: "Component",
            ElementType.DATABASE: "ContainerDb",
            ElementType.QUEUE: "ContainerQueue"
        }
    
    def format_diagram(self, diagram: C4Diagram) -> str:
        """Format diagram as PlantUML C4 syntax"""
        lines = []
        
        # Header
        lines.append("@startuml")
        lines.append("!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml")
        lines.append("!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml")
        lines.append("!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml")
        lines.append("")
        
        # Title
        if diagram.title:
            lines.append(f"title {diagram.title}")
            lines.append("")
        
        # Elements
        for element in diagram.elements:
            lines.append(self._format_element(element))
        
        lines.append("")
        
        # Relationships
        for relationship in diagram.relationships:
            lines.append(self._format_relationship(relationship, diagram))
        
        lines.append("")
        lines.append("@enduml")
        
        return "\\n".join(lines)
    
    def _format_element(self, element: C4Element) -> str:
        """Format a single element"""
        style = self.element_styles.get(element.element_type, "Component")
        
        # Build element definition
        parts = [style, f'"{element.id}"', f'"{element.name}"']
        
        # Add technology if available and configured
        if self.config.show_technology and element.technology:
            parts.append(f'"{element.technology}"')
        elif self.config.show_descriptions and element.description:
            parts.append(f'"{self._truncate_text(element.description)}"')
        
        return f"{parts[0]}({', '.join(parts[1:])})"
    
    def _format_relationship(self, relationship: C4Relationship, diagram: C4Diagram) -> str:
        """Format a relationship"""
        arrow_type = self._get_arrow_type(relationship.relationship_type)
        
        label_parts = []
        if relationship.label:
            label_parts.append(relationship.label)
        if self.config.show_technology and relationship.technology:
            label_parts.append(f"[{relationship.technology}]")
        
        label = " ".join(label_parts) if label_parts else ""
        
        if label:
            return f'Rel("{relationship.source_id}", "{relationship.target_id}", "{label}")'
        else:
            return f'Rel("{relationship.source_id}", "{relationship.target_id}")'
    
    def _get_arrow_type(self, rel_type: RelationshipType) -> str:
        """Get PlantUML arrow type for relationship"""
        arrow_map = {
            RelationshipType.USES: "Rel",
            RelationshipType.DEPENDS_ON: "Rel",
            RelationshipType.INCLUDES: "Rel",
            RelationshipType.EXTENDS: "Rel",
            RelationshipType.IMPLEMENTS: "Rel",
            RelationshipType.CALLS: "Rel",
            RelationshipType.READS_FROM: "Rel",
            RelationshipType.WRITES_TO: "Rel"
        }
        return arrow_map.get(rel_type, "Rel")
    
    def get_file_extension(self) -> str:
        return ".puml"
    
    def _escape_text(self, text: str) -> str:
        """Escape text for PlantUML"""
        return text.replace('"', '\\"')


class MermaidFormatter(DiagramFormatter):
    """Formatter for Mermaid diagrams"""
    
    def __init__(self, config: FormatterConfig = None):
        super().__init__(config)
        self.node_shapes = {
            ElementType.PERSON: "subgraph",
            ElementType.SYSTEM: "subgraph",
            ElementType.EXTERNAL_SYSTEM: "subgraph",
            ElementType.CONTAINER: "subgraph",
            ElementType.COMPONENT: "subgraph",
            ElementType.DATABASE: "[({})]",
            ElementType.QUEUE: "{{{}}}",
            ElementType.FILE_SYSTEM: "[{}]"
        }
    
    def format_diagram(self, diagram: C4Diagram) -> str:
        """Format diagram as Mermaid syntax"""
        lines = []
        
        # Determine diagram type
        if diagram.diagram_type == DiagramType.CONTEXT:
            lines.append("graph TB")
        else:
            lines.append("graph TB")
        
        lines.append("")
        
        # Style definitions
        lines.extend(self._get_style_definitions())
        lines.append("")
        
        # Elements as subgraphs for systems/containers
        systems = self._group_elements_by_system(diagram)
        
        for system_id, system_info in systems.items():
            if system_info['element'].element_type in [ElementType.SYSTEM, ElementType.EXTERNAL_SYSTEM]:
                lines.append(f"  subgraph {system_id}[\"{system_info['element'].name}\"]")
                
                # Add containers in this system
                for container in system_info['containers']:
                    lines.append(f"    {container.id}[\"{container.name}\"]")
                    if container.components:
                        for component in container.components:
                            lines.append(f"    {component.id}[\"{component.name}\"]")
                
                lines.append("  end")
                lines.append("")
        
        # Standalone elements
        for element in diagram.elements:
            if not self._is_contained_element(element, systems):
                shape = self._get_node_shape(element)
                lines.append(f"  {element.id}{shape}")
        
        lines.append("")
        
        # Relationships
        for relationship in diagram.relationships:
            lines.append(self._format_relationship(relationship))
        
        # Apply styles
        lines.append("")
        lines.extend(self._get_element_styles(diagram.elements))
        
        return "\\n".join(lines)
    
    def _group_elements_by_system(self, diagram: C4Diagram) -> Dict[str, Dict]:
        """Group containers and components by their parent system"""
        systems = {}
        
        # First, collect all systems
        for element in diagram.elements:
            if element.element_type in [ElementType.SYSTEM, ElementType.EXTERNAL_SYSTEM]:
                systems[element.id] = {
                    'element': element,
                    'containers': [],
                    'components': []
                }
        
        # Then, assign containers to systems
        for element in diagram.elements:
            if element.element_type == ElementType.CONTAINER:
                system_id = getattr(element, 'system_id', None)
                if system_id and system_id in systems:
                    systems[system_id]['containers'].append(element)
        
        return systems
    
    def _is_contained_element(self, element: C4Element, systems: Dict) -> bool:
        """Check if element is contained within a system subgraph"""
        if element.element_type in [ElementType.SYSTEM, ElementType.EXTERNAL_SYSTEM]:
            return True
        
        if element.element_type == ElementType.CONTAINER:
            system_id = getattr(element, 'system_id', None)
            return system_id in systems
        
        if element.element_type == ElementType.COMPONENT:
            container_id = getattr(element, 'container_id', None)
            if container_id:
                # Check if this component's container is in any system
                for system_info in systems.values():
                    if any(c.id == container_id for c in system_info['containers']):
                        return True
        
        return False
    
    def _get_node_shape(self, element: C4Element) -> str:
        """Get Mermaid node shape for element"""
        shape_template = self.node_shapes.get(element.element_type, "[{}]")
        if "{}" in shape_template:
            return shape_template.format(f'"{element.name}"')
        return f'["{element.name}"]'
    
    def _format_relationship(self, relationship: C4Relationship) -> str:
        """Format a relationship"""
        arrow = self._get_arrow_style(relationship.relationship_type)
        label = relationship.label or relationship.relationship_type.value
        
        return f"  {relationship.source_id} {arrow} {relationship.target_id}"
    
    def _get_arrow_style(self, rel_type: RelationshipType) -> str:
        """Get Mermaid arrow style"""
        arrow_map = {
            RelationshipType.USES: "-->",
            RelationshipType.DEPENDS_ON: "-.->",
            RelationshipType.INCLUDES: "-->",
            RelationshipType.EXTENDS: "-->",
            RelationshipType.IMPLEMENTS: "-.->",
            RelationshipType.CALLS: "-->",
            RelationshipType.READS_FROM: "-->",
            RelationshipType.WRITES_TO: "-->"
        }
        return arrow_map.get(rel_type, "-->")
    
    def _get_style_definitions(self) -> List[str]:
        """Get style definitions for different element types"""
        return [
            "  classDef person fill:#08427b,stroke:#073B6F,stroke-width:2px,color:#fff",
            "  classDef system fill:#1168bd,stroke:#0b4884,stroke-width:2px,color:#fff",
            "  classDef external fill:#999999,stroke:#666666,stroke-width:2px,color:#fff",
            "  classDef container fill:#438dd5,stroke:#2E6295,stroke-width:2px,color:#fff",
            "  classDef component fill:#85bbf0,stroke:#5d82a8,stroke-width:1px,color:#000"
        ]
    
    def _get_element_styles(self, elements: List[C4Element]) -> List[str]:
        """Apply styles to elements"""
        lines = []
        
        class_map = {
            ElementType.PERSON: "person",
            ElementType.SYSTEM: "system",
            ElementType.EXTERNAL_SYSTEM: "external",
            ElementType.CONTAINER: "container",
            ElementType.COMPONENT: "component"
        }
        
        for element in elements:
            css_class = class_map.get(element.element_type, "component")
            lines.append(f"  class {element.id} {css_class}")
        
        return lines
    
    def get_file_extension(self) -> str:
        return ".mmd"
    
    def _escape_text(self, text: str) -> str:
        """Escape text for Mermaid"""
        return text.replace('"', '\\"').replace('[', '\\[').replace(']', '\\]')


class SVGFormatter(DiagramFormatter):
    """Formatter for SVG diagrams"""
    
    def __init__(self, config: FormatterConfig = None):
        super().__init__(config)
        self.width = 800
        self.height = 600
        self.margin = 50
        self.element_width = 120
        self.element_height = 60
        self.colors = {
            ElementType.PERSON: "#08427b",
            ElementType.SYSTEM: "#1168bd",
            ElementType.EXTERNAL_SYSTEM: "#999999",
            ElementType.CONTAINER: "#438dd5",
            ElementType.COMPONENT: "#85bbf0",
            ElementType.DATABASE: "#438dd5",
            ElementType.QUEUE: "#85bbf0"
        }
    
    def format_diagram(self, diagram: C4Diagram) -> str:
        """Format diagram as SVG"""
        # Calculate layout
        positions = self._calculate_layout(diagram)
        
        # Create SVG root
        svg = ET.Element("svg")
        svg.set("width", str(self.width))
        svg.set("height", str(self.height))
        svg.set("xmlns", "http://www.w3.org/2000/svg")
        
        # Add title
        if diagram.title:
            title_elem = ET.SubElement(svg, "title")
            title_elem.text = diagram.title
        
        # Add styles
        self._add_styles(svg)
        
        # Draw relationships first (so they appear behind elements)
        for relationship in diagram.relationships:
            self._draw_relationship(svg, relationship, positions)
        
        # Draw elements
        for element in diagram.elements:
            self._draw_element(svg, element, positions[element.id])
        
        # Convert to string
        return ET.tostring(svg, encoding='unicode')
    
    def _calculate_layout(self, diagram: C4Diagram) -> Dict[str, tuple]:
        """Calculate positions for elements using a simple grid layout"""
        positions = {}
        
        # Simple grid layout
        cols = int((len(diagram.elements) ** 0.5)) + 1
        x_spacing = (self.width - 2 * self.margin) // cols
        y_spacing = (self.height - 2 * self.margin) // ((len(diagram.elements) // cols) + 1)
        
        for i, element in enumerate(diagram.elements):
            col = i % cols
            row = i // cols
            x = self.margin + col * x_spacing + x_spacing // 2
            y = self.margin + row * y_spacing + y_spacing // 2
            positions[element.id] = (x, y)
        
        return positions
    
    def _add_styles(self, svg: ET.Element) -> None:
        """Add CSS styles to SVG"""
        style_text = """
        .element-rect { stroke-width: 2; }
        .element-text { font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }
        .element-title { font-weight: bold; font-size: 14px; }
        .relationship-line { stroke: #666; stroke-width: 2; marker-end: url(#arrowhead); }
        .relationship-text { font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; }
        """
        
        defs = ET.SubElement(svg, "defs")
        style = ET.SubElement(defs, "style")
        style.text = style_text
        
        # Add arrowhead marker
        marker = ET.SubElement(defs, "marker")
        marker.set("id", "arrowhead")
        marker.set("markerWidth", "10")
        marker.set("markerHeight", "7")
        marker.set("refX", "9")
        marker.set("refY", "3.5")
        marker.set("orient", "auto")
        
        polygon = ET.SubElement(marker, "polygon")
        polygon.set("points", "0 0, 10 3.5, 0 7")
        polygon.set("fill", "#666")
    
    def _draw_element(self, svg: ET.Element, element: C4Element, position: tuple) -> None:
        """Draw a single element"""
        x, y = position
        color = self.colors.get(element.element_type, "#85bbf0")
        
        # Draw rectangle
        rect = ET.SubElement(svg, "rect")
        rect.set("x", str(x - self.element_width // 2))
        rect.set("y", str(y - self.element_height // 2))
        rect.set("width", str(self.element_width))
        rect.set("height", str(self.element_height))
        rect.set("fill", color)
        rect.set("class", "element-rect")
        
        # Draw text
        text_elem = ET.SubElement(svg, "text")
        text_elem.set("x", str(x))
        text_elem.set("y", str(y - 5))
        text_elem.set("class", "element-text element-title")
        text_elem.set("fill", "white")
        text_elem.text = self._truncate_text(element.name, 15)
        
        # Draw technology if available
        if self.config.show_technology and element.technology:
            tech_text = ET.SubElement(svg, "text")
            tech_text.set("x", str(x))
            tech_text.set("y", str(y + 10))
            tech_text.set("class", "element-text")
            tech_text.set("fill", "white")
            tech_text.text = f"[{self._truncate_text(element.technology, 12)}]"
    
    def _draw_relationship(self, svg: ET.Element, relationship: C4Relationship, positions: Dict[str, tuple]) -> None:
        """Draw a relationship line"""
        source_pos = positions.get(relationship.source_id)
        target_pos = positions.get(relationship.target_id)
        
        if not source_pos or not target_pos:
            return
        
        x1, y1 = source_pos
        x2, y2 = target_pos
        
        # Draw line
        line = ET.SubElement(svg, "line")
        line.set("x1", str(x1))
        line.set("y1", str(y1))
        line.set("x2", str(x2))
        line.set("y2", str(y2))
        line.set("class", "relationship-line")
        
        # Draw label
        if relationship.label:
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2
            
            text_elem = ET.SubElement(svg, "text")
            text_elem.set("x", str(mid_x))
            text_elem.set("y", str(mid_y - 5))
            text_elem.set("class", "relationship-text")
            text_elem.text = self._truncate_text(relationship.label, 20)
    
    def get_file_extension(self) -> str:
        return ".svg"
    
    def _escape_text(self, text: str) -> str:
        """Escape text for SVG"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#39;"))
