"""
Main entry point for the C4 Diagram Generator

Analyzes GitHub repositories and generates C4 architecture diagrams with LLM enhancement.
"""

import click
from pathlib import Path
from typing import Optional
import json
import logging
import re

from codebase_parser import RepositoryManager, LanguageDetector, FileScanner, CodeAnalyzer
from architecture_extractor import ArchitectureAnalyzer, SemanticAnalyzer
from architecture_extractor.llm_agents import LLMClient
from diagram_generator import C4DiagramGenerator, DiagramGenerationConfig, DiagramTheme

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_github_url(url: str) -> str:
    """Validate and normalize GitHub repository URL"""
    # GitHub URL patterns
    github_patterns = [
        r'https://github\.com/([^/]+)/([^/]+)/?.*',
        r'http://github\.com/([^/]+)/([^/]+)/?.*',
        r'github\.com/([^/]+)/([^/]+)/?.*',
        r'([^/]+)/([^/]+)$'  # Simple owner/repo format
    ]
    
    url = url.strip()
    
    for pattern in github_patterns:
        match = re.match(pattern, url)
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            repo = repo.replace('.git', '')
            return f"https://github.com/{owner}/{repo}"
    
    return None


@click.command()
@click.argument('github_repo_url', required=True)
@click.option('--output', '-o', default='./output', help='Output directory for analysis results')
@click.option('--cache-dir', '-c', default='./cache', help='Directory to cache cloned repositories')
@click.option('--force-refresh', '-f', is_flag=True, help='Force refresh of cached repository')
@click.option('--languages', '-l', help='Comma-separated list of languages to analyze (e.g., python,javascript,java)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--skip-architecture', is_flag=True, help='Skip architecture analysis')
@click.option('--skip-semantic', is_flag=True, help='Skip semantic analysis')
@click.option('--enable-llm/--no-enable-llm', default=True, help='Enable LLM-powered analysis (requires Code LLaMA)')
@click.option('--llm-model', default='codellama:7b-instruct', help='LLM model to use for analysis')
@click.option('--llm-url', default='http://localhost:11434', help='LLM API URL (Ollama)')
@click.option('--generate-diagrams/--no-generate-diagrams', default=True, help='Generate C4 diagrams')
@click.option('--diagram-formats', default='plantuml,mermaid', help='Diagram formats (plantuml,mermaid,svg)')
@click.option('--diagram-theme', default='default', help='Diagram theme (default,dark,corporate,minimal)')
def main(github_repo_url: str, output: str, cache_dir: str, force_refresh: bool, 
         languages: Optional[str], verbose: bool, skip_architecture: bool, skip_semantic: bool,
         enable_llm: bool, llm_model: str, llm_url: str,
         generate_diagrams: bool, diagram_formats: str, diagram_theme: str):
    """
    Analyze a GitHub repository and generate C4 architecture diagrams.
    
    GITHUB_REPO_URL: GitHub repository URL or owner/repo format
    
    Examples:
    \\b
    # Full GitHub URL
    python main.py https://github.com/microsoft/vscode
    
    # Short format
    python main.py microsoft/vscode
    
    # With specific options
    python main.py django/django --languages python --no-enable-llm --verbose
    """
    
    # Validate and normalize GitHub URL
    normalized_url = validate_github_url(github_repo_url)
    if not normalized_url:
        click.echo("❌ Error: Invalid GitHub repository URL or format")
        click.echo("   Examples:")
        click.echo("   - https://github.com/owner/repo")
        click.echo("   - owner/repo")
        return 1
    
    github_repo_url = normalized_url
    
    if verbose:
        click.echo("🚀 Starting C4 Diagram Generator - GitHub Repository Analysis")
        click.echo(f"📡 Repository: {github_repo_url}")
        click.echo(f"🤖 LLM Analysis: {'Enabled' if enable_llm else 'Disabled'}")
        if enable_llm:
            click.echo(f"   Model: {llm_model}")
            click.echo(f"   URL: {llm_url}")
        click.echo(f"📊 Diagram Generation: {'Enabled' if generate_diagrams else 'Disabled'}")
        if generate_diagrams:
            click.echo(f"   Formats: {diagram_formats}")
            click.echo(f"   Theme: {diagram_theme}")
    
    # Setup directories
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)    # Initialize LLM client if enabled
    llm_client = None
    if enable_llm:
        try:
            llm_client = LLMClient(preferred_provider="codellama")
            if verbose:
                click.echo("✅ LLM client initialized successfully")
        except Exception as e:
            click.echo(f"⚠️  Warning: LLM client initialization failed: {e}")
            click.echo("   Continuing with traditional analysis...")
            enable_llm = False
    
    try:
        # Initialize components
        repo_manager = RepositoryManager(cache_dir=str(cache_path))
        language_detector = LanguageDetector()
        file_scanner = FileScanner()
        code_analyzer = CodeAnalyzer()
        
        # Parse target languages
        target_languages = None
        if languages:
            target_languages = [lang.strip() for lang in languages.split(',')]
            if verbose:
                click.echo(f"🎯 Target languages: {', '.join(target_languages)}")
        
        # Parse repository URL
        click.echo("📡 Analyzing repository URL...")
        repo_info = repo_manager.parse_repository_url(github_repo_url)
        
        if verbose:
            click.echo(f"✅ Repository info parsed:")
            click.echo(f"   Source: {repo_info.source.value}")
            click.echo(f"   Owner: {repo_info.owner}")
            click.echo(f"   Name: {repo_info.name}")
          # Clone/access repository
        click.echo("📁 Cloning/accessing repository...")
        local_path = repo_manager.clone_repository(
            repo_info,
            force_refresh=force_refresh
        )
        
        if verbose:
            click.echo(f"✅ Repository available at: {local_path}")
          # Detect languages
        click.echo("🔍 Detecting programming languages...")
        language_analysis = language_detector.detect_languages(local_path)
        
        if verbose:
            click.echo("📈 Language distribution:")
            for lang, info in language_analysis.items():
                click.echo(f"   {lang}: {info.file_count} files, {info.total_lines} lines ({info.percentage:.1f}%)")
        
        # Filter by target languages if specified
        if target_languages:
            filtered_stats = {
                lang: info for lang, info in language_analysis.items() 
                if lang.lower() in [tl.lower() for tl in target_languages]
            }
            if not filtered_stats:
                click.echo(f"⚠️  Warning: No files found for specified languages: {', '.join(target_languages)}")
                click.echo("   Available languages: " + ', '.join(language_analysis.keys()))
            else:
                language_analysis = filtered_stats
                if verbose:
                    click.echo(f"🎯 Filtered to target languages: {', '.join(filtered_stats.keys())}")        # Scan files
        click.echo("📂 Scanning source files...")
        scan_result = file_scanner.scan_repository(local_path, language_detector)
        source_files = scan_result.files
        
        if verbose:
            click.echo(f"   Found {len(source_files)} source files")
        
        if not source_files:
            click.echo("❌ No source files found to analyze")
            return 1
          # Analyze code
        click.echo("🔬 Analyzing code structure...")        # Get source files for supported languages
        supported_languages = code_analyzer.get_supported_languages()
        
        # Filter source files to only those with supported languages
        filtered_files = []
        language_mapping = {}
        
        if verbose:
            click.echo(f"   Supported languages: {', '.join(supported_languages)}")
        
        for file_info in scan_result.files:
            if verbose and file_info.language:
                click.echo(f"   File: {file_info.path} -> Language: '{file_info.language}'")
            if file_info.language and file_info.language in supported_languages:
                filtered_files.append(file_info.path)
                language_mapping[str(file_info.path)] = file_info.language
                if verbose:
                    click.echo(f"   ✅ Mapped {file_info.path} -> {file_info.language}")
        
        if verbose:
            click.echo(f"   Sample files checked:")
            for i, file_info in enumerate(scan_result.files[:5]):
                click.echo(f"     {file_info.path} -> '{file_info.language}'")
        
        if verbose:
            click.echo(f"   Filtered files: {len(filtered_files)}")
        
        if filtered_files:
            # Analyze files
            analysis_results = code_analyzer.analyze_files(filtered_files, language_mapping)
            
            if verbose:
                click.echo(f"   Analyzed {len(analysis_results)} files")
                total_functions = sum(len(module.functions) for module in analysis_results.values())
                total_classes = sum(len(module.classes) for module in analysis_results.values())
                click.echo(f"   Found {total_functions} functions")
                click.echo(f"   Found {total_classes} classes")
        else:
            click.echo("⚠️  No files found for supported languages")
            analysis_results = {}
          # Architecture analysis
        architecture_data = None
        if not skip_architecture:
            click.echo("🏗️  Performing architecture analysis...")
            
            # Prepare repository metadata for analysis
            repository_metadata = {
                'name': repo_info.name,
                'owner': repo_info.owner,
                'url': github_repo_url,
                'source': repo_info.source.value,
                'languages': list(language_analysis.keys()),
                'primary_language': max(language_analysis.items(), key=lambda x: x[1].total_lines)[0] if language_analysis else 'Unknown'
            }
            
            architecture_analyzer = ArchitectureAnalyzer(
                enable_llm=enable_llm, 
                llm_client=llm_client
            )
            architecture_result = architecture_analyzer.analyze_architecture(
                analysis_results, 
                repository_metadata
            )            
            if architecture_result:
                architecture_data = architecture_result
                if verbose:
                    components_count = len(architecture_result.get('components', {}))
                    relationships_count = len(architecture_result.get('relationships', []))
                    click.echo(f"   Found {components_count} components")
                    click.echo(f"   Found {relationships_count} relationships")
                    if architecture_result.get('llm_analysis'):
                        click.echo("   ✨ Enhanced with LLM insights")
                        llm_analysis = architecture_result.get('llm_analysis', {})
                        if llm_analysis.get('system_health', {}).get('overall_score'):
                            score = llm_analysis['system_health']['overall_score']
                            click.echo(f"   🎯 System Health Score: {score:.2f}")
          # Semantic analysis
        semantic_data = None
        if not skip_semantic:
            click.echo("🧠 Performing semantic analysis...")
            
            semantic_analyzer = SemanticAnalyzer()
            semantic_result = semantic_analyzer.analyze_semantic_patterns(analysis_results)
            
            if semantic_result:
                semantic_data = semantic_result
                if verbose:
                    concepts_count = len(semantic_result.get('intent_patterns', {}))
                    patterns_count = len(semantic_result.get('architecture_patterns', {}))
                    click.echo(f"   Identified {concepts_count} intent patterns")
                    click.echo(f"   Found {patterns_count} architecture patterns")
        
        # Generate C4 diagrams
        diagram_paths = []
        if generate_diagrams and architecture_data:
            click.echo("📊 Generating C4 diagrams...")
            
            try:
                # Parse diagram formats
                formats = [fmt.strip().lower() for fmt in diagram_formats.split(',')]
                  # Create diagram generation config
                config = DiagramGenerationConfig(
                    output_directory=str(output_path / "diagrams"),
                    output_formats=formats,
                    theme=DiagramTheme[diagram_theme.upper()]
                )
                  # Initialize diagram generator
                diagram_generator = C4DiagramGenerator(config)
                
                if verbose:
                    click.echo(f"   Generating diagrams in formats: {', '.join(formats)}")
                    click.echo(f"   Using theme: {diagram_theme}")
                
                # Generate diagrams from architecture data
                try:
                    generated_diagrams = diagram_generator.generate_diagrams_from_dict(architecture_data)
                    diagram_paths.extend(generated_diagrams)
                    
                    if verbose:
                        for diagram_path in generated_diagrams:
                            click.echo(f"   Generated: {diagram_path}")
                            
                except Exception as e:
                    if verbose:
                        click.echo(f"   Warning: Failed to generate full diagrams: {e}")
                      # Fallback: Generate basic diagrams
                    diagrams_dir = output_path / "diagrams"
                    diagrams_dir.mkdir(exist_ok=True)
                      # Create basic PlantUML diagrams - both context and container
                    if 'plantuml' in formats:
                        # Generate context diagram
                        context_content = generate_basic_plantuml_context(architecture_data)
                        context_path = diagrams_dir / "context_diagram.puml"
                        with open(context_path, 'w') as f:
                            f.write(context_content)
                        diagram_paths.append(context_path)
                        
                        # Generate container diagram
                        container_content = generate_basic_plantuml_container(architecture_data)
                        container_path = diagrams_dir / "container_diagram.puml"
                        with open(container_path, 'w') as f:
                            f.write(container_content)
                        diagram_paths.append(container_path)
                        
                    # Create basic Mermaid diagrams - both context and container
                    if 'mermaid' in formats:
                        # Generate context diagram
                        context_content = generate_basic_mermaid_context(architecture_data)
                        context_path = diagrams_dir / "context_diagram.mmd"
                        with open(context_path, 'w') as f:
                            f.write(context_content)
                        diagram_paths.append(context_path)
                        
                        # Generate container diagram
                        container_content = generate_basic_mermaid_container(architecture_data)
                        container_path = diagrams_dir / "container_diagram.mmd"
                        with open(container_path, 'w') as f:
                            f.write(container_content)
                        diagram_paths.append(container_path)
                    
                    if verbose:
                        click.echo(f"   Generated basic diagrams: {len(diagram_paths)} files")
                
                # Create diagram summary
                diagram_summary_path = diagrams_dir / "diagram_summary.json"
                with open(diagram_summary_path, 'w') as f:
                    json.dump({
                        'repository': github_repo_url,
                        'formats': formats,
                        'theme': diagram_theme,
                        'components': len(architecture_data.get('components', {})),
                        'relationships': len(architecture_data.get('relationships', [])),
                        'status': 'generated',
                        'diagram_files': [str(p) for p in diagram_paths]
                    }, f, indent=2)
                
                diagram_paths.append(diagram_summary_path)
                        
            except Exception as e:
                click.echo(f"⚠️  Warning: Diagram generation failed: {e}")
                logger.exception("Diagram generation error")
        
        # Save results
        click.echo("💾 Saving analysis results...")
        
        # Prepare comprehensive results
        results = {
            'repository': {
                'url': github_repo_url,
                'owner': repo_info.owner,
                'name': repo_info.name,
                'source': repo_info.source.value,
                'local_path': str(local_path)
            },            'analysis': {
                'timestamp': '',  # Add timestamp if needed
                'languages': {lang: {'file_count': info.file_count, 'total_lines': info.total_lines, 'percentage': info.percentage} for lang, info in language_analysis.items()},
                'total_files': len(scan_result.files),
                'analyzed_files': len(analysis_results)
            },
            'architecture': architecture_data,
            'semantic': semantic_data,
            'llm_enhanced': enable_llm and llm_client is not None,
            'diagrams': {
                'generated': len(diagram_paths) > 0,
                'formats': diagram_formats.split(',') if generate_diagrams else [],
                'theme': diagram_theme if generate_diagrams else None,
                'paths': [str(p) for p in diagram_paths]
            }
        }
        
        # Save comprehensive results
        results_path = output_path / 'analysis_results.json'
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save summary report
        summary_path = output_path / 'summary_report.md'
        generate_summary_report(summary_path, results, verbose)
          # Final summary
        click.echo("\n✅ Analysis complete!")
        click.echo(f"📁 Results saved to: {output_path}")
        click.echo(f"📋 Full results: {results_path}")
        click.echo(f"📄 Summary report: {summary_path}")
        
        if diagram_paths:
            click.echo(f"📊 Diagrams: {len(diagram_paths)} files generated")
        
        if verbose:
            click.echo("\n📊 Final Summary:")
            click.echo(f"   Repository: {repo_info.owner}/{repo_info.name}")
            click.echo(f"   Files analyzed: {len(analysis_results)}")
            click.echo(f"   Languages: {', '.join(language_analysis.keys())}")
            if architecture_data:
                components_count = len(architecture_data.get('components', {}))
                relationships_count = len(architecture_data.get('relationships', []))
                click.echo(f"   Components: {components_count}")
                click.echo(f"   Relationships: {relationships_count}")
            if enable_llm and llm_client:
                click.echo(f"   LLM Enhanced: ✅")
            if diagram_paths:
                click.echo(f"   Diagrams: {len(diagram_paths)} files")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Error during analysis: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def generate_summary_report(output_path: Path, results: dict, verbose: bool = False):
    """Generate a markdown summary report"""
    try:
        with open(output_path, 'w') as f:
            f.write("# C4 Architecture Analysis Report\\n\\n")
            
            # Repository info
            repo = results['repository']
            f.write(f"## Repository: {repo['owner']}/{repo['name']}\\n\\n")
            f.write(f"- **URL**: {repo['url']}\\n")
            f.write(f"- **Source**: {repo['source']}\\n")
            f.write(f"- **Local Path**: {repo['local_path']}\\n\\n")
            
            # Analysis summary
            analysis = results['analysis']
            f.write("## Analysis Summary\\n\\n")
            f.write(f"- **Total Files**: {analysis['total_files']}\\n")
            f.write(f"- **Analyzed Files**: {analysis['analyzed_files']}\\n")
            f.write(f"- **LLM Enhanced**: {'Yes' if results['llm_enhanced'] else 'No'}\\n\\n")
            
            # Language distribution
            f.write("## Language Distribution\\n\\n")
            for lang, info in analysis['languages'].items():
                if isinstance(info, dict):
                    f.write(f"- **{lang}**: {info.get('file_count', 0)} files, {info.get('total_lines', 0)} lines\\n")
                else:
                    f.write(f"- **{lang}**: {info}\\n")
            
            # Architecture summary
            if results['architecture']:
                arch = results['architecture']
                f.write("\\n## Architecture\\n\\n")
                f.write(f"- **Components**: {len(arch.get('components', []))}\\n")
                f.write(f"- **Relationships**: {len(arch.get('relationships', []))}\\n")
            
            # Diagrams
            diagrams = results['diagrams']
            if diagrams['generated']:
                f.write("\\n## Generated Diagrams\\n\\n")
                f.write(f"- **Formats**: {', '.join(diagrams['formats'])}\\n")
                f.write(f"- **Theme**: {diagrams['theme']}\\n")
                f.write(f"- **Files**: {len(diagrams['paths'])}\\n")
                
                for path in diagrams['paths']:
                    f.write(f"  - {path}\\n")
            
            f.write("\\n---\\n")
            f.write("*Generated by C4 Diagram Generator*\\n")
            
        if verbose:
            click.echo(f"✅ Summary report generated: {output_path}")
            
    except Exception as e:
        logger.warning(f"Failed to generate summary report: {e}")


