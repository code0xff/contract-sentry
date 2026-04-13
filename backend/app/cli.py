"""CLI — `python -m app.cli`."""
from __future__ import annotations

import json
from pathlib import Path

import click
import httpx


@click.group()
@click.option("--api", default="http://localhost:8000", envvar="CENTRY_API")
@click.pass_context
def cli(ctx: click.Context, api: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj["api"] = api.rstrip("/")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--name", default=None)
@click.pass_context
def analyze(ctx: click.Context, file: Path, name: str | None) -> None:
    source = file.read_text(encoding="utf-8")
    payload = {"name": name or file.name, "language": "solidity", "source": source}
    api = ctx.obj["api"]
    resp = httpx.post(f"{api}/api/v1/contracts", json=payload, timeout=30)
    resp.raise_for_status()
    contract = resp.json()
    resp2 = httpx.post(f"{api}/api/v1/contracts/{contract['id']}/analyze", json={}, timeout=30)
    resp2.raise_for_status()
    click.echo(json.dumps(resp2.json(), indent=2))


@cli.command()
@click.argument("job_id")
@click.pass_context
def status(ctx: click.Context, job_id: str) -> None:
    api = ctx.obj["api"]
    resp = httpx.get(f"{api}/api/v1/jobs/{job_id}", timeout=15)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))


@cli.command()
@click.argument("job_id")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "markdown", "html"]))
@click.pass_context
def report(ctx: click.Context, job_id: str, fmt: str) -> None:
    api = ctx.obj["api"]
    suffix = "" if fmt == "json" else f"/{fmt}"
    resp = httpx.get(f"{api}/api/v1/reports/{job_id}{suffix}", timeout=15)
    resp.raise_for_status()
    click.echo(resp.text)


if __name__ == "__main__":
    cli(obj={})
