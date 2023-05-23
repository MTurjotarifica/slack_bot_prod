from Imports.importFunction import *
from flask import Flask, request, make_response
from threading import Thread

def wiki_csv_trigger(client):
    data = request.form
    #we are usging data2 to parse the information
    data2 = request.form.to_dict()
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    #getting language to for wiki csv trigger
    wordcloud_lang_to = data.get('text').split()[0].lower()
    # obtaining the keyword anything after the 3rd letter
    # because example: en "keyword"
    wordcloud_lang_kw = data.get('text')[3:]
    
    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"

    
    client.chat_postMessage(channel=channel_id, # updated to channel_id edit: mar 15, 2023
                            text="CSV loading. Please wait."
                            )
    
    
    #triggering backgroundworker for deepl with arguments lang to translate from
    #translate to and text to translate
    thr = Thread(target=backgroundworker_wiki_csv_trigger, 
                 args=[client,
                       wordcloud_lang_to,
                       wordcloud_lang_kw,
                       response_url,
                       channel_id,
                       ]
                 )
    
    thr.start()
    
    #returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________