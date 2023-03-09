#mp3 command added 
import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
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

#################################################


#######################################_________________________

#######################################_______________________________________________
# backgroundworker for new combined flow


#creating an empty list for condition branching on wordcloud
condition_list = []

#creating an empty list for condition branching on dd_vis_trigger
condition_list_dd_vis = []

#######################################----------------------------------------------



################################################
# st edit mar 08, 2023 fixed indentation using vs code
# indendation errors are being caused by spyder (the ide I use)


################################################-------------------------------------------



#######################################################__________________________________

# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)


# Define the function that handles the /hello command

# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def handle_hello_request():
    data = request.form
    channel_id = data.get('channel_id')
    # Execute the /hello command function
    slack_app.client.chat_postMessage(response_type= "in_channel", channel=channel_id, text="it works!", )
    client.chat_postMessage(response_type= "in_channel", channel='#slack_bot_prod', text=" 2nd it works!2!", )
    return "Hello world1" , 200



# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
