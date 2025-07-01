"""Command-line interface for MemoryBank SDK."""

import asyncio
import json
import sys
from typing import Optional, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import tabulate

from .client import AsyncMemoryBankClient
from .config import MemoryBankConfig
from .models import MemoryMetadata
from .exceptions import MemoryBankError

console = Console()

def create_client(config_file: Optional[str] = None) -> AsyncMemoryBankClient:
    """Create a MemoryBank client from config."""
    if config_file:
        config = MemoryBankConfig.from_file(config_file)
    else:
        config = MemoryBankConfig.from_env()
    
    return AsyncMemoryBankClient(config)

@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """MemoryBank CLI - Manage your AI's long-term memory."""
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config

@cli.command()
@click.argument('content')
@click.option('--user-id', help='User ID for the memory')
@click.option('--category', help='Category for the memory')
@click.option('--tags', help='Comma-separated tags')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.pass_context
def store(ctx, content, user_id, category, tags, metadata):
    """Store a new memory."""
    async def _store():
        async with create_client(ctx.obj['config_file']) as client:
            # Build metadata
            meta_dict = {}
            if user_id:
                meta_dict['user_id'] = user_id
            if category:
                meta_dict['category'] = category
            if tags:
                meta_dict['tags'] = [tag.strip() for tag in tags.split(',')]
            if metadata:
                try:
                    extra_meta = json.loads(metadata)
                    meta_dict.update(extra_meta)
                except json.JSONDecodeError:
                    console.print("[red]Error: Invalid JSON in metadata[/red]")
                    return
            
            memory_metadata = MemoryMetadata.from_dict(meta_dict)
            
            try:
                memory_id = await client.store_memory(content, memory_metadata)
                console.print(f"[green]✓ Memory stored with ID: {memory_id}[/green]")
            except MemoryBankError as e:
                console.print(f"[red]Error storing memory: {e}[/red]")
    
    asyncio.run(_store())

@cli.command()
@click.argument('query')
@click.option('--top-k', '-k', default=5, help='Number of memories to retrieve')
@click.option('--user-id', help='Filter by user ID')
@click.option('--category', help='Filter by category')
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json', 'simple']), 
              help='Output format')
@click.pass_context
def retrieve(ctx, query, top_k, user_id, category, output_format):
    """Retrieve memories matching a query."""
    async def _retrieve():
        async with create_client(ctx.obj['config_file']) as client:
            # Build metadata filter
            meta_dict = {}
            if user_id:
                meta_dict['user_id'] = user_id
            if category:
                meta_dict['category'] = category
            
            metadata_filter = MemoryMetadata.from_dict(meta_dict) if meta_dict else None
            
            try:
                results = await client.retrieve_memories(query, top_k, metadata_filter)
                
                if not results:
                    console.print("[yellow]No memories found matching the query[/yellow]")
                    return
                
                if output_format == 'json':
                    output = [result.to_dict() for result in results]
                    console.print(json.dumps(output, indent=2))
                
                elif output_format == 'simple':
                    for i, result in enumerate(results, 1):
                        console.print(f"{i}. [bold]{result.memory.content}[/bold]")
                        console.print(f"   Score: {result.score:.3f}")
                        console.print(f"   ID: {result.memory.memory_id}")
                        console.print()
                
                else:  # table format
                    table = Table(title=f"Memories for query: '{query}'")
                    table.add_column("Score", style="cyan", width=8)
                    table.add_column("Content", style="white")
                    table.add_column("Category", style="green", width=12)
                    table.add_column("Memory ID", style="dim", width=12)
                    
                    for result in results:
                        memory = result.memory
                        table.add_row(
                            f"{result.score:.3f}",
                            memory.content[:80] + "..." if len(memory.content) > 80 else memory.content,
                            memory.metadata.category or "N/A",
                            memory.memory_id[:8] + "..."
                        )
                    
                    console.print(table)
                
            except MemoryBankError as e:
                console.print(f"[red]Error retrieving memories: {e}[/red]")
    
    asyncio.run(_retrieve())

