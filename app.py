#mp3 command added 
import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
#from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from threading import Thread
import azure.cognitiveservices.speech as speechsdk

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
import requests
import json

import deepl

import mysql.connector as mysql
import numpy as np
import pandas as pd
from datetime import date
from datetime import datetime as dt
from datetime import timedelta as delta
from datetime import timedelta

# visualization packages
import seaborn as sns
import plotly.graph_objects as go
import plotly
import plotly.io as pio
import plotly.offline as pyo
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.dates as mdates
import kaleido # required for fig.write in azure
import scipy.signal #used in dd_vis generation


# for wiki_csv trigger
import wikipedia
from nltk import tokenize #wiki sentences

import nltk
nltk.download('punkt')

# for wordcloud trigger
import stylecloud
from stop_words import get_stop_words


from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07

# from vis_functions import *
from Blocks.blocks import *
from BackgroundWorkers.vis_functions import *
from Database.database import *
from BackgroundWorkers.wiki_csv import *
from BackgroundWorkers.wordcloud_slack import *
from BackgroundWorkers.ddviz import *


load_dotenv()


# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

client = slack_app.client


df_raw = load_dd_df()

# converting date to datetime object
df_raw['date'] = pd.to_datetime(df_raw['date'])


#creating an empty list for condition branching on wordcloud
condition_list = []

#creating an empty list for condition branching on dd_vis_trigger
condition_list_dd_vis = []

#########################################################################################
@app.route('/slack/interactive-endpoint', methods=['GET','POST'])
def interactive_trigger():

    data = request.form
    data2 = request.form.to_dict()
    user_id = data.get('user_id')
    channel_id = json.loads(data2['payload'])['container']['channel_id']
    text = data.get('text')

    response_url = json.loads(data2['payload'])['response_url']
    actions = data.get("actions")
    actions_value = data.get("actions.value")
    action_id = json.loads(data2['payload'])['actions'][0]['action_id']

    if action_id == "wordcloud_kw_inp_act":
        payload = json.loads(data2['payload'])
        #obtain the value inserted in the text prompt
        kw_value=payload['actions'][0]['value']
        
        # appending arguments to the list that we created for wordcloud
        condition_list.append(kw_value)
        
        
        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text=f"{kw_value}    {response_url}",
                                blocks=wordcloud_lang_block
                                )
        
    elif action_id == "wordcloud_kw_lang_act":
        payload = json.loads(data2['payload'])
        kw_value=payload['actions'][0]['selected_option']['value']
        condition_list.append(kw_value)
        
        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text=f"{kw_value}     {response_url}",
                                blocks=wordcloud_shape_block2
                                )
        
    elif action_id == "wordcloud_shape_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['selected_option']['value']
        condition_list.append(kw_value)
        
        
        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text=f"{kw_value}     {response_url}",
                                blocks=wordcloud_color_block
                                )
        
    elif action_id == "wordcloud_color_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['selected_option']['value']
        condition_list.append(kw_value)
    #def backgroundworker_wordcloud_shape(wordcloud_lang_to, 
                                            #wordcloud_lang_kw, 
                                            #wordcloud_shape_kw, 
                                            #response_url):
                                                
        thr = Thread(target=backgroundworker_wordcloud_shape, args=[client,
                                                                    condition_list[-3], 
                                                                    condition_list[-4], 
                                                                    condition_list[-2],
                                                                    condition_list[-1],
                                                                    response_url,
                                                                    channel_id])
        thr.start()

    elif action_id == "dd_vis_trigger_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['value']
        condition_list_dd_vis.append(kw_value)

            
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text= f"{channel_id} language selection dropdown",
                                blocks=dd_vis_blocks_startdate )
        
    elif action_id == "dd_vis_blocks_startdate_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['selected_date']
        
        condition_list_dd_vis.append(kw_value)
        
        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text=f"{kw_value}     {response_url}",
                                blocks=dd_vis_blocks_indexdate
                                )
    
    elif action_id == "dd_vis_blocks_indexdate_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['selected_date']
        condition_list_dd_vis.append(kw_value)
        

        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text=f"{kw_value}     {response_url}",
                                blocks=dd_vis_blocks_outputtype
                                )
    elif action_id == "dd_vis_blocks_image_export_action":
        payload = json.loads(data2['payload'])
        kw_value=payload['actions'][0]['selected_option']['value']
        condition_list_dd_vis.append(kw_value)

        # condition_list_dd_vis[-4] is keyword
        # condition_list_dd_vis[-3] is start date
        # condition_list_dd_vis[-2] is index date
        # condition_list_dd_vis[-1] is output format
        
        thr = Thread(target=backgroundworker3_ddviz, args=[client,
                                                            df_raw,
                                                            condition_list_dd_vis[-4],
                                                            condition_list_dd_vis[-3],
                                                            condition_list_dd_vis[-2], 
                                                            condition_list_dd_vis[-1],
                                                            response_url,
                                                            channel_id])
        thr.start()
        
        client.chat_postMessage(channel=channel_id, text="A backgroundworker is running your task. Please wait.")
	

        #client.chat_postMessage(channel=channel_id, text=f"dd_vis_blocks_indexdate_act working kw: {condition_list_dd_vis[-3]} & startd: {condition_list_dd_vis[-2]} & indexd: {condition_list_dd_vis[-1]} & responseurl: {response_url} & chID:{channel_id}")
        
    else:
        client.chat_postMessage(channel=channel_id, text="Error: Please try again with different values.")
        #pass
        
    
    return 'interactive trigger works', 200
