"""
LLM Agent System

Integrates with Code LLaMA and other LLMs to understand code structure, relationships, and responsibilities.
"""

from .llm_client import LLMClient, LLMRequest, LLMResponse
from .code_understanding_agent import (
    CodeUnderstandingAgent, 
    CodeStructureAnalysis, 
    ModuleUnderstanding
)
from .relationship_analysis_agent import (
    RelationshipAnalysisAgent,
    CodeRelationship,
    ComponentInterface,
    RelationshipAnalysis
)
from .responsibility_agent import (
    ResponsibilityAgent,
    BusinessResponsibility,
    TechnicalResponsibility,
    ComponentResponsibilities
)
from .llm_orchestrator import (
    LLMOrchestrator,
    ComprehensiveAnalysis,
    SystemAnalysis
)

__all__ = [
    # LLM Client
    'LLMClient',
    'LLMRequest', 
    'LLMResponse',
    
    # Code Understanding Agent
    'CodeUnderstandingAgent',
    'CodeStructureAnalysis',
    'ModuleUnderstanding',
    
    # Relationship Analysis Agent
    'RelationshipAnalysisAgent',
    'CodeRelationship',
    'ComponentInterface',
    'RelationshipAnalysis',
    
    # Responsibility Agent
    'ResponsibilityAgent',
    'BusinessResponsibility',
    'TechnicalResponsibility',
    'ComponentResponsibilities',
    
    # Orchestrator
    'LLMOrchestrator',
    'ComprehensiveAnalysis',
    'SystemAnalysis'
]
