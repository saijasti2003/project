"""
Code Understanding Agent

Uses LLM to analyze code structure, patterns, and architectural significance.
"""

import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from pathlib import Path
import logging

from .llm_client import LLMClient, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class CodeStructureAnalysis:
    """Analysis of code structure and patterns"""
    component_type: str  # 'service', 'controller', 'model', 'utility', 'config', etc.
    architectural_layer: str  # 'presentation', 'business', 'data', 'infrastructure'
    design_patterns: List[str]  # patterns like 'singleton', 'factory', 'mvc', etc.
    complexity_level: str  # 'low', 'medium', 'high'
    responsibilities: List[str]  # what this code is responsible for
    key_abstractions: List[str]  # main classes, interfaces, or concepts
    external_dependencies: List[str]  # external systems or libraries used
    confidence: float  # confidence in the analysis (0.0 to 1.0)


@dataclass
class ModuleUnderstanding:
    """Understanding of a complete module/file"""
    file_path: Path
    primary_purpose: str
    secondary_purposes: List[str]
    c4_classification: str  # 'person', 'software_system', 'container', 'component'
    interfaces_provided: List[str]  # APIs, functions, classes exposed
    interfaces_consumed: List[str]  # external APIs, services used
    data_entities: List[str]  # data structures, models handled
    business_rules: List[str]  # business logic or rules implemented
    technical_concerns: List[str]  # logging, caching, security, etc.
    quality_indicators: Dict[str, Any]  # metrics about code quality


class CodeUnderstandingAgent:
    """Agent for understanding code structure and architectural significance"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    def analyze_code_structure(self, 
                             code_content: str, 
                             file_path: Path,
                             language: str) -> CodeStructureAnalysis:
        """Analyze the structure and patterns in code"""
        
        system_prompt = """You are an expert software architect analyzing code for C4 architecture diagrams.
        Analyze the provided code and identify:
        1. Component type (service, controller, model, utility, config, etc.)
        2. Architectural layer (presentation, business, data, infrastructure)
        3. Design patterns used
        4. Complexity level
        5. Key responsibilities
        6. Main abstractions
        7. External dependencies
        
        Respond with a JSON object matching this schema:
        {
            "component_type": "string",
            "architectural_layer": "string", 
            "design_patterns": ["string"],
            "complexity_level": "string",
            "responsibilities": ["string"],
            "key_abstractions": ["string"],
            "external_dependencies": ["string"],
            "confidence": 0.0-1.0
        }"""
        
        user_prompt = f"""Analyze this {language} code from {file_path}:

```{language}
{code_content}
```

Focus on architectural significance and patterns. Consider:
- What role does this code play in the overall system?
- What design patterns are evident?
- What are the key responsibilities?
- How complex is this code?
- What external systems does it interact with?"""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1024
        )
        
        try:
            response = self.llm_client.generate(request)
            analysis_data = self._parse_json_response(response.content)
            
            return CodeStructureAnalysis(
                component_type=analysis_data.get('component_type', 'unknown'),
                architectural_layer=analysis_data.get('architectural_layer', 'unknown'),
                design_patterns=analysis_data.get('design_patterns', []),
                complexity_level=analysis_data.get('complexity_level', 'medium'),
                responsibilities=analysis_data.get('responsibilities', []),
                key_abstractions=analysis_data.get('key_abstractions', []),
                external_dependencies=analysis_data.get('external_dependencies', []),
                confidence=analysis_data.get('confidence', 0.5)
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze code structure for {file_path}: {e}")
            return self._fallback_structure_analysis(code_content, file_path)
    
    def understand_module(self, 
                         code_content: str,
                         file_path: Path, 
                         language: str,
                         context: Optional[Dict[str, Any]] = None) -> ModuleUnderstanding:
        """Get comprehensive understanding of a module"""
        
        system_prompt = """You are an expert software architect creating C4 architecture diagrams.
        Analyze the provided code module and provide comprehensive understanding including:
        1. Primary and secondary purposes
        2. C4 classification (person, software_system, container, component)
        3. Interfaces provided and consumed
        4. Data entities handled
        5. Business rules implemented
        6. Technical concerns addressed
        7. Quality indicators
        
        Respond with a JSON object matching this schema:
        {
            "primary_purpose": "string",
            "secondary_purposes": ["string"],
            "c4_classification": "string",
            "interfaces_provided": ["string"],
            "interfaces_consumed": ["string"], 
            "data_entities": ["string"],
            "business_rules": ["string"],
            "technical_concerns": ["string"],
            "quality_indicators": {
                "maintainability": "string",
                "testability": "string",
                "reusability": "string",
                "performance_concerns": "string"
            }
        }"""
        
        context_info = ""
        if context:
            context_info = f"\nAdditional context:\n{json.dumps(context, indent=2)}"
        
        user_prompt = f"""Analyze this {language} module from {file_path}:{context_info}

