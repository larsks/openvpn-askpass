import pydantic
from typing import ClassVar
import asyncio
import concurrent.futures
import subprocess


class DialogOptions(pydantic.BaseModel):
    _argmap: ClassVar = {
        "entryText": "--entry-text",
    }

    title: str | None
    text: str | None
    entryText: str | None
    width: int | None
    height: int | None


class PasswordOptions(DialogOptions):
    username: bool | None


class Zenity:
    async def zenity(self, *args):
        cmdline = ["zenity"] + list(args)

        loop = asyncio.get_running_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = await loop.run_in_executor(pool, subprocess.check_output, cmdline)
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return True, ""
            raise

        return False, res.decode().rstrip("\n")

    def opts_to_args(self, options: DialogOptions | PasswordOptions):
        args = []
        for field in options.__fields__:
            if val := getattr(options, field, None):
                arg = options._argmap.get(field, field)
                args.append(f"--{arg}")
                if not isinstance(val, bool):
                    args.append(val)
        return args

    async def entry(self, options: DialogOptions):
        args = ["--entry"] + self.opts_to_args(options)
        cancelled, res = await self.zenity(*args)
        return {"cancelled": cancelled, "answer": res}

    async def password(self, options: PasswordOptions):
        args = ["--password"] + self.opts_to_args(options)
        cancelled, res = await self.zenity(*args)
        if not cancelled and options.username:
            username, password = res.split("|", 1)
        else:
            username = res
            password = ""

        return {"cancelled": cancelled, "username": username, "password": password}


zenity = Zenity()
