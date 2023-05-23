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

# Functions to import 
from Imports.importFunction import *

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




#########################################################################################
@app.route('/slack/interactive-endpoint', methods=['GET','POST'])
def interactive_trigger():
    return interactive_trigger_route(client)





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
    thr = Thread(target=backgroundworker_mp3, args=[client, text, response_url, channel_id])
    thr.start()


    # returning empty string with 200 response
    return f'{greeting_message}', 200
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
                 args=[client,
                       gdelt_text,
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