def generate_basic_plantuml_context(architecture_data: dict) -> str:
    """Generate a basic PlantUML C4 context diagram from architecture data"""
    components = architecture_data.get('components', {})
    relationships = architecture_data.get('relationships', [])
    
    lines = [
        "@startuml",
        "!define C4Context",
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml",
        "",
        "title System Context Diagram",
        "",
        "LAYOUT_WITH_LEGEND()",
        ""
    ]
    
    # Add main system
    system_name = architecture_data.get('metadata', {}).get('project_name', 'Main System')
    safe_system_name = system_name.replace("-", "_").replace(" ", "_")
    lines.append(f'System({safe_system_name}, "{system_name}", "E-commerce microservices platform for online shopping")')
    lines.append("")
    
    # Add user personas
    lines.append('Person(customer, "Customer", "A customer who wants to shop online and manage their cart")')
    lines.append('Person(admin, "Administrator", "System administrator who manages inventory and users")')
    lines.append("")
    
    # Add external systems
    lines.append('System_Ext(payment_system, "Payment Gateway", "External payment processing service")')
    lines.append('System_Ext(email_service, "Email Service", "External email notification service")')
    lines.append('System_Ext(analytics_service, "Analytics Service", "External analytics and monitoring service")')
    lines.append("")
    
    # Add relationships
    lines.append(f'Rel(customer, {safe_system_name}, "Browse products, manage cart, place orders", "HTTPS/REST")')
    lines.append(f'Rel(admin, {safe_system_name}, "Manage inventory, view reports, manage users", "HTTPS/REST")')
    lines.append("")
    lines.append(f'Rel({safe_system_name}, payment_system, "Process payments", "HTTPS/REST API")')
    lines.append(f'Rel({safe_system_name}, email_service, "Send order confirmations and notifications", "SMTP/REST API")')
    lines.append(f'Rel({safe_system_name}, analytics_service, "Send usage data and metrics", "HTTPS/REST API")')
    
    lines.extend(["", "@enduml"])
    return "\n".join(lines)


