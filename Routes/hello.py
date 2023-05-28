from flask import request

def handle_hello_request(client):
    data = request.form
    channel_id = data.get('channel_id')
    # Execute the /hello command function
    client.chat_postMessage(response_type= "in_channel", channel=channel_id, text=" 2nd it works!33!", )
    return "Hello world1" , 200