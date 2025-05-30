"""
Responsibility Agent

Uses LLM to determine code responsibilities and business logic mapping.
"""

import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import logging

from .llm_client import LLMClient, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class BusinessResponsibility:
    """Business responsibility of a code component"""
    name: str
    description: str
    business_capability: str  # high-level business capability
    functional_area: str  # specific functional area
    stakeholders: List[str]  # who cares about this responsibility
    business_rules: List[str]  # specific business rules implemented
    data_owned: List[str]  # data entities this component owns
    service_level: str  # 'critical', 'important', 'supporting'
    compliance_requirements: List[str]  # regulatory or compliance needs


@dataclass
class TechnicalResponsibility:
    """Technical responsibility of a code component"""
    name: str
    description: str
    technical_capability: str  # authentication, data_processing, integration, etc.
    quality_attributes: List[str]  # performance, security, reliability, etc.
    technologies_used: List[str]  # specific technologies and frameworks
    integration_points: List[str]  # external systems integrated with
    scalability_concerns: List[str]  # scaling challenges or requirements
    maintenance_complexity: str  # 'low', 'medium', 'high'


@dataclass
class ComponentResponsibilities:
    """Complete responsibility analysis for a component"""
    component_name: str
    primary_purpose: str
    business_responsibilities: List[BusinessResponsibility]
    technical_responsibilities: List[TechnicalResponsibility]
    responsibility_boundaries: Dict[str, str]  # what this component should/shouldn't do
    change_drivers: List[str]  # what would cause this component to change
    risk_factors: List[str]  # potential risks or concerns
    improvement_opportunities: List[str]  # suggestions for improvement


class ResponsibilityAgent:
    """Agent for determining code responsibilities and business logic mapping"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    def analyze_component_responsibilities(self, 
                                         component_code: str,
                                         component_name: str,
                                         context: Optional[Dict[str, Any]] = None,
                                         language: str = 'python') -> ComponentResponsibilities:
        """Analyze the responsibilities of a code component"""
        
        system_prompt = """You are an expert business analyst and software architect.
        Analyze the provided code component to identify its responsibilities both from business and technical perspectives.
        
        For business responsibilities, consider:
        - What business capabilities does this component enable?
        - What business rules does it implement?
        - What data does it own or manage?
        - Who are the stakeholders that care about this component?
        
        For technical responsibilities, consider:
        - What technical capabilities does it provide?
        - What quality attributes are important (performance, security, etc.)?
        - What technologies and frameworks does it use?
        - What are its integration responsibilities?
        
        Respond with a JSON object matching this schema:
        {
            "primary_purpose": "string",
            "business_responsibilities": [
                {
                    "name": "string",
                    "description": "string",
                    "business_capability": "string",
                    "functional_area": "string",
                    "stakeholders": ["string"],
                    "business_rules": ["string"],
                    "data_owned": ["string"],
                    "service_level": "string",
                    "compliance_requirements": ["string"]
                }
            ],
            "technical_responsibilities": [
                {
                    "name": "string",
                    "description": "string",
                    "technical_capability": "string",
                    "quality_attributes": ["string"],
                    "technologies_used": ["string"],
                    "integration_points": ["string"],
                    "scalability_concerns": ["string"],
                    "maintenance_complexity": "string"
                }
            ],
            "responsibility_boundaries": {
                "should_do": "string",
                "should_not_do": "string"
            },
            "change_drivers": ["string"],
            "risk_factors": ["string"],
            "improvement_opportunities": ["string"]
        }"""
        
        # Prepare context information
        context_info = ""
        if context:
            context_info = f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"
        
        user_prompt = f"""Analyze the responsibilities of component '{component_name}' in this {language} code:{context_info}

```{language}
{component_code}
```

Focus on identifying:
1. The primary business purpose and value this component provides
2. Specific business capabilities and rules it implements
3. Technical capabilities and quality responsibilities
4. Clear boundaries of what it should and shouldn't do
5. What would cause this component to change
6. Potential risks and improvement opportunities