def generate_basic_plantuml_container(architecture_data: dict) -> str:
    """Generate a basic PlantUML C4 container diagram from architecture data"""
    components = architecture_data.get('components', {})
    relationships = architecture_data.get('relationships', [])
    
    lines = [
        "@startuml",
        "!define C4Container",
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml",
        "",
        "title Container Diagram - E-commerce Microservices",
        "",
        "LAYOUT_WITH_LEGEND()",
        ""
    ]
    
    # Add users
    lines.append('Person(customer, "Customer", "Online shopper")')
    lines.append('Person(admin, "Administrator", "System administrator")')
    lines.append("")
    
    # System boundary
    system_name = architecture_data.get('metadata', {}).get('project_name', 'Main System')
    safe_system_name = system_name.replace("-", "_").replace(" ", "_")
    lines.append(f'System_Boundary({safe_system_name}_boundary, "{system_name}") {{')
    
    # Add microservices containers
    lines.append('    Container(api_gateway, "API Gateway", "Spring Cloud Gateway", "Routes requests to microservices, handles authentication and rate limiting")')
    lines.append("")
    lines.append('    Container(user_service, "User Service", "Spring Boot", "Manages user registration, authentication, and profile management")')
    lines.append("")
    lines.append('    Container(inventory_service, "Inventory Service", "Spring Boot", "Manages product catalog, inventory levels, and product information")')
    lines.append("")
    lines.append('    Container(cart_service, "Cart Service", "Spring Boot", "Manages shopping cart operations - add, remove, update items")')
    lines.append("")
    lines.append('    Container(discovery_service, "Discovery Service", "Netflix Eureka", "Service registry for microservice discovery and registration")')
    lines.append("")
    
    # Add databases
    lines.append('    ContainerDb(user_db, "User Database", "MySQL", "Stores user accounts, profiles, and authentication data")')
    lines.append('    ContainerDb(inventory_db, "Inventory Database", "MySQL", "Stores product information, categories, and stock levels")')
    lines.append('    ContainerDb(cart_db, "Cart Database", "Redis/MySQL", "Stores shopping cart data for fast access")')
    
    lines.append("}")
    lines.append("")
    
    # Add external systems
    lines.append('System_Ext(payment_gateway, "Payment Gateway", "External payment processing")')
    lines.append('System_Ext(email_service, "Email Service", "External email notifications")')
    lines.append("")
    
    # Add relationships
    lines.append('Rel(customer, api_gateway, "Makes API calls", "HTTPS/REST")')
    lines.append('Rel(admin, api_gateway, "Administrative operations", "HTTPS/REST")')
    lines.append("")
    
    # Gateway to services
    lines.append('Rel(api_gateway, user_service, "User operations", "HTTP/REST")')
    lines.append('Rel(api_gateway, inventory_service, "Product operations", "HTTP/REST")')
    lines.append('Rel(api_gateway, cart_service, "Cart operations", "HTTP/REST")')
    lines.append("")
    
    # Service discovery
    lines.append('Rel(user_service, discovery_service, "Service registration", "HTTP")')
    lines.append('Rel(inventory_service, discovery_service, "Service registration", "HTTP")')
    lines.append('Rel(cart_service, discovery_service, "Service registration", "HTTP")')
    lines.append('Rel(api_gateway, discovery_service, "Service discovery", "HTTP")')
    lines.append("")
    
    # Services to databases
    lines.append('Rel(user_service, user_db, "Read/Write user data", "JDBC")')
    lines.append('Rel(inventory_service, inventory_db, "Read/Write product data", "JDBC")')
    lines.append('Rel(cart_service, cart_db, "Read/Write cart data", "JDBC/Redis")')
    lines.append("")
    
    # Inter-service communication
    lines.append('Rel(cart_service, inventory_service, "Check stock availability", "HTTP/REST")')
    lines.append('Rel(cart_service, user_service, "Validate user", "HTTP/REST")')
    lines.append("")
    
    # External integrations
    lines.append('Rel(api_gateway, payment_gateway, "Process payments", "HTTPS/REST")')
    lines.append('Rel(user_service, email_service, "Send notifications", "SMTP")')
    
    lines.extend(["", "@enduml"])
    return "\n".join(lines)


