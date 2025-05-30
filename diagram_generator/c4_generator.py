"""
C4 Diagram Generator

This module provides the main functionality for generating C4 diagrams from 
architecture analysis results. It transforms parsed code structure into 
visual C4 architectural representations.
"""

from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging

from .c4_models import (
    C4Diagram, C4Element, C4Person, C4System, C4Container, C4Component, 
    C4Relationship, DiagramType, ElementType, RelationshipType
)
from .diagram_formatters import DiagramFormatter, PlantUMLFormatter, MermaidFormatter, SVGFormatter, FormatterConfig

logger = logging.getLogger(__name__)


class DiagramTheme(Enum):
    """Available diagram themes"""
    DEFAULT = "default"
    DARK = "dark"
    CORPORATE = "corporate"
    MINIMAL = "minimal"
    COLORFUL = "colorful"


@dataclass
class DiagramGenerationConfig:
    """Configuration for diagram generation"""
    # Output settings
    output_formats: List[str] = field(default_factory=lambda: ["plantuml", "mermaid"])
    theme: DiagramTheme = DiagramTheme.DEFAULT
    output_directory: str = "./diagrams"
    
    # Content settings
    include_external_systems: bool = True
    include_databases: bool = True
    include_infrastructure: bool = False
    show_technology_stack: bool = True
    show_descriptions: bool = True
    
    # Layout settings
    max_elements_per_diagram: int = 20
    group_by_responsibility: bool = True
    auto_layout: bool = True
    
    # Filtering settings
    exclude_test_components: bool = True
    exclude_utility_components: bool = False
    minimum_relationship_weight: float = 0.1
    
    # LLM enhancement settings
    use_llm_insights: bool = True
    confidence_threshold: float = 0.7


