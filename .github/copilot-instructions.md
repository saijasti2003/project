<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# C4 Diagram Generator Project Instructions

This is a Python project for automatically generating C4 architecture diagrams from source code. The project uses AI-powered analysis to extract architectural relationships and create meaningful visual representations.

## Project Architecture

- `codebase_parser/`: Handles repository cloning and initial code parsing
- `architecture_extractor/`: Performs semantic analysis and relationship extraction
- `diagram_generator/`: Creates C4 diagrams in various formats
- `tests/`: Contains unit and integration tests
- `examples/`: Sample outputs and usage demonstrations
- `config/`: Configuration files and settings

## Code Style Guidelines

- Follow PEP 8 for Python code style
- Use type hints for all function parameters and return values
- Write comprehensive docstrings for all classes and functions
- Implement proper error handling and logging
- Use dataclasses or Pydantic models for structured data
- Prefer composition over inheritance
- Keep functions focused and single-purpose

## Key Technologies

- tree-sitter for language-agnostic parsing
- GitPython for repository operations
- Pydantic for data validation
- Click for CLI interface
- Python's ast module for Python-specific analysis

## Testing Guidelines

- Write unit tests for all core functionality
- Include integration tests for end-to-end workflows
- Use pytest as the testing framework
- Mock external dependencies (Git repositories, APIs)
- Test with sample repositories of different types

## Documentation

- Include clear examples in docstrings
- Document all configuration options
- Provide usage examples for different repository types
- Explain the C4 diagram generation process
