import os
from typing import List

import docker


def run_in_container(
    commands: List[str], container_name: str = None, image_name="ubuntu:latest"
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
            # set cwd to current working directory
            working_dir=os.getcwd(),
            ports={"80/tcp": None, "443/tcp": None},
            cap_add=["NET_RAW", "NET_ADMIN"],
        )

    # Run the commands
    for command in commands:
        command = f'/bin/sh -c "{command}"'  # This line wraps the command with shell.
        # Stream output from long-running commands
        yield f"\n> {command}\n"
        result = container.exec_run(command, stream=True)
        for line in result.output:
            yield line.strip().decode()


def test_run_in_container():
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


if __name__ == "__main__":
    test_run_in_container()
