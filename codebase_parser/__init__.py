"""
Codebase Parser Module

This module provides functionality to parse codebases from various sources including:
- GitHub repositories
- GitLab projects  
- Apache Software Foundation projects
- Local repositories

The parser handles cloning, file discovery, and initial code analysis.
"""

from .repository_manager import RepositoryManager
from .code_analyzer import CodeAnalyzer
from .language_detector import LanguageDetector
from .file_scanner import FileScanner

__all__ = [
    'RepositoryManager',
    'CodeAnalyzer', 
    'LanguageDetector',
    'FileScanner'
]
