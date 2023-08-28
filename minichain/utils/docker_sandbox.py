import asyncio
import json
import os
import threading
from time import sleep
from typing import List

import docker

SPECIAL_END_TOKEN = "END_OF_COMMAND_293842"  # Rare special token


async def run_in_container(
    commands: List[str],
    container_name: str = None,
    image_name="nielsrolf/minichain:latest",
    timeout=60,  # in seconds
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
        if os.path.exists("requirements.txt"):
            print(container.exec_run("pip install -r requirements.txt").output.decode())
        if os.path.exists("setup.py"):
            print(container.exec_run("pip install -e .").output.decode())
        if os.path.exists("package.json"):
            print(container.exec_run("npm install").output.decode())
        container.exec_run("screen -dmS default_session")

    # Run the commands
    for command in commands:
        temp_file = f"/tmp/output_{os.urandom(8).hex()}.txt"

        # command_to_run = f'screen -S default_session -X stuff "{command} >{temp_file} 2>&1; echo {SPECIAL_END_TOKEN} >>{temp_file};"'
        # command_with_stdbuf = f'stdbuf -oL -eL {command}'
        # we use json.dumps for the opening " and to escape the command
        # command_to_run = f'screen -S default_session -X stuff "{command} >{temp_file} 2>&1; echo {SPECIAL_END_TOKEN} >>{temp_file};\n"'
        maybe_newline = "\n" if ">" in command else ""
        command_to_run = f'screen -S default_session -X stuff {json.dumps(command)[:-1]}{maybe_newline} >{temp_file} 2>&1; echo {SPECIAL_END_TOKEN} >>{temp_file};\n"'
        # command_to_run = f'screen -S default_session -X stuff "{command} >{temp_file} 2>&1 ; echo {SPECIAL_END_TOKEN} >>{temp_file} \n"'
        print("command_to_run:", command_to_run)

        yield f"\n> {command}\n"
        container.exec_run(command_to_run)

        # Wait for either the timeout or the special end token
        elapsed_time = 0
        streamed = ""
        while elapsed_time < timeout:
            await asyncio.sleep(1)
            elapsed_time += 1

            result = container.exec_run(f"cat {temp_file}")
            output = result.output.decode()
            new_streamed = output.replace(streamed, "")
            yield new_streamed.replace(SPECIAL_END_TOKEN, "")
            streamed = output

            if SPECIAL_END_TOKEN in output:
                break

        else:
            yield "TIMEOUT - execution did not finish but is continuing in the background\n"

        # Clean up the temporary file
        container.exec_run(f"rm {temp_file}")


async def bash(commands, session="default", stream=None, timeout=60):
    """Callback wrapper for run_in_container.

    Args:
        commands (List[str]): A list of bash commands.
        session (str, optional): A session name. Defaults to None.
        on_newline (async Callable[[str], str], optional): A callback function that
            takes a string and returns a string. Defaults to lambda i: i.

    Returns:
        List[str]: The output of the bash commands.
    """
    # with open("last_bash_request.json", "w") as f:
    #     f.write(json.dumps(commands))
    if stream is None:

        async def stream(i):
            return

    outputs = []
    async for token in run_in_container(commands, session, timeout=timeout):
        await stream(token)
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
        "pip install -e .",
        "ls",
        "mkdir test12",
        "cd test12",
        "pwd",
        "cd ..",
        "rm -rf test12",
        "echo next",
        "sleep 1",
        "echo hello world",
    ]
    
#     commands = ["""
# echo yoyoyo
# echo "hello world" > test.txt
# echo '"hello world"' > test2.txt
# echo "'hello world'" > test3.txt
# """, "cat test.txt", "cat test2.txt", "cat test3.txt"]
    
#     commands = ["echo \"hello\" > test1", "echo '\"hello\"' > test2", "echo \"hello\nworld\" > test3"]

#     commands = ["echo \"hello\" > test1"]

#     commands = ["""echo "hello world" > test2
# """]
    
    outputs = await bash(commands)
    print("outputs:", "\n".join(outputs))


if __name__ == "__main__":
    # test_run_in_container()
    asyncio.run(test_bash())
