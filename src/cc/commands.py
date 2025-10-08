import asyncio
import shutil

import click

from .context import show_context
from .lib.fs import root
from .profile import show_profile


@click.command()
def nuke() -> None:
    """Deletes the .cogency directory in the project root."""
    project_root = root()
    if project_root:
        cogency_path = project_root / ".cogency"
        if cogency_path.exists() and cogency_path.is_dir():
            click.echo(f"Nuking {cogency_path}...")
            shutil.rmtree(cogency_path)
            click.echo("Done.")
        else:
            click.echo(f"No .cogency directory found at {cogency_path}.")
    else:
        click.echo("No project root found.")


@click.command()
@click.pass_context
def profile(ctx: click.Context) -> None:
    """Shows the user profile."""
    asyncio.run(show_profile())


@click.command()
@click.pass_context
def context(ctx: click.Context) -> None:
    """Shows the assembled context."""
    asyncio.run(show_context())
