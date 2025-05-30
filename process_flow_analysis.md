# C4 Diagram Generator - Process Flow and LLM Integration Analysis

## Overview
The C4 Diagram Generator is an intelligent system that automatically generates C4 architecture diagrams from source code using AI-powered analysis. It integrates multiple LLM agents to understand code structure, relationships, and responsibilities.

## High-Level Process Flow

### 1. **Initialization Phase**
```
main_github.py (Entry Point)
├── Parse GitHub URL and validate
├── Initialize LLM Client (if enabled)
│   ├── Try CodeLlama Client (preferred)
│   ├── Fallback to OpenAI Client
│   └── Fallback to LocalLLM (mock)
├── Initialize Core Components
│   ├── RepositoryManager
│   ├── LanguageDetector
│   ├── FileScanner
│   └── CodeAnalyzer
└── Initialize ArchitectureAnalyzer (with LLM support)
```

### 2. **Repository Processing Phase**
```
Repository Management
├── Parse repository URL
├── Clone/access repository (with caching)
├── Detect programming languages
│   └── Analyze file extensions and content
├── Scan source files
│   ├── Filter by file patterns
│   ├── Exclude test/config/documentation files
│   └── Apply language filters
└── Analyze code structure
    ├── Use tree-sitter parsers for supported languages
    ├── Extract functions, classes, imports
    └── Calculate complexity scores
```

### 3. **Architecture Analysis Phase (Core LLM Integration)**
```
ArchitectureAnalyzer.analyze_architecture()
├── Traditional Analysis
│   ├── ComponentClassifier.classify_components()
│   └── RelationshipExtractor.extract_relationships()
├── LLM-Enhanced Analysis (if enabled)
│   ├── Prepare components for LLM analysis
│   ├── LLMOrchestrator.analyze_system()
│   └── Integrate LLM insights with traditional analysis
└── Generate architecture insights
```

### 4. **LLM Orchestration (Detailed Flow)**
```
LLMOrchestrator.analyze_system()
├── Step 1: Individual Component Analysis
│   └── For each component:
│       ├── CodeUnderstandingAgent.understand_module()
│       ├── RelationshipAnalysisAgent.analyze_component_relationships()
│       └── ResponsibilityAgent.analyze_component_responsibilities()
├── Step 2: System-wide Relationship Analysis
│   └── RelationshipAnalysisAgent.analyze_system_relationships()
├── Step 3: Cross-cutting Concerns Analysis
│   └── RelationshipAnalysisAgent.identify_cross_cutting_concerns()
├── Step 4: Responsibility Conflicts Analysis
│   └── ResponsibilityAgent.identify_responsibility_conflicts()
├── Step 5: Extract Architectural Patterns
├── Step 6: Assess System Health
└── Step 7: Generate Recommendations
```

### 5. **Diagram Generation Phase**
```
Diagram Generation
├── Create C4DiagramGenerator
├── Generate diagrams from architecture data
│   ├── Context Diagrams
│   ├── Container Diagrams
│   └── Component Diagrams
├── Support multiple formats (PlantUML, Mermaid, SVG)
└── Apply themes and styling
```

## LLM Integration Points and Detailed Prompts

### 1. **CodeUnderstandingAgent - Module Understanding**

**Location**: `architecture_extractor/llm_agents/code_understanding_agent.py`

**Purpose**: Understand the architectural significance and purpose of code modules

**Key LLM Calls**:

#### `understand_module()` Method
- **System Prompt**: 
```
You are an expert software architect creating C4 architecture diagrams.
Analyze the provided code module and provide comprehensive understanding including:
1. Primary and secondary purposes
2. C4 classification (person, software_system, container, component)
3. Interfaces provided and consumed
4. Data entities handled
5. Business rules implemented
6. Technical concerns addressed
7. Quality indicators
```

- **User Prompt Template**:
```python
f"""Analyze this {language} module from {file_path}:{context_info}

```{language}
{code_content}
```

Provide a comprehensive architectural understanding focusing on:
- What is the main purpose and responsibility?
- How does it fit in C4 architecture (Component, Container, etc.)?
- What interfaces does it provide to other components?
- What external interfaces does it use?
- What data does it handle?
- What business logic does it implement?
- What technical concerns does it address?"""
```

- **Expected Response**: JSON object with module understanding details
- **Temperature**: 0.1 (low for consistency)
- **Max Tokens**: 1536

#### `analyze_code_structure()` Method
- **System Prompt**: Focuses on structural analysis and design patterns
- **User Prompt**: Analyzes code structure, complexity, and architectural patterns
- **Expected Response**: CodeStructureAnalysis object
- **Temperature**: 0.1
- **Max Tokens**: 1024

### 2. **RelationshipAnalysisAgent - Component Relationships**

**Location**: `architecture_extractor/llm_agents/relationship_analysis_agent.py`

**Purpose**: Identify and analyze relationships between code components

**Key LLM Calls**:

#### `analyze_component_relationships()` Method
- **System Prompt**:
```
You are an expert software architect analyzing code relationships for C4 diagrams.
Analyze the provided component and its context to identify:
1. Direct relationships (uses, depends_on, implements, extends, contains, calls, imports)
2. Interfaces provided and consumed
3. Dependency groups and patterns
4. Integration complexity
5. Coupling level
```

- **User Prompt Template**:
```python
f"""Analyze relationships for component '{component_name}' in this {language} code:

```{language}
{component_code}
```{context_info}

Identify all relationships this component has with:
1. Other internal components/modules
2. External services and APIs
3. Databases and data stores
4. Frameworks and libraries
5. Infrastructure components

Focus on:
- Import/dependency statements
- Function calls and method invocations
- API endpoints consumed or provided
- Database connections and queries
- Message passing or event handling
- Configuration dependencies

Provide specific evidence from the code for each relationship."""
```

