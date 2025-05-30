"""
Architecture Analyzer

Main orchestrator for architecture extraction and analysis with LLM integration.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import logging

from .component_classifier import ComponentClassifier, C4Component, C4ComponentType
from .relationship_extractor import RelationshipExtractor, C4Relationship
from .llm_agents import LLMClient, LLMOrchestrator, SystemAnalysis
from codebase_parser.code_analyzer import ModuleInfo

logger = logging.getLogger(__name__)


class ArchitectureAnalyzer:
    """
    Main analyzer that orchestrates component classification and relationship extraction.
    Enhanced with LLM-powered analysis capabilities.
    """
    
    def __init__(self, enable_llm: bool = True, llm_client: Optional[LLMClient] = None):
        self.classifier = ComponentClassifier()
        self.relationship_extractor = RelationshipExtractor()
        
        # LLM integration
        self.enable_llm = enable_llm
        self.llm_client = llm_client
        self.llm_orchestrator = None
        
        if self.enable_llm:
            if not self.llm_client:
                # Try to initialize LLM client
                try:
                    self.llm_client = LLMClient()
                    logger.info("Initialized LLM client successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize LLM client: {e}")
                    self.enable_llm = False
            
            if self.llm_client:
                self.llm_orchestrator = LLMOrchestrator(self.llm_client)
    def analyze_architecture(self, analysis_results: Dict[str, ModuleInfo], 
                           repository_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform complete architecture analysis with optional LLM enhancement.
        
        Args:
            analysis_results: Results from code analysis
            repository_info: Repository metadata
            
        Returns:
            Complete architecture analysis results
        """
        print("🏗️  Starting architecture analysis...")
        
        # Step 1: Classify components (traditional approach)
        print("📋 Classifying C4 components...")
        components = self.classifier.classify_architecture(analysis_results, repository_info)
        print(f"✅ Identified {len(components)} components")
        
        # Step 2: Extract relationships (traditional approach)
        print("🔗 Extracting relationships...")
        relationships = self.relationship_extractor.extract_relationships(components, analysis_results)
        print(f"✅ Found {len(relationships)} relationships")
        
        # Step 3: LLM-enhanced analysis (if enabled)
        llm_analysis = None
        if self.enable_llm and self.llm_orchestrator:
            print("🤖 Performing LLM-enhanced analysis...")
            try:
                llm_analysis = self._perform_llm_analysis(analysis_results, repository_info)
                print("✅ LLM analysis completed")
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                print("⚠️  LLM analysis failed, continuing with traditional analysis")
        
        # Step 4: Generate architecture insights
        print("💡 Generating architecture insights...")
        insights = self._generate_insights(components, relationships, analysis_results, llm_analysis)
        
        # Step 5: Create architecture summary
        architecture_data = {
            'metadata': {
                'project_name': repository_info.get('name', 'Unknown'),
                'analysis_timestamp': str(Path().cwd()),  # Placeholder
                'total_components': len(components),
                'total_relationships': len(relationships),
                'llm_enhanced': llm_analysis is not None
            },
            'components': self._serialize_components(components),
            'relationships': self._serialize_relationships(relationships),
            'insights': insights,
            'c4_levels': self._organize_by_c4_levels(components),
            'architecture_patterns': self._identify_patterns(components, relationships),
            'llm_analysis': self._serialize_llm_analysis(llm_analysis) if llm_analysis else None
        }
        
        print("✅ Architecture analysis complete!")
        return architecture_data
    
    def _serialize_components(self, components: Dict[str, C4Component]) -> Dict[str, Dict[str, Any]]:
        """Serialize components to JSON-compatible format."""
        serialized = {}
        
        for name, component in components.items():
            serialized[name] = {
                'name': component.name,
                'type': component.type.value,
                'description': component.description,
                'technology': component.technology,
                'responsibilities': component.responsibilities,
                'interfaces': component.interfaces,
                'source_files': [str(path) for path in component.source_files],
                'code_elements_count': len(component.code_elements),
                'metadata': component.metadata
            }
        
        return serialized
    
    def _serialize_relationships(self, relationships: List[C4Relationship]) -> List[Dict[str, Any]]:
        """Serialize relationships to JSON-compatible format."""
        return [
            {
                'source': rel.source,
                'target': rel.target,
                'type': rel.relationship_type.value,
                'description': rel.description,
                'technology': rel.technology,
                'protocol': rel.protocol,
                'metadata': rel.metadata
            }
            for rel in relationships
        ]
    
    def _organize_by_c4_levels(self, components: Dict[str, C4Component]) -> Dict[str, List[str]]:
        """Organize components by C4 levels."""
        levels = {
            'context': [],  # Systems and external systems
            'containers': [],  # Containers
            'components': [],  # Components
            'code': []  # Code elements (if needed)
        }
        
        for name, component in components.items():
            if component.type == C4ComponentType.SOFTWARE_SYSTEM:
                levels['context'].append(name)
            elif component.type == C4ComponentType.CONTAINER:
                levels['containers'].append(name)
            elif component.type == C4ComponentType.COMPONENT:
                levels['components'].append(name)
        
        return levels
    
    def _identify_patterns(self, components: Dict[str, C4Component], 
                          relationships: List[C4Relationship]) -> Dict[str, Any]:
        """Identify common architecture patterns."""
        patterns = {
            'layered_architecture': False,
            'microservices': False,
            'mvc_pattern': False,
            'repository_pattern': False,
            'api_gateway': False,
            'event_driven': False
        }
        
        component_names = [comp.name.lower() for comp in components.values()]
        functional_areas = [comp.metadata.get('functional_area', '') for comp in components.values()]
        
        # Check for MVC pattern
        if any('controller' in area for area in functional_areas) and \
           any('model' in area for area in functional_areas):
            patterns['mvc_pattern'] = True
        
        # Check for repository pattern
        if any('data_access' in area for area in functional_areas) or \
           any('repository' in name for name in component_names):
            patterns['repository_pattern'] = True
        
        # Check for layered architecture
        layers = ['controller', 'service', 'data']
        if sum(any(layer in area for area in functional_areas) for layer in layers) >= 2:
            patterns['layered_architecture'] = True
        
        # Check for API pattern
        if any('api' in area for area in functional_areas):
            patterns['api_gateway'] = True
        
        # Simple microservices check (multiple containers)
        containers = [comp for comp in components.values() if comp.type == C4ComponentType.CONTAINER]
        if len(containers) > 2:  # More than app + database
            patterns['microservices'] = True
        
        return patterns
    
    def _generate_insights(self, components: Dict[str, C4Component], 
                          relationships: List[C4Relationship],
                          analysis_results: Dict[str, ModuleInfo], llm_analysis: Optional[SystemAnalysis] = None) -> Dict[str, Any]:
        """Generate architecture insights and recommendations."""
        insights = {
            'complexity_analysis': self._analyze_complexity(components, relationships),
            'architectural_health': self._assess_health(components, relationships),
            'recommendations': self._generate_recommendations(components, relationships),
            'metrics': self._calculate_metrics(components, relationships, analysis_results)
        }
        
        # Integrate LLM analysis results if available
        if llm_analysis:
            insights['llm_analysis'] = self._serialize_llm_analysis(llm_analysis)
        
        return insights
    
    def _analyze_complexity(self, components: Dict[str, C4Component], 
                           relationships: List[C4Relationship]) -> Dict[str, Any]:
        """Analyze architectural complexity."""
        # Calculate component complexity
        component_complexity = {}
        for name, component in components.items():
            complexity_score = 0
            
            # More code elements = higher complexity
            complexity_score += len(component.code_elements) * 0.1
            
            # More relationships = higher complexity
            related_count = sum(1 for rel in relationships if rel.source == name or rel.target == name)
            complexity_score += related_count * 0.5
            
            # External dependencies increase complexity
            if component.metadata.get('external', False):
                complexity_score += 1
            
            component_complexity[name] = round(complexity_score, 2)
        
        return {
            'component_complexity': component_complexity,
            'average_complexity': round(sum(component_complexity.values()) / len(component_complexity), 2) if component_complexity else 0,
            'most_complex_component': max(component_complexity.items(), key=lambda x: x[1]) if component_complexity else None
        }
    
    def _assess_health(self, components: Dict[str, C4Component], 
                      relationships: List[C4Relationship]) -> Dict[str, Any]:
        """Assess architectural health."""
        health_metrics = {
            'modularity_score': 0,
            'coupling_score': 0,
            'cohesion_score': 0,
            'overall_health': 'Unknown'
        }
        
        if not components:
            return health_metrics
        
        # Calculate modularity (number of components vs relationships)
        num_components = len([c for c in components.values() if c.type == C4ComponentType.COMPONENT])
        num_relationships = len(relationships)
        
        if num_components > 0:
            # Lower ratio = better modularity
            modularity_ratio = num_relationships / num_components
            health_metrics['modularity_score'] = max(0, min(10, 10 - modularity_ratio))
        
        # Calculate coupling (external dependencies)
        external_deps = sum(1 for c in components.values() if c.metadata.get('external', False))
        total_components = len(components)
        coupling_ratio = external_deps / total_components if total_components > 0 else 0
        health_metrics['coupling_score'] = max(0, min(10, 10 - coupling_ratio * 10))
        
        # Calculate cohesion (components with clear functional areas)
        components_with_areas = sum(1 for c in components.values() 
                                  if c.metadata.get('functional_area') and c.type == C4ComponentType.COMPONENT)
        cohesion_ratio = components_with_areas / num_components if num_components > 0 else 0
        health_metrics['cohesion_score'] = cohesion_ratio * 10
        
        # Overall health
        avg_score = (health_metrics['modularity_score'] + 
                    health_metrics['coupling_score'] + 
                    health_metrics['cohesion_score']) / 3
        
        if avg_score >= 8:
            health_metrics['overall_health'] = 'Excellent'
        elif avg_score >= 6:
            health_metrics['overall_health'] = 'Good'
        elif avg_score >= 4:
            health_metrics['overall_health'] = 'Fair'
        else:
            health_metrics['overall_health'] = 'Poor'
        
        return health_metrics
    
    def _generate_recommendations(self, components: Dict[str, C4Component], 
                                relationships: List[C4Relationship]) -> List[str]:
        """Generate architecture improvement recommendations."""
        recommendations = []
        
        # Check for highly coupled components
        component_connections = {}
        for rel in relationships:
            component_connections[rel.source] = component_connections.get(rel.source, 0) + 1
            component_connections[rel.target] = component_connections.get(rel.target, 0) + 1
        
        for comp_name, connections in component_connections.items():
            if connections > 5:  # Arbitrary threshold
                recommendations.append(f"Consider breaking down '{comp_name}' - it has {connections} connections")
        
        # Check for missing architectural layers
        functional_areas = set()
        for component in components.values():
            if component.type == C4ComponentType.COMPONENT:
                area = component.metadata.get('functional_area', '')
                if area:
                    functional_areas.add(area)
        
        expected_layers = {'controllers', 'services', 'data_access'}
        missing_layers = expected_layers - functional_areas
        
        if missing_layers:
            recommendations.append(f"Consider adding {', '.join(missing_layers)} layer(s) for better separation of concerns")
        
        # Check for external dependencies
        external_systems = [c for c in components.values() if c.metadata.get('external', False)]
        if len(external_systems) > 3:
            recommendations.append("High number of external dependencies - consider consolidating or creating facade patterns")
        
        # Check for database access patterns
        db_relationships = [r for r in relationships if r.relationship_type.value in ['reads_from', 'writes_to']]
        direct_db_access = set(r.source for r in db_relationships)
        
        if len(direct_db_access) > 1:
            recommendations.append("Multiple components access database directly - consider implementing repository pattern")
        
        if not recommendations:
            recommendations.append("Architecture looks well-structured! Continue following current patterns.")
        
        return recommendations
    
    def _calculate_metrics(self, components: Dict[str, C4Component], 
                          relationships: List[C4Relationship],
                          analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Any]:
        """Calculate various architecture metrics."""
        metrics = {
            'component_count_by_type': {},
            'relationship_count_by_type': {},
            'lines_of_code_by_component': {},
            'files_by_component': {},
            'dependency_depth': 0
        }
        
        # Count components by type
        for component in components.values():
            comp_type = component.type.value
            metrics['component_count_by_type'][comp_type] = metrics['component_count_by_type'].get(comp_type, 0) + 1
        
        # Count relationships by type
        for relationship in relationships:
            rel_type = relationship.relationship_type.value
            metrics['relationship_count_by_type'][rel_type] = metrics['relationship_count_by_type'].get(rel_type, 0) + 1
        
        # Calculate lines of code and files per component
        for name, component in components.items():
            if component.type == C4ComponentType.COMPONENT:
                total_lines = 0
                file_count = len(component.source_files)
                
                for source_file in component.source_files:
                    module_info = analysis_results.get(str(source_file))
                    if module_info:
                        # Estimate lines based on code elements (rough approximation)
                        total_lines += len(module_info.classes) * 20  # Assume 20 lines per class
                        total_lines += len(module_info.functions) * 10  # Assume 10 lines per function
                
                metrics['lines_of_code_by_component'][name] = total_lines
                metrics['files_by_component'][name] = file_count
        
        # Calculate dependency depth (simplified)
        dependency_graph = {}
        for rel in relationships:
            if rel.relationship_type.value == 'depends_on':
                if rel.source not in dependency_graph:
                    dependency_graph[rel.source] = []
                dependency_graph[rel.source].append(rel.target)
        
        # Find maximum depth
        max_depth = 0
        for source in dependency_graph:
            depth = self._calculate_dependency_depth(source, dependency_graph, set())
            max_depth = max(max_depth, depth)
        
        metrics['dependency_depth'] = max_depth
        
        return metrics
    
    def _calculate_dependency_depth(self, node: str, graph: Dict[str, List[str]], 
                                  visited: set, depth: int = 0) -> int:
        """Calculate dependency depth recursively."""
        if node in visited or node not in graph:
            return depth
        
        visited.add(node)
        max_child_depth = depth
        
        for child in graph[node]:
            child_depth = self._calculate_dependency_depth(child, graph, visited.copy(), depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def save_results(self, architecture_data: Dict[str, Any], output_path: Path):
        """Save architecture analysis results to file."""
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save complete results as JSON
        json_path = output_path / "architecture_analysis.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(architecture_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Architecture analysis saved to {json_path}")
        
        # Save summary report
        self._generate_summary_report(architecture_data, output_path)
    
    def _generate_summary_report(self, architecture_data: Dict[str, Any], output_path: Path):
        """Generate a human-readable summary report."""
        report_path = output_path / "architecture_summary.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# Architecture Analysis Report\n\n")
            f.write(f"**Project:** {architecture_data['metadata']['project_name']}\n")
            f.write(f"**Components:** {architecture_data['metadata']['total_components']}\n")
            f.write(f"**Relationships:** {architecture_data['metadata']['total_relationships']}\n\n")
            
            # Components by type
            f.write("## Components by Type\n\n")
            for comp_type, components in architecture_data['c4_levels'].items():
                if components:
                    f.write(f"### {comp_type.title()}\n")
                    for comp_name in components:
                        comp_data = architecture_data['components'][comp_name]
                        f.write(f"- **{comp_name}**: {comp_data['description']}\n")
                    f.write("\n")
            
            # Architecture patterns
            f.write("## Identified Patterns\n\n")
            patterns = architecture_data['architecture_patterns']
            for pattern, present in patterns.items():
                status = "✅" if present else "❌"
                f.write(f"- {status} {pattern.replace('_', ' ').title()}\n")
            f.write("\n")
            
            # Health assessment
            f.write("## Architecture Health\n\n")
            health = architecture_data['insights']['architectural_health']
            f.write(f"**Overall Health:** {health['overall_health']}\n")
            f.write(f"- Modularity Score: {health['modularity_score']:.1f}/10\n")
            f.write(f"- Coupling Score: {health['coupling_score']:.1f}/10\n")
            f.write(f"- Cohesion Score: {health['cohesion_score']:.1f}/10\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            for rec in architecture_data['insights']['recommendations']:
                f.write(f"- {rec}\n")
            
        print(f"✅ Architecture summary saved to {report_path}")
    
    def _perform_llm_analysis(self, analysis_results: Dict[str, ModuleInfo], 
                            repository_info: Dict[str, Any]) -> Optional[SystemAnalysis]:
        """Perform LLM-enhanced analysis of the codebase"""
        
        # Prepare components for LLM analysis
        components_for_llm = {}
        
        for module_name, module_info in analysis_results.items():
            try:
                # Read the source file content
                if module_info.path.exists():
                    with open(module_info.path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    components_for_llm[module_name] = {
                        'content': content,
                        'path': str(module_info.path),
                        'language': module_info.language,
                        'context': {
                            'lines_of_code': module_info.lines_of_code,
                            'functions_count': len(module_info.functions),
                            'classes_count': len(module_info.classes),
                            'complexity': module_info.complexity_score
                        }
                    }
            except Exception as e:
                logger.warning(f"Failed to prepare {module_name} for LLM analysis: {e}")
                continue
        
        # Add business context from repository info
        business_context = {
            'project_name': repository_info.get('name', 'Unknown'),
            'project_type': repository_info.get('type', 'Unknown'),
            'technologies': repository_info.get('technologies', []),
            'description': repository_info.get('description', '')
        }
        
        # Perform system-wide LLM analysis
        try:
            return self.llm_orchestrator.analyze_system(
                components=components_for_llm,
                business_context=business_context
            )
        except Exception as e:
            logger.error(f"LLM system analysis failed: {e}")
            return None
    
    def _serialize_llm_analysis(self, llm_analysis: SystemAnalysis) -> Dict[str, Any]:
        """Serialize LLM analysis results"""
        if not llm_analysis:
            return None
        
        return {
            'system_health': llm_analysis.system_health,
            'architectural_patterns': llm_analysis.architectural_patterns,
            'cross_cutting_concerns': llm_analysis.cross_cutting_concerns,
            'responsibility_conflicts': llm_analysis.responsibility_conflicts,
            'recommendations': llm_analysis.recommendations,
            'components_analysis': {
                name: {
                    'understanding': {
                        'primary_purpose': comp.understanding.primary_purpose,
                        'c4_classification': comp.understanding.c4_classification,
                        'interfaces_provided': comp.understanding.interfaces_provided,
                        'interfaces_consumed': comp.understanding.interfaces_consumed
                    },
                    'relationships': {
                        'direct_relationships_count': len(comp.relationships.direct_relationships),
                        'integration_complexity': comp.relationships.integration_complexity,
                        'coupling_level': comp.relationships.coupling_level
                    },
                    'responsibilities': {
                        'primary_purpose': comp.responsibilities.primary_purpose,
                        'business_responsibilities_count': len(comp.responsibilities.business_responsibilities),
                        'technical_responsibilities_count': len(comp.responsibilities.technical_responsibilities)
                    },
                    'confidence_scores': comp.confidence_scores
                }
                for name, comp in llm_analysis.components.items()
            }
        }