#######################################################__________________________________



#########################################################################################
# backgroundworker for mp3 post on slack
def backgroundworker_mp3(text, response_url, channel_id):
    
    # your task
    # The environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    
 
    
    # subscription and speech_region values are obtained from azure portal
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                           region=os.environ.get('SPEECH_REGION'))
    
    #to output audio to a file called file.wav
    audio_config = speechsdk.audio.AudioOutputConfig(filename=f"{(text[:3]+text[-3:])}.mp3")
    
    # The language of the voice that speaks. en-GB is british accent
    speech_config.speech_synthesis_voice_name='en-GB-RyanNeural'
    
    #creating speech_synthesizer object

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, 
                                                     audio_config=audio_config)
    
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")
            
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    
    #uploading the file to slack using bolt syntax for py
    
    #uploading the file to azure blob storage
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    container_name = "mp3"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = f"{(text[:3]+text[-3:])}.mp3"
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)
        
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()
        
        # Open the audio file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
            
        
#         filename=f"{(text[:3]+text[-3:])}.mp3"
        response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        initial_comment="Audio: ")
        assert response["file"]  # the uploaded file
        # Delete the blob

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

    requests.post(response_url,data=json.dumps(payload))
#######################################################__________________________________

#########################################################################################
# mp3 trigger slash command which creates mp3 and posts to slack
@app.route('/mp3_trigger', methods=['POST'])
def mp3_trigger():
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
    thr = Thread(target=backgroundworker_mp3, args=[text, response_url, channel_id])
    thr.start()


    # returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________

#########################################################################################
# background worker for deep l 
def backgroundworker_deepl_text_lang(text_lang_to, text_to_translate, response_url, channel_id):

    # your task

    # DeepL auth key is stored in environment variable which we are obtaining
    translator = deepl.Translator(os.environ.get('DEEPL_AUTH_KEY'))

    #using text argument to translate text to Specified language
    result = translator.translate_text(f'{text_to_translate}', 
                                       target_lang=f'{text_lang_to}') 

    #storing translated in a variable
    translated_text = result.text



    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}

    #posting translated text to slack channel
    client.chat_postMessage(channel=channel_id,
                            text=f"{translated_text}"
                            )


    requests.post(response_url,data=json.dumps(payload))
#######################################################__________________________________

#########################################################################################
#deepl trigger slash command which creates translation for speech blocks 
#and posts to slack
@app.route('/deepl_trigger_with_lang', methods=['POST'])
def deepl_trigger_with_lang():
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
                 args=[text_lang_to,
                       text_to_translate,
                       response_url,
                       channel_id
                      ]
                 )

    thr.start()

    #returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________

