"""
LLM Orchestrator

Coordinates all LLM agents to provide comprehensive code understanding.
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .llm_client import LLMClient
from .code_understanding_agent import CodeUnderstandingAgent, ModuleUnderstanding
from .relationship_analysis_agent import RelationshipAnalysisAgent, RelationshipAnalysis
from .responsibility_agent import ResponsibilityAgent, ComponentResponsibilities

logger = logging.getLogger(__name__)


@dataclass
class ComprehensiveAnalysis:
    """Complete analysis combining all agent results"""
    component_name: str
    file_path: Path
    understanding: ModuleUnderstanding
    relationships: RelationshipAnalysis
    responsibilities: ComponentResponsibilities
    confidence_scores: Dict[str, float]
    analysis_metadata: Dict[str, Any]


@dataclass
class SystemAnalysis:
    """Complete system-wide analysis"""
    components: Dict[str, ComprehensiveAnalysis]
    system_relationships: Dict[str, Any]
    cross_cutting_concerns: Dict[str, Any]
    responsibility_conflicts: Dict[str, Any]
    architectural_patterns: List[str]
    system_health: Dict[str, Any]
    recommendations: List[str]


class LLMOrchestrator:
    """Orchestrates all LLM agents for comprehensive code analysis"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.code_understanding_agent = CodeUnderstandingAgent(llm_client)
        self.relationship_agent = RelationshipAnalysisAgent(llm_client)
        self.responsibility_agent = ResponsibilityAgent(llm_client)
        
    def analyze_component(self, 
                         code_content: str,
                         file_path: Path,
                         language: str,
                         context: Optional[Dict[str, Any]] = None,
                         context_code: Optional[Dict[str, str]] = None) -> ComprehensiveAnalysis:
        """Perform comprehensive analysis of a single component"""
        
        component_name = file_path.stem
        confidence_scores = {}
        analysis_metadata = {
            'analysis_timestamp': None,
            'llm_model': self.llm_client.get_model_info() if hasattr(self.llm_client, 'get_model_info') else 'unknown',
            'language': language,
            'code_size': len(code_content)
        }
        
        logger.info(f"Starting comprehensive analysis of {component_name}")
        
        try:
            # Step 1: Code Understanding
            logger.debug(f"Analyzing code structure for {component_name}")
            understanding = self.code_understanding_agent.understand_module(
                code_content=code_content,
                file_path=file_path,
                language=language,
                context=context
            )
            confidence_scores['understanding'] = 0.8  # Default confidence
            
        except Exception as e:
            logger.warning(f"Code understanding failed for {component_name}: {e}")
            understanding = self._fallback_module_understanding(file_path)
            confidence_scores['understanding'] = 0.3
        
        try:
            # Step 2: Relationship Analysis
            logger.debug(f"Analyzing relationships for {component_name}")
            relationships = self.relationship_agent.analyze_component_relationships(
                component_code=code_content,
                component_name=component_name,
                context_code=context_code or {},
                language=language
            )
            confidence_scores['relationships'] = 0.8
            
        except Exception as e:
            logger.warning(f"Relationship analysis failed for {component_name}: {e}")
            relationships = self._fallback_relationship_analysis(component_name)
            confidence_scores['relationships'] = 0.3
        
        try:
            # Step 3: Responsibility Analysis
            logger.debug(f"Analyzing responsibilities for {component_name}")
            responsibilities = self.responsibility_agent.analyze_component_responsibilities(
                component_code=code_content,
                component_name=component_name,
                context=context,
                language=language
            )
            confidence_scores['responsibilities'] = 0.8
            
        except Exception as e:
            logger.warning(f"Responsibility analysis failed for {component_name}: {e}")
            responsibilities = self._fallback_responsibility_analysis(component_name)
            confidence_scores['responsibilities'] = 0.3
        
        return ComprehensiveAnalysis(
            component_name=component_name,
            file_path=file_path,
            understanding=understanding,
            relationships=relationships,
            responsibilities=responsibilities,
            confidence_scores=confidence_scores,
            analysis_metadata=analysis_metadata
        )
    
    def analyze_system(self, 
                      components: Dict[str, Dict[str, Any]],
                      business_context: Optional[Dict[str, Any]] = None) -> SystemAnalysis:
        """Perform comprehensive analysis of entire system"""
        
        logger.info(f"Starting system-wide analysis of {len(components)} components")
        
        # Step 1: Analyze individual components
        component_analyses = {}
        component_codes = {}
        
        for component_name, component_info in components.items():
            try:
                code_content = component_info['content']
                file_path = Path(component_info['path'])
                language = component_info.get('language', 'python')
                context = component_info.get('context', {})
                
                # Build context code for relationships
                context_code = {k: v['content'] for k, v in components.items() if k != component_name}
                
                analysis = self.analyze_component(
                    code_content=code_content,
                    file_path=file_path,
                    language=language,
                    context=context,
                    context_code=context_code
                )
                
                component_analyses[component_name] = analysis
                component_codes[component_name] = code_content
                
            except Exception as e:
                logger.error(f"Failed to analyze component {component_name}: {e}")
                # Add minimal fallback analysis
                component_analyses[component_name] = self._fallback_comprehensive_analysis(
                    component_name, Path(component_info['path'])
                )
        
        # Step 2: System-wide relationship analysis
        logger.info("Analyzing system-wide relationships")
        try:
            system_relationships = self.relationship_agent.analyze_system_relationships(
                components=component_codes,
                language=components[list(components.keys())[0]].get('language', 'python')
            )
        except Exception as e:
            logger.warning(f"System relationship analysis failed: {e}")
            system_relationships = {}
        
        # Step 3: Cross-cutting concerns
        logger.info("Identifying cross-cutting concerns")
        try:
            relationship_analyses = {name: analysis.relationships for name, analysis in component_analyses.items()}
            cross_cutting_concerns = self.relationship_agent.identify_cross_cutting_concerns(relationship_analyses)
        except Exception as e:
            logger.warning(f"Cross-cutting concern analysis failed: {e}")
            cross_cutting_concerns = {}
        
        # Step 4: Responsibility conflicts
        logger.info("Analyzing responsibility conflicts")
        try:
            responsibility_analyses = {name: analysis.responsibilities for name, analysis in component_analyses.items()}
            responsibility_conflicts = self.responsibility_agent.identify_responsibility_conflicts(responsibility_analyses)
        except Exception as e:
            logger.warning(f"Responsibility conflict analysis failed: {e}")
            responsibility_conflicts = {}
        
        # Step 5: Extract architectural patterns
        architectural_patterns = self._extract_system_patterns(component_analyses)
        
        # Step 6: Assess system health
        system_health = self._assess_system_health(component_analyses, responsibility_conflicts)
        
        # Step 7: Generate recommendations
        recommendations = self._generate_recommendations(
            component_analyses, 
            responsibility_conflicts, 
            cross_cutting_concerns
        )
        
        return SystemAnalysis(
            components=component_analyses,
            system_relationships=system_relationships,
            cross_cutting_concerns=cross_cutting_concerns,
            responsibility_conflicts=responsibility_conflicts,
            architectural_patterns=architectural_patterns,
            system_health=system_health,
            recommendations=recommendations
        )
    
    def export_analysis(self, analysis: SystemAnalysis, output_path: Path) -> None:
        """Export complete analysis to JSON file"""
        
        # Convert to serializable format
        export_data = {
            'components': {},
            'system_relationships': analysis.system_relationships,
            'cross_cutting_concerns': analysis.cross_cutting_concerns,
            'responsibility_conflicts': analysis.responsibility_conflicts,
            'architectural_patterns': analysis.architectural_patterns,
            'system_health': analysis.system_health,
            'recommendations': analysis.recommendations
        }
        
        # Serialize component analyses
        for name, comp_analysis in analysis.components.items():
            export_data['components'][name] = {
                'component_name': comp_analysis.component_name,
                'file_path': str(comp_analysis.file_path),
                'understanding': asdict(comp_analysis.understanding),
                'relationships': asdict(comp_analysis.relationships),
                'responsibilities': asdict(comp_analysis.responsibilities),
                'confidence_scores': comp_analysis.confidence_scores,
                'analysis_metadata': comp_analysis.analysis_metadata
            }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Analysis exported to {output_path}")
    
    def _extract_system_patterns(self, component_analyses: Dict[str, ComprehensiveAnalysis]) -> List[str]:
        """Extract architectural patterns from component analyses"""
        
        all_patterns = set()
        for analysis in component_analyses.values():
            # From relationships
            all_patterns.update(analysis.relationships.architectural_patterns)
            
            # From understanding
            structure_analysis = getattr(analysis.understanding, 'structure_analysis', None)
            if structure_analysis and hasattr(structure_analysis, 'design_patterns'):
                all_patterns.update(structure_analysis.design_patterns)
        
        return list(all_patterns)
    
    def _assess_system_health(self, 
                            component_analyses: Dict[str, ComprehensiveAnalysis],
                            responsibility_conflicts: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall system health"""
        
        # Calculate average confidence scores
        total_confidence = 0
        confidence_count = 0
        
        for analysis in component_analyses.values():
            for score in analysis.confidence_scores.values():
                total_confidence += score
                confidence_count += 1
        
        avg_confidence = total_confidence / max(confidence_count, 1)
        
        # Count various metrics
        high_coupling_components = sum(
            1 for analysis in component_analyses.values()
            if analysis.relationships.coupling_level in ['tight', 'high']
        )
        
        high_complexity_components = sum(
            1 for analysis in component_analyses.values()
            if analysis.relationships.integration_complexity == 'high'
        )
        
        # Analyze conflicts
        conflict_count = (
            len(responsibility_conflicts.get('business_capability_overlaps', {})) +
            len(responsibility_conflicts.get('data_ownership_conflicts', {}))
        )
        
        # Determine overall health
        health_score = avg_confidence
        if conflict_count > len(component_analyses) * 0.3:
            health_score -= 0.2
        if high_coupling_components > len(component_analyses) * 0.4:
            health_score -= 0.15
        if high_complexity_components > len(component_analyses) * 0.3:
            health_score -= 0.1
        
        health_level = 'good'
        if health_score < 0.4:
            health_level = 'poor'
        elif health_score < 0.7:
            health_level = 'fair'
        
        return {
            'overall_score': health_score,
            'health_level': health_level,
            'analysis_confidence': avg_confidence,
            'high_coupling_components': high_coupling_components,
            'high_complexity_components': high_complexity_components,
            'responsibility_conflicts': conflict_count,
            'total_components': len(component_analyses)
        }
    
    def _generate_recommendations(self, 
                                component_analyses: Dict[str, ComprehensiveAnalysis],
                                responsibility_conflicts: Dict[str, Any],
                                cross_cutting_concerns: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        
        recommendations = []
        
        # Coupling recommendations
        high_coupling = [
            name for name, analysis in component_analyses.items()
            if analysis.relationships.coupling_level in ['tight', 'high']
        ]
        if high_coupling:
            recommendations.append(
                f"Consider reducing coupling for components: {', '.join(high_coupling[:3])}"
            )
        
        # Complexity recommendations
        high_complexity = [
            name for name, analysis in component_analyses.items()
            if analysis.relationships.integration_complexity == 'high'
        ]
        if high_complexity:
            recommendations.append(
                f"Simplify integration complexity for: {', '.join(high_complexity[:3])}"
            )
        
        # Responsibility conflict recommendations
        if responsibility_conflicts.get('business_capability_overlaps'):
            recommendations.append(
                "Resolve overlapping business capabilities between components"
            )
        
        if responsibility_conflicts.get('data_ownership_conflicts'):
            recommendations.append(
                "Clarify data ownership to avoid consistency issues"
            )
        
        # Cross-cutting concerns recommendations
        shared_infra = cross_cutting_concerns.get('shared_infrastructure', [])
        if len(shared_infra) > 5:
            recommendations.append(
                "Consider centralizing shared infrastructure components"
            )
        
        return recommendations
    
    # Fallback methods
    def _fallback_module_understanding(self, file_path: Path):
        """Fallback when module understanding fails"""
        from .code_understanding_agent import ModuleUnderstanding
        return ModuleUnderstanding(
            file_path=file_path,
            primary_purpose='Unknown - analysis failed',
            secondary_purposes=[],
            c4_classification='component',
            interfaces_provided=[],
            interfaces_consumed=[],
            data_entities=[],
            business_rules=[],
            technical_concerns=[],
            quality_indicators={}
        )
    
    def _fallback_relationship_analysis(self, component_name: str):
        """Fallback when relationship analysis fails"""
        from .relationship_analysis_agent import RelationshipAnalysis
        return RelationshipAnalysis(
            component_name=component_name,
            direct_relationships=[],
            interfaces=[],
            dependency_groups={},
            architectural_patterns=[],
            integration_complexity='medium',
            coupling_level='moderate'
        )
    
    def _fallback_responsibility_analysis(self, component_name: str):
        """Fallback when responsibility analysis fails"""
        from .responsibility_agent import ComponentResponsibilities
        return ComponentResponsibilities(
            component_name=component_name,
            primary_purpose='Unknown - analysis failed',
            business_responsibilities=[],
            technical_responsibilities=[],
            responsibility_boundaries={},
            change_drivers=[],
            risk_factors=[],
            improvement_opportunities=[]
        )
    
    def _fallback_comprehensive_analysis(self, component_name: str, file_path: Path) -> ComprehensiveAnalysis:
        """Fallback comprehensive analysis"""
        return ComprehensiveAnalysis(
            component_name=component_name,
            file_path=file_path,
            understanding=self._fallback_module_understanding(file_path),
            relationships=self._fallback_relationship_analysis(component_name),
            responsibilities=self._fallback_responsibility_analysis(component_name),
            confidence_scores={'understanding': 0.1, 'relationships': 0.1, 'responsibilities': 0.1},
            analysis_metadata={'error': 'Analysis failed, using fallback'}
        )
