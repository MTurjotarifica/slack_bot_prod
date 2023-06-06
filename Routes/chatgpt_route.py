from flask import request

def chatgpt_trigger(client, gptquery):
    data = request.form
    channel_id = data.get('channel_id')

    client.chat_postMessage(channel=channel_id, 
                                        text="Query:  ",
                                        blocks = gptquery
                                        )

    #returning empty string with 200 response
    return '', 200