```{language}
{code_content}
```

Provide a comprehensive architectural understanding focusing on:
- What is the main purpose and responsibility?
- How does it fit in C4 architecture (Component, Container, etc.)?
- What interfaces does it provide to other components?
- What external interfaces does it use?
- What data does it handle?
- What business logic does it implement?
- What technical concerns does it address?"""

        request = LLMRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1536
        )
        
        try:
            response = self.llm_client.generate(request)
            understanding_data = self._parse_json_response(response.content)
            
            return ModuleUnderstanding(
                file_path=file_path,
                primary_purpose=understanding_data.get('primary_purpose', 'Unknown'),
                secondary_purposes=understanding_data.get('secondary_purposes', []),
                c4_classification=understanding_data.get('c4_classification', 'component'),
                interfaces_provided=understanding_data.get('interfaces_provided', []),
                interfaces_consumed=understanding_data.get('interfaces_consumed', []),
                data_entities=understanding_data.get('data_entities', []),
                business_rules=understanding_data.get('business_rules', []),
                technical_concerns=understanding_data.get('technical_concerns', []),
                quality_indicators=understanding_data.get('quality_indicators', {})
            )
            
        except Exception as e:
            logger.warning(f"Failed to understand module {file_path}: {e}")
            return self._fallback_module_understanding(file_path)
    
    def analyze_batch(self, 
                     code_files: List[Dict[str, Any]],
                     max_batch_size: int = 5) -> List[ModuleUnderstanding]:
        """Analyze multiple files in batches for efficiency"""
        results = []
        
        for i in range(0, len(code_files), max_batch_size):
            batch = code_files[i:i + max_batch_size]
            batch_results = []
            
            for file_info in batch:
                try:
                    understanding = self.understand_module(
                        code_content=file_info['content'],
                        file_path=Path(file_info['path']),
                        language=file_info.get('language', 'unknown'),
                        context=file_info.get('context')
                    )
                    batch_results.append(understanding)
                except Exception as e:
                    logger.error(f"Failed to analyze {file_info['path']}: {e}")
                    # Add fallback understanding
                    batch_results.append(self._fallback_module_understanding(Path(file_info['path'])))
            
            results.extend(batch_results)
            
        return results
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            # Try to find JSON in the response
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return empty dict if parsing fails
            logger.warning(f"Failed to parse JSON response: {content[:200]}...")
            return {}
    
    def _fallback_structure_analysis(self, code_content: str, file_path: Path) -> CodeStructureAnalysis:
        """Fallback analysis when LLM fails"""
        # Simple heuristic-based analysis
        file_name = file_path.name.lower()
        
        component_type = 'unknown'
        if 'controller' in file_name or 'handler' in file_name:
            component_type = 'controller'
        elif 'service' in file_name:
            component_type = 'service'
        elif 'model' in file_name or 'entity' in file_name:
            component_type = 'model'
        elif 'util' in file_name or 'helper' in file_name:
            component_type = 'utility'
        elif 'config' in file_name:
            component_type = 'config'
        
        return CodeStructureAnalysis(
            component_type=component_type,
            architectural_layer='unknown',
            design_patterns=[],
            complexity_level='medium',
            responsibilities=[],
            key_abstractions=[],
            external_dependencies=[],
            confidence=0.3
        )
    
    def _fallback_module_understanding(self, file_path: Path) -> ModuleUnderstanding:
        """Fallback understanding when LLM fails"""
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
