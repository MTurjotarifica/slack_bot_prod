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
from Routes.mp3_route import *
from Routes.deepl_route import *
from Routes.gdelt_route import *
from Routes.wiki_route import *
from Routes.wordcloud_route import *
from Routes.ddviz_route import *

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
def interactive_trigger_route(client):
    #creating an empty list for condition branching on wordcloud
    condition_list = []

    #creating an empty list for condition branching on dd_vis_trigger
    condition_list_dd_vis = []

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



#########################################################################################
# mp3 trigger slash command which creates mp3 and posts to slack
@app.route('/mp3_trigger', methods=['POST'])
def mp3_route():
    return mp3_trigger(client)


#deepl trigger slash command which creates translation for speech blocks and posts to slack
@app.route('/deepl_trigger_with_lang', methods=['POST'])
def deepl_route():
    return deepl_trigger_with_lang(client)


#creating a slash command for gdelt api to create a csv
@app.route('/gdelt_csv_trigger', methods=['POST'])
def gedlt_route():
    return gdelt_csv_trigger(client)


@app.route('/wiki_csv_trigger', methods=['POST'])
def wiki_route():
    return wiki_csv_trigger(client)


#wordcloud_shape_trigger slash command which creates and sends wordcloud images of user input and posts to slack
@app.route('/wordcloud_shape_trigger', methods=['POST'])
def wordcloud_route():
    return wordcloud_shape_trigger(client)


# dd vis trigger slash command
@app.route('/dd_vis_trigger', methods=['POST'])
def ddviz_route():
    return dd_vis_trigger(client)

#######################################################__________________________________
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
# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
