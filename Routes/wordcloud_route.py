from Imports.importFunction import *

def wordcloud_shape_trigger(client):
    #condition_list reset
    condition_list=[]
    
    data = request.form
    #we are usging data2 to parse the information
    data2 = request.form.to_dict()
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    response_url = data.get("response_url")
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"
    
    
    
    
    client.chat_postMessage(channel=channel_id,
                            text=f"Please provide the keyword for wordcloud",
                            blocks=word_cloud_kw_block
                            )
    
    return f'{greeting_message}', 200
#######################################################__________________________________