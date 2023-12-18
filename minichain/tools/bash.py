import time
import asyncio
from typing import Optional
from enum import Enum
# import jupyter_client
import re


from pydantic import BaseModel, Field

from minichain.agent import Function


def shorten_response(response: str, max_lines = 100, max_chars = 200) -> str:
    # remove character in each line after the first 100 characters, add ... if the line is longer

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    response = ansi_escape.sub('', response)
    response = "\n".join(
        [
            line[:max_chars] + ("..." if len(line) > max_lines else "")
            for line in response.split("\n")
        ]
    )
    # if more than 100 lines, remove all lines except the first 5 and the last 5 and insert ...
    lines = response.split("\n")
    if len(lines) > max_lines:
        response = "\n".join(lines[:max_lines // 2] + ["..."] + lines[-max_lines // 2:])
    return response


class Type(str, Enum):
    python = "python"
    bash = "bash"


class JupyterQuery(BaseModel):
    code: str = Field(
        ...,
        description="Code or commands to run",
    )
    type: Type = Field(
        Type.python,
        description="The type of code to run.",
    )
    timeout: int = Field(60, description="The timeout in seconds.")
    process: str = Field(
        "main",
        description="Anything other than 'main' causes the process to run in the background. Set to e.g. 'backend' if you webserver in the background (Use: `node server.js` rather than `node server.js &` ). Commands will be run in a new jupyter kernel. Tasks like installing dependencies should run in 'main'.")
    restart: bool = Field(
        False,
        description="Set to true in order to restart the jupyter kernel before running the code. Required to import newly installed pip packages.")

class Jupyter(Function):
    def __init__(self, message_handler=None, continue_on_timeout=False, **kwargs):
        super().__init__(
            name="jupyter",
            openapi=JupyterQuery,
            function=self,
            description="Run python code and or bash commands in a jupyter kernel. ",
            message_handler=message_handler,
        )

        # Start a Jupyter kernel
        # self.kernel_manager = jupyter_client.KernelManager(kernel_name='python3')
        # self.kernel_manager.start_kernel()
        # self.kernel_client = self.kernel_manager.client()
        # self.kernel_client.start_channels()
        # self.continue_on_timeout = continue_on_timeout
        # self.has_code_argument = True
        # self.bg_processes = {}
    
    async def __call__(self, **arguments):
        self.check_arguments_raise_error(arguments)
        result = await self.call(**arguments)
        return result

    async def call(self, code: str, timeout: int = 60, type: str = "python", process='main', restart=False) -> str:
        if process != "main":
            if self.bg_processes.get(process):
                jupyter = self.bg_processes[process]
                if code == 'logs':
                    logs = jupyter.message_handler.current_message['content']
                    logs = shorten_response(logs, 20)
                    await self.message_handler.set(f"Logs of process {process}:\n{logs}")
                    return f"Logs of process {process}:\n{logs}"
                # interrupt the process if it is still running
                jupyter.kernel_manager.restart_kernel()
            else:
                if code == 'logs':
                    await self.message_handler.set(f"Process {process} does not exist.")
                    return f"Process {process} does not exist."
                # run this code in a new juptyer kernel
                jupyter = Jupyter(continue_on_timeout=True)
                self.bg_processes[process] = jupyter

            # remove `&` from the end of the code
            code = "\n".join([line if not line.strip().endswith("&") else line.strip()[:-1] for line in code.split("\n")])
            await self.message_handler.set(f"Starting background process...")
            initial_logs = await jupyter(code=code, timeout=10, type=type)
            initial_logs = shorten_response(initial_logs, 20)
            output = f"Started background process with logs:\n{initial_logs}\n"
            output += f"You can check the logs of this process by typing \n```\nlogs\n```\n and calling jupyter with process={process}"
            await self.message_handler.set(output)
            return output
        if type == "bash" and not code.startswith("!"):
            code = "\n".join([f"!{line}" for line in code.split("\n")])
        
        if restart:
            self.kernel_manager.restart_kernel()
            self.kernel_client = self.kernel_manager.client()
            self.kernel_client.start_channels()
        # Execute the code
        msg_id = self.kernel_client.execute(code)
        await self.message_handler.chunk(f"Out: \n")

        start_time = time.time()

        while True:
            try:
                # async sleep to avoid blocking the event loop
                await asyncio.sleep(0.1)
                msg = self.kernel_client.get_iopub_msg(timeout=0.5)
            except:
                if time.time() - start_time < timeout:
                    continue
                # Timeout
                if self.continue_on_timeout:
                    # just return the current output
                    return self.message_handler.current_message['content']
                else:
                    await self.message_handler.chunk("Timeout")
                    output =  self.message_handler.current_message['content']
                    # Interrupt the kernel
                    self.kernel_manager.interrupt_kernel()
                    return output
            try:
                # await self.message_handler.chunk(str(msg) + "\n")
                # Check for output messages
                if msg['parent_header'].get('msg_id') == msg_id:
                    msg_type = msg['header']['msg_type']
                    content = msg['content']

                    if msg_type == 'stream':
                        await self.message_handler.chunk(content['text'])
                    
                    elif msg_type == 'display_data':
                        await self.message_handler.chunk(
                            content['data'].get('text/plain', "") + "\n",
                            meta={"display_data": [content['data']]}
                        )

                    elif msg_type == 'execute_result':
                        await self.message_handler.chunk(
                            "",
                            meta={"display_data": [content['data']]}
                        )
                        await self.message_handler.set(
                            content['data']['text/plain'] + "\n"
                        )
                    
                    elif msg_type == 'error':
                        await self.message_handler.chunk(
                            content['evalue'] + "\n",
                        )

                    elif msg_type == 'status' and content['execution_state'] == 'idle':
                        await self.message_handler.set() # Flush the message handler - send the meta data
                        break  # Execution is finished

            except KeyboardInterrupt:
                # Cleanup in case of interruption
                self.kernel_client.stop_channels()
                break
        # Return all the captured outputs as a single string
        output = self.message_handler.current_message['content']
        short = shorten_response(output)
        await self.message_handler.set(short)
        return short

    # def __del__(self):
    #     # Ensure cleanup when the class instance is deleted
    #     self.kernel_client.stop_channels()
    #     self.kernel_manager.shutdown_kernel()
