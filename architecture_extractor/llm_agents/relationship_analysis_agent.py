"""
Relationship Analysis Agent

Uses LLM to identify and analyze relationships between code components.
"""

import json
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

from .llm_client import LLMClient, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class CodeRelationship:
    """Relationship between code components"""
    source_component: str
    target_component: str
    relationship_type: str  # 'uses', 'depends_on', 'implements', 'extends', 'contains', 'calls', 'imports'
    relationship_strength: str  # 'strong', 'medium', 'weak'
    description: str
    evidence: List[str]  # specific code evidence for the relationship
    bidirectional: bool = False
    confidence: float = 0.5


@dataclass
class ComponentInterface:
    """Interface provided or consumed by a component"""
    name: str
    type: str  # 'api', 'function', 'class', 'service', 'database', 'queue'
    direction: str  # 'provides', 'consumes'
    description: str
    protocols: List[str]  # HTTP, gRPC, database, etc.
    data_formats: List[str]  # JSON, XML, binary, etc.


@dataclass
class RelationshipAnalysis:
    """Complete relationship analysis for a component or system"""
    component_name: str
    direct_relationships: List[CodeRelationship]
    interfaces: List[ComponentInterface]
    dependency_groups: Dict[str, List[str]]  # grouped by type
    architectural_patterns: List[str]  # patterns evident from relationships
    integration_complexity: str  # 'low', 'medium', 'high'
    coupling_level: str  # 'loose', 'moderate', 'tight'


class RelationshipAnalysisAgent:
    """Agent for analyzing relationships between code components"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    def analyze_component_relationships(self, 
                                      component_code: str,
                                      component_name: str,
                                      context_code: Dict[str, str],
                                      language: str) -> RelationshipAnalysis:
        """Analyze relationships for a specific component"""
        
        system_prompt = """You are an expert software architect analyzing code relationships for C4 diagrams.
        Analyze the provided component and its context to identify:
        1. Direct relationships (uses, depends_on, implements, extends, contains, calls, imports)
        2. Interfaces provided and consumed
        3. Dependency groups and patterns
        4. Integration complexity
        5. Coupling level
        
        For each relationship, provide:
        - Source and target components
        - Relationship type and strength
        - Evidence from the code
        - Description
        
        Respond with a JSON object matching this schema:
        {
            "direct_relationships": [
                {
                    "source_component": "string",
                    "target_component": "string", 
                    "relationship_type": "string",
                    "relationship_strength": "string",
                    "description": "string",
                    "evidence": ["string"],
                    "bidirectional": false,
                    "confidence": 0.0-1.0
                }
            ],
            "interfaces": [
                {
                    "name": "string",
                    "type": "string",
                    "direction": "string",
                    "description": "string",
                    "protocols": ["string"],
                    "data_formats": ["string"]
                }
            ],
            "dependency_groups": {
                "external_services": ["string"],
                "databases": ["string"],
                "frameworks": ["string"],
                "internal_modules": ["string"]
            },
            "architectural_patterns": ["string"],
            "integration_complexity": "string",
            "coupling_level": "string"
        }"""
        
        # Prepare context information
        context_info = ""
        if context_code:
            context_info = "\n\nContext from related files:\n"
            for file_name, code in list(context_code.items())[:3]:  # Limit context
                context_info += f"\n--- {file_name} ---\n{code[:500]}...\n"
        
        user_prompt = f"""Analyze relationships for component '{component_name}' in this {language} code:

```{language}
{component_code}
```{context_info}

Identify all relationships this component has with:
1. Other internal components/modules
2. External services and APIs
3. Databases and data stores
4. Frameworks and libraries
5. Infrastructure components

Focus on:
- Import/dependency statements
- Function calls and method invocations
- API endpoints consumed or provided
- Database connections and queries
- Message passing or event handling
- Configuration dependencies

Provide specific evidence from the code for each relationship."""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2048
        )
        
        try:
            response = self.llm_client.generate(request)
            analysis_data = self._parse_json_response(response.content)
            
            # Parse relationships
            relationships = []
            for rel_data in analysis_data.get('direct_relationships', []):
                relationships.append(CodeRelationship(
                    source_component=rel_data.get('source_component', component_name),
                    target_component=rel_data.get('target_component', 'unknown'),
                    relationship_type=rel_data.get('relationship_type', 'uses'),
                    relationship_strength=rel_data.get('relationship_strength', 'medium'),
                    description=rel_data.get('description', ''),
                    evidence=rel_data.get('evidence', []),
                    bidirectional=rel_data.get('bidirectional', False),
                    confidence=rel_data.get('confidence', 0.5)
                ))
            
            # Parse interfaces
            interfaces = []
            for int_data in analysis_data.get('interfaces', []):
                interfaces.append(ComponentInterface(
                    name=int_data.get('name', ''),
                    type=int_data.get('type', 'unknown'),
                    direction=int_data.get('direction', 'provides'),
                    description=int_data.get('description', ''),
                    protocols=int_data.get('protocols', []),
                    data_formats=int_data.get('data_formats', [])
                ))
            
            return RelationshipAnalysis(
                component_name=component_name,
                direct_relationships=relationships,
                interfaces=interfaces,
                dependency_groups=analysis_data.get('dependency_groups', {}),
                architectural_patterns=analysis_data.get('architectural_patterns', []),
                integration_complexity=analysis_data.get('integration_complexity', 'medium'),
                coupling_level=analysis_data.get('coupling_level', 'moderate')
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze relationships for {component_name}: {e}")
            return self._fallback_relationship_analysis(component_name)
    
    def analyze_system_relationships(self, 
                                   components: Dict[str, str],
                                   language: str) -> Dict[str, RelationshipAnalysis]:
        """Analyze relationships across an entire system"""
        
        system_prompt = """You are an expert software architect analyzing system-wide relationships for C4 diagrams.
        Given multiple components, identify all relationships between them and with external systems.
        
        Focus on:
        1. Component-to-component relationships
        2. Shared dependencies
        3. System boundaries
        4. Integration patterns
        5. Data flow patterns
        
        Respond with a JSON object where each key is a component name and value follows the relationship analysis schema."""
        
        # Prepare components summary
        components_summary = "System components:\n"
        for name, code in components.items():
            components_summary += f"\n--- {name} ---\n{code[:300]}...\n"
        
        user_prompt = f"""Analyze system-wide relationships in this {language} system:

