#mp3 command added 
import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
#from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from slack_sdk import WebClient
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
import seaborn as sns
import plotly.graph_objects as go
import plotly
import plotly.io as pio
import plotly.offline as pyo
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.dates as mdates
import slack
import scipy.signal

from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07

# from vis_functions import *


load_dotenv()


# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)


client = slack_app.client


##################################################________________________________________
#function to create load difital demand as dataframe
def load_dd_df():
    '''
    loads digital demand dataframe for all dates
    where country is DE
    and gt_category 13
    returns:
        df_dd_raw (Dataframe)
    '''    
    #SQL ALCHEMY
    #creating the engine
    #syntax: dialect+driver://username:password@host:port/database
    engine = create_engine('mysql+pymysql://sandbox_read_only:zhsqehk23Xs8tVmVn3sSkyq5TvZumR5q@mysqldatabase.cmi5f1vp8ktf.us-east-1.rds.amazonaws.com:3306/sandbox')
    
    #creating a connection object
    connection = engine.connect()
    
    #creating the metadata object
    # metadata = MetaData()
    
    #loading the digital_demand table #edit pik 2023-03-07
    # df_dd_raw_table = Table('digital_demand',
    #                        metadata)
    
    #this is the query to be performed #edit st 2023-03-07
    stmt = "SELECT * FROM digital_demand WHERE (gt_category = 13) AND (country = 'DE') and (date >= '2023-01-01');"
    
    df_dd_raw = pd.read_sql(sqlalctext(stmt), connection) #edit st 2023-03-07
    df_dd_raw['date'] = pd.to_datetime(df_dd_raw['date'])
    
    connection.close()
    
    return df_dd_raw

#storing df_digital_demand in variable df_raw to maintain code in viz generator
df_raw = load_dd_df()

#################################################


#######################################_________________________

#######################################_______________________________________________
# backgroundworker for new combined flow


#creating an empty list for condition branching on wordcloud
condition_list = []

#creating an empty list for condition branching on dd_vis_trigger
condition_list_dd_vis = []

#######################################----------------------------------------------
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

    if action_id == "dd_vis_trigger_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['value']
        condition_list_dd_vis.append(kw_value)

        #client.chat_postMessage(channel=channel_id, text="dd vis trigger and interactive trigger working")
        
        #datetime picker block for startdate that is triggered after text input block

        dd_vis_blocks_startdate = [
    
		{
 			"type": "input",
 			"element": {
				"type": "datepicker",
				"initial_date": "2022-01-01",
				"placeholder": {
 					"type": "plain_text",
 					"text": "Select a date",
 					"emoji": True
				},
				"action_id": "dd_vis_blocks_startdate_act"
 			},
 			"label": {
				"type": "plain_text",
				"text": "Please select the startdate for the Visualization",
				"emoji": True
 			}
		}]
        
        #sending kw_value and language selection dropdown
        client.chat_postMessage(channel=channel_id,
                                text= f"{channel_id} language selection dropdown",
                                blocks=dd_vis_blocks_startdate )
        
    elif action_id == "dd_vis_blocks_startdate_act":
        payload = json.loads(data2['payload'])
        #obtaining kw_value and appending value to list
        kw_value=payload['actions'][0]['selected_date']
        
        condition_list_dd_vis.append(kw_value)
        
        #datetime picker block for startdate that is triggered after text input block
        dd_vis_blocks_indexdate = [
  		{
   			"type": "input",
   			"element": {
  				"type": "datepicker",
  				"initial_date": "2022-06-01",
  				"placeholder": {
   					"type": "plain_text",
   					"text": "Please select the index date for the Visualization",
   					"emoji": True
  				},
  				"action_id": "dd_vis_blocks_indexdate_act"
   			},
   			"label": {
  				"type": "plain_text",
  				"text": "Please select the index date for the Visualization",
  				"emoji": True
   			}
  		}
   	]
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
        
        # condition_list_dd_vis[-3] is keyword
        # condition_list_dd_vis[-2] is start date
        # condition_list_dd_vis[-1] is index date
        
        # thr = Thread(target=backgroundworker3_ddviz, args=[condition_list_dd_vis[-3], 
        #                                                    condition_list_dd_vis[-2], 
        #                                                    condition_list_dd_vis[-1], 
        #                                                    response_url, 
        #                                                    channel_id])
        # thr.start()
        

        client.chat_postMessage(channel=channel_id, text=f"dd_vis_blocks_indexdate_act working kw: {condition_list_dd_vis[-3]} & startd: {condition_list_dd_vis[-2]} & indexd: {condition_list_dd_vis[-1]} & responseurl: {response_url} & chID:{channel_id}")
        
    else:
        client.chat_postMessage(channel="#slack_bot_prod", text="not dd vis trigger")
        #pass
        
    
    return 'interactive trigger works', 200


################################################
# st edit mar 08, 2023 fixed indentation using vs code
# indendation errors are being caused by spyder (the ide I use)


################################################-------------------------------------------



#######################################################__________________________________

# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)


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
        client.chat_postMessage(channel='#slack_bot_prod', text=f"it worksssss! max date: {df_raw.date.max()} & min date: {df_raw.date.min()}")
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


    # Return an empty response to Slack
    return make_response("", 200)


# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def handle_hello_request():
    data = request.form
    channel_id = data.get('channel_id')
    # Execute the /hello command function
    slack_app.client.chat_postMessage(response_type= "in_channel", channel=channel_id, text="it works!", )
    client.chat_postMessage(response_type= "in_channel", channel='#slack_bot_prod', text=" 2nd it works!2!", )
    return "Hello world1" , 200


# dd vis trigger slash command
@app.route('/dd_vis_trigger', methods=['POST'])
def dd_vis_trigger():
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

    #utilizing threading
    #thr = Thread(target=backgroundworker, args=[text,response_url])
    #thr.start()

    #this creates the text prompt in slack block kit
    dd_vis_trigger_block = [
        {
           "type": "divider"
           },
        {
            "dispatch_action": True,
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "action_id": "dd_vis_trigger_act"
            },
            "label": {
                "type": "plain_text",
                "text": "Please type the keyword for the visualization ",
                "emoji": True
            }
        }
    ]

    client.chat_postMessage(channel=channel_id, 
                                        text="Visualization:  ",
                                        blocks = dd_vis_trigger_block
                                        )


    #returning empty string with 200 response
    return 'dd_vis trigger works', 200

# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
