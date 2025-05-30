"""
Relationship Extractor

Extracts relationships between C4 architecture components.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum

from .component_classifier import C4Component, C4ComponentType
from codebase_parser.code_analyzer import ModuleInfo, CodeElement


class RelationshipType(Enum):
    """Types of relationships between components"""
    USES = "uses"
    DEPENDS_ON = "depends_on"
    INCLUDES = "includes"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    SENDS_DATA_TO = "sends_data_to"
    READS_FROM = "reads_from"
    WRITES_TO = "writes_to"


@dataclass
class C4Relationship:
    """Represents a relationship between C4 components"""
    source: str  # Component name
    target: str  # Component name
    relationship_type: RelationshipType
    description: str
    technology: Optional[str] = None
    protocol: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RelationshipExtractor:
    """
    Extracts relationships between C4 architecture components.
    """
    
    def __init__(self):
        self.api_patterns = {
            'rest': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
            'graphql': ['query', 'mutation', 'subscription'],
            'grpc': ['rpc', 'service']
        }
        
        self.database_operations = {
            'read': ['select', 'find', 'get', 'fetch', 'load', 'retrieve'],
            'write': ['insert', 'create', 'save', 'update', 'delete', 'remove']
        }
    
    def extract_relationships(self, components: Dict[str, C4Component], 
                            analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """
        Extract relationships between components.
        
        Args:
            components: Dictionary of C4 components
            analysis_results: Results from code analysis
            
        Returns:
            List of relationships between components
        """
        relationships = []
        
        # Extract different types of relationships
        relationships.extend(self._extract_dependency_relationships(components, analysis_results))
        relationships.extend(self._extract_containment_relationships(components))
        relationships.extend(self._extract_api_relationships(components, analysis_results))
        relationships.extend(self._extract_database_relationships(components, analysis_results))
        relationships.extend(self._extract_external_relationships(components, analysis_results))
        relationships.extend(self._extract_code_relationships(components, analysis_results))
        
        return self._deduplicate_relationships(relationships)
    
    def _extract_dependency_relationships(self, components: Dict[str, C4Component], 
                                        analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """Extract dependency relationships based on imports."""
        relationships = []
        
        # Create mapping of modules to components
        module_to_component = self._create_module_component_mapping(components)
        
        for module_path, module_info in analysis_results.items():
            source_component = module_to_component.get(module_path)
            if not source_component:
                continue
            
            # Check imports for dependencies
            for import_name in module_info.imports:
                # Find target component that might contain this import
                target_component = self._find_component_by_import(import_name, components, analysis_results)
                
                if target_component and target_component != source_component:
                    relationships.append(C4Relationship(
                        source=source_component,
                        target=target_component,
                        relationship_type=RelationshipType.DEPENDS_ON,
                        description=f"Imports {import_name}",
                        metadata={'import': import_name}
                    ))
        
        return relationships
    
    def _extract_containment_relationships(self, components: Dict[str, C4Component]) -> List[C4Relationship]:
        """Extract containment relationships (system contains containers, containers contain components)."""
        relationships = []
        
        # Find system components
        systems = [comp for comp in components.values() if comp.type == C4ComponentType.SOFTWARE_SYSTEM]
        containers = [comp for comp in components.values() if comp.type == C4ComponentType.CONTAINER]
        code_components = [comp for comp in components.values() if comp.type == C4ComponentType.COMPONENT]
        
        # Systems contain containers
        for system in systems:
            if not system.metadata.get('external', False):  # Only for internal systems
                for container in containers:
                    relationships.append(C4Relationship(
                        source=system.name,
                        target=container.name,
                        relationship_type=RelationshipType.INCLUDES,
                        description=f"Contains {container.name}"
                    ))
        
        # Containers contain components
        for container in containers:
            if container.metadata.get('container_type') == 'application':
                for component in code_components:
                    relationships.append(C4Relationship(
                        source=container.name,
                        target=component.name,
                        relationship_type=RelationshipType.INCLUDES,
                        description=f"Contains {component.name}"
                    ))
        
        return relationships
    
    def _extract_api_relationships(self, components: Dict[str, C4Component], 
                                 analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """Extract API-related relationships."""
        relationships = []
        
        # Find API components
        api_components = [comp for comp in components.values() 
                         if 'api' in comp.metadata.get('functional_area', '').lower()]
        
        # Find frontend components
        frontend_components = [comp for comp in components.values() 
                             if comp.metadata.get('container_type') == 'frontend']
        
        # Frontend uses API
        for frontend in frontend_components:
            for api in api_components:
                relationships.append(C4Relationship(
                    source=frontend.name,
                    target=api.name,
                    relationship_type=RelationshipType.USES,
                    description="Makes API calls",
                    protocol="HTTPS",
                    technology="REST/JSON"
                ))
        
        return relationships
    
    def _extract_database_relationships(self, components: Dict[str, C4Component], 
                                      analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """Extract database-related relationships."""
        relationships = []
        
        # Find database components
        db_components = [comp for comp in components.values() 
                        if comp.metadata.get('container_type') == 'database']
        
        # Find data access components
        data_components = [comp for comp in components.values() 
                          if 'data' in comp.metadata.get('functional_area', '').lower()]
        
        if not db_components:
            return relationships
        
        # Data access components interact with database
        for data_comp in data_components:
            for db_comp in db_components:
                # Check for read operations
                if self._has_database_operations(data_comp, 'read', analysis_results):
                    relationships.append(C4Relationship(
                        source=data_comp.name,
                        target=db_comp.name,
                        relationship_type=RelationshipType.READS_FROM,
                        description="Reads data",
                        technology=db_comp.technology
                    ))
                
                # Check for write operations
                if self._has_database_operations(data_comp, 'write', analysis_results):
                    relationships.append(C4Relationship(
                        source=data_comp.name,
                        target=db_comp.name,
                        relationship_type=RelationshipType.WRITES_TO,
                        description="Writes data",
                        technology=db_comp.technology
                    ))
        
        return relationships
    
    def _extract_external_relationships(self, components: Dict[str, C4Component], 
                                      analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """Extract relationships with external systems."""
        relationships = []
        
        # Find external systems
        external_systems = [comp for comp in components.values() 
                           if comp.metadata.get('external', False)]
        
        # Find internal components that use external systems
        internal_components = [comp for comp in components.values() 
                             if not comp.metadata.get('external', False) and 
                             comp.type == C4ComponentType.COMPONENT]
        
        for internal_comp in internal_components:
            for external_sys in external_systems:
                # Check if internal component imports anything from external system
                external_imports = external_sys.metadata.get('imports', [])
                component_imports = self._get_component_imports(internal_comp, analysis_results)
                
                if any(ext_imp in component_imports for ext_imp in external_imports):
                    relationships.append(C4Relationship(
                        source=internal_comp.name,
                        target=external_sys.name,
                        relationship_type=RelationshipType.USES,
                        description=f"Uses {external_sys.name} services",
                        metadata={'external': True}
                    ))
        
        return relationships
    
    def _extract_code_relationships(self, components: Dict[str, C4Component], 
                                  analysis_results: Dict[str, ModuleInfo]) -> List[C4Relationship]:
        """Extract relationships based on code structure (inheritance, composition, etc.)."""
        relationships = []
        
        # Find components with code elements
        code_components = [comp for comp in components.values() 
                          if comp.type == C4ComponentType.COMPONENT and comp.code_elements]
        
        for source_comp in code_components:
            for target_comp in code_components:
                if source_comp == target_comp:
                    continue
                
                # Check for method calls between components
                if self._has_method_calls(source_comp, target_comp, analysis_results):
                    relationships.append(C4Relationship(
                        source=source_comp.name,
                        target=target_comp.name,
                        relationship_type=RelationshipType.CALLS,
                        description="Calls methods",
                        metadata={'code_relationship': True}
                    ))
                
                # Check for inheritance relationships
                if self._has_inheritance(source_comp, target_comp, analysis_results):
                    relationships.append(C4Relationship(
                        source=source_comp.name,
                        target=target_comp.name,
                        relationship_type=RelationshipType.EXTENDS,
                        description="Extends/inherits from",
                        metadata={'code_relationship': True}
                    ))
        
        return relationships
    
    def _create_module_component_mapping(self, components: Dict[str, C4Component]) -> Dict[str, str]:
        """Create mapping from module paths to component names."""
        mapping = {}
        
        for comp_name, component in components.items():
            if component.type == C4ComponentType.COMPONENT:
                for source_file in component.source_files:
                    mapping[str(source_file)] = comp_name
        
        return mapping
    
    def _find_component_by_import(self, import_name: str, components: Dict[str, C4Component], 
                                analysis_results: Dict[str, ModuleInfo]) -> Optional[str]:
        """Find which component contains a specific import."""
        # Simple heuristic: check if any component's modules match the import
        for comp_name, component in components.items():
            if component.type == C4ComponentType.COMPONENT:
                for source_file in component.source_files:
                    module_info = analysis_results.get(str(source_file))
                    if module_info:
                        module_name = module_info.path.stem
                        if import_name == module_name or import_name.endswith(f'.{module_name}'):
                            return comp_name
        
        # Check external systems
        for comp_name, component in components.items():
            if component.metadata.get('external', False):
                external_imports = component.metadata.get('imports', [])
                if import_name in external_imports:
                    return comp_name
        
        return None
    
    def _has_database_operations(self, component: C4Component, operation_type: str, 
                               analysis_results: Dict[str, ModuleInfo]) -> bool:
        """Check if component has database operations of specified type."""
        operation_keywords = self.database_operations.get(operation_type, [])
        
        for source_file in component.source_files:
            module_info = analysis_results.get(str(source_file))
            if module_info:
                # Check function names
                for func in module_info.functions:
                    if any(keyword in func.name.lower() for keyword in operation_keywords):
                        return True
                
                # Check class method names
                for cls in module_info.classes:
                    if any(keyword in cls.name.lower() for keyword in operation_keywords):
                        return True
        
        return False
    
    def _get_component_imports(self, component: C4Component, 
                             analysis_results: Dict[str, ModuleInfo]) -> Set[str]:
        """Get all imports used by a component."""
        imports = set()
        
        for source_file in component.source_files:
            module_info = analysis_results.get(str(source_file))
            if module_info:
                imports.update(module_info.imports)
        
        return imports
    
    def _has_method_calls(self, source_comp: C4Component, target_comp: C4Component, 
                         analysis_results: Dict[str, ModuleInfo]) -> bool:
        """Check if source component calls methods from target component."""
        # Get class and function names from target component
        target_names = set()
        for source_file in target_comp.source_files:
            module_info = analysis_results.get(str(source_file))
            if module_info:
                target_names.update(cls.name for cls in module_info.classes)
                target_names.update(func.name for func in module_info.functions)
        
        # Check if source component references any of these names
        source_imports = self._get_component_imports(source_comp, analysis_results)
        
        # Simple heuristic: check if target module is imported by source
        for source_file in source_comp.source_files:
            for target_file in target_comp.source_files:
                target_module = analysis_results.get(str(target_file))
                if target_module:
                    target_module_name = target_module.path.stem
                    if any(target_module_name in imp for imp in source_imports):
                        return True
        
        return False
    
    def _has_inheritance(self, source_comp: C4Component, target_comp: C4Component, 
                        analysis_results: Dict[str, ModuleInfo]) -> bool:
        """Check if source component inherits from target component."""
        # This is a simplified check - would need more sophisticated analysis for real inheritance
        # For now, just check naming patterns that suggest inheritance
        
        target_class_names = set()
        for source_file in target_comp.source_files:
            module_info = analysis_results.get(str(source_file))
            if module_info:
                target_class_names.update(cls.name for cls in module_info.classes)
        
        # Check if source has classes with names suggesting inheritance (e.g., SpecialUser extends User)
        for source_file in source_comp.source_files:
            module_info = analysis_results.get(str(source_file))
            if module_info:
                for cls in module_info.classes:
                    # Simple heuristic: if class name contains target class name, might be inheritance
                    for target_name in target_class_names:
                        if target_name.lower() in cls.name.lower() and target_name != cls.name:
                            return True
        
        return False
    
    def _deduplicate_relationships(self, relationships: List[C4Relationship]) -> List[C4Relationship]:
        """Remove duplicate relationships."""
        seen = set()
        unique_relationships = []
        
        for rel in relationships:
            # Create a unique key for the relationship
            key = (rel.source, rel.target, rel.relationship_type)
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)
        
        return unique_relationships