Consider both the business value and technical implementation aspects."""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2048
        )
        
        try:
            response = self.llm_client.generate(request)
            analysis_data = self._parse_json_response(response.content)
            
            # Parse business responsibilities
            business_responsibilities = []
            for br_data in analysis_data.get('business_responsibilities', []):
                business_responsibilities.append(BusinessResponsibility(
                    name=br_data.get('name', ''),
                    description=br_data.get('description', ''),
                    business_capability=br_data.get('business_capability', ''),
                    functional_area=br_data.get('functional_area', ''),
                    stakeholders=br_data.get('stakeholders', []),
                    business_rules=br_data.get('business_rules', []),
                    data_owned=br_data.get('data_owned', []),
                    service_level=br_data.get('service_level', 'supporting'),
                    compliance_requirements=br_data.get('compliance_requirements', [])
                ))
            
            # Parse technical responsibilities
            technical_responsibilities = []
            for tr_data in analysis_data.get('technical_responsibilities', []):
                technical_responsibilities.append(TechnicalResponsibility(
                    name=tr_data.get('name', ''),
                    description=tr_data.get('description', ''),
                    technical_capability=tr_data.get('technical_capability', ''),
                    quality_attributes=tr_data.get('quality_attributes', []),
                    technologies_used=tr_data.get('technologies_used', []),
                    integration_points=tr_data.get('integration_points', []),
                    scalability_concerns=tr_data.get('scalability_concerns', []),
                    maintenance_complexity=tr_data.get('maintenance_complexity', 'medium')
                ))
            
            return ComponentResponsibilities(
                component_name=component_name,
                primary_purpose=analysis_data.get('primary_purpose', 'Unknown'),
                business_responsibilities=business_responsibilities,
                technical_responsibilities=technical_responsibilities,
                responsibility_boundaries=analysis_data.get('responsibility_boundaries', {}),
                change_drivers=analysis_data.get('change_drivers', []),
                risk_factors=analysis_data.get('risk_factors', []),
                improvement_opportunities=analysis_data.get('improvement_opportunities', [])
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze responsibilities for {component_name}: {e}")
            return self._fallback_responsibility_analysis(component_name)
    
    def analyze_system_responsibilities(self, 
                                      components: Dict[str, str],
                                      business_context: Optional[Dict[str, Any]] = None,
                                      language: str = 'python') -> Dict[str, ComponentResponsibilities]:
        """Analyze responsibilities across the entire system"""
        
        system_prompt = """You are an expert enterprise architect analyzing system-wide responsibilities.
        Given multiple components and business context, identify how responsibilities are distributed across the system.
        
        Consider:
        1. How business capabilities are divided among components
        2. Overlapping or conflicting responsibilities
        3. Missing capabilities or gaps
        4. Proper separation of concerns
        5. Business-to-technical alignment
        
        For each component, provide detailed responsibility analysis."""
        
        # Prepare business context
        business_info = ""
        if business_context:
            business_info = f"\n\nBusiness context:\n{json.dumps(business_context, indent=2)}"
        
        # Prepare components summary
        components_summary = "\nSystem components:\n"
        for name, code in components.items():
            components_summary += f"\n--- {name} ---\n{code[:400]}...\n"
        
        user_prompt = f"""Analyze responsibilities across this {language} system:{business_info}{components_summary}

For each component, identify:
1. Its unique business responsibilities and value
2. Technical responsibilities and capabilities
3. How it fits in the overall business architecture
4. Proper responsibility boundaries
5. Potential overlaps or gaps with other components

Ensure clear separation of concerns and proper business-technical alignment."""

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
                    results[component_name] = self._parse_component_responsibilities(component_name, comp_data)
                else:
                    # Analyze individual component if not in system analysis
                    results[component_name] = self.analyze_component_responsibilities(
                        components[component_name], 
                        component_name, 
                        business_context,
                        language
                    )
            
            return results
            
        except Exception as e:
            logger.warning(f"Failed to analyze system responsibilities: {e}")
            # Fall back to individual component analysis
            results = {}
            for name, code in components.items():
                results[name] = self.analyze_component_responsibilities(
                    code, name, business_context, language
                )
            return results
    
    def identify_responsibility_conflicts(self, 
                                        component_responsibilities: Dict[str, ComponentResponsibilities]) -> Dict[str, Any]:
        """Identify conflicts, overlaps, and gaps in responsibilities"""
        
        all_business_caps = {}
        all_technical_caps = {}
        all_data_owned = {}
        
        # Collect all responsibilities
        for comp_name, responsibilities in component_responsibilities.items():
            for br in responsibilities.business_responsibilities:
                if br.business_capability not in all_business_caps:
                    all_business_caps[br.business_capability] = []
                all_business_caps[br.business_capability].append(comp_name)
                
                for data in br.data_owned:
                    if data not in all_data_owned:
                        all_data_owned[data] = []
                    all_data_owned[data].append(comp_name)
            
            for tr in responsibilities.technical_responsibilities:
                if tr.technical_capability not in all_technical_caps:
                    all_technical_caps[tr.technical_capability] = []
                all_technical_caps[tr.technical_capability].append(comp_name)
        
        system_prompt = """You are an expert enterprise architect analyzing responsibility distribution.
        Based on the capability mapping, identify:
        1. Overlapping responsibilities that could cause conflicts
        2. Gaps where important capabilities might be missing
        3. Recommendations for better responsibility distribution
        4. Potential consolidation opportunities
        
        Respond with a JSON object describing these issues and recommendations."""
        
        user_prompt = f"""Analyze this responsibility distribution across components:

