from Imports.importFunction import *

def deepl_trigger_with_lang(client):
    data = request.form
    channel_id = data.get('channel_id')
    #we are usging data2 to parse the information
    data2 = request.form.to_dict()
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    #getting language to translate to
    text_lang_to = data.get('text').split()[0]
    #text to translate (we are taking portions after en-gb/en-us etc)
    if (text_lang_to.lower() == 'en-gb'):
        text_to_translate = data.get('text')[6:]
    elif (text_lang_to.lower() == 'en-us'):
        text_to_translate = data.get('text')[6:]
    elif (text_lang_to.lower() == 'pt-pt'):
        text_to_translate = data.get('text')[6:]
    elif (text_lang_to.lower() == 'pt-br'):
        text_to_translate = data.get('text')[6:]
    else:
        text_to_translate = data.get('text')[3:]

    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"


    client.chat_postMessage(channel=channel_id,
                            text="DeepL Translation loading. Please wait."
                            )


    #triggering backgroundworker for deepl with arguments lang to translate from
    #translate to and text to translate
    thr = Thread(target=backgroundworker_deepl_text_lang, 
                 args=[client,
                       text_lang_to,
                       text_to_translate,
                       response_url,
                       channel_id
                      ]
                 )

    thr.start()

    #returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________