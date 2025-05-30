"""
Language Detector

Detects programming languages in repositories and determines parsing strategies.
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter
import mimetypes
from dataclasses import dataclass


@dataclass
class LanguageInfo:
    """Information about a detected language"""
    name: str
    extensions: Set[str]
    file_count: int
    total_lines: int
    percentage: float
    mime_types: Set[str] = None

    def __post_init__(self):
        if self.mime_types is None:
            self.mime_types = set()


class LanguageDetector:
    """
    Detects programming languages in repositories based on file extensions,
    content analysis, and file patterns.
    """
    
    # Language to extension mapping
    LANGUAGE_EXTENSIONS = {
        'Python': {'.py', '.pyw', '.py3', '.pyi'},
        'Java': {'.java', '.jsp', '.jspx'},
        'JavaScript': {'.js', '.mjs', '.jsx'},
        'TypeScript': {'.ts', '.tsx', '.d.ts'},
        'C++': {'.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hh', '.hxx', '.h++'},
        'C': {'.c', '.h'},
        'C#': {'.cs', '.csx'},
        'Go': {'.go'},
        'Rust': {'.rs'},
        'PHP': {'.php', '.php3', '.php4', '.php5', '.phtml'},
        'Ruby': {'.rb', '.rbw'},
        'Swift': {'.swift'},
        'Kotlin': {'.kt', '.kts'},
        'Scala': {'.scala', '.sc'},
        'R': {'.r', '.R'},
        'MATLAB': {'.m'},
        'Shell': {'.sh', '.bash', '.zsh', '.fish'},
        'PowerShell': {'.ps1', '.psm1', '.psd1'},
        'Perl': {'.pl', '.pm', '.perl'},
        'Lua': {'.lua'},
        'Haskell': {'.hs', '.lhs'},
        'Erlang': {'.erl', '.hrl'},
        'Elixir': {'.ex', '.exs'},
        'Clojure': {'.clj', '.cljs', '.cljc'},
        'F#': {'.fs', '.fsi', '.fsx'},
        'VB.NET': {'.vb'},
        'Dart': {'.dart'},
        'HTML': {'.html', '.htm', '.xhtml'},
        'CSS': {'.css', '.scss', '.sass', '.less'},
        'XML': {'.xml', '.xsd', '.xsl', '.xslt'},
        'JSON': {'.json'},
        'YAML': {'.yaml', '.yml'},
        'TOML': {'.toml'},
        'Dockerfile': {'Dockerfile', '.dockerfile'},
        'Makefile': {'Makefile', 'makefile', '.mk'},
        'CMake': {'.cmake', 'CMakeLists.txt'},
        'SQL': {'.sql'},
    }
    
    # Configuration files that indicate language/framework
    FRAMEWORK_INDICATORS = {
        'package.json': ['JavaScript', 'TypeScript', 'Node.js'],
        'pom.xml': ['Java', 'Maven'],
        'build.gradle': ['Java', 'Kotlin', 'Gradle'],
        'Cargo.toml': ['Rust'],
        'go.mod': ['Go'],
        'requirements.txt': ['Python'],
        'setup.py': ['Python'],
        'pyproject.toml': ['Python'],
        'composer.json': ['PHP'],
        'Gemfile': ['Ruby'],
        'Package.swift': ['Swift'],
        '.csproj': ['C#'],
        '.sln': ['C#', 'VB.NET'],
        'build.sbt': ['Scala'],
    }
    
    # Ignore patterns for files/directories
    IGNORE_PATTERNS = {
        # Version control
        '.git', '.svn', '.hg', '.bzr',
        # Dependencies
        'node_modules', 'vendor', 'target', 'build', 'dist', 'out',
        # Python
        '__pycache__', '.pytest_cache', 'venv', 'env', '.env',
        # IDE
        '.vscode', '.idea', '.eclipse', '.settings',
        # OS
        '.DS_Store', 'Thumbs.db',
        # Logs
        'logs', '*.log',
        # Archives
        '*.zip', '*.tar', '*.gz', '*.rar',
        # Temporary
        'tmp', 'temp', '.tmp'
    }
    
    def __init__(self, min_file_threshold: int = 1):
        """
        Initialize language detector.
        
        Args:
            min_file_threshold: Minimum number of files to consider a language present
        """
        self.min_file_threshold = min_file_threshold
        self._extension_to_language = self._build_extension_mapping()
    
    def _build_extension_mapping(self) -> Dict[str, str]:
        """Build reverse mapping from extensions to languages."""
        mapping = {}
        for language, extensions in self.LANGUAGE_EXTENSIONS.items():
            for ext in extensions:
                # Handle special cases without dots
                if ext in ['Dockerfile', 'Makefile', 'makefile', 'CMakeLists.txt']:
                    mapping[ext] = language
                else:
                    mapping[ext.lower()] = language
        return mapping
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path).lower()
        for pattern in self.IGNORE_PATTERNS:
            if pattern in path_str or path.name.lower().startswith(pattern.lower()):
                return True
        return False
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file safely."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def detect_languages(self, repo_path: Path) -> Dict[str, LanguageInfo]:
        """
        Detect programming languages in the repository.
        
        Args:
            repo_path: Path to repository root
            
        Returns:
            Dictionary mapping language names to LanguageInfo objects
        """
        language_stats = Counter()
        language_files = {}
        language_lines = {}
        
        # Walk through repository files
        for root, dirs, files in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                
                if self._should_ignore(file_path):
                    continue
                
                # Detect language by extension
                language = self._detect_language_by_extension(file_path)
                
                if language:
                    language_stats[language] += 1
                    
                    if language not in language_files:
                        language_files[language] = set()
                        language_lines[language] = 0
                    
                    language_files[language].add(file_path.suffix.lower())
                    language_lines[language] += self._count_lines(file_path)
        
        # Check for framework indicators
        framework_languages = self._detect_framework_indicators(repo_path)
        for lang in framework_languages:
            if lang not in language_stats:
                language_stats[lang] = 0
        
        # Calculate percentages and create LanguageInfo objects
        total_files = sum(language_stats.values())
        total_lines = sum(language_lines.values())
        
        result = {}
        for language, file_count in language_stats.items():
            if file_count >= self.min_file_threshold:
                extensions = language_files.get(language, set())
                lines = language_lines.get(language, 0)
                percentage = (file_count / total_files * 100) if total_files > 0 else 0
                
                result[language] = LanguageInfo(
                    name=language,
                    extensions=extensions,
                    file_count=file_count,
                    total_lines=lines,
                    percentage=percentage
                )
        
        return result
    
    def _detect_language_by_extension(self, file_path: Path) -> str:
        """Detect language by file extension."""
        # Handle special files without extensions
        if file_path.name in self._extension_to_language:
            return self._extension_to_language[file_path.name]
        
        # Handle regular extensions
        ext = file_path.suffix.lower()
        return self._extension_to_language.get(ext)
    
    def _detect_framework_indicators(self, repo_path: Path) -> List[str]:
        """Detect languages based on framework/build files."""
        detected_languages = []
        
        for indicator_file, languages in self.FRAMEWORK_INDICATORS.items():
            if (repo_path / indicator_file).exists():
                detected_languages.extend(languages)
        
        return detected_languages
    
    def get_primary_language(self, languages: Dict[str, LanguageInfo]) -> str:
        """
        Get the primary language based on line count and file count.
        
        Args:
            languages: Dictionary of detected languages
            
        Returns:
            Name of primary language or 'Unknown' if none detected
        """
        if not languages:
            return 'Unknown'
        
        # Sort by total lines, then by file count
        sorted_languages = sorted(
            languages.items(),
            key=lambda x: (x[1].total_lines, x[1].file_count),
            reverse=True
        )
        
        return sorted_languages[0][0]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages."""
        return list(self.LANGUAGE_EXTENSIONS.keys())
    
    def is_supported_language(self, language: str) -> bool:
        """Check if a language is supported for parsing."""
        # For now, we'll focus on major languages with good tree-sitter support
        supported = {
            'Python', 'Java', 'JavaScript', 'TypeScript', 
            'C++', 'C', 'Go', 'Rust', 'C#'
        }
        return language in supported
