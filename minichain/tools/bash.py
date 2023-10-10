import asyncio
import os
from typing import List, Optional
import jupyter_client

from pydantic import BaseModel, Field

from minichain.agent import Function
from minichain.schemas import BashQuery


def shorten_response(response: str) -> str:
    # remove character in each line after the first 100 characters, add ... if the line is longer
    response = "\n".join(
        [
            line[:200] + ("..." if len(line) > 200 else "")
            for line in response.split("\n")
        ]
    )
    # if more than 100 lines, remove all lines except the first 5 and the last 5 and insert ...
    lines = response.split("\n")
    if len(lines) > 100:
        response = "\n".join(lines[:20] + ["..."] + lines[-80:])
    return response


class JupyterQuery(BaseModel):
    code: str = Field(
        ...,
        description="Python code to run",
    )
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")


class Jupyter(Function):
    def __init__(self, message_handler=None, **kwargs):
        super().__init__(
            name="jupyter",
            openapi=JupyterQuery,
            function=self,
            description="Run python code and or `!bash_commands` in a jupyter kernel. ",
            message_handler=message_handler,
        )

        # Start a Jupyter kernel
        self.kernel_manager = jupyter_client.KernelManager(kernel_name='python3')
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

    async def __call__(self, code: str, timeout: int = 60) -> str:
        # Execute the code
        msg_id = self.kernel_client.execute(code)
        await self.message_handler.chunk(f"Out: \n")

        while True:
            try:
                # Get messages from the kernel
                msg = self.kernel_client.get_iopub_msg(timeout=timeout)

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
                self.kernel_manager.shutdown_kernel()
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