- **Expected Response**: JSON with relationship analysis
- **Temperature**: 0.1
- **Max Tokens**: 2048

#### `analyze_system_relationships()` Method
- **Purpose**: Analyze relationships across the entire system
- **Processes multiple components simultaneously**
- **Identifies system-wide patterns and dependencies**

#### `identify_cross_cutting_concerns()` Method
- **Purpose**: Identify concerns that span multiple components
- **Analyzes security, logging, error handling, caching patterns**

### 3. **ResponsibilityAgent - Business and Technical Responsibilities**

**Location**: `architecture_extractor/llm_agents/responsibility_agent.py`

**Purpose**: Determine business and technical responsibilities of components

**Key LLM Calls**:

#### `analyze_component_responsibilities()` Method
- **System Prompt**:
```
You are an expert business analyst and software architect.
Analyze the provided code component to identify its responsibilities both from business and technical perspectives.

For business responsibilities, consider:
- What business capabilities does this component enable?
- What business rules does it implement?
- What data does it own or manage?
- Who are the stakeholders that care about this component?

For technical responsibilities, consider:
- What technical capabilities does it provide?
- What quality attributes are important (performance, security, etc.)?
- What technologies and frameworks does it use?
- What are its integration responsibilities?
```

- **User Prompt**: Analyzes component code for business and technical responsibilities
- **Expected Response**: JSON with responsibility analysis
- **Temperature**: 0.1
- **Max Tokens**: 1536

#### `identify_responsibility_conflicts()` Method
- **Purpose**: Identify overlapping or conflicting responsibilities between components
- **Analyzes business capability overlaps and data ownership conflicts**

### 4. **LLMOrchestrator - System-wide Analysis**

**Location**: `architecture_extractor/llm_agents/llm_orchestrator.py`

**Purpose**: Coordinates all LLM agents for comprehensive analysis

**Key Methods**:

#### `analyze_component()` Method
- **Orchestrates all three agents for a single component**
- **Returns ComprehensiveAnalysis object**
- **Includes confidence scores and metadata**

#### `analyze_system()` Method
- **Performs system-wide analysis**
- **Coordinates analysis of all components**
- **Generates system health assessment**
- **Creates improvement recommendations**

## LLM Client Architecture

### **LLMClient Class Hierarchy**
```
BaseLLMClient (Abstract)
├── CodeLlamaClient (Primary - via Ollama)
├── OpenAIClient (Fallback)
└── LocalLLMClient (Mock for testing)
```

### **CodeLlamaClient Details**
- **Default Model**: `codellama:7b-instruct`
- **API Endpoint**: `http://localhost:11434` (Ollama)
- **Request Format**: Ollama API format
- **Timeout**: 120 seconds
- **Temperature**: 0.1 (low for consistency)
- **Streaming**: Disabled for better error handling

### **Request/Response Flow**
```
LLMRequest → BaseLLMClient.generate() → LLMResponse
├── prompt: str
├── system_prompt: Optional[str]
├── max_tokens: int (2048 default)
├── temperature: float (0.1 default)
└── model: Optional[str]
```

## Error Handling and Fallbacks

### **LLM Availability Checks**
1. **Server Availability**: Check if Ollama is running
2. **Model Availability**: Verify CodeLlama model is installed
3. **Graceful Degradation**: Fall back to traditional analysis if LLM fails

### **Fallback Mechanisms**
- **Component Analysis**: Provides minimal fallback data if LLM fails
- **Confidence Scoring**: Lower confidence scores for fallback data
- **Analysis Metadata**: Records when fallbacks are used

## Performance Considerations

### **Batching and Optimization**
- **Component Batching**: Process multiple components efficiently
- **Context Limiting**: Limit context code to prevent token overflow
- **Timeout Management**: 120-second timeout for LLM requests

### **Caching**
- **Repository Caching**: Cache cloned repositories
- **LLM Response Caching**: Could be implemented for repeated analyses

## Output and Integration

### **Architecture Data Structure**
```json
{
  "metadata": {
    "project_name": "string",
    "total_components": "number",
    "llm_enhanced": "boolean"
  },
  "components": {},
  "relationships": [],
  "llm_analysis": {
    "system_health": {},
    "architectural_patterns": [],
    "recommendations": []
  }
}
```

### **Diagram Generation Integration**
- LLM analysis enhances traditional C4 diagram generation
- Provides richer component descriptions and relationships
- Enables better categorization and grouping

## Configuration Options

### **Command Line Options**
- `--enable-llm/--no-enable-llm`: Toggle LLM analysis
- `--llm-model`: Specify model (default: codellama:7b-instruct)
- `--llm-url`: Specify Ollama URL (default: http://localhost:11434)

### **Environment Dependencies**
- **Ollama Server**: Must be running for CodeLlama
- **Model Installation**: CodeLlama model must be pulled
- **API Keys**: OpenAI key for fallback (optional)

## Summary of LLM Calls

The system makes approximately **4-7 LLM calls per component**:

1. **Code Structure Analysis** (CodeUnderstandingAgent)
2. **Module Understanding** (CodeUnderstandingAgent)
3. **Component Relationships** (RelationshipAnalysisAgent)
4. **Component Responsibilities** (ResponsibilityAgent)
5. **System Relationships** (once per system)
6. **Cross-cutting Concerns** (once per system)
7. **Responsibility Conflicts** (once per system)

For a system with 10 components, this results in approximately **40-50 LLM calls**, making the analysis comprehensive but potentially time-consuming.