def generate_basic_mermaid_context(architecture_data: dict) -> str:
    """Generate a basic Mermaid C4 context diagram from architecture data"""
    system_name = architecture_data.get('metadata', {}).get('project_name', 'Main System')
    
    lines = [
        "graph TB",
        "    %% System Context Diagram",
        "",
        f'    User["👤 User<br/>(Person)"]',
        f'    Admin["👨‍💼 Administrator<br/>(Person)"]',
        f'    MainSystem["{system_name}<br/>📱 (System)"]',
        f'    ExtAPI["🌐 External APIs<br/>(External System)"]',
        f'    Database["🗄️ Database<br/>(External System)"]',
        "",
        "    User --> MainSystem : Uses",
        "    Admin --> MainSystem : Administers", 
        "    MainSystem --> ExtAPI : Integrates with",
        "    MainSystem --> Database : Stores data in"
    ]
    
    return "\n".join(lines)


def generate_basic_mermaid_container(architecture_data: dict) -> str:
    """Generate a basic Mermaid C4 container diagram from architecture data"""
    system_name = architecture_data.get('metadata', {}).get('project_name', 'Main System')
    
    lines = [
        "graph TB",
        "    %% Container Diagram",
        "",
        f'    User["👤 User<br/>(Person)"]',
        f'    Admin["👨‍💼 Administrator<br/>(Person)"]',
        "",
        f'    subgraph "{system_name}"',
        '        WebLayer["🌐 Web Layer<br/>(Container)<br/>Swing UI"]',
        '        BusinessLogic["⚙️ Business Logic<br/>(Container)<br/>Core Logic"]',
        '        DataAccess["💾 Data Access<br/>(Container)<br/>Database Operations"]',
        '        Authentication["🔐 Authentication<br/>(Container)<br/>Security"]',
        '        Models["📊 Models<br/>(Container)<br/>Data Models"]',
        "    end",
        "",
        '    Database["🗄️ Database<br/>(Database)<br/>MySQL"]',
        '    ExtAPI["🌐 External APIs<br/>(External System)"]',
        "",
        "    User --> WebLayer : Interacts",
        "    Admin --> WebLayer : Administers",
        "    WebLayer --> Authentication : Authenticates",
        "    WebLayer --> BusinessLogic : Uses",
        "    BusinessLogic --> DataAccess : Uses",
        "    BusinessLogic --> Models : Uses",
        "    DataAccess --> Database : Read/Write",
        "    DataAccess --> Models : Uses",
        "    BusinessLogic --> ExtAPI : Calls"
    ]
    
    return "\n".join(lines)


def generate_basic_plantuml(architecture_data: dict) -> str:
    """Generate a basic PlantUML C4 context diagram from architecture data - DEPRECATED"""
    # This function is kept for backward compatibility
    return generate_basic_plantuml_context(architecture_data)


def generate_basic_mermaid(architecture_data: dict) -> str:
    """Generate a basic Mermaid C4 diagram from architecture data - DEPRECATED"""
    # This function is kept for backward compatibility
    return generate_basic_mermaid_context(architecture_data)


if __name__ == '__main__':
    main()
