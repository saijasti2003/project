"""
Code Analyzer

Performs detailed analysis of source code using tree-sitter for language-agnostic parsing.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# Tree-sitter imports
try:
    import tree_sitter_python as tspython
    import tree_sitter_java as tsjava  
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    import tree_sitter_cpp as tscpp
    import tree_sitter_go as tsgo
    from tree_sitter import Language, Parser, Tree, Node
    TREE_SITTER_AVAILABLE = True
except ImportError as e:
    TREE_SITTER_AVAILABLE = False
    print(f"Warning: tree-sitter not available ({e}), falling back to basic analysis")

# Fallback to AST for Python
import ast
import re


@dataclass
class CodeElement:
    """Represents a code element (class, function, module, etc.)"""
    name: str
    type: str  # 'class', 'function', 'module', 'interface', etc.
    file_path: Path
    start_line: int
    end_line: int
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    modifiers: Set[str] = field(default_factory=set)  # public, private, static, etc.
    docstring: Optional[str] = None
    complexity: int = 0


@dataclass
class ModuleInfo:
    """Information about a code module/file"""
    path: Path
    language: str
    imports: Set[str] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)
    classes: List[CodeElement] = field(default_factory=list)
    functions: List[CodeElement] = field(default_factory=list)
    interfaces: List[CodeElement] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    complexity_score: int = 0


class BaseAnalyzer(ABC):
    """Base class for language-specific analyzers"""
    
    @abstractmethod
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze a single file and extract code elements."""
        pass


