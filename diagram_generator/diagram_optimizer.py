"""
Diagram Optimizer

This module provides optimization capabilities for C4 diagrams including:
- Layout optimization for better visual clarity
- Element grouping and clustering
- Relationship simplification
- Performance optimization for large diagrams
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import logging

from .c4_models import (
    C4Diagram, C4Element, C4Relationship, ElementType, RelationshipType
)

logger = logging.getLogger(__name__)


class LayoutStrategy(Enum):
    """Available layout strategies"""
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    FORCE_DIRECTED = "force_directed"
    GRID = "grid"
    LAYERED = "layered"


@dataclass
class OptimizationConfig:
    """Configuration for diagram optimization"""
    # Layout settings
    layout_strategy: LayoutStrategy = LayoutStrategy.HIERARCHICAL
    canvas_width: int = 1200
    canvas_height: int = 800
    margin: int = 50
    
    # Element spacing
    min_element_distance: int = 100
    element_width: int = 120
    element_height: int = 80
    
    # Relationship optimization
    merge_duplicate_relationships: bool = True
    simplify_transitive_relationships: bool = True
    max_relationship_labels: int = 50
    
    # Grouping settings
    enable_clustering: bool = True
    cluster_by_type: bool = True
    cluster_by_responsibility: bool = True
    max_cluster_size: int = 8
    
    # Performance settings
    max_optimization_iterations: int = 100
    force_threshold: float = 0.1


class DiagramOptimizer:
    """Optimizes C4 diagrams for better visual representation"""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
    
    def optimize_diagram(self, diagram: C4Diagram) -> C4Diagram:
        """
        Optimize a diagram for better visual representation
        
        Args:
            diagram: The diagram to optimize
            
        Returns:
            Optimized diagram
        """
        logger.info(f"Optimizing diagram: {diagram.title}")
        
        # Create a copy to avoid modifying the original
        optimized = self._deep_copy_diagram(diagram)
        
        # Apply optimizations
        optimized = self._optimize_relationships(optimized)
        optimized = self._apply_clustering(optimized)
        optimized = self._optimize_layout(optimized)
        optimized = self._validate_optimization(optimized)
        
        logger.info(f"Optimization complete. Elements: {len(optimized.elements)}, "
                   f"Relationships: {len(optimized.relationships)}")
        
        return optimized
    
    def _optimize_relationships(self, diagram: C4Diagram) -> C4Diagram:
        """Optimize relationships for clarity"""
        if self.config.merge_duplicate_relationships:
            diagram = self._merge_duplicate_relationships(diagram)
        
        if self.config.simplify_transitive_relationships:
            diagram = self._simplify_transitive_relationships(diagram)
        
        diagram = self._optimize_relationship_labels(diagram)
        
        return diagram
    
    def _merge_duplicate_relationships(self, diagram: C4Diagram) -> C4Diagram:
        """Merge duplicate relationships between the same elements"""
        relationship_map = {}
        
        for rel in diagram.relationships:
            key = (rel.source_id, rel.target_id)
            
            if key in relationship_map:
                # Merge with existing relationship
                existing = relationship_map[key]
                merged_label = self._merge_relationship_labels(existing.label, rel.label)
                existing.label = merged_label
                
                # Merge properties
                existing.properties.update(rel.properties)
            else:
                relationship_map[key] = rel
        
        diagram.relationships = list(relationship_map.values())
        return diagram
    
    def _simplify_transitive_relationships(self, diagram: C4Diagram) -> C4Diagram:
        """Remove redundant transitive relationships (A->B->C, remove A->C)"""
        # Build adjacency list
        adjacency = {}
        for rel in diagram.relationships:
            if rel.source_id not in adjacency:
                adjacency[rel.source_id] = set()
            adjacency[rel.source_id].add(rel.target_id)
        
        # Find transitive relationships to remove
        to_remove = set()
        
        for rel in diagram.relationships:
            source, target = rel.source_id, rel.target_id
            
            # Check if there's an indirect path
            if source in adjacency:
                for intermediate in adjacency[source]:
                    if (intermediate != target and 
                        intermediate in adjacency and 
                        target in adjacency[intermediate]):
                        # Found transitive relationship
                        to_remove.add(rel.id)
                        break
        
        # Remove transitive relationships
        diagram.relationships = [rel for rel in diagram.relationships if rel.id not in to_remove]
        
        logger.info(f"Removed {len(to_remove)} transitive relationships")
        return diagram
    
    def _optimize_relationship_labels(self, diagram: C4Diagram) -> C4Diagram:
        """Optimize relationship labels for clarity"""
        label_counts = {}
        
        # Count label frequency
        for rel in diagram.relationships:
            label = rel.label.lower().strip()
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # Simplify common labels
        for rel in diagram.relationships:
            label = rel.label.lower().strip()
            
            # If label is very common, consider shortening it
            if label_counts[label] > self.config.max_relationship_labels * 0.3:
                rel.label = self._shorten_label(rel.label)
        
        return diagram
    
    def _apply_clustering(self, diagram: C4Diagram) -> C4Diagram:
        """Apply clustering to group related elements"""
        if not self.config.enable_clustering:
            return diagram
        
        clusters = []
        
        if self.config.cluster_by_type:
            clusters.extend(self._cluster_by_element_type(diagram))
        
        if self.config.cluster_by_responsibility:
            clusters.extend(self._cluster_by_responsibility(diagram))
        
        # Apply clustering information to elements
        for cluster in clusters:
            cluster_id = f"cluster_{len(diagram.metadata.get('clusters', []))}"
            
            for element_id in cluster['elements']:
                element = diagram.get_element_by_id(element_id)
                if element:
                    if 'cluster_id' not in element.properties:
                        element.properties['cluster_id'] = cluster_id
                    element.properties['cluster_type'] = cluster['type']
        
        # Store cluster information
        if 'clusters' not in diagram.metadata:
            diagram.metadata['clusters'] = []
        diagram.metadata['clusters'].extend(clusters)
        
        return diagram
    
    def _cluster_by_element_type(self, diagram: C4Diagram) -> List[Dict[str, Any]]:
        """Create clusters based on element types"""
        type_clusters = {}
        
        for element in diagram.elements:
            element_type = element.element_type
            if element_type not in type_clusters:
                type_clusters[element_type] = []
            type_clusters[element_type].append(element.id)
        
        clusters = []
        for element_type, element_ids in type_clusters.items():
            if len(element_ids) >= 2:  # Only cluster if there are multiple elements
                clusters.append({
                    'type': 'element_type',
                    'name': f"{element_type.value.title()} Cluster",
                    'elements': element_ids
                })
        
        return clusters
    
    def _cluster_by_responsibility(self, diagram: C4Diagram) -> List[Dict[str, Any]]:
        """Create clusters based on component responsibilities"""
        responsibility_clusters = {}
        
        for element in diagram.elements:
            responsibility = element.properties.get('responsibility', 'unknown')
            if responsibility not in responsibility_clusters:
                responsibility_clusters[responsibility] = []
            responsibility_clusters[responsibility].append(element.id)
        
        clusters = []
        for responsibility, element_ids in responsibility_clusters.items():
            if len(element_ids) >= 2 and len(element_ids) <= self.config.max_cluster_size:
                clusters.append({
                    'type': 'responsibility',
                    'name': f"{responsibility} Components",
                    'elements': element_ids
                })
        
        return clusters
    
    def _optimize_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Optimize element positions using the selected layout strategy"""
        if self.config.layout_strategy == LayoutStrategy.HIERARCHICAL:
            diagram = self._apply_hierarchical_layout(diagram)
        elif self.config.layout_strategy == LayoutStrategy.CIRCULAR:
            diagram = self._apply_circular_layout(diagram)
        elif self.config.layout_strategy == LayoutStrategy.FORCE_DIRECTED:
            diagram = self._apply_force_directed_layout(diagram)
        elif self.config.layout_strategy == LayoutStrategy.GRID:
            diagram = self._apply_grid_layout(diagram)
        elif self.config.layout_strategy == LayoutStrategy.LAYERED:
            diagram = self._apply_layered_layout(diagram)
        
        return diagram
    
    def _apply_hierarchical_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Apply hierarchical layout based on element types"""
        # Group elements by hierarchy level
        hierarchy_levels = {
            ElementType.PERSON: 0,
            ElementType.SYSTEM: 1,
            ElementType.EXTERNAL_SYSTEM: 1,
            ElementType.CONTAINER: 2,
            ElementType.COMPONENT: 3,
            ElementType.DATABASE: 2,
            ElementType.QUEUE: 2
        }
        
        levels = {}
        for element in diagram.elements:
            level = hierarchy_levels.get(element.element_type, 3)
            if level not in levels:
                levels[level] = []
            levels[level].append(element)
        
        # Position elements
        y_spacing = (self.config.canvas_height - 2 * self.config.margin) / max(len(levels), 1)
        
        for level, elements in levels.items():
            y = self.config.margin + level * y_spacing
            x_spacing = (self.config.canvas_width - 2 * self.config.margin) / max(len(elements), 1)
            
            for i, element in enumerate(elements):
                element.x = self.config.margin + i * x_spacing + x_spacing / 2
                element.y = y
        
        return diagram
    
    def _apply_circular_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Apply circular layout"""
        center_x = self.config.canvas_width / 2
        center_y = self.config.canvas_height / 2
        radius = min(center_x, center_y) - self.config.margin - self.config.element_width
        
        angle_step = 2 * math.pi / len(diagram.elements)
        
        for i, element in enumerate(diagram.elements):
            angle = i * angle_step
            element.x = center_x + radius * math.cos(angle)
            element.y = center_y + radius * math.sin(angle)
        
        return diagram
    
    def _apply_force_directed_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Apply force-directed layout algorithm"""
        # Initialize random positions
        for element in diagram.elements:
            if element.x is None or element.y is None:
                element.x = self.config.margin + (self.config.canvas_width - 2 * self.config.margin) * hash(element.id) % 1000 / 1000
                element.y = self.config.margin + (self.config.canvas_height - 2 * self.config.margin) * hash(element.id + "y") % 1000 / 1000
        
        # Build adjacency list
        adjacency = {}
        for rel in diagram.relationships:
            if rel.source_id not in adjacency:
                adjacency[rel.source_id] = []
            adjacency[rel.source_id].append(rel.target_id)
        
        # Force-directed algorithm
        for iteration in range(self.config.max_optimization_iterations):
            forces = {element.id: [0.0, 0.0] for element in diagram.elements}
            
            # Repulsive forces
            for i, elem1 in enumerate(diagram.elements):
                for j, elem2 in enumerate(diagram.elements):
                    if i != j:
                        dx = elem1.x - elem2.x
                        dy = elem1.y - elem2.y
                        distance = math.sqrt(dx*dx + dy*dy) + 0.01  # Avoid division by zero
                        
                        force = self.config.min_element_distance / (distance * distance)
                        forces[elem1.id][0] += force * dx / distance
                        forces[elem1.id][1] += force * dy / distance
            
            # Attractive forces for connected elements
            for rel in diagram.relationships:
                elem1 = diagram.get_element_by_id(rel.source_id)
                elem2 = diagram.get_element_by_id(rel.target_id)
                
                if elem1 and elem2:
                    dx = elem2.x - elem1.x
                    dy = elem2.y - elem1.y
                    distance = math.sqrt(dx*dx + dy*dy) + 0.01
                    
                    force = distance / self.config.min_element_distance
                    forces[elem1.id][0] += force * dx / distance
                    forces[elem1.id][1] += force * dy / distance
                    forces[elem2.id][0] -= force * dx / distance
                    forces[elem2.id][1] -= force * dy / distance
            
            # Apply forces
            max_force = 0
            for element in diagram.elements:
                fx, fy = forces[element.id]
                max_force = max(max_force, abs(fx), abs(fy))
                
                element.x += fx * 0.1
                element.y += fy * 0.1
                
                # Keep within canvas bounds
                element.x = max(self.config.margin, min(self.config.canvas_width - self.config.margin, element.x))
                element.y = max(self.config.margin, min(self.config.canvas_height - self.config.margin, element.y))
            
            # Check convergence
            if max_force < self.config.force_threshold:
                logger.info(f"Force-directed layout converged after {iteration} iterations")
                break
        
        return diagram
    
    def _apply_grid_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Apply simple grid layout"""
        cols = int(math.sqrt(len(diagram.elements))) + 1
        rows = (len(diagram.elements) + cols - 1) // cols
        
        x_spacing = (self.config.canvas_width - 2 * self.config.margin) / cols
        y_spacing = (self.config.canvas_height - 2 * self.config.margin) / rows
        
        for i, element in enumerate(diagram.elements):
            col = i % cols
            row = i // cols
            
            element.x = self.config.margin + col * x_spacing + x_spacing / 2
            element.y = self.config.margin + row * y_spacing + y_spacing / 2
        
        return diagram
    
    def _apply_layered_layout(self, diagram: C4Diagram) -> C4Diagram:
        """Apply layered layout based on dependency levels"""
        # Calculate dependency levels
        levels = self._calculate_dependency_levels(diagram)
        
        # Group elements by level
        level_groups = {}
        for element in diagram.elements:
            level = levels.get(element.id, 0)
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(element)
        
        # Position elements
        if level_groups:
            y_spacing = (self.config.canvas_height - 2 * self.config.margin) / len(level_groups)
            
            for level, elements in level_groups.items():
                y = self.config.margin + level * y_spacing + y_spacing / 2
                x_spacing = (self.config.canvas_width - 2 * self.config.margin) / max(len(elements), 1)
                
                for i, element in enumerate(elements):
                    element.x = self.config.margin + i * x_spacing + x_spacing / 2
                    element.y = y
        
        return diagram
    
    def _calculate_dependency_levels(self, diagram: C4Diagram) -> Dict[str, int]:
        """Calculate dependency levels for layered layout"""
        levels = {}
        in_degree = {}
        
        # Initialize
        for element in diagram.elements:
            levels[element.id] = 0
            in_degree[element.id] = 0
        
        # Calculate in-degrees
        for rel in diagram.relationships:
            if rel.target_id in in_degree:
                in_degree[rel.target_id] += 1
        
        # Topological sort to assign levels
        queue = [elem_id for elem_id, degree in in_degree.items() if degree == 0]
        
        while queue:
            current = queue.pop(0)
            
            # Update levels of dependent elements
            for rel in diagram.relationships:
                if rel.source_id == current:
                    target = rel.target_id
                    levels[target] = max(levels[target], levels[current] + 1)
                    in_degree[target] -= 1
                    
                    if in_degree[target] == 0:
                        queue.append(target)
        
        return levels
    
    def _validate_optimization(self, diagram: C4Diagram) -> C4Diagram:
        """Validate the optimized diagram"""
        errors = diagram.validate()
        
        if errors:
            logger.warning(f"Diagram validation found {len(errors)} issues after optimization")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {error}")
        
        # Ensure all elements have positions
        for element in diagram.elements:
            if element.x is None or element.y is None:
                logger.warning(f"Element {element.name} has no position, applying default")
                element.x = self.config.margin + self.config.element_width / 2
                element.y = self.config.margin + self.config.element_height / 2
        
        return diagram
    
    def _deep_copy_diagram(self, diagram: C4Diagram) -> C4Diagram:
        """Create a deep copy of the diagram"""
        # For simplicity, we'll create a new diagram and copy elements/relationships
        new_diagram = C4Diagram(
            title=diagram.title,
            description=diagram.description,
            diagram_type=diagram.diagram_type
        )
        
        # Copy metadata
        new_diagram.metadata = diagram.metadata.copy()
        
        # Copy elements
        for element in diagram.elements:
            new_element = type(element)(
                id=element.id,
                name=element.name,
                description=element.description,
                element_type=element.element_type,
                technology=element.technology,
                tags=element.tags.copy(),
                properties=element.properties.copy(),
                x=element.x,
                y=element.y
            )
            new_diagram.elements.append(new_element)
        
        # Copy relationships
        for rel in diagram.relationships:
            new_rel = C4Relationship(
                id=rel.id,
                source_id=rel.source_id,
                target_id=rel.target_id,
                label=rel.label,
                description=rel.description,
                relationship_type=rel.relationship_type,
                technology=rel.technology,
                properties=rel.properties.copy()
            )
            new_diagram.relationships.append(new_rel)
        
        return new_diagram
    
    def _merge_relationship_labels(self, label1: str, label2: str) -> str:
        """Merge two relationship labels intelligently"""
        if not label1:
            return label2
        if not label2:
            return label1
        if label1 == label2:
            return label1
        
        # If one is more specific, use it
        if len(label2) > len(label1) and label1.lower() in label2.lower():
            return label2
        if len(label1) > len(label2) and label2.lower() in label1.lower():
            return label1
        
        # Otherwise, combine them
        return f"{label1} / {label2}"
    
    def _shorten_label(self, label: str) -> str:
        """Shorten a relationship label"""
        # Common shortenings
        shortenings = {
            'depends on': 'uses',
            'communicates with': 'calls',
            'sends data to': 'sends to',
            'receives data from': 'gets from',
            'interacts with': 'uses'
        }
        
        lower_label = label.lower()
        for long_form, short_form in shortenings.items():
            if long_form in lower_label:
                return label.replace(long_form, short_form)
        
        # If still too long, truncate
        if len(label) > 20:
            return label[:17] + "..."
        
        return label