Business capabilities:
{json.dumps(all_business_caps, indent=2)}

Technical capabilities:
{json.dumps(all_technical_caps, indent=2)}

Data ownership:
{json.dumps(all_data_owned, indent=2)}

Identify:
1. Capabilities handled by multiple components (potential conflicts)
2. Data owned by multiple components (potential consistency issues)
3. Missing capabilities or gaps
4. Recommendations for improvement"""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1024
        )
        
        try:
            response = self.llm_client.generate(request)
            conflict_analysis = self._parse_json_response(response.content)
            
            # Add computed overlaps
            conflict_analysis['computed_overlaps'] = {
                'business_capability_overlaps': {k: v for k, v in all_business_caps.items() if len(v) > 1},
                'technical_capability_overlaps': {k: v for k, v in all_technical_caps.items() if len(v) > 1},
                'data_ownership_conflicts': {k: v for k, v in all_data_owned.items() if len(v) > 1}
            }
            
            return conflict_analysis
            
        except Exception as e:
            logger.warning(f"Failed to identify responsibility conflicts: {e}")
            return {
                'business_capability_overlaps': {k: v for k, v in all_business_caps.items() if len(v) > 1},
                'technical_capability_overlaps': {k: v for k, v in all_technical_caps.items() if len(v) > 1},
                'data_ownership_conflicts': {k: v for k, v in all_data_owned.items() if len(v) > 1},
                'recommendations': [],
                'gaps_identified': []
            }
    
    def _parse_component_responsibilities(self, component_name: str, data: Dict[str, Any]) -> ComponentResponsibilities:
        """Parse component responsibilities from JSON data"""
        
        business_responsibilities = []
        for br_data in data.get('business_responsibilities', []):
            business_responsibilities.append(BusinessResponsibility(
                name=br_data.get('name', ''),
                description=br_data.get('description', ''),
                business_capability=br_data.get('business_capability', ''),
                functional_area=br_data.get('functional_area', ''),
                stakeholders=br_data.get('stakeholders', []),
                business_rules=br_data.get('business_rules', []),
                data_owned=br_data.get('data_owned', []),
                service_level=br_data.get('service_level', 'supporting'),
                compliance_requirements=br_data.get('compliance_requirements', [])
            ))
        
        technical_responsibilities = []
        for tr_data in data.get('technical_responsibilities', []):
            technical_responsibilities.append(TechnicalResponsibility(
                name=tr_data.get('name', ''),
                description=tr_data.get('description', ''),
                technical_capability=tr_data.get('technical_capability', ''),
                quality_attributes=tr_data.get('quality_attributes', []),
                technologies_used=tr_data.get('technologies_used', []),
                integration_points=tr_data.get('integration_points', []),
                scalability_concerns=tr_data.get('scalability_concerns', []),
                maintenance_complexity=tr_data.get('maintenance_complexity', 'medium')
            ))
        
        return ComponentResponsibilities(
            component_name=component_name,
            primary_purpose=data.get('primary_purpose', 'Unknown'),
            business_responsibilities=business_responsibilities,
            technical_responsibilities=technical_responsibilities,
            responsibility_boundaries=data.get('responsibility_boundaries', {}),
            change_drivers=data.get('change_drivers', []),
            risk_factors=data.get('risk_factors', []),
            improvement_opportunities=data.get('improvement_opportunities', [])
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
    
    def _fallback_responsibility_analysis(self, component_name: str) -> ComponentResponsibilities:
        """Fallback responsibility analysis when LLM fails"""
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
