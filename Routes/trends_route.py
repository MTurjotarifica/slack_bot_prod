from flask import request

def zenserp_trends(client,trend_block):
    data = request.form
    channel_id = data.get('channel_id')

    client.chat_postMessage(channel=channel_id, 
                                    text="Trend:  ",
                                    blocks = trend_block
                                    )

    return 'Thank you for your request', 200