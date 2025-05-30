"""
File Scanner

Scans repository files and organizes them for analysis.
"""

import os
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
import fnmatch


@dataclass
class FileInfo:
    """Information about a scanned file"""
    path: Path
    relative_path: Path
    language: Optional[str]
    size: int
    lines: int = 0
    is_test: bool = False
    is_config: bool = False
    is_documentation: bool = False


@dataclass 
class ScanResult:
    """Results of file scanning"""
    files: List[FileInfo] = field(default_factory=list)
    directories: Set[Path] = field(default_factory=set)
    total_files: int = 0
    total_size: int = 0
    languages: Set[str] = field(default_factory=set)
    
    def get_files_by_language(self, language: str) -> List[FileInfo]:
        """Get all files for a specific language."""
        return [f for f in self.files if f.language == language]
    
    def get_source_files(self) -> List[FileInfo]:
        """Get non-test, non-config source files."""
        return [f for f in self.files 
                if not f.is_test and not f.is_config and not f.is_documentation]


class FileScanner:
    """
    Scans repository files and categorizes them for analysis.
    """
    
    # Patterns for different file types
    TEST_PATTERNS = [
        '*test*', '*tests*', '*spec*', '*specs*',
        'test_*', '*_test.*', '*_spec.*', 
        '__tests__/*', 'spec/*', 'tests/*'
    ]
    
    CONFIG_PATTERNS = [
        '*.json', '*.yaml', '*.yml', '*.toml', '*.ini', '*.cfg', '*.conf',
        '*.xml', '*.properties', '.env*', 'Dockerfile*', 'Makefile*',
        '*.gradle', '*.maven', 'pom.xml', 'build.*', 'package.json',
        'requirements.txt', 'setup.py', 'pyproject.toml', 'Cargo.toml',
        'go.mod', 'go.sum', 'composer.json', 'Gemfile*'
    ]
    
    DOCUMENTATION_PATTERNS = [
        '*.md', '*.rst', '*.txt', '*.adoc', '*.tex',
        'README*', 'CHANGELOG*', 'LICENSE*', 'CONTRIBUTING*',
        'docs/*', 'doc/*', 'documentation/*'
    ]
    
    # Files and directories to ignore
    IGNORE_PATTERNS = [
        # Version control
        '.git/*', '.svn/*', '.hg/*', '.bzr/*',
        # Dependencies and build outputs
        'node_modules/*', 'vendor/*', 'target/*', 'build/*', 
        'dist/*', 'out/*', 'bin/*', 'obj/*',
        # Python
        '__pycache__/*', '*.pyc', '*.pyo', '*.pyd', '.pytest_cache/*',
        'venv/*', 'env/*', '.env/*', '*.egg-info/*',
        # IDE and editors
        '.vscode/*', '.idea/*', '.eclipse/*', '.settings/*',
        '*.swp', '*.swo', '*~',
        # OS files
        '.DS_Store', 'Thumbs.db', 'desktop.ini',
        # Logs and temp
        '*.log', 'logs/*', 'tmp/*', 'temp/*', '.tmp/*',
        # Archives
        '*.zip', '*.tar', '*.gz', '*.rar', '*.7z',
        # Generated files
        '*.min.js', '*.min.css', '*.bundle.*',
        # Large data files
        '*.db', '*.sqlite', '*.dat', '*.dump'
    ]
    
    def __init__(self, max_file_size: int = 1024 * 1024):  # 1MB default
        """
        Initialize file scanner.
        
        Args:
            max_file_size: Maximum file size to process (in bytes)
        """
        self.max_file_size = max_file_size
    
    def scan_repository(self, repo_path: Path, language_detector=None) -> ScanResult:
        """
        Scan repository and categorize files.
        
        Args:
            repo_path: Path to repository root
            language_detector: Optional language detector instance
            
        Returns:
            ScanResult with categorized files
        """
        result = ScanResult()
        
        for root, dirs, files in os.walk(repo_path):
            root_path = Path(root)
            
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_directory(root_path / d, repo_path)]
            
            # Add directory to result
            result.directories.add(root_path.relative_to(repo_path))
            
            for file in files:
                file_path = root_path / file
                
                if self._should_ignore_file(file_path, repo_path):
                    continue
                
                # Get file info
                try:
                    file_stat = file_path.stat()
                    file_size = file_stat.st_size
                    
                    # Skip large files
                    if file_size > self.max_file_size:
                        continue
                    
                    relative_path = file_path.relative_to(repo_path)
                    
                    # Detect language
                    language = None
                    if language_detector:
                        language = language_detector._detect_language_by_extension(file_path)
                    
                    # Count lines for text files
                    lines = self._count_lines(file_path) if self._is_text_file(file_path) else 0
                    
                    # Categorize file
                    file_info = FileInfo(
                        path=file_path,
                        relative_path=relative_path,
                        language=language,
                        size=file_size,
                        lines=lines,
                        is_test=self._is_test_file(relative_path),
                        is_config=self._is_config_file(relative_path),
                        is_documentation=self._is_documentation_file(relative_path)
                    )
                    
                    result.files.append(file_info)
                    result.total_files += 1
                    result.total_size += file_size
                    
                    if language:
                        result.languages.add(language)
                        
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
        
        return result
    
    def _should_ignore_file(self, file_path: Path, repo_root: Path) -> bool:
        """Check if file should be ignored."""
        relative_path = file_path.relative_to(repo_root)
        
        for pattern in self.IGNORE_PATTERNS:
            if fnmatch.fnmatch(str(relative_path), pattern):
                return True
            if fnmatch.fnmatch(file_path.name, pattern):
                return True
        
        return False
    
    def _should_ignore_directory(self, dir_path: Path, repo_root: Path) -> bool:
        """Check if directory should be ignored."""
        try:
            relative_path = dir_path.relative_to(repo_root)
            
            for pattern in self.IGNORE_PATTERNS:
                if fnmatch.fnmatch(str(relative_path), pattern):
                    return True
                if fnmatch.fnmatch(dir_path.name, pattern):
                    return True
        except ValueError:
            # Path is not relative to repo_root
            return True
        
        return False
    
    def _is_test_file(self, relative_path: Path) -> bool:
        """Check if file is a test file."""
        path_str = str(relative_path).lower()
        
        for pattern in self.TEST_PATTERNS:
            if fnmatch.fnmatch(path_str, pattern.lower()):
                return True
            if fnmatch.fnmatch(relative_path.name.lower(), pattern.lower()):
                return True
        
        return False
    
    def _is_config_file(self, relative_path: Path) -> bool:
        """Check if file is a configuration file."""
        path_str = str(relative_path).lower()
        
        for pattern in self.CONFIG_PATTERNS:
            if fnmatch.fnmatch(path_str, pattern.lower()):
                return True
            if fnmatch.fnmatch(relative_path.name.lower(), pattern.lower()):
                return True
        
        return False
    
    def _is_documentation_file(self, relative_path: Path) -> bool:
        """Check if file is documentation."""
        path_str = str(relative_path).lower()
        
        for pattern in self.DOCUMENTATION_PATTERNS:
            if fnmatch.fnmatch(path_str, pattern.lower()):
                return True
            if fnmatch.fnmatch(relative_path.name.lower(), pattern.lower()):
                return True
        
        return False
    
    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is a text file."""
        try:
            # Try to read a small portion as text
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                f.read(1024)
            return True
        except (UnicodeDecodeError, PermissionError):
            return False
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def filter_by_language(self, scan_result: ScanResult, languages: List[str]) -> ScanResult:
        """
        Filter scan result to only include specific languages.
        
        Args:
            scan_result: Original scan result
            languages: List of languages to keep
            
        Returns:
            Filtered scan result
        """
        filtered_files = [f for f in scan_result.files if f.language in languages]
        
        return ScanResult(
            files=filtered_files,
            directories=scan_result.directories,
            total_files=len(filtered_files),
            total_size=sum(f.size for f in filtered_files),
            languages=set(languages) & scan_result.languages
        )
    
    def get_file_statistics(self, scan_result: ScanResult) -> Dict:
        """
        Get statistical summary of scanned files.
        
        Args:
            scan_result: Scan result to analyze
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_files': scan_result.total_files,
            'total_size': scan_result.total_size,
            'total_lines': sum(f.lines for f in scan_result.files),
            'languages': len(scan_result.languages),
            'directories': len(scan_result.directories),
            'source_files': len(scan_result.get_source_files()),
            'test_files': len([f for f in scan_result.files if f.is_test]),
            'config_files': len([f for f in scan_result.files if f.is_config]),
            'doc_files': len([f for f in scan_result.files if f.is_documentation]),
        }
        
        # Language breakdown
        language_stats = {}
        for lang in scan_result.languages:
            lang_files = scan_result.get_files_by_language(lang)
            language_stats[lang] = {
                'files': len(lang_files),
                'lines': sum(f.lines for f in lang_files),
                'size': sum(f.size for f in lang_files)
            }
        
        stats['by_language'] = language_stats
        
        return stats
