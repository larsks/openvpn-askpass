#!/usr/bin/python3

import asyncio
import click
import re
import logging

from . import zenity

logging.basicConfig(level="INFO")
log = logging.getLogger(__name__)


async def handle_auth(ctx, reader, writer, match, line):
    while True:
        res = await zenity.zenity.password(zenity.PasswordOptions(username=True))
        if res["cancelled"] or res["username"]:
            break

    if res["cancelled"]:
        writer.write("exit\n".encode())
    else:
        username = res["username"]
        password = res["password"].replace('"', '\\"')
        label = match.group("label")
        writer.write(f'username "{label}" "{username}"\n'.encode())
        writer.write(f'password "{label}" "{password}"\n'.encode())


async def handle_auth_failed(ctx, reader, writer, match, line):
    log.error("password verification failed")


async def log_message(ctx, reader, writer, match, line):
    levellog = {
        "INFO": log.info,
        "SUCCESS": log.info,
        "ERROR": log.error,
        "FATAL": log.error,
    }[match.group("level")]

    levellog(match.group("message"))


cmdMap = {
    r""">PASSWORD:Need '(?P<label>[^']*)' username/password""": handle_auth,
    r""">PASSWORD:Verification Failed: '(?P<label>[^']*)'""": handle_auth_failed,
    r"""(?P<level>(SUCCESS|ERROR|INFO)):(?P<message>.*)""": log_message,
    r""">(?P<level>(FATAL|ERROR|INFO)):(?P<message>.*)""": log_message,
}

cmdMap = {re.compile(k): v for k, v in cmdMap.items()}


async def ovpn_management(reader, writer):
    ctx = {}

    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode()
        for pattern, action in cmdMap.items():
            if match := pattern.match(line):
                await action(ctx, reader, writer, match, line)
                break
        else:
            log.info("ignored message: %s", line)


async def async_main(socketpath):
    log.warning("start server on %s", socketpath)
    server = await asyncio.start_unix_server(ovpn_management, path=socketpath)
    await server.serve_forever()


@click.command()
@click.option(
    "--socket", "-s", "socketpath", envvar="ASKPASS_SOCKET", default="askpass.sock"
)
def main(socketpath):
    asyncio.run(async_main(socketpath))
