# C4 Diagram Generator

An intelligent system for automatically generating C4 architecture diagrams from source code using AI-powered analysis.

## Features

- **Multi-source Code Parsing**: Support for GitHub, GitLab, and Apache Software Foundation repositories
- **Language Agnostic**: Supports Python, Java, JavaScript/TypeScript, C++, Go, and more
- **Automated C4 Diagrams**: Generates Context, Container, and Component level diagrams
- **Dependency Mapping**: Accurate extraction of architectural relationships
- **Version Control Integration**: Works with Git repositories

## Project Structure

```
├── codebase_parser/          # Code parsing and repository handling
├── architecture_extractor/   # Architecture analysis and relationship extraction
├── diagram_generator/        # C4 diagram generation
├── tests/                   # Unit and integration tests
├── examples/                # Sample outputs and usage examples
└── config/                  # Configuration files
```

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the parser on a repository:
```bash
python main.py --repo https://github.com/example/repo --output ./diagrams
```

## Architecture

The system consists of three main components:

1. **Codebase Parser**: Clones and analyzes repositories from various sources
2. **Architecture Extractor**: Uses tree-sitter for language-agnostic parsing and AI for semantic analysis
3. **Diagram Generator**: Creates visual C4 diagrams in multiple formats

## Supported Repository Sources

- GitHub public repositories
- GitLab projects  
- Apache Software Foundation projects
- Local repositories

## Supported Languages

- Python
- Java
- JavaScript/TypeScript
- C++
- Go
- And more through tree-sitter

## License

MIT License