class PythonTreeSitterAnalyzer(BaseAnalyzer):
    """Analyzer for Python code using tree-sitter"""
    
    def __init__(self):
        if TREE_SITTER_AVAILABLE:
            self.language = Language(tspython.language())
            self.parser = Parser(self.language)
        else:
            raise ImportError("tree-sitter-python not available")
    
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze Python file using tree-sitter."""
        module_info = ModuleInfo(path=file_path, language="Python")
        
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parser.parse(source_code)
            
            # Extract imports
            self._extract_imports(tree.root_node, source_code, module_info)
            
            # Extract classes and functions
            self._extract_code_elements(tree.root_node, source_code, module_info)
            
        except Exception as e:
            print(f"Error analyzing Python file {file_path}: {e}")
        
        return module_info
    
    def _extract_imports(self, node: Node, source: bytes, module_info: ModuleInfo):
        """Extract import statements."""
        if node.type == 'import_statement':
            # import module
            module_name = self._get_import_name(node, source)
            if module_name:
                module_info.imports.add(module_name)
                module_info.dependencies.add(module_name)
        
        elif node.type == 'import_from_statement':
            # from module import item
            module_name = self._get_from_import_module(node, source)
            if module_name:
                module_info.imports.add(module_name)
                module_info.dependencies.add(module_name)
        
        # Recursively check children
        for child in node.children:
            self._extract_imports(child, source, module_info)
    
    def _extract_code_elements(self, node: Node, source: bytes, module_info: ModuleInfo, parent_name: str = None):
        """Extract classes and functions."""
        if node.type == 'class_definition':
            class_element = self._extract_class(node, source, parent_name)
            class_element.file_path = module_info.path
            module_info.classes.append(class_element)
            
            # Extract nested elements
            self._extract_code_elements(node, source, module_info, class_element.name)
        
        elif node.type == 'function_definition':
            func_element = self._extract_function(node, source, parent_name)
            func_element.file_path = module_info.path
            module_info.functions.append(func_element)
        
        # Recursively check children
        for child in node.children:
            self._extract_code_elements(child, source, module_info, parent_name)
    
    def _extract_class(self, node: Node, source: bytes, parent_name: str = None) -> CodeElement:
        """Extract class definition."""
        name = self._get_node_name(node, source, 'identifier')
        
        return CodeElement(
            name=name,
            type='class',
            file_path=Path(""),  # Will be set by caller
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_name,
            docstring=self._get_docstring(node, source)
        )
    
    def _extract_function(self, node: Node, source: bytes, parent_name: str = None) -> CodeElement:
        """Extract function definition."""
        name = self._get_node_name(node, source, 'identifier')
        
        return CodeElement(
            name=name,
            type='function',
            file_path=Path(""),  # Will be set by caller
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_name,
            docstring=self._get_docstring(node, source)
        )
    
    def _get_node_name(self, node: Node, source: bytes, target_type: str) -> str:
        """Get name from a node by finding child of target type."""
        for child in node.children:
            if child.type == target_type:
                return source[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return "Unknown"
    
    def _get_import_name(self, node: Node, source: bytes) -> str:
        """Get module name from import statement."""
        for child in node.children:
            if child.type == 'dotted_name':
                return source[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return ""
    
    def _get_from_import_module(self, node: Node, source: bytes) -> str:
        """Get module name from from-import statement."""
        for child in node.children:
            if child.type == 'dotted_name':
                return source[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return ""
    
    def _get_docstring(self, node: Node, source: bytes) -> Optional[str]:
        """Extract docstring from function or class."""
        # Look for string literal as first statement in body
        for child in node.children:
            if child.type == 'block':
                for stmt in child.children:
                    if stmt.type == 'expression_statement':
                        for expr in stmt.children:
                            if expr.type == 'string':
                                return source[expr.start_byte:expr.end_byte].decode('utf-8', errors='ignore').strip('"\'')
        return None


class JavaTreeSitterAnalyzer(BaseAnalyzer):
    """Analyzer for Java code using tree-sitter"""
    
    def __init__(self):
        if TREE_SITTER_AVAILABLE:
            self.language = Language(tsjava.language())
            self.parser = Parser(self.language)
        else:
            raise ImportError("tree-sitter-java not available")
    
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze Java file using tree-sitter."""
        module_info = ModuleInfo(path=file_path, language="Java")
        
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parser.parse(source_code)
            
            # Extract package and imports
            self._extract_package_imports(tree.root_node, source_code, module_info)
            
            # Extract classes and interfaces
            self._extract_code_elements(tree.root_node, source_code, module_info)
            
        except Exception as e:
            print(f"Error analyzing Java file {file_path}: {e}")
        
        return module_info
    
    def _extract_package_imports(self, node: Node, source: bytes, module_info: ModuleInfo):
        """Extract package and import declarations."""
        if node.type == 'import_declaration':
            import_name = self._get_java_import_name(node, source)
            if import_name:
                module_info.imports.add(import_name)
                module_info.dependencies.add(import_name)
        
        for child in node.children:
            self._extract_package_imports(child, source, module_info)
    
    def _extract_code_elements(self, node: Node, source: bytes, module_info: ModuleInfo, parent_name: str = None):
        """Extract Java classes, interfaces, and methods."""
        if node.type == 'class_declaration':
            class_element = self._extract_java_class(node, source, parent_name)
            class_element.file_path = module_info.path
            module_info.classes.append(class_element)
            self._extract_code_elements(node, source, module_info, class_element.name)
        
        elif node.type == 'interface_declaration':
            interface_element = self._extract_java_interface(node, source, parent_name)
            interface_element.file_path = module_info.path
            module_info.interfaces.append(interface_element)
            self._extract_code_elements(node, source, module_info, interface_element.name)
        
        elif node.type == 'method_declaration':
            method_element = self._extract_java_method(node, source, parent_name)
            method_element.file_path = module_info.path
            module_info.functions.append(method_element)
        
        for child in node.children:
            self._extract_code_elements(child, source, module_info, parent_name)
    
    def _get_java_import_name(self, node: Node, source: bytes) -> str:
        """Get import name from Java import declaration."""
        for child in node.children:
            if child.type in ['scoped_identifier', 'identifier']:
                return source[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return ""
    
    def _extract_java_class(self, node: Node, source: bytes, parent_name: str = None) -> CodeElement:
        """Extract Java class."""
        name = self._get_java_identifier(node, source)
        modifiers = self._get_java_modifiers(node, source)
        
        return CodeElement(
            name=name,
            type='class',
            file_path=Path(""),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_name,
            modifiers=modifiers
        )
    
    def _extract_java_interface(self, node: Node, source: bytes, parent_name: str = None) -> CodeElement:
        """Extract Java interface."""
        name = self._get_java_identifier(node, source)
        modifiers = self._get_java_modifiers(node, source)
        
        return CodeElement(
            name=name,
            type='interface',
            file_path=Path(""),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_name,
            modifiers=modifiers
        )
    
    def _extract_java_method(self, node: Node, source: bytes, parent_name: str = None) -> CodeElement:
        """Extract Java method."""
        name = self._get_java_identifier(node, source)
        modifiers = self._get_java_modifiers(node, source)
        
        return CodeElement(
            name=name,
            type='method',
            file_path=Path(""),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_name,
            modifiers=modifiers
        )
    
    def _get_java_identifier(self, node: Node, source: bytes) -> str:
        """Get identifier from Java node."""
        for child in node.children:
            if child.type == 'identifier':
                return source[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return "Unknown"
    
    def _get_java_modifiers(self, node: Node, source: bytes) -> Set[str]:
        """Get modifiers from Java declaration."""
        modifiers = set()
        for child in node.children:
            if child.type == 'modifiers':
                for modifier in child.children:
                    if modifier.type in ['public', 'private', 'protected', 'static', 'final', 'abstract']:
                        modifiers.add(modifier.type)
        return modifiers


class PythonASTAnalyzer(BaseAnalyzer):
    """Fallback Python analyzer using AST"""
    
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze Python file using AST."""
        module_info = ModuleInfo(path=file_path, language="Python")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract imports
            self._extract_imports(tree, module_info)
            
            # Extract classes and functions
            self._extract_code_elements(tree, module_info, content.splitlines())
            
        except Exception as e:
            print(f"Error analyzing Python file {file_path}: {e}")
        
        return module_info
    
    def _extract_imports(self, tree: ast.AST, module_info: ModuleInfo):
        """Extract import statements from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_info.imports.add(alias.name)
                    module_info.dependencies.add(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_info.imports.add(node.module)
                    module_info.dependencies.add(node.module)
    
    def _extract_code_elements(self, tree: ast.AST, module_info: ModuleInfo, lines: List[str], parent_name: str = None):
        """Extract classes and functions from AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_element = CodeElement(
                    name=node.name,
                    type='class',
                    file_path=module_info.path,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    parent=parent_name,
                    docstring=ast.get_docstring(node)
                )
                module_info.classes.append(class_element)
            
            elif isinstance(node, ast.FunctionDef):
                func_element = CodeElement(
                    name=node.name,
                    type='function',
                    file_path=module_info.path,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    parent=parent_name,
                    docstring=ast.get_docstring(node)
                )
                module_info.functions.append(func_element)


class SimplePatternAnalyzer(BaseAnalyzer):
    """Simple analyzer using regex patterns for various languages"""
    
    def __init__(self, language: str):
        self.language = language
    
    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze file using pattern matching."""
        module_info = ModuleInfo(path=file_path, language=self.language)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
            
            if self.language == "Java":
                self._analyze_java(content, lines, module_info)
            elif self.language == "JavaScript":
                self._analyze_javascript(content, lines, module_info)
            elif self.language == "TypeScript":
                self._analyze_typescript(content, lines, module_info)
            
        except Exception as e:
            print(f"Error analyzing {self.language} file {file_path}: {e}")
        
        return module_info
    
    def _analyze_java(self, content: str, lines: List[str], module_info: ModuleInfo):
        """Analyze Java using patterns."""
        # Extract imports
        import_pattern = r'import\s+(?:static\s+)?([a-zA-Z0-9_.]+(?:\.\*)?);'
        imports = re.findall(import_pattern, content)
        
        for imp in imports:
            module_info.imports.add(imp)
            module_info.dependencies.add(imp)
        
        # Extract classes
        class_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            class_element = CodeElement(
                name=class_name,
                type='class',
                file_path=module_info.path,
                start_line=start_line,
                end_line=start_line
            )
            module_info.classes.append(class_element)
        
        # Extract methods
        method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*{'
        for match in re.finditer(method_pattern, content, re.MULTILINE):
            method_name = match.group(1)
            if method_name not in ['if', 'for', 'while', 'switch']:
                start_line = content[:match.start()].count('\n') + 1
                
                method_element = CodeElement(
                    name=method_name,
                    type='method',
                    file_path=module_info.path,
                    start_line=start_line,
                    end_line=start_line
                )
                module_info.functions.append(method_element)
    
    def _analyze_javascript(self, content: str, lines: List[str], module_info: ModuleInfo):
        """Analyze JavaScript using patterns."""
        # Extract imports/requires
        import_pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
        require_pattern = r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        
        imports = re.findall(import_pattern, content) + re.findall(require_pattern, content)
        for imp in imports:
            module_info.imports.add(imp)
            module_info.dependencies.add(imp)
        
        # Extract functions
        func_pattern = r'function\s+(\w+)\s*\([^)]*\)'
        arrow_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[\w,\s]+)\s*=>'
        
        for pattern in [func_pattern, arrow_pattern]:
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1
                
                func_element = CodeElement(
                    name=func_name,
                    type='function',
                    file_path=module_info.path,
                    start_line=start_line,
                    end_line=start_line
                )
                module_info.functions.append(func_element)
        
        # Extract classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            class_element = CodeElement(
                name=class_name,
                type='class',
                file_path=module_info.path,
                start_line=start_line,
                end_line=start_line
            )
            module_info.classes.append(class_element)
    
    def _analyze_typescript(self, content: str, lines: List[str], module_info: ModuleInfo):
        """Analyze TypeScript using patterns."""
        # Similar to JavaScript but with additional patterns
        self._analyze_javascript(content, lines, module_info)
        
        # Extract interfaces
        interface_pattern = r'interface\s+(\w+)'
        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            interface_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            interface_element = CodeElement(
                name=interface_name,
                type='interface',
                file_path=module_info.path,
                start_line=start_line,
                end_line=start_line
            )
            module_info.interfaces.append(interface_element)


class CodeAnalyzer:
    """
    Main code analyzer that coordinates language-specific analyzers.
    """
    
    def __init__(self):
        self.analyzers = {}
        self._initialize_analyzers()
    
    def _initialize_analyzers(self):
        """Initialize language-specific analyzers."""
        # Try tree-sitter first, fall back to simpler analyzers
        try:
            if TREE_SITTER_AVAILABLE:
                self.analyzers['Python'] = PythonTreeSitterAnalyzer()
                print("✅ Initialized Python tree-sitter analyzer")
            else:
                self.analyzers['Python'] = PythonASTAnalyzer()
                print("✅ Initialized Python AST analyzer")
        except Exception as e:
            print(f"⚠️  Could not initialize Python analyzer: {e}")
            self.analyzers['Python'] = PythonASTAnalyzer()
        
        try:
            if TREE_SITTER_AVAILABLE:
                self.analyzers['Java'] = JavaTreeSitterAnalyzer()
                print("✅ Initialized Java tree-sitter analyzer")
            else:
                self.analyzers['Java'] = SimplePatternAnalyzer("Java")
                print("✅ Initialized Java pattern analyzer")
        except Exception as e:
            print(f"⚠️  Could not initialize Java tree-sitter analyzer: {e}")
            self.analyzers['Java'] = SimplePatternAnalyzer("Java")
        
        # Add pattern-based analyzers for other languages
        self.analyzers['JavaScript'] = SimplePatternAnalyzer("JavaScript")
        self.analyzers['TypeScript'] = SimplePatternAnalyzer("TypeScript")
        print("✅ Initialized JavaScript and TypeScript pattern analyzers")
    
    def analyze_files(self, files: List[Path], languages: Dict[str, str]) -> Dict[str, ModuleInfo]:
        """
        Analyze multiple files.
        
        Args:
            files: List of file paths to analyze
            languages: Mapping of file paths to languages
            
        Returns:
            Dictionary mapping file paths to ModuleInfo objects
        """
        results = {}
        
        for file_path in files:
            language = languages.get(str(file_path))
            if language and language in self.analyzers:
                try:
                    module_info = self.analyzers[language].analyze_file(file_path)
                    module_info.path = file_path
                    results[str(file_path)] = module_info
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
        
        return results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self.analyzers.keys())
    
    def extract_dependencies(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Set[str]]:
        """
        Extract dependency relationships between modules.
        
        Args:
            analysis_results: Results from analyze_files
            
        Returns:
            Dictionary mapping module names to their dependencies
        """
        dependencies = {}
        module_names = set()
        
        # Collect all module names
        for module_info in analysis_results.values():
            module_name = module_info.path.stem
            module_names.add(module_name)
        
        # Extract dependencies
        for file_path, module_info in analysis_results.items():
            module_name = module_info.path.stem
            deps = set()
            
            # Filter imports to only include internal modules
            for imp in module_info.imports:
                # Simple heuristic: check if import matches any module name
                for mod_name in module_names:
                    if mod_name in imp or imp in mod_name:
                        deps.add(mod_name)
            
            dependencies[module_name] = deps
        
        return dependencies
    
    def calculate_complexity_metrics(self, analysis_results: Dict[str, ModuleInfo]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate complexity metrics for analyzed code.
        
        Args:
            analysis_results: Results from analyze_files
            
        Returns:
            Dictionary with complexity metrics per module
        """
        metrics = {}
        
        for file_path, module_info in analysis_results.items():
            module_name = module_info.path.stem
            
            metrics[module_name] = {
                'classes': len(module_info.classes),
                'functions': len(module_info.functions),
                'interfaces': len(module_info.interfaces),
                'imports': len(module_info.imports),
                'dependencies': len(module_info.dependencies),
                'total_elements': len(module_info.classes) + len(module_info.functions) + len(module_info.interfaces)
            }
        
        return metrics
