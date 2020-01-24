# coding: future_fstrings

import click
import hvac
import yaml

from vc.config import update_config_token
from vc.kv_client import MountNotFound


@click.group()
def cli():
    pass


@cli.command()
@click.option("--password", prompt=True, hide_input=True)
@click.pass_context
def login(ctx, password):
    """Authenticate against Vault using your prefered method."""
    client = ctx.obj["client"]
    config = ctx.obj["config"]

    auth = config.get("authentication")
    if not auth:
        click.echo(
            "Please configure the 'authentication' section in your config file",
            err=True,
        )
        exit(1)

    user = auth.get("user")
    if not user:
        click.echo(
            "Please specifiy a user with which to authenticate against vault ('user' setting)",
            err=True,
        )
        exit(1)

    auth_type = auth.get("type")
    if not auth_type:
        click.echo("Please specify the type of the authentication backend", err=True)
        exit(1)

    if auth_type == "ldap":
        auth_path = auth.get("path")
        if not auth_path:
            click.echo(
                "Please specify the path to the authentication backend", err=True
            )
            exit(1)
    elif auth_type == "userpass":
        auth_path = "userpass"

    try:
        token = client.login(user, password, auth_path, auth_type)
        update_config_token(token)
    except hvac.exceptions.InvalidPath:
        click.echo(
            "It appears that your configured authentication backend does not exis",
            err=True,
        )


@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx, query):
    """Search for secret paths that contrain the search string"""
    client = ctx.obj["client"]

    try:
        paths = client.traverse()
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)

    results = [path for path in paths if query in path]
    if not results:
        click.echo("No search results.")
    elif len(results) == 1:
        path = results[0]
        secret = client.get(path)
        click.echo(f"# {path}")
        click.echo(yaml.dump(secret))
    else:
        for path in results:
            click.echo(path)


@cli.command()
@click.argument("path")
@click.pass_context
def show(ctx, path):
    """Show an existing secret"""
    client = ctx.obj["client"]
    try:
        secret = client.get(path)
        click.echo(yaml.dump(secret))
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)


@cli.command()
@click.argument("src")
@click.argument("dest")
@click.pass_context
def mv(ctx, src, dest):
    """Move an existing secret to another location"""
    client = ctx.obj["client"]

    try:
        secret = client.get(src)
    except hvac.exceptions.InvalidPath:
        click.echo(f'Source path "{src}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Source path "{src}" is not under a valid mount point.', err=True)
        exit(1)

    try:
        secret = client.get(dest)
        click.echo("The destination secret already exists.")
        if not click.confirm("Do you want overwrite it?", abort=True):
            return

        client.delete(dest)
    except hvac.exceptions.InvalidPath:
        pass

    except MountNotFound:
        click.echo(f'Source path "{path}" is not under a valid mount point.', err=True)
        exit(1)

    client.put(dest, secret)
    client.delete(src)
    click.echo("Secret successfully moved!")


@cli.command()
@click.argument("src")
@click.argument("dest")
@click.pass_context
def cp(ctx, src, dest):
    """Copy an existing secret to another location"""
    client = ctx.obj["client"]

    try:
        secret = client.get(src)
    except hvac.exceptions.InvalidPath:
        click.echo(f'Source path "{src}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Source path "{src}" is not under a valid mount point.', err=True)
        exit(1)

    try:
        secret = client.get(dest)
        click.echo("The destination secret already exists.")
        if not click.confirm("Do you want overwrite it?", abort=True):
            exit(1)
        client.delete(dest)
    except hvac.exceptions.InvalidPath:
        pass
    except MountNotFound:
        click.echo(
            f'Destination path "{path}" is not under a valid mount point.', err=True
        )
        exit(1)

    client.put(dest, secret)
    click.echo("Secret successfully copied!")


@cli.command()
@click.argument("path")
@click.pass_context
def edit(ctx, path):
    """Edit a secret at specified path"""
    client = ctx.obj["client"]

    try:
        secret = client.get(path)
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not yet exist. Creating a new secret.')
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)

    if secret:
        edited = click.edit(yaml.dump(secret))
    else:
        edited = click.edit()

    data = yaml.load(edited, Loader=yaml.FullLoader)
    client.put(path, data)
    click.echo("Secret successfully edited!")


@cli.command()
@click.argument("path")
@click.argument("data")
@click.pass_context
def insert(ctx, path, data):
    """Insert an new secret"""
    client = ctx.obj["client"]

    try:
        key, value = data.split("=")
    except ValueError as e:
        click.echo(f'Data "{data}" is not a valid key/value pair.', err=True)
        exit(1)

    try:
        secret = client.put(path, {key: value})
        click.echo("Secret successfully inserted!")
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)


@cli.command()
@click.argument("path", required=False, default="/")
@click.option("-r", "--recursive/--no-recursive", default=False)
@click.pass_context
def ls(ctx, path, recursive):
    """List all secrets at specified path"""
    client = ctx.obj["client"]

    try:
        if recursive:
            paths = client.traverse(path)
        else:
            paths = client.list(path)
        for p in paths:
            click.echo(p)
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)


@cli.command()
@click.argument("path", required=False)
@click.pass_context
def rm(ctx, path):
    """Remove a secret at specified path"""
    client = ctx.obj["client"]
    try:
        client.get(path)
        client.delete(path)
        click.echo("Secret successfully deleted")
    except hvac.exceptions.InvalidPath:
        click.echo(f'Path "{path}" does not exist.', err=True)
        exit(1)
    except MountNotFound:
        click.echo(f'Path "{path}" is not under a valid mount point.', err=True)
        exit(1)
