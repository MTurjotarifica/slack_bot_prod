from flask import request
from threading import Thread

def gdelt_csv_trigger(client, backgroundworker_gdelt_csv_trigger):
    data = request.form
    # we are not usging data2 to parse the information in this case
    data2 = request.form.to_dict()
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    #getting keyword from user input and storing them into gdelt_text variable
    gdelt_text = data.get('text')
    
    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"

    
    client.chat_postMessage(channel=channel_id,
                            text="CSV loading. Please wait."
                            )
    
    
    #triggering backgroundworker for deepl with arguments lang to translate from
    #translate to and text to translate
    thr = Thread(target=backgroundworker_gdelt_csv_trigger, 
                 args=[client,
                       gdelt_text,
                       response_url,
                       channel_id]
                 )
    
    thr.start()
    
    #returning empty string with 200 response
    return f'{greeting_message}', 200