{components_summary}

Identify:
1. How components interact with each other
2. Shared external dependencies
3. System boundaries and interfaces
4. Data flow patterns
5. Integration complexity across the system

For each component, provide detailed relationship analysis."""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=3072
        )
        
        try:
            response = self.llm_client.generate(request)
            system_data = self._parse_json_response(response.content)
            
            results = {}
            for component_name in components.keys():
                if component_name in system_data:
                    comp_data = system_data[component_name]
                    results[component_name] = self._parse_relationship_analysis(component_name, comp_data)
                else:
                    # Fallback for missing components
                    results[component_name] = self._fallback_relationship_analysis(component_name)
            
            return results
            
        except Exception as e:
            logger.warning(f"Failed to analyze system relationships: {e}")
            # Return fallback analyses for all components
            return {name: self._fallback_relationship_analysis(name) for name in components.keys()}
    
    def identify_cross_cutting_concerns(self, 
                                      relationship_analyses: Dict[str, RelationshipAnalysis]) -> Dict[str, Any]:
        """Identify cross-cutting concerns and system-wide patterns"""
        
        all_relationships = []
        all_patterns = []
        all_dependencies = {}
        
        for analysis in relationship_analyses.values():
            all_relationships.extend(analysis.direct_relationships)
            all_patterns.extend(analysis.architectural_patterns)
            
            for dep_type, deps in analysis.dependency_groups.items():
                if dep_type not in all_dependencies:
                    all_dependencies[dep_type] = set()
                all_dependencies[dep_type].update(deps)
        
        system_prompt = """You are an expert software architect analyzing cross-cutting concerns.
        Based on the relationship data, identify:
        1. Shared infrastructure components
        2. Common architectural patterns
        3. Integration bottlenecks
        4. Security boundaries
        5. Performance critical paths
        6. Data consistency requirements
        
        Respond with a JSON object describing these cross-cutting concerns."""
        
        user_prompt = f"""Analyze these system-wide patterns and dependencies:

Relationships: {len(all_relationships)} total relationships
Patterns found: {list(set(all_patterns))}
Dependency types: {list(all_dependencies.keys())}

Common external dependencies:
{json.dumps({k: list(v) for k, v in all_dependencies.items()}, indent=2)}

Identify cross-cutting concerns, shared infrastructure, and system-wide patterns that affect architecture design."""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1024
        )
        
        try:
            response = self.llm_client.generate(request)
            return self._parse_json_response(response.content)
        except Exception as e:
            logger.warning(f"Failed to identify cross-cutting concerns: {e}")
            return {
                "shared_infrastructure": list(all_dependencies.get('external_services', [])),
                "common_patterns": list(set(all_patterns)),
                "integration_points": [],
                "security_boundaries": [],
                "performance_concerns": []
            }
    
    def _parse_relationship_analysis(self, component_name: str, data: Dict[str, Any]) -> RelationshipAnalysis:
        """Parse relationship analysis from JSON data"""
        
        relationships = []
        for rel_data in data.get('direct_relationships', []):
            relationships.append(CodeRelationship(
                source_component=rel_data.get('source_component', component_name),
                target_component=rel_data.get('target_component', 'unknown'),
                relationship_type=rel_data.get('relationship_type', 'uses'),
                relationship_strength=rel_data.get('relationship_strength', 'medium'),
                description=rel_data.get('description', ''),
                evidence=rel_data.get('evidence', []),
                bidirectional=rel_data.get('bidirectional', False),
                confidence=rel_data.get('confidence', 0.5)
            ))
        
        interfaces = []
        for int_data in data.get('interfaces', []):
            interfaces.append(ComponentInterface(
                name=int_data.get('name', ''),
                type=int_data.get('type', 'unknown'),
                direction=int_data.get('direction', 'provides'),
                description=int_data.get('description', ''),
                protocols=int_data.get('protocols', []),
                data_formats=int_data.get('data_formats', [])
            ))
        
        return RelationshipAnalysis(
            component_name=component_name,
            direct_relationships=relationships,
            interfaces=interfaces,
            dependency_groups=data.get('dependency_groups', {}),
            architectural_patterns=data.get('architectural_patterns', []),
            integration_complexity=data.get('integration_complexity', 'medium'),
            coupling_level=data.get('coupling_level', 'moderate')
        )
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse JSON response: {content[:200]}...")
            return {}
    
    def _fallback_relationship_analysis(self, component_name: str) -> RelationshipAnalysis:
        """Fallback relationship analysis when LLM fails"""
        return RelationshipAnalysis(
            component_name=component_name,
            direct_relationships=[],
            interfaces=[],
            dependency_groups={},
            architectural_patterns=[],
            integration_complexity='medium',
            coupling_level='moderate'
        )
