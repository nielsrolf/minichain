import time
from typing import Optional
from enum import Enum
import jupyter_client
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


class PythonOrBashEnum(str, Enum):
    python = "python"
    bash = "bash"

class JupyterQuery(BaseModel):
    code: str = Field(
        ...,
        description="Code or commands to run",
    )
    type: PythonOrBashEnum = Field(
        PythonOrBashEnum.python,
        description="The type of code to run.",
    )
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")
    background: Optional[bool] = Field(False, description="Set to true if you start e.g. a webserver in the background (Use: `node server.js` rather than `node server.js &` ). Commands will be run in a new jupyter kernel.")


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
        self.kernel_manager = jupyter_client.KernelManager(kernel_name='python3')
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.continue_on_timeout = continue_on_timeout

    async def __call__(self, code: str, timeout: int = 60, type: str = "python", background=False) -> str:
        if background:
            # run this code in a new juptyer kernel
            jupyter = Jupyter(continue_on_timeout=True)
            # remove `&` from the end of the code
            code = "\n".join([line if not line.strip().endswith("&") else line.strip()[:-1] for line in code.split("\n")])
            initial_logs = await jupyter(code, timeout=10, type=type)
            initial_logs = shorten_response(initial_logs, 20)
            output = f"Started background process with logs:\n{initial_logs}"
            await self.message_handler.set(output)
            return output
        if type == "bash" and not code.startswith("!"):
            code = "\n".join([f"!{line}" for line in code.split("\n")])
        # Execute the code
        msg_id = self.kernel_client.execute(code)
        await self.message_handler.chunk(f"Out: \n")

        start_time = time.time()

        while True:
            try:
                # Get messages from the kernel
                remaining_time = timeout - (time.time() - start_time)
                msg = self.kernel_client.get_iopub_msg(timeout=remaining_time)
            except:
                # Timeout
                await self.message_handler.chunk("Timeout")
                if self.continue_on_timeout:
                    # just return the current output
                    return self.message_handler.current_message['content']
                else:
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

    def __del__(self):
        # Ensure cleanup when the class instance is deleted
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel()