class C4DiagramGenerator:
    """Generates C4 diagrams from architecture analysis results"""
    
    def __init__(self, config: DiagramGenerationConfig = None):
        self.config = config or DiagramGenerationConfig()
        self.formatters = self._initialize_formatters()
        
    def _initialize_formatters(self) -> Dict[str, DiagramFormatter]:
        """Initialize diagram formatters"""
        formatter_config = FormatterConfig(
            theme=self.config.theme.value,
            show_technology=self.config.show_technology_stack,
            show_descriptions=self.config.show_descriptions
        )
        
        return {
            'plantuml': PlantUMLFormatter(formatter_config),
            'mermaid': MermaidFormatter(formatter_config),
            'svg': SVGFormatter(formatter_config)
        }
    
    def generate_diagrams(self, analysis_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate C4 diagrams from architecture analysis results
        
        Args:
            analysis_results: Results from ArchitectureAnalyzer
            
        Returns:
            Dictionary mapping diagram types to lists of generated diagram paths
        """
        logger.info("Starting C4 diagram generation")
        
        try:
            # Extract architectural data
            architectural_data = self._extract_architectural_data(analysis_results)
            
            # Generate different diagram types
            diagrams = {}
            
            # Context diagram
            context_diagram = self._generate_context_diagram(architectural_data)
            if context_diagram:
                diagrams['context'] = context_diagram
                
            # Container diagrams
            container_diagrams = self._generate_container_diagrams(architectural_data)
            if container_diagrams:
                diagrams['container'] = container_diagrams
                
            # Component diagrams
            component_diagrams = self._generate_component_diagrams(architectural_data)
            if component_diagrams:
                diagrams['component'] = component_diagrams
            
            # Generate output files
            output_paths = self._generate_output_files(diagrams)
            
            logger.info(f"Generated {len(output_paths)} diagram files")
            return output_paths
            
        except Exception as e:
            logger.error(f"Error generating diagrams: {e}")
            raise
    
    def generate_diagrams_from_dict(self, architecture_data: Dict[str, Any]) -> List[str]:
        """
        Generate C4 diagrams directly from architecture dictionary data
        
        Args:
            architecture_data: Dictionary containing architecture components and relationships
            
        Returns:
            List of generated diagram file paths
        """
        logger.info("Generating C4 diagrams from dictionary data")
        
        try:
            # Generate different diagram types
            diagrams = {}
            
            # Context diagram
            context_diagram = self._generate_context_diagram(architecture_data)
            if context_diagram:
                diagrams['context'] = context_diagram
                
            # Container diagrams
            container_diagrams = self._generate_container_diagrams(architecture_data)
            if container_diagrams:
                diagrams['container'] = container_diagrams
                
            # Component diagrams (optional)
            if len(architecture_data.get('components', {})) <= self.config.max_elements_per_diagram:
                component_diagrams = self._generate_component_diagrams(architecture_data)
                if component_diagrams:
                    diagrams['component'] = component_diagrams
            
            # Generate output files
            all_output_paths = []
            output_paths = self._generate_output_files(diagrams)
            for diagram_type, paths in output_paths.items():
                if isinstance(paths, list):
                    all_output_paths.extend(paths)
                else:
                    all_output_paths.append(paths)
            
            logger.info(f"Generated {len(all_output_paths)} diagram files from dict")
            return all_output_paths
            
        except Exception as e:
            logger.error(f"Error generating diagrams from dict: {e}")
            raise

    def _extract_architectural_data(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and structure architectural data from analysis results"""
        data = {
            'components': [],
            'relationships': [],
            'systems': [],
            'external_dependencies': [],
            'technologies': set(),
            'llm_insights': {}
        }
        
        # Extract components from file analysis
        if 'files' in analysis_results:
            for file_path, file_data in analysis_results['files'].items():
                components = self._extract_components_from_file(file_path, file_data)
                data['components'].extend(components)
        
        # Extract relationships
        if 'relationships' in analysis_results:
            data['relationships'] = analysis_results['relationships']
        
        # Extract external dependencies
        if 'dependencies' in analysis_results:
            data['external_dependencies'] = analysis_results['dependencies']
        
        # Extract LLM insights if available
        if 'llm_analysis' in analysis_results:
            data['llm_insights'] = analysis_results['llm_analysis']
        
        # Extract technology stack
        if 'technology_stack' in analysis_results:
            data['technologies'] = set(analysis_results['technology_stack'])
        
        return data
    
    def _extract_components_from_file(self, file_path: str, file_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract components from individual file analysis"""
        components = []
        
        # Extract classes as components
        if 'classes' in file_data:
            for class_info in file_data['classes']:
                component = {
                    'name': class_info.get('name', ''),
                    'type': 'class',
                    'file_path': file_path,
                    'description': class_info.get('docstring', ''),
                    'methods': class_info.get('methods', []),
                    'dependencies': class_info.get('dependencies', []),
                    'responsibility': self._infer_responsibility(class_info),
                    'technology': self._infer_technology(file_path)
                }
                components.append(component)
        
        # Extract functions as components (for functional programming)
        if 'functions' in file_data:
            for func_info in file_data['functions']:
                if not self._is_utility_function(func_info):
                    component = {
                        'name': func_info.get('name', ''),
                        'type': 'function',
                        'file_path': file_path,
                        'description': func_info.get('docstring', ''),
                        'dependencies': func_info.get('dependencies', []),
                        'responsibility': self._infer_responsibility(func_info),
                        'technology': self._infer_technology(file_path)
                    }
                    components.append(component)
        
        return components
    
    def _generate_context_diagram(self, data: Dict[str, Any]) -> Optional[C4Diagram]:
        """Generate a context-level C4 diagram"""
        logger.info("Generating context diagram")
        
        diagram = C4Diagram(
            title="System Context",
            description="High-level view of the system and its interactions",
            diagram_type=DiagramType.CONTEXT
        )
        
        # Create main system
        main_system = C4System(
            name=self._get_system_name(data),
            description="The main software system",
            technology=", ".join(list(data['technologies'])[:3]) if data['technologies'] else None
        )
        diagram.add_element(main_system)
        
        # Add external systems
        external_systems = self._identify_external_systems(data)
        for ext_system in external_systems:
            system_element = C4System(
                name=ext_system['name'],
                description=ext_system.get('description', ''),
                is_external=True,
                technology=ext_system.get('technology')
            )
            diagram.add_element(system_element)
            
            # Add relationship to main system
            relationship = C4Relationship(
                source_id=main_system.id,
                target_id=system_element.id,
                label=ext_system.get('interaction_type', 'uses'),
                relationship_type=RelationshipType.USES
            )
            diagram.add_relationship(relationship)
        
        # Add user personas if identifiable
        users = self._identify_user_personas(data)
        for user in users:
            person = C4Person(
                name=user['name'],
                description=user.get('description', ''),
                role=user.get('role')
            )
            diagram.add_element(person)
            
            # Add relationship to main system
            relationship = C4Relationship(
                source_id=person.id,
                target_id=main_system.id,
                label=user.get('interaction_type', 'uses'),
                relationship_type=RelationshipType.USES
            )
            diagram.add_relationship(relationship)
        
        return diagram if len(diagram.elements) > 1 else None
    
    def _generate_container_diagrams(self, data: Dict[str, Any]) -> List[C4Diagram]:
        """Generate container-level C4 diagrams"""
        logger.info("Generating container diagrams")
        
        diagrams = []
        
        # Group components by logical containers (modules, packages, etc.)
        containers = self._identify_containers(data)
        
        if not containers:
            return diagrams
        
        diagram = C4Diagram(
            title="Container Diagram",
            description="Software architecture showing containers and their relationships",
            diagram_type=DiagramType.CONTAINER
        )
        
        container_elements = {}
        
        # Create container elements
        for container_info in containers:
            container = C4Container(
                name=container_info['name'],
                description=container_info.get('description', ''),
                technology=container_info.get('technology', ''),
                port=container_info.get('port')
            )
            diagram.add_element(container)
            container_elements[container_info['name']] = container
        
        # Add relationships between containers
        for rel in self._extract_container_relationships(data, containers):
            if rel['source'] in container_elements and rel['target'] in container_elements:
                relationship = C4Relationship(
                    source_id=container_elements[rel['source']].id,
                    target_id=container_elements[rel['target']].id,
                    label=rel.get('description', ''),
                    relationship_type=self._map_relationship_type(rel.get('type', 'uses'))
                )
                diagram.add_relationship(relationship)
        
        if len(diagram.elements) > 0:
            diagrams.append(diagram)
        
        return diagrams
    
    def _generate_component_diagrams(self, data: Dict[str, Any]) -> List[C4Diagram]:
        """Generate component-level C4 diagrams"""
        logger.info("Generating component diagrams")
        
        diagrams = []
        containers = self._identify_containers(data)
        
        for container_info in containers:
            components = [c for c in data['components'] 
                         if self._belongs_to_container(c, container_info)]
            
            if not components:
                continue
            
            # Split large containers into multiple diagrams
            component_chunks = self._chunk_components(components, self.config.max_elements_per_diagram)
            
            for i, chunk in enumerate(component_chunks):
                suffix = f" - Part {i+1}" if len(component_chunks) > 1 else ""
                
                diagram = C4Diagram(
                    title=f"{container_info['name']} Components{suffix}",
                    description=f"Detailed view of components in {container_info['name']}",
                    diagram_type=DiagramType.COMPONENT
                )
                
                component_elements = {}
                
                # Add components
                for comp in chunk:
                    if self._should_include_component(comp):
                        component = C4Component(
                            name=comp['name'],
                            description=comp.get('description', ''),
                            technology=comp.get('technology', ''),
                            responsibility=comp.get('responsibility', ''),
                            interfaces=comp.get('interfaces', [])
                        )
                        diagram.add_element(component)
                        component_elements[comp['name']] = component
                
                # Add relationships
                for rel in data['relationships']:
                    source_name = rel.get('source')
                    target_name = rel.get('target')
                    
                    if (source_name in component_elements and 
                        target_name in component_elements):
                        relationship = C4Relationship(
                            source_id=component_elements[source_name].id,
                            target_id=component_elements[target_name].id,
                            label=rel.get('description', ''),
                            relationship_type=self._map_relationship_type(rel.get('type', 'uses')),
                            technology=rel.get('technology')
                        )
                        diagram.add_relationship(relationship)
                
                if len(diagram.elements) > 0:
                    diagrams.append(diagram)
        
        return diagrams
    
    def _generate_output_files(self, diagrams: Dict[str, Union[C4Diagram, List[C4Diagram]]]) -> Dict[str, List[str]]:
        """Generate output files in specified formats"""
        output_paths = {}
        output_dir = Path(self.config.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for diagram_type, diagram_data in diagrams.items():
            diagram_list = diagram_data if isinstance(diagram_data, list) else [diagram_data]
            
            for i, diagram in enumerate(diagram_list):
                suffix = f"_{i+1}" if len(diagram_list) > 1 else ""
                base_name = f"{diagram_type}{suffix}"
                
                type_paths = []
                
                for format_name in self.config.output_formats:
                    if format_name in self.formatters:
                        formatter = self.formatters[format_name]
                        content = formatter.format_diagram(diagram)
                        
                        file_path = output_dir / f"{base_name}{formatter.get_file_extension()}"
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        type_paths.append(str(file_path))
                        logger.info(f"Generated {format_name} diagram: {file_path}")
                
                if diagram_type not in output_paths:
                    output_paths[diagram_type] = []
                output_paths[diagram_type].extend(type_paths)
        
        # Generate summary report
        self._generate_summary_report(diagrams, output_dir)
        
        return output_paths
    
    def _generate_summary_report(self, diagrams: Dict, output_dir: Path) -> None:
        """Generate a summary report of all generated diagrams"""
        report = {
            'generation_timestamp': str(Path().cwd()),
            'configuration': {
                'formats': self.config.output_formats,
                'theme': self.config.theme.value,
                'include_external_systems': self.config.include_external_systems
            },
            'diagrams': {}
        }
        
        for diagram_type, diagram_data in diagrams.items():
            diagram_list = diagram_data if isinstance(diagram_data, list) else [diagram_data]
            
            report['diagrams'][diagram_type] = []
            for diagram in diagram_list:
                stats = diagram.get_statistics()
                validation_errors = diagram.validate()
                
                diagram_info = {
                    'title': diagram.title,
                    'description': diagram.description,
                    'statistics': stats,
                    'validation_errors': validation_errors
                }
                report['diagrams'][diagram_type].append(diagram_info)
        
        report_path = output_dir / "diagram_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Generated summary report: {report_path}")
    
    # Helper methods
    def _get_system_name(self, data: Dict[str, Any]) -> str:
        """Determine the main system name"""
        if 'llm_insights' in data and 'system_overview' in data['llm_insights']:
            return data['llm_insights']['system_overview'].get('name', 'Software System')
        return "Software System"
    
    def _identify_external_systems(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify external systems from dependencies"""
        external_systems = []
        
        for dep in data.get('external_dependencies', []):
            if isinstance(dep, dict):
                external_systems.append({
                    'name': dep.get('name', dep.get('package', 'External System')),
                    'description': dep.get('description', ''),
                    'technology': dep.get('type', ''),
                    'interaction_type': 'depends on'
                })
        
        return external_systems
    
    def _identify_user_personas(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify user personas from LLM insights or code patterns"""
        users = []
        
        # Check LLM insights first
        if 'llm_insights' in data and 'user_personas' in data['llm_insights']:
            return data['llm_insights']['user_personas']
        
        # Fallback: infer from common patterns
        common_users = [
            {'name': 'End User', 'description': 'Primary system user', 'role': 'user'},
            {'name': 'Administrator', 'description': 'System administrator', 'role': 'admin'}
        ]
        
        return common_users
    
    def _identify_containers(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify logical containers from components"""
        containers = {}
        
        # Group by module/package structure
        for component in data.get('components', []):
            file_path = component.get('file_path', '')
            parts = Path(file_path).parts
            
            if len(parts) > 1:
                # Use the first directory as container name
                container_name = parts[0] if parts[0] != '.' else parts[1] if len(parts) > 1 else 'Core'
            else:
                container_name = 'Core'
            
            if container_name not in containers:
                containers[container_name] = {
                    'name': container_name,
                    'description': f"Components in {container_name}",
                    'technology': component.get('technology', ''),
                    'components': []
                }
            
            containers[container_name]['components'].append(component)
        
        return list(containers.values())
    
    def _extract_container_relationships(self, data: Dict[str, Any], containers: List[Dict]) -> List[Dict]:
        """Extract relationships between containers"""
        relationships = []
        container_map = {c['name']: c for c in containers}
        
        for rel in data.get('relationships', []):
            source_container = self._find_component_container(rel.get('source'), containers)
            target_container = self._find_component_container(rel.get('target'), containers)
            
            if (source_container and target_container and 
                source_container != target_container):
                relationships.append({
                    'source': source_container,
                    'target': target_container,
                    'type': rel.get('type', 'uses'),
                    'description': rel.get('description', '')
                })
        
        return relationships
    
    def _find_component_container(self, component_name: str, containers: List[Dict]) -> Optional[str]:
        """Find which container a component belongs to"""
        for container in containers:
            for component in container.get('components', []):
                if component.get('name') == component_name:
                    return container['name']
        return None
    
    def _belongs_to_container(self, component: Dict, container_info: Dict) -> bool:
        """Check if a component belongs to a specific container"""
        return component in container_info.get('components', [])
    
    def _chunk_components(self, components: List[Dict], max_size: int) -> List[List[Dict]]:
        """Split components into chunks of maximum size"""
        chunks = []
        for i in range(0, len(components), max_size):
            chunks.append(components[i:i + max_size])
        return chunks
    
    def _should_include_component(self, component: Dict) -> bool:
        """Determine if a component should be included in the diagram"""
        if self.config.exclude_test_components and 'test' in component.get('name', '').lower():
            return False
        
        if self.config.exclude_utility_components and self._is_utility_component(component):
            return False
        
        return True
    
    def _is_utility_component(self, component: Dict) -> bool:
        """Check if a component is a utility component"""
        utility_patterns = ['util', 'helper', 'common', 'shared', 'base']
        name = component.get('name', '').lower()
        return any(pattern in name for pattern in utility_patterns)
    
    def _is_utility_function(self, func_info: Dict) -> bool:
        """Check if a function is a utility function"""
        utility_patterns = ['_', 'helper', 'util', 'get_', 'set_']
        name = func_info.get('name', '')
        return any(name.startswith(pattern) for pattern in utility_patterns)
    
    def _infer_responsibility(self, element_info: Dict) -> str:
        """Infer the responsibility of a component from its structure"""
        name = element_info.get('name', '').lower()
        methods = element_info.get('methods', [])
        
        # Common responsibility patterns
        if 'controller' in name or 'handler' in name:
            return "Request handling and routing"
        elif 'service' in name:
            return "Business logic processing"
        elif 'repository' in name or 'dao' in name:
            return "Data access and persistence"
        elif 'model' in name or 'entity' in name:
            return "Data representation"
        elif 'view' in name or 'template' in name:
            return "User interface rendering"
        elif any('validate' in m.get('name', '') for m in methods):
            return "Data validation"
        else:
            return "Core functionality"
    
    def _infer_technology(self, file_path: str) -> str:
        """Infer technology from file extension"""
        ext = Path(file_path).suffix.lower()
        tech_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP'
        }
        return tech_map.get(ext, 'Unknown')
    
    def _map_relationship_type(self, rel_type: str) -> RelationshipType:
        """Map string relationship type to enum"""
        type_map = {
            'uses': RelationshipType.USES,
            'depends_on': RelationshipType.DEPENDS_ON,
            'calls': RelationshipType.CALLS,
            'includes': RelationshipType.INCLUDES,
            'extends': RelationshipType.EXTENDS,
            'implements': RelationshipType.IMPLEMENTS,
            'reads_from': RelationshipType.READS_FROM,
            'writes_to': RelationshipType.WRITES_TO
        }
        return type_map.get(rel_type.lower(), RelationshipType.USES)
