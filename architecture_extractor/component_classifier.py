"""
Component Classifier

Classifies code elements into C4 architecture components (Person, Software System, Container, Component).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from enum import Enum

from codebase_parser.code_analyzer import ModuleInfo, CodeElement


class C4ComponentType(Enum):
    """C4 architecture component types"""
    PERSON = "person"
    SOFTWARE_SYSTEM = "software_system"
    CONTAINER = "container"
    COMPONENT = "component"


@dataclass
class C4Component:
    """Represents a C4 architecture component"""
    name: str
    type: C4ComponentType
    description: str
    technology: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    source_files: Set[Path] = field(default_factory=set)
    code_elements: List[CodeElement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitectureContext:
    """Context information for architecture analysis"""
    project_name: str
    project_type: str  # web_app, microservice, library, etc.
    framework: Optional[str] = None
    database_type: Optional[str] = None
    has_api: bool = False
    has_ui: bool = False
    deployment_patterns: Set[str] = field(default_factory=set)


class ComponentClassifier:
    """
    Classifies code elements into C4 architecture components.
    """
    
    def __init__(self):
        self.framework_patterns = {
            'flask': {'type': 'web_framework', 'container_type': 'web_application'},
            'django': {'type': 'web_framework', 'container_type': 'web_application'},
            'fastapi': {'type': 'api_framework', 'container_type': 'api_application'},
            'spring': {'type': 'web_framework', 'container_type': 'web_application'},
            'express': {'type': 'web_framework', 'container_type': 'web_application'},
            'react': {'type': 'frontend_framework', 'container_type': 'spa'},
            'angular': {'type': 'frontend_framework', 'container_type': 'spa'},
            'vue': {'type': 'frontend_framework', 'container_type': 'spa'}
        }
        
        self.database_patterns = {
            'sqlite', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'dynamodb'
        }
        
        self.api_patterns = {
            'rest', 'graphql', 'grpc', 'soap', 'api', 'endpoint', 'controller'
        }
    
    def classify_architecture(self, analysis_results: Dict[str, ModuleInfo], 
                            repository_info: Dict[str, Any]) -> Dict[str, C4Component]:
        """
        Classify the entire codebase into C4 components.
        
        Args:
            analysis_results: Results from code analysis
            repository_info: Repository metadata
            
        Returns:
            Dictionary mapping component names to C4Component objects
        """
        # Analyze project context
        context = self._analyze_project_context(analysis_results, repository_info)
        
        # Classify components
        components = {}
        
        # 1. Identify the main software system
        main_system = self._identify_main_system(analysis_results, context)
        components[main_system.name] = main_system
        
        # 2. Identify containers (applications, databases, etc.)
        containers = self._identify_containers(analysis_results, context)
        components.update(containers)
        
        # 3. Identify components within containers
        code_components = self._identify_code_components(analysis_results, context)
        components.update(code_components)
        
        # 4. Identify external systems
        external_systems = self._identify_external_systems(analysis_results, context)
        components.update(external_systems)
        
        return components
    
    def _analyze_project_context(self, analysis_results: Dict[str, ModuleInfo], 
                                repository_info: Dict[str, Any]) -> ArchitectureContext:
        """Analyze project context to understand the type of system."""
        project_name = repository_info.get('name', 'Unknown Project')
        
        # Detect frameworks and technologies
        all_imports = set()
        all_filenames = set()
        
        for module_info in analysis_results.values():
            all_imports.update(module_info.imports)
            all_filenames.add(module_info.path.name.lower())
        
        # Detect project type
        project_type = self._detect_project_type(all_imports, all_filenames)
        framework = self._detect_framework(all_imports)
        database_type = self._detect_database(all_imports)
        has_api = self._has_api_functionality(all_imports, analysis_results)
        has_ui = self._has_ui_functionality(all_imports, all_filenames)
        
        return ArchitectureContext(
            project_name=project_name,
            project_type=project_type,
            framework=framework,
            database_type=database_type,
            has_api=has_api,
            has_ui=has_ui
        )
    
    def _detect_project_type(self, imports: Set[str], filenames: Set[str]) -> str:
        """Detect the type of project based on imports and files."""
        # Web application indicators
        web_indicators = {'flask', 'django', 'fastapi', 'express', 'spring-boot'}
        if any(indicator in str(imports).lower() for indicator in web_indicators):
            return 'web_application'
        
        # API service indicators  
        api_indicators = {'fastapi', 'flask-restful', 'express', 'spring-web'}
        if any(indicator in str(imports).lower() for indicator in api_indicators):
            return 'api_service'
        
        # Desktop application indicators
        desktop_indicators = {'tkinter', 'pyside', 'electron', 'swing'}
        if any(indicator in str(imports).lower() for indicator in desktop_indicators):
            return 'desktop_application'
        
        # Library indicators
        if 'setup.py' in filenames or 'pyproject.toml' in filenames:
            return 'library'
        
        return 'application'
    
    def _detect_framework(self, imports: Set[str]) -> Optional[str]:
        """Detect the main framework being used."""
        imports_str = ' '.join(imports).lower()
        
        for framework, info in self.framework_patterns.items():
            if framework in imports_str:
                return framework
        
        return None
    
    def _detect_database(self, imports: Set[str]) -> Optional[str]:
        """Detect database technology being used."""
        imports_str = ' '.join(imports).lower()
        
        for db_type in self.database_patterns:
            if db_type in imports_str:
                return db_type
        
        return None
    
    def _has_api_functionality(self, imports: Set[str], analysis_results: Dict[str, ModuleInfo]) -> bool:
        """Check if the project has API functionality."""
        imports_str = ' '.join(imports).lower()
        
        # Check for API-related imports
        for pattern in self.api_patterns:
            if pattern in imports_str:
                return True
        
        # Check for route decorators and API patterns in code
        for module_info in analysis_results.values():
            for func in module_info.functions:
                if any(keyword in func.name.lower() for keyword in ['route', 'endpoint', 'api', 'get', 'post']):
                    return True
        
        return False
    
    def _has_ui_functionality(self, imports: Set[str], filenames: Set[str]) -> bool:
        """Check if the project has UI functionality."""
        ui_patterns = {'tkinter', 'pyside', 'react', 'angular', 'vue', 'html', 'css', 'js'}
        imports_str = ' '.join(imports).lower()
        filenames_str = ' '.join(filenames).lower()
        
        return any(pattern in imports_str or pattern in filenames_str for pattern in ui_patterns)
    
    def _identify_main_system(self, analysis_results: Dict[str, ModuleInfo], 
                             context: ArchitectureContext) -> C4Component:
        """Identify the main software system."""
        description = f"{context.project_type.replace('_', ' ').title()}"
        if context.framework:
            description += f" built with {context.framework.title()}"
        
        return C4Component(
            name=context.project_name,
            type=C4ComponentType.SOFTWARE_SYSTEM,
            description=description,
            technology=context.framework,
            source_files=set(Path(path) for path in analysis_results.keys()),
            metadata={
                'project_type': context.project_type,
                'has_api': context.has_api,
                'has_ui': context.has_ui
            }
        )
    
    def _identify_containers(self, analysis_results: Dict[str, ModuleInfo], 
                           context: ArchitectureContext) -> Dict[str, C4Component]:
        """Identify containers (applications, databases, etc.)."""
        containers = {}
        
        # Main application container
        if context.project_type in ['web_application', 'api_service']:
            app_name = f"{context.project_name} Application"
            description = f"Main {context.project_type.replace('_', ' ')} container"
            
            containers[app_name] = C4Component(
                name=app_name,
                type=C4ComponentType.CONTAINER,
                description=description,
                technology=context.framework,
                source_files=set(Path(path) for path in analysis_results.keys()),
                metadata={'container_type': 'application'}
            )
        
        # Database container
        if context.database_type:
            db_name = f"{context.database_type.title()} Database"
            containers[db_name] = C4Component(
                name=db_name,
                type=C4ComponentType.CONTAINER,
                description=f"Stores application data",
                technology=context.database_type,
                metadata={'container_type': 'database'}
            )
        
        # Frontend container (if separate from backend)
        if context.has_ui and context.project_type == 'api_service':
            ui_name = "Web Frontend"
            containers[ui_name] = C4Component(
                name=ui_name,
                type=C4ComponentType.CONTAINER,
                description="User interface for the application",
                technology="HTML/CSS/JavaScript",
                metadata={'container_type': 'frontend'}
            )
        
        return containers
    
    def _identify_code_components(self, analysis_results: Dict[str, ModuleInfo], 
                                context: ArchitectureContext) -> Dict[str, C4Component]:
        """Identify code components within containers."""
        components = {}
        
        # Group modules by functional areas
        functional_groups = self._group_modules_by_function(analysis_results)
        
        for group_name, modules in functional_groups.items():
            component_name = f"{group_name.title()} Component"
            
            # Collect all code elements from the modules
            code_elements = []
            source_files = set()
            
            for module_path in modules:
                if module_path in analysis_results:
                    module_info = analysis_results[module_path]
                    code_elements.extend(module_info.classes)
                    code_elements.extend(module_info.functions)
                    code_elements.extend(module_info.interfaces)
                    source_files.add(module_info.path)
            
            if code_elements:  # Only create component if it has code elements
                components[component_name] = C4Component(
                    name=component_name,
                    type=C4ComponentType.COMPONENT,
                    description=f"Handles {group_name.replace('_', ' ')} functionality",
                    code_elements=code_elements,
                    source_files=source_files,
                    metadata={'functional_area': group_name}
                )
        
        return components
    
    def _group_modules_by_function(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, List[str]]:
        """Group modules by their functional purpose."""
        groups = {
            'authentication': [],
            'user_management': [],
            'data_access': [],
            'api': [],
            'business_logic': [],
            'utilities': [],
            'configuration': [],
            'models': [],
            'controllers': [],
            'services': []
        }
        
        for module_path, module_info in analysis_results.items():
            module_name = module_info.path.stem.lower()
            parent_dir = module_info.path.parent.name.lower()
            
            # Classify based on naming patterns
            if any(keyword in module_name for keyword in ['auth', 'login', 'session']):
                groups['authentication'].append(module_path)
            elif any(keyword in module_name for keyword in ['user', 'profile', 'account']):
                groups['user_management'].append(module_path)
            elif any(keyword in module_name for keyword in ['model', 'entity', 'schema']):
                groups['models'].append(module_path)
            elif any(keyword in module_name for keyword in ['controller', 'view', 'handler']):
                groups['controllers'].append(module_path)
            elif any(keyword in module_name for keyword in ['service', 'business', 'logic']):
                groups['services'].append(module_path)
            elif any(keyword in module_name for keyword in ['api', 'rest', 'endpoint']):
                groups['api'].append(module_path)
            elif any(keyword in module_name for keyword in ['dao', 'repository', 'db', 'database']):
                groups['data_access'].append(module_path)
            elif any(keyword in module_name for keyword in ['config', 'settings', 'env']):
                groups['configuration'].append(module_path)
            elif any(keyword in module_name for keyword in ['util', 'helper', 'common']):
                groups['utilities'].append(module_path)
            else:
                # Classify based on parent directory
                if any(keyword in parent_dir for keyword in ['model', 'entity']):
                    groups['models'].append(module_path)
                elif any(keyword in parent_dir for keyword in ['controller', 'view']):
                    groups['controllers'].append(module_path)
                elif any(keyword in parent_dir for keyword in ['service', 'business']):
                    groups['services'].append(module_path)
                else:
                    groups['business_logic'].append(module_path)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _identify_external_systems(self, analysis_results: Dict[str, ModuleInfo], 
                                 context: ArchitectureContext) -> Dict[str, C4Component]:
        """Identify external systems based on imports."""
        external_systems = {}
        
        # Collect all external imports
        external_imports = set()
        for module_info in analysis_results.values():
            for imp in module_info.imports:
                # Filter out standard library and local imports
                if not self._is_local_import(imp) and not self._is_standard_library(imp):
                    external_imports.add(imp)
        
        # Group external imports by system
        system_groups = self._group_external_imports(external_imports)
        
        for system_name, imports in system_groups.items():
            external_systems[system_name] = C4Component(
                name=system_name,
                type=C4ComponentType.SOFTWARE_SYSTEM,
                description=f"External {system_name} system",
                metadata={
                    'external': True,
                    'imports': list(imports)
                }
            )
        
        return external_systems
    
    def _is_local_import(self, import_name: str) -> bool:
        """Check if an import is a local module."""
        # Simple heuristic: local imports usually start with '.' or contain the project name
        return import_name.startswith('.') or len(import_name.split('.')) == 1
    
    def _is_standard_library(self, import_name: str) -> bool:
        """Check if an import is from the standard library."""
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 'pathlib', 're', 'collections',
            'itertools', 'functools', 'typing', 'abc', 'dataclasses', 'enum',
            'asyncio', 'threading', 'multiprocessing', 'logging', 'unittest',
            'http', 'urllib', 'socket', 'ssl', 'email', 'html', 'xml',
            'sqlite3', 'csv', 'configparser', 'argparse', 'math', 'random'
        }
        
        root_module = import_name.split('.')[0]
        return root_module in stdlib_modules
    
    def _group_external_imports(self, external_imports: Set[str]) -> Dict[str, Set[str]]:
        """Group external imports by likely system."""
        groups = {}
        
        # Common external system patterns
        system_patterns = {
            'Database': {'sqlalchemy', 'pymongo', 'psycopg2', 'mysql', 'redis', 'cassandra'},
            'Web Framework': {'flask', 'django', 'fastapi', 'tornado', 'aiohttp'},
            'HTTP Client': {'requests', 'httpx', 'aiohttp', 'urllib3'},
            'Cloud Services': {'boto3', 'azure', 'google-cloud', 'kubernetes'},
            'Message Queue': {'celery', 'rabbitmq', 'kafka', 'redis'},
            'Monitoring': {'prometheus', 'datadog', 'sentry', 'newrelic'},
            'Testing': {'pytest', 'unittest', 'mock', 'coverage'}
        }
        
        for import_name in external_imports:
            categorized = False
            for system_name, patterns in system_patterns.items():
                if any(pattern in import_name.lower() for pattern in patterns):
                    if system_name not in groups:
                        groups[system_name] = set()
                    groups[system_name].add(import_name)
                    categorized = True
                    break
            
            if not categorized:
                # Create a generic external system entry
                root_module = import_name.split('.')[0]
                system_name = f"External {root_module.title()} System"
                if system_name not in groups:
                    groups[system_name] = set()
                groups[system_name].add(import_name)
        
        return groups
