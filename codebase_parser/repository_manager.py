"""
Repository Manager

Handles cloning and managing repositories from different sources:
- GitHub
- GitLab  
- Apache Software Foundation
- Local directories
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import git
from git import Repo
import requests
from dataclasses import dataclass
from enum import Enum


class RepositorySource(Enum):
    """Supported repository sources"""
    GITHUB = "github"
    GITLAB = "gitlab"
    APACHE = "apache"
    LOCAL = "local"


@dataclass
class RepositoryInfo:
    """Repository information container"""
    url: str
    source: RepositorySource
    name: str
    owner: Optional[str] = None
    branch: str = "main"
    local_path: Optional[Path] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RepositoryManager:
    """
    Manages repository operations including cloning, caching, and cleanup.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the repository manager.
        
        Args:
            cache_dir: Directory to cache cloned repositories. If None, uses temp directory.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "c4_repo_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._active_repos: Dict[str, Repo] = {}
    
    def parse_repository_url(self, url: str) -> RepositoryInfo:
        """
        Parse repository URL and determine source type.
        
        Args:
            url: Repository URL or local path
            
        Returns:
            RepositoryInfo object with parsed details
            
        Raises:
            ValueError: If URL format is not supported
        """
        # Handle local paths
        if os.path.exists(url) or not url.startswith(('http', 'git')):
            path = Path(url).resolve()
            return RepositoryInfo(
                url=str(path),
                source=RepositorySource.LOCAL,
                name=path.name,
                local_path=path
            )
        
        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        
        # Determine source type
        if "github.com" in hostname:
            source = RepositorySource.GITHUB
        elif "gitlab" in hostname:
            source = RepositorySource.GITLAB
        elif any(apache_domain in hostname for apache_domain in ["apache.org", "gitbox.apache.org"]):
            source = RepositorySource.APACHE
        else:
            # Default to GitHub for git URLs
            source = RepositorySource.GITHUB
        
        # Extract owner and repo name from path
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1].replace('.git', '')
        else:
            owner = None
            repo_name = path_parts[0] if path_parts else "unknown"
        
        return RepositoryInfo(
            url=url,
            source=source,
            name=repo_name,
            owner=owner
        )
    
    def clone_repository(self, repo_info: RepositoryInfo, force_refresh: bool = False) -> Path:
        """
        Clone repository to local cache directory.
        
        Args:
            repo_info: Repository information
            force_refresh: If True, delete existing cache and re-clone
            
        Returns:
            Path to cloned repository
            
        Raises:
            git.exc.GitError: If cloning fails
        """
        if repo_info.source == RepositorySource.LOCAL:
            return repo_info.local_path
        
        # Create cache path
        cache_path = self.cache_dir / f"{repo_info.source.value}_{repo_info.owner}_{repo_info.name}"
        
        # Remove existing cache if force refresh
        if force_refresh and cache_path.exists():
            shutil.rmtree(cache_path)
        
        # Clone if not exists
        if not cache_path.exists():
            print(f"Cloning repository from {repo_info.url}...")
            repo = Repo.clone_from(
                repo_info.url, 
                cache_path,
                branch=repo_info.branch,
                depth=1  # Shallow clone for faster download
            )
            self._active_repos[str(cache_path)] = repo
        else:
            print(f"Using cached repository at {cache_path}")
            # Try to update existing repo
            try:
                repo = Repo(cache_path)
                repo.remotes.origin.pull()
                self._active_repos[str(cache_path)] = repo
            except Exception as e:
                print(f"Warning: Could not update cached repo: {e}")
        
        repo_info.local_path = cache_path
        return cache_path
    
    def get_repository_metadata(self, repo_info: RepositoryInfo) -> Dict[str, Any]:
        """
        Fetch repository metadata from API if available.
        
        Args:
            repo_info: Repository information
            
        Returns:
            Dictionary containing repository metadata
        """
        metadata = {}
        
        if repo_info.source == RepositorySource.GITHUB and repo_info.owner:
            try:
                api_url = f"https://api.github.com/repos/{repo_info.owner}/{repo_info.name}"
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    metadata = {
                        'description': data.get('description', ''),
                        'language': data.get('language', ''),
                        'stars': data.get('stargazers_count', 0),
                        'forks': data.get('forks_count', 0),
                        'size': data.get('size', 0),
                        'topics': data.get('topics', []),
                        'created_at': data.get('created_at', ''),
                        'updated_at': data.get('updated_at', ''),
                        'license': data.get('license', {}).get('name', '') if data.get('license') else ''
                    }
            except Exception as e:
                print(f"Warning: Could not fetch GitHub metadata: {e}")
        
        repo_info.metadata = metadata
        return metadata
    
    def cleanup(self):
        """Clean up active repositories and optionally remove cache."""
        for repo in self._active_repos.values():
            try:
                repo.close()
            except:
                pass
        self._active_repos.clear()
    
    def remove_cache(self):
        """Remove all cached repositories."""
        self.cleanup()
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
    
    def list_cached_repositories(self) -> list[Path]:
        """
        List all cached repositories.
        
        Returns:
            List of paths to cached repositories
        """
        if not self.cache_dir.exists():
            return []
        
        return [p for p in self.cache_dir.iterdir() if p.is_dir()]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