#########################################################################################
#background worker for creating csv from gdelt data (we are not using gdelt package)
def backgroundworker_gdelt_csv_trigger(gdelt_text, response_url, channel_id):

    # your task
    def gdelt(key):
        """ Gets Data from GDELT database (https://gdelt.github.io/ ; https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
    
        Args:
            key (str): Keyword to track
    
        Returns:
            df: Dataframe with volume of articles
        """
    
        # Define startdate
        startdate = 20170101000000
        # Get Dataframe TimelineVolInfo with urls and volume intensity 
        df_TimelineVolInfo = pd.read_csv(f"https://api.gdeltproject.org/api/v2/doc/doc?query={key}&mode=TimelineVolInfo&startdatetime={startdate}&timezoom=yes&FORMAT=csv")
    
        # Get Dataframe TimelineVolRaw with information on the count of articles
        df_TimelineVolRaw = pd.read_csv(f"https://api.gdeltproject.org/api/v2/doc/doc?query={key}&mode=TimelineVolRaw&startdatetime={startdate}&timezoom=yes&FORMAT=csv")
    
        # Filter only for keyword article count (not all articles)
        df_count = df_TimelineVolRaw[df_TimelineVolRaw['Series'] == 'Article Count']
    
        # Rename column
        df_count = df_count.rename(columns={'Value': 'articles' })
    
        # Merge both dataframes
        df = pd.merge(df_count[['Date','articles']],df_TimelineVolInfo, how='left', on=['Date'])
    
        # Save dataframe to csv
        df.to_csv((f"{gdelt_text}.csv"), index=False) # updated filename and directory edit mar 15 2023
        
        return 'csv completed'
    
    # using the function defined above to produce csv
    # we are passing in the key obtained from the slash command in the function
    gdelt(f'{gdelt_text}')
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    
    #uploading the file to azure blob storage
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    container_name = "gdelt"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = f"{gdelt_text}.csv"
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)
        
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()
        
        # Open the gdelt file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
            
        # filename = "gdelt_file.csv"
        response = client.files_upload(channels=channel_id,
                                        filename=filename, # added filename parameter and updated formatting edit mar 15, 2023
                                        file=file_data, 
                                        filetype="csv", 
                                        initial_comment=f"CSV generated for Gdelt keyword: \n{gdelt_text.upper()}: ")
        assert response["file"]  # the uploaded file
        # Delete the blob

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

    requests.post(response_url,data=json.dumps(payload))
#######################################################__________________________________

#########################################################################################
#creating a slash command for gdelt api to create a csv
@app.route('/gdelt_csv_trigger', methods=['POST'])
def gdelt_csv_trigger():
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
                 args=[gdelt_text,
                       response_url,
                       channel_id]
                 )
    
    thr.start()
    
    #returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________


@app.route('/wiki_csv_trigger', methods=['POST'])
def wiki_csv_trigger():
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


#########################################################################################
#wordcloud_shape_trigger slash command which creates and sends wordcloud images of user input 
#and posts to slack
@app.route('/wordcloud_shape_trigger', methods=['POST'])
def wordcloud_shape_trigger():
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


#########################################################################################
# Define the function that handles the /hello command
# Handle incoming slash command requests
@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    # Parse the command and its parameters from the request
    command = request.form.get("command")
    text = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Execute the appropriate function based on the command
    if command == "/example":
        client.chat_postMessage(channel='#slack_bot_prod', text=f"it worksssss! max date: {df_raw.date.max()} & min date: {df_raw.date.min()} & blob df min date: {df_raw_10_21.date.min()}")

    else:
        response_text = "Unknown command: {}".format(command)


    # Return an empty response to Slack
    return make_response("", 200)
#######################################################__________________________________

#########################################################################################
# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def handle_hello_request():
    data = request.form
    channel_id = data.get('channel_id')
    # Execute the /hello command function
    slack_app.client.chat_postMessage(response_type= "in_channel", channel=channel_id, text="it works!", )
    client.chat_postMessage(response_type= "in_channel", channel=channel_id, text=" 2nd it works!33!", )
    return "Hello world1" , 200
#######################################################__________________________________

#########################################################################################
# dd vis trigger slash command
@app.route('/dd_vis_trigger', methods=['POST'])
def dd_vis_trigger():
    data = request.form
    channel_id = data.get('channel_id')

    client.chat_postMessage(channel=channel_id, 
                                        text="Visualization:  ",
                                        blocks = dd_vis_trigger_block
                                        )


    #returning empty string with 200 response
    return 'dd_vis trigger works', 200
#######################################################__________________________________

#########################################################################################
# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
