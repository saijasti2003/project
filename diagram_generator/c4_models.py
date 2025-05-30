"""
C4 Model Data Structures

This module defines the core data structures for C4 architecture diagrams
following the C4 model principles: Context, Container, Component, and Code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from enum import Enum
import uuid


class DiagramType(Enum):
    """Types of C4 diagrams"""
    CONTEXT = "context"
    CONTAINER = "container"
    COMPONENT = "component"
    CODE = "code"


class ElementType(Enum):
    """Types of C4 elements"""
    PERSON = "person"
    SYSTEM = "system"
    EXTERNAL_SYSTEM = "external_system"
    CONTAINER = "container"
    COMPONENT = "component"
    DATABASE = "database"
    QUEUE = "queue"
    FILE_SYSTEM = "file_system"


class RelationshipType(Enum):
    """Types of relationships between C4 elements"""
    USES = "uses"
    DEPENDS_ON = "depends_on"
    INCLUDES = "includes"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    READS_FROM = "reads_from"
    WRITES_TO = "writes_to"
    SUBSCRIBES_TO = "subscribes_to"
    PUBLISHES_TO = "publishes_to"


@dataclass
class C4Element:
    """Base class for all C4 elements"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    element_type: ElementType = ElementType.COMPONENT
    technology: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    x: Optional[float] = None
    y: Optional[float] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        if not self.name:
            self.name = f"Unnamed {self.element_type.value}"
        
        # Ensure tags is a set
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)


@dataclass
class C4Person(C4Element):
    """Represents a person in the C4 model"""
    element_type: ElementType = field(default=ElementType.PERSON, init=False)
    role: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.role:
            self.properties['role'] = self.role


@dataclass
class C4System(C4Element):
    """Represents a software system in the C4 model"""
    element_type: ElementType = field(default=ElementType.SYSTEM, init=False)
    is_external: bool = False
    containers: List['C4Container'] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if self.is_external:
            self.element_type = ElementType.EXTERNAL_SYSTEM
        self.properties['is_external'] = self.is_external
    
    def add_container(self, container: 'C4Container') -> None:
        """Add a container to this system"""
        container.system_id = self.id
        self.containers.append(container)
    
    def get_container_by_name(self, name: str) -> Optional['C4Container']:
        """Find a container by name"""
        return next((c for c in self.containers if c.name == name), None)


@dataclass
class C4Container(C4Element):
    """Represents a container (application/service) in the C4 model"""
    element_type: ElementType = field(default=ElementType.CONTAINER, init=False)
    system_id: Optional[str] = None
    components: List['C4Component'] = field(default_factory=list)
    port: Optional[int] = None
    url: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.port:
            self.properties['port'] = self.port
        if self.url:
            self.properties['url'] = self.url
    
    def add_component(self, component: 'C4Component') -> None:
        """Add a component to this container"""
        component.container_id = self.id
        self.components.append(component)
    
    def get_component_by_name(self, name: str) -> Optional['C4Component']:
        """Find a component by name"""
        return next((c for c in self.components if c.name == name), None)


@dataclass
class C4Component(C4Element):
    """Represents a component in the C4 model"""
    element_type: ElementType = field(default=ElementType.COMPONENT, init=False)
    container_id: Optional[str] = None
    responsibility: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        if self.responsibility:
            self.properties['responsibility'] = self.responsibility
        if self.interfaces:
            self.properties['interfaces'] = self.interfaces


@dataclass
class C4Relationship:
    """Represents a relationship between C4 elements"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    description: Optional[str] = None
    relationship_type: RelationshipType = RelationshipType.USES
    technology: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation"""
        if not self.source_id or not self.target_id:
            raise ValueError("Relationship must have both source_id and target_id")
        
        if not self.label:
            self.label = self.relationship_type.value.replace('_', ' ').title()


@dataclass
class C4Diagram:
    """Represents a complete C4 diagram"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    diagram_type: DiagramType = DiagramType.COMPONENT
    elements: List[C4Element] = field(default_factory=list)
    relationships: List[C4Relationship] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup"""
        if not self.title:
            self.title = f"{self.diagram_type.value.title()} Diagram"
    
    def add_element(self, element: C4Element) -> None:
        """Add an element to the diagram"""
        # Check for duplicate IDs
        if any(e.id == element.id for e in self.elements):
            raise ValueError(f"Element with ID {element.id} already exists")
        self.elements.append(element)
    
    def add_relationship(self, relationship: C4Relationship) -> None:
        """Add a relationship to the diagram"""
        # Validate that source and target elements exist
        element_ids = {e.id for e in self.elements}
        if relationship.source_id not in element_ids:
            raise ValueError(f"Source element {relationship.source_id} not found")
        if relationship.target_id not in element_ids:
            raise ValueError(f"Target element {relationship.target_id} not found")
        
        self.relationships.append(relationship)
    
    def get_element_by_id(self, element_id: str) -> Optional[C4Element]:
        """Find an element by ID"""
        return next((e for e in self.elements if e.id == element_id), None)
    
    def get_element_by_name(self, name: str) -> Optional[C4Element]:
        """Find an element by name"""
        return next((e for e in self.elements if e.name == name), None)
    
    def get_elements_by_type(self, element_type: ElementType) -> List[C4Element]:
        """Get all elements of a specific type"""
        return [e for e in self.elements if e.element_type == element_type]
    
    def get_relationships_for_element(self, element_id: str) -> List[C4Relationship]:
        """Get all relationships involving a specific element"""
        return [r for r in self.relationships 
                if r.source_id == element_id or r.target_id == element_id]
    
    def remove_element(self, element_id: str) -> bool:
        """Remove an element and all its relationships"""
        # Remove relationships first
        self.relationships = [r for r in self.relationships 
                            if r.source_id != element_id and r.target_id != element_id]
        
        # Remove element
        original_count = len(self.elements)
        self.elements = [e for e in self.elements if e.id != element_id]
        return len(self.elements) < original_count
    
    def validate(self) -> List[str]:
        """Validate the diagram and return any errors"""
        errors = []
        
        # Check for orphaned relationships
        element_ids = {e.id for e in self.elements}
        for rel in self.relationships:
            if rel.source_id not in element_ids:
                errors.append(f"Relationship {rel.id} has invalid source {rel.source_id}")
            if rel.target_id not in element_ids:
                errors.append(f"Relationship {rel.id} has invalid target {rel.target_id}")
        
        # Check for duplicate element names within the same type
        type_names = {}
        for element in self.elements:
            key = (element.element_type, element.name)
            if key in type_names:
                errors.append(f"Duplicate {element.element_type.value} name: {element.name}")
            type_names[key] = element.id
        
        return errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get diagram statistics"""
        element_counts = {}
        for element in self.elements:
            element_type = element.element_type.value
            element_counts[element_type] = element_counts.get(element_type, 0) + 1
        
        relationship_counts = {}
        for rel in self.relationships:
            rel_type = rel.relationship_type.value
            relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
        
        return {
            'total_elements': len(self.elements),
            'total_relationships': len(self.relationships),
            'element_types': element_counts,
            'relationship_types': relationship_counts,
            'diagram_type': self.diagram_type.value
        }
