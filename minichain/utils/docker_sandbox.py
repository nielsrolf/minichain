import asyncio
import os
import threading
from time import sleep
from typing import List

import docker
import asyncio




SPECIAL_END_TOKEN = "END_OF_COMMAND_293842"  # Rare special token

async def run_in_container(
    commands: List[str],
    container_name: str = None,
    image_name="nielsrolf/minichain:latest",
    timeout=60  # in seconds
):
    client = docker.from_env()

    if container_name:
        # Check if container exists
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            container = None
    else:
        container = None

    if container is None or container.status != "running":
        # Run a new container
        container = client.containers.run(
            image=image_name,
            name=container_name,
            command='/bin/sh -c "tail -f /dev/null"',
            detach=True,
            volumes={os.getcwd(): {"bind": os.getcwd(), "mode": "rw"}},
            working_dir=os.getcwd(),
            ports={"80/tcp": None, "443/tcp": None},
            cap_add=["NET_RAW", "NET_ADMIN"],
        )
        container.exec_run('screen -dmS default_session')

    # Run the commands
    for command in commands:
        temp_file = f"/tmp/output_{os.urandom(8).hex()}.txt"
        
        command_to_run = f'screen -S default_session -X stuff "{command} >{temp_file} 2>&1 && echo {SPECIAL_END_TOKEN} >>{temp_file}\n"'
        yield f"\n> {command}\n"
        container.exec_run(command_to_run)

        # Wait for either the timeout or the special end token
        elapsed_time = 0
        streamed = ""
        while elapsed_time < timeout:
            result = container.exec_run(f'cat {temp_file}')
            output = result.output.decode()
            new_streamed = output.replace(streamed, "")
            yield new_streamed.replace(SPECIAL_END_TOKEN, "")
            streamed = output

            if SPECIAL_END_TOKEN in output:
                break

            await asyncio.sleep(1)
            elapsed_time += 1
        else:
            yield "TIMEOUT - execution did not finish but is continuing in the background\n"

        # Clean up the temporary file
        container.exec_run(f'rm {temp_file}')


async def bash(commands, session=None, stream=lambda i: i):
    """Callback wrapper for run_in_container.

    Args:
        commands (List[str]): A list of bash commands.
        session (str, optional): A session name. Defaults to None.
        on_newline (Callable[[str], str], optional): A callback function that
            takes a string and returns a string. Defaults to lambda i: i.

    Returns:
        List[str]: The output of the bash commands.
    """
    outputs = []
    async for token in run_in_container(commands, session):
        stream(token)
        outputs += [token]
    return outputs


async def test_run_in_container():
    commands = [
        "pwd",
        "ls",
        "touch test.txt",
        "ls",
    ]
    for token in run_in_container(commands):
        print(token, end="")
    commands = [
        "ls",
        "cd .. && ls",  # Use "&&" to chain commands in shell.
    ]
    for token in run_in_container(commands):
        print(token, end="")
    commands = ["pwd"]
    for token in run_in_container(commands):
        print(token, end="")


async def test_bash():
    commands = [
        "mkdir test12",
        "cd test12",
        "pwd",
        "cd ..",
        "rm -rf test12",
        "sleep 1 && echo hello world && sleep 1 && echo hello world",
        "echo next",
        "sleep 1",
        "echo hello world",
        "pip install --upgrade pip",
    ]
    outputs = await bash(commands, stream=lambda i: print(i, end=""))
    print("outputs:", outputs)


if __name__ == "__main__":
    # test_run_in_container()
    asyncio.run(test_bash())