@cli.command()
@click.argument('memory_id')
@click.pass_context
def forget(ctx, memory_id):
    """Delete a memory by ID."""
    async def _forget():
        async with create_client(ctx.obj['config_file']) as client:
            try:
                success = await client.forget_memory(memory_id)
                if success:
                    console.print(f"[green]✓ Memory {memory_id} deleted[/green]")
                else:
                    console.print(f"[yellow]Memory {memory_id} not found[/yellow]")
            except MemoryBankError as e:
                console.print(f"[red]Error deleting memory: {e}[/red]")
    
    asyncio.run(_forget())

@cli.command()
@click.argument('message')
@click.option('--system-prompt', help='System prompt for the LLM')
@click.option('--model', help='Specific model to use')
@click.option('--user-id', help='User ID for context')
@click.pass_context
def chat(ctx, message, system_prompt, model, user_id):
    """Chat with memory-augmented LLM."""
    async def _chat():
        async with create_client(ctx.obj['config_file']) as client:
            metadata = None
            if user_id:
                metadata = MemoryMetadata(user_id=user_id)
            
            try:
                response = await client.chat(
                    message,
                    system_prompt=system_prompt,
                    model=model,
                    metadata=metadata
                )
                
                # Display response
                panel = Panel(
                    response.response,
                    title="Assistant Response",
                    border_style="blue"
                )
                console.print(panel)
                
                # Display used memories
                if response.memories_used:
                    console.print(f"\n[dim]Used {len(response.memories_used)} memories:[/dim]")
                    for i, result in enumerate(response.memories_used[:3], 1):
                        console.print(f"[dim]{i}. {result.memory.content[:60]}... (score: {result.score:.3f})[/dim]")
                
                console.print(f"\n[dim]Model: {response.model_used}[/dim]")
                
            except MemoryBankError as e:
                console.print(f"[red]Error in chat: {e}[/red]")
    
    asyncio.run(_chat())

@cli.command()
@click.pass_context
def stats(ctx):
    """Show memory statistics."""
    async def _stats():
        async with create_client(ctx.obj['config_file']) as client:
            try:
                stats = await client.get_memory_stats()
                
                table = Table(title="Memory Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("Total Memories", str(stats.total_memories))
                table.add_row("Average Importance", f"{stats.avg_importance:.3f}")
                table.add_row("Oldest Memory", str(stats.oldest_memory) if stats.oldest_memory else "N/A")
                table.add_row("Newest Memory", str(stats.newest_memory) if stats.newest_memory else "N/A")
                table.add_row("Embedding Provider", stats.embedding_provider)
                
                console.print(table)
                
            except MemoryBankError as e:
                console.print(f"[red]Error getting stats: {e}[/red]")
    
    asyncio.run(_stats())

@cli.command()
@click.pass_context
def health(ctx):
    """Check API health."""
    async def _health():
        async with create_client(ctx.obj['config_file']) as client:
            try:
                health_data = await client.health_check()
                if health_data.get('status') == 'healthy':
                    console.print("[green]✓ API is healthy[/green]")
                    console.print(f"Timestamp: {health_data.get('timestamp')}")
                else:
                    console.print("[yellow]⚠ API status unknown[/yellow]")
                    console.print(health_data)
            except Exception as e:
                console.print(f"[red]✗ API is not responding: {e}[/red]")
    
    asyncio.run(_health())

@cli.command()
@click.pass_context
def forget_curve(ctx):
    """Run the forgetting curve manually."""
    async def _forget_curve():
        async with create_client(ctx.obj['config_file']) as client:
            try:
                result = await client.run_forgetting_curve()
                console.print("[green]✓ Forgetting curve applied[/green]")
                console.print(f"Timestamp: {result.get('timestamp')}")
            except MemoryBankError as e:
                console.print(f"[red]Error running forgetting curve: {e}[/red]")
    
    asyncio.run(_forget_curve())

@cli.command()
@click.option('--api-key', prompt=True, hide_input=True, help='API key')
@click.option('--base-url', default='http://localhost:8000', help='Base URL')
@click.option('--llm-provider', default='claude', help='LLM provider')
@click.option('--output', '-o', default='memorybank-config.json', help='Output file')
def configure(api_key, base_url, llm_provider, output):
    """Create a configuration file."""
    config = MemoryBankConfig(
        api_key=api_key,
        base_url=base_url,
        llm_provider=llm_provider
    )
    
    try:
        config.to_file(output)
        console.print(f"[green]✓ Configuration saved to {output}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]")

def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    main()