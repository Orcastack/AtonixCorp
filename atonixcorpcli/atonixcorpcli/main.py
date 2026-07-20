"""Click command line interface for AtonixCorp DCI."""
import json
import os

import click
from atonixcorpsdk import AtonixCorpClient, AtonixCorpError, Credentials, SANDBOX_URL


def _client(ctx):
    return AtonixCorpClient(
        base_url=ctx.obj["url"],
        credentials=Credentials(access_token=ctx.obj.get("token"), api_key=ctx.obj.get("api_key")),
    )


def _emit(ctx, value):
    click.echo(json.dumps(value, indent=2, sort_keys=True) if ctx.obj["output"] == "json" else _plain(value))


def _plain(value):
    if isinstance(value, dict):
        return "\n".join(f"{key}: {item}" for key, item in value.items())
    return str(value)


@click.group()
@click.option("--url", default=lambda: os.getenv("ATONIXCORP_API_URL", SANDBOX_URL), show_default="sandbox")
@click.option("--token", envvar="ATONIXCORP_ACCESS_TOKEN", help="DCI OAuth2/JWT Bearer token.")
@click.option("--api-key", envvar="ATONIXCORP_API_KEY", help="DCI API key.")
@click.option("--output", type=click.Choice(["json", "text"]), default="json")
@click.pass_context
def cli(ctx, url, token, api_key, output):
    """Manage AtonixCorp enterprise governance through DCI."""
    ctx.ensure_object(dict)
    ctx.obj.update(url=url, token=token, api_key=api_key, output=output)


@cli.command("login")
@click.option("--organization-id", required=True)
@click.option("--api-key", required=True, prompt=True, hide_input=True)
@click.pass_context
def login(ctx, organization_id, api_key):
    """Exchange a DCI API key for a short-lived Bearer token."""
    try:
        _emit(ctx, _client(ctx).login(api_key=api_key, organization_id=organization_id))
    except AtonixCorpError as error:
        raise click.ClickException(str(error)) from error


@cli.group()
def entity():
    """Create and inspect enterprise entities."""


@entity.command("create")
@click.option("--organization-id", required=True, type=int)
@click.option("--name", required=True)
@click.option("--country", required=True)
@click.option("--entity-type", default="corporation", show_default=True)
@click.option("--department", "departments", multiple=True, help="Approved department catalog key; repeat as needed.")
@click.pass_context
def create_entity(ctx, organization_id, name, country, entity_type, departments):
    """Create an audited entity with governed department selections."""
    payload = {"organization_id": organization_id, "name": name, "country": country, "entity_type": entity_type, "department_selections": list(departments)}
    try:
        _emit(ctx, _client(ctx).create_entity(payload))
    except AtonixCorpError as error:
        raise click.ClickException(str(error)) from error


@cli.group()
def workspace():
    """Create governed workspaces and collaboration resources."""


@workspace.command("create")
@click.option("--name", required=True)
@click.option("--description", default="")
@click.option("--linked-entity-id", type=int)
@click.pass_context
def create_workspace(ctx, name, description, linked_entity_id):
    payload = {"name": name, "description": description, "linked_entity_id": linked_entity_id}
    try:
        _emit(ctx, _client(ctx).create_workspace(payload))
    except AtonixCorpError as error:
        raise click.ClickException(str(error)) from error


@cli.group()
def equity():
    """Allocate shareholder equity through the governed registry."""


@equity.command("allocate")
@click.option("--entity-id", required=True, type=int)
@click.option("--shareholder-id", required=True)
@click.option("--share-class-id", required=True)
@click.option("--quantity", required=True, type=int)
@click.option("--department-id", type=int)
@click.pass_context
def allocate_equity(ctx, entity_id, shareholder_id, share_class_id, quantity, department_id):
    """Allocate equity to a shareholder; optional department metadata is audited."""
    payload = {"shareholder": shareholder_id, "share_class": share_class_id, "quantity": quantity}
    if department_id:
        payload["department_id"] = department_id
    try:
        _emit(ctx, _client(ctx).allocate_equity(entity_id, payload))
    except AtonixCorpError as error:
        raise click.ClickException(str(error)) from error


@cli.command("sandbox-status")
@click.pass_context
def sandbox_status(ctx):
    """Confirm connectivity to a sandbox DCI API."""
    try:
        _emit(ctx, _client(ctx).request("GET", "/status", authenticated=False))
    except AtonixCorpError as error:
        raise click.ClickException(str(error)) from error


def main():
    cli(prog_name="atonixcorp")


if __name__ == "__main__":
    main()
