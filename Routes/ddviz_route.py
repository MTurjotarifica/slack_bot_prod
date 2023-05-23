from ..Imports.importFunction import *
from ..Blocks.blocks import *
from flask import Flask, request, make_response

def dd_vis_trigger(client):
    data = request.form
    channel_id = data.get('channel_id')

    client.chat_postMessage(channel=channel_id, 
                                        text="Visualization:  ",
                                        blocks = dd_vis_trigger_block
                                        )


    #returning empty string with 200 response
    return 'dd_vis trigger works', 200