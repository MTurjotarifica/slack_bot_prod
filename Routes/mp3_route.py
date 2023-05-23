# Functions to import 
from BackgroundWorkers.mp3 import *
from flask import Flask, request, make_response
from threading import Thread

def mp3_trigger(client):
    data = request.form
    #we are usging data2 to parse the information
    data2 = request.form.to_dict()
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    text = data.get('text')
    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"


    client.chat_postMessage(channel=channel_id,
                            text="MP3 loading. Please wait."
                            )


    # triggering backgroundworker1 
    thr = Thread(target=backgroundworker_mp3, args=[client, text, response_url, channel_id])
    thr.start()


    # returning empty string with 200 response
    return f'{greeting_message}', 200