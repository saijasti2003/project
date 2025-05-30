"""
Semantic Analyzer

Provides advanced semantic analysis capabilities for understanding code intent and relationships.
"""

import re
from typing import Dict, List, Set, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from codebase_parser.code_analyzer import ModuleInfo, CodeElement


@dataclass
class SemanticPattern:
    """Represents a semantic pattern found in code"""
    pattern_type: str
    confidence: float
    description: str
    evidence: List[str]
    location: Optional[str] = None


class SemanticAnalyzer:
    """
    Provides semantic analysis to understand code intent and architectural patterns.
    """
    
    def __init__(self):
        # Patterns for identifying architectural intentions
        self.intent_patterns = {
            'authentication': {
                'keywords': ['auth', 'login', 'logout', 'session', 'token', 'jwt', 'oauth', 'password'],
                'functions': ['authenticate', 'authorize', 'login', 'logout', 'validate_token'],
                'classes': ['User', 'Auth', 'Session', 'Token']
            },
            'data_persistence': {
                'keywords': ['save', 'load', 'store', 'persist', 'db', 'database', 'repository', 'dao'],
                'functions': ['save', 'find', 'create', 'update', 'delete', 'query'],
                'classes': ['Repository', 'DAO', 'Model', 'Entity']
            },
            'api_endpoint': {
                'keywords': ['route', 'endpoint', 'api', 'rest', 'get', 'post', 'put', 'delete'],
                'functions': ['get', 'post', 'put', 'delete', 'patch'],
                'classes': ['Controller', 'Handler', 'Resource']
            },
            'business_logic': {
                'keywords': ['process', 'calculate', 'validate', 'transform', 'business', 'service'],
                'functions': ['process', 'calculate', 'validate', 'transform', 'execute'],
                'classes': ['Service', 'Processor', 'Calculator', 'Validator']
            },
            'configuration': {
                'keywords': ['config', 'settings', 'env', 'environment', 'properties'],
                'functions': ['load_config', 'get_setting', 'configure'],
                'classes': ['Config', 'Settings', 'Environment']
            },
            'notification': {
                'keywords': ['notify', 'send', 'email', 'sms', 'alert', 'message'],
                'functions': ['send_email', 'send_notification', 'alert', 'notify'],
                'classes': ['Notifier', 'EmailService', 'MessageQueue']
            },
            'validation': {
                'keywords': ['validate', 'check', 'verify', 'sanitize', 'clean'],
                'functions': ['validate', 'check', 'verify', 'is_valid'],
                'classes': ['Validator', 'Checker']
            },
            'caching': {
                'keywords': ['cache', 'redis', 'memcache', 'store', 'temp'],
                'functions': ['cache', 'get_cached', 'set_cache', 'clear_cache'],
                'classes': ['Cache', 'CacheManager']
            }
        }
        
        # Patterns for architectural styles
        self.architecture_patterns = {
            'mvc': {
                'indicators': ['model', 'view', 'controller'],
                'structure': ['models/', 'views/', 'controllers/']
            },
            'layered': {
                'indicators': ['presentation', 'business', 'data', 'service'],
                'structure': ['presentation/', 'business/', 'data/', 'services/']
            },
            'microservices': {
                'indicators': ['service', 'api', 'endpoint', 'gateway'],
                'structure': ['services/', 'gateway/', 'apis/']
            },
            'repository': {
                'indicators': ['repository', 'dao', 'data_access'],
                'structure': ['repositories/', 'dao/', 'data/']
            }
        }
    
    def analyze_semantic_patterns(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Any]:
        """
        Analyze code for semantic patterns and architectural intent.
        
        Args:
            analysis_results: Results from code analysis
            
        Returns:
            Dictionary containing semantic analysis results
        """
        print("🧠 Starting semantic analysis...")
        
        # Analyze intent patterns
        intent_analysis = self._analyze_intent_patterns(analysis_results)
        
        # Analyze architectural patterns
        architecture_analysis = self._analyze_architecture_patterns(analysis_results)
        
        # Analyze naming conventions
        naming_analysis = self._analyze_naming_conventions(analysis_results)
        
        # Analyze complexity patterns
        complexity_analysis = self._analyze_complexity_patterns(analysis_results)
        
        # Generate semantic insights
        insights = self._generate_semantic_insights(
            intent_analysis, architecture_analysis, naming_analysis, complexity_analysis
        )
        
        return {
            'intent_patterns': intent_analysis,
            'architecture_patterns': architecture_analysis,
            'naming_conventions': naming_analysis,
            'complexity_patterns': complexity_analysis,
            'insights': insights
        }
    
    def _analyze_intent_patterns(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, List[SemanticPattern]]:
        """Analyze code for intent patterns."""
        patterns_found = {}
        
        for intent_type, pattern_config in self.intent_patterns.items():
            patterns_found[intent_type] = []
            
            for file_path, module_info in analysis_results.items():
                module_patterns = self._find_intent_in_module(module_info, intent_type, pattern_config)
                patterns_found[intent_type].extend(module_patterns)
        
        return patterns_found
    
    def _find_intent_in_module(self, module_info: ModuleInfo, intent_type: str, 
                              pattern_config: Dict[str, List[str]]) -> List[SemanticPattern]:
        """Find intent patterns in a single module."""
        patterns = []
        evidence = []
        confidence = 0.0
        
        # Check module name
        module_name = module_info.path.stem.lower()
        if any(keyword in module_name for keyword in pattern_config['keywords']):
            evidence.append(f"Module name contains {intent_type} keywords")
            confidence += 0.3
        
        # Check function names
        for func in module_info.functions:
            func_name = func.name.lower()
            if any(keyword in func_name for keyword in pattern_config['keywords']):
                evidence.append(f"Function '{func.name}' suggests {intent_type}")
                confidence += 0.2
            
            if func_name in [f.lower() for f in pattern_config['functions']]:
                evidence.append(f"Function '{func.name}' is typical for {intent_type}")
                confidence += 0.4
        
        # Check class names
        for cls in module_info.classes:
            cls_name = cls.name
            if any(keyword in cls_name.lower() for keyword in pattern_config['keywords']):
                evidence.append(f"Class '{cls.name}' suggests {intent_type}")
                confidence += 0.3
            
            if cls_name in pattern_config['classes']:
                evidence.append(f"Class '{cls.name}' is typical for {intent_type}")
                confidence += 0.5
        
        # Check imports
        for imp in module_info.imports:
            if any(keyword in imp.lower() for keyword in pattern_config['keywords']):
                evidence.append(f"Import '{imp}' suggests {intent_type}")
                confidence += 0.1
        
        if evidence and confidence > 0.3:  # Threshold for considering a pattern
            pattern = SemanticPattern(
                pattern_type=intent_type,
                confidence=min(confidence, 1.0),
                description=f"Module shows evidence of {intent_type} functionality",
                evidence=evidence,
                location=str(module_info.path)
            )
            patterns.append(pattern)
        
        return patterns
    
    def _analyze_architecture_patterns(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Any]:
        """Analyze for architectural patterns."""
        architecture_analysis = {}
        
        # Get all module paths and directory structure
        all_paths = [module_info.path for module_info in analysis_results.values()]
        directory_structure = self._extract_directory_structure(all_paths)
        
        for pattern_name, pattern_config in self.architecture_patterns.items():
            score = self._calculate_architecture_pattern_score(
                analysis_results, directory_structure, pattern_config
            )
            
            architecture_analysis[pattern_name] = {
                'score': score,
                'present': score > 0.5,
                'confidence': min(score, 1.0)
            }
        
        return architecture_analysis
    
    def _extract_directory_structure(self, paths: List[Path]) -> Set[str]:
        """Extract directory structure from file paths."""
        directories = set()
        
        for path in paths:
            # Get all parent directories
            current = path.parent
            while current != Path('.'):
                directories.add(current.name.lower())
                current = current.parent
        
        return directories
    
    def _calculate_architecture_pattern_score(self, analysis_results: Dict[str, ModuleInfo], 
                                            directory_structure: Set[str], 
                                            pattern_config: Dict[str, List[str]]) -> float:
        """Calculate score for an architecture pattern."""
        score = 0.0
        
        # Check for structural indicators
        structure_indicators = pattern_config.get('structure', [])
        for indicator in structure_indicators:
            clean_indicator = indicator.rstrip('/').lower()
            if clean_indicator in directory_structure:
                score += 0.3
        
        # Check for naming indicators in modules
        naming_indicators = pattern_config.get('indicators', [])
        for module_info in analysis_results.values():
            module_name = module_info.path.stem.lower()
            parent_dir = module_info.path.parent.name.lower()
            
            for indicator in naming_indicators:
                if indicator in module_name or indicator in parent_dir:
                    score += 0.1
        
        return min(score, 1.0)
    
    def _analyze_naming_conventions(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Any]:
        """Analyze naming conventions used in the codebase."""
        naming_stats = {
            'snake_case_files': 0,
            'camel_case_files': 0,
            'kebab_case_files': 0,
            'snake_case_functions': 0,
            'camel_case_functions': 0,
            'pascal_case_classes': 0,
            'snake_case_classes': 0,
            'total_files': len(analysis_results),
            'total_functions': 0,
            'total_classes': 0
        }
        
        for module_info in analysis_results.values():
            # Analyze file names
            file_name = module_info.path.stem
            if self._is_snake_case(file_name):
                naming_stats['snake_case_files'] += 1
            elif self._is_camel_case(file_name):
                naming_stats['camel_case_files'] += 1
            elif self._is_kebab_case(file_name):
                naming_stats['kebab_case_files'] += 1
            
            # Analyze function names
            for func in module_info.functions:
                naming_stats['total_functions'] += 1
                if self._is_snake_case(func.name):
                    naming_stats['snake_case_functions'] += 1
                elif self._is_camel_case(func.name):
                    naming_stats['camel_case_functions'] += 1
            
            # Analyze class names
            for cls in module_info.classes:
                naming_stats['total_classes'] += 1
                if self._is_pascal_case(cls.name):
                    naming_stats['pascal_case_classes'] += 1
                elif self._is_snake_case(cls.name):
                    naming_stats['snake_case_classes'] += 1
        
        # Calculate consistency scores
        consistency = self._calculate_naming_consistency(naming_stats)
        
        return {
            'statistics': naming_stats,
            'consistency': consistency,
            'recommendations': self._generate_naming_recommendations(naming_stats, consistency)
        }
    
    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r'^[a-z_][a-z0-9_]*$', name) is not None
    
    def _is_camel_case(self, name: str) -> bool:
        """Check if name follows camelCase convention."""
        return re.match(r'^[a-z][a-zA-Z0-9]*$', name) is not None and any(c.isupper() for c in name)
    
    def _is_pascal_case(self, name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return re.match(r'^[A-Z][a-zA-Z0-9]*$', name) is not None
    
    def _is_kebab_case(self, name: str) -> bool:
        """Check if name follows kebab-case convention."""
        return re.match(r'^[a-z-][a-z0-9-]*$', name) is not None and '-' in name
    
    def _calculate_naming_consistency(self, stats: Dict[str, int]) -> Dict[str, float]:
        """Calculate naming consistency scores."""
        consistency = {}
        
        # File naming consistency
        if stats['total_files'] > 0:
            file_consistency = max(
                stats['snake_case_files'],
                stats['camel_case_files'],
                stats['kebab_case_files']
            ) / stats['total_files']
            consistency['files'] = file_consistency
        
        # Function naming consistency
        if stats['total_functions'] > 0:
            function_consistency = max(
                stats['snake_case_functions'],
                stats['camel_case_functions']
            ) / stats['total_functions']
            consistency['functions'] = function_consistency
        
        # Class naming consistency
        if stats['total_classes'] > 0:
            class_consistency = max(
                stats['pascal_case_classes'],
                stats['snake_case_classes']
            ) / stats['total_classes']
            consistency['classes'] = class_consistency
        
        return consistency
    
    def _generate_naming_recommendations(self, stats: Dict[str, int], 
                                       consistency: Dict[str, float]) -> List[str]:
        """Generate naming convention recommendations."""
        recommendations = []
        
        # Check file naming
        if consistency.get('files', 0) < 0.8:
            recommendations.append("Consider standardizing file naming convention (prefer snake_case for Python)")
        
        # Check function naming
        if consistency.get('functions', 0) < 0.8:
            recommendations.append("Consider standardizing function naming convention (prefer snake_case for Python)")
        
        # Check class naming
        if consistency.get('classes', 0) < 0.8:
            recommendations.append("Consider standardizing class naming convention (prefer PascalCase)")
        
        return recommendations
    
    def _analyze_complexity_patterns(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Any]:
        """Analyze complexity patterns in the codebase."""
        complexity_data = {
            'modules_by_complexity': {},
            'average_functions_per_module': 0,
            'average_classes_per_module': 0,
            'hotspots': []  # Modules with high complexity
        }
        
        total_functions = 0
        total_classes = 0
        
        for file_path, module_info in analysis_results.items():
            module_name = module_info.path.stem
            
            # Calculate module complexity
            num_functions = len(module_info.functions)
            num_classes = len(module_info.classes)
            num_imports = len(module_info.imports)
            
            # Simple complexity score
            complexity_score = (num_functions * 0.5) + (num_classes * 1.0) + (num_imports * 0.1)
            
            complexity_data['modules_by_complexity'][module_name] = {
                'score': complexity_score,
                'functions': num_functions,
                'classes': num_classes,
                'imports': num_imports
            }
            
            total_functions += num_functions
            total_classes += num_classes
            
            # Identify hotspots (high complexity modules)
            if complexity_score > 10:  # Arbitrary threshold
                complexity_data['hotspots'].append({
                    'module': module_name,
                    'score': complexity_score,
                    'path': str(module_info.path)
                })
        
        # Calculate averages
        if analysis_results:
            complexity_data['average_functions_per_module'] = total_functions / len(analysis_results)
            complexity_data['average_classes_per_module'] = total_classes / len(analysis_results)
        
        return complexity_data
    
    def _generate_semantic_insights(self, intent_analysis: Dict, architecture_analysis: Dict,
                                  naming_analysis: Dict, complexity_analysis: Dict) -> List[str]:
        """Generate high-level semantic insights."""
        insights = []
        
        # Intent insights
        dominant_intents = []
        for intent_type, patterns in intent_analysis.items():
            if len(patterns) > 2:  # Threshold for considering dominant
                dominant_intents.append(intent_type)
        
        if dominant_intents:
            insights.append(f"Primary functional areas: {', '.join(dominant_intents)}")
        
        # Architecture insights
        detected_patterns = [pattern for pattern, data in architecture_analysis.items() 
                           if data['present']]
        if detected_patterns:
            insights.append(f"Follows {', '.join(detected_patterns)} architectural pattern(s)")
        
        # Naming insights
        file_consistency = naming_analysis['consistency'].get('files', 0)
        if file_consistency > 0.9:
            insights.append("Excellent naming consistency across the codebase")
        elif file_consistency < 0.6:
            insights.append("Inconsistent naming conventions detected")
        
        # Complexity insights
        hotspots = complexity_analysis.get('hotspots', [])
        if len(hotspots) > 3:
            insights.append(f"Multiple complexity hotspots detected ({len(hotspots)} modules)")
        elif len(hotspots) == 0:
            insights.append("Well-balanced complexity distribution")
        
        return insights
