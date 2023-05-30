#mp3 command added 
import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response, session
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


# For wiki_csv trigger
import wikipedia
from nltk import tokenize #wiki sentences

import nltk
nltk.download('punkt')

from stop_words import get_stop_words


from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07

# Functions to import 
from Imports.importFunction import *


load_dotenv()


# Initialize the Flask app and the Slack app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_KEY')

slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)
client = slack_app.client


df_raw = load_dd_df()

# Converting date to datetime object
df_raw['date'] = pd.to_datetime(df_raw['date'])

#########################################################################################
@app.route('/slack/interactive-endpoint', methods=['GET','POST'])
def interactive_trigger():

    return interactive_trigger_route(client,
                                     df_raw,
                                     backgroundworker_wordcloud_shape, 
                                     backgroundworker3_ddviz, 
                                     backgroundworker_zenserp_trends,
                                     wordcloud_lang_block, wordcloud_shape_block2, 
                                     wordcloud_color_block, 
                                     dd_vis_blocks_startdate, 
                                     dd_vis_blocks_indexdate, 
                                     dd_vis_blocks_outputtype,)
    


#########################################################################################
@app.route('/trends', methods=['POST'])
def trend_route():
    return zenserp_trends(client, trend_block)


# mp3 trigger slash command which creates mp3 and posts to slack
@app.route('/mp3_trigger', methods=['POST'])
def mp3_route():
    return mp3_trigger(client, backgroundworker_mp3)


#deepl trigger slash command which creates translation for speech blocks and posts to slack
@app.route('/deepl_trigger_with_lang', methods=['POST'])
def deepl_route():
    return deepl_trigger_with_lang(client, backgroundworker_deepl_text_lang)


#creating a slash command for gdelt api to create a csv
@app.route('/gdelt_csv_trigger', methods=['POST'])
def gedlt_route():
    return gdelt_csv_trigger(client, backgroundworker_gdelt_csv_trigger)


@app.route('/wiki_csv_trigger', methods=['POST'])
def wiki_route():
    return wiki_csv_trigger(client, backgroundworker_wiki_csv_trigger)


#wordcloud_shape_trigger slash command which creates and sends wordcloud images of user input and posts to slack
@app.route('/wordcloud_shape_trigger', methods=['POST'])
def wordcloud_route():
    return wordcloud_shape_trigger(client, word_cloud_kw_block)


# dd vis trigger slash command
@app.route('/dd_vis_trigger', methods=['POST'])
def ddviz_route():
    return dd_vis_trigger(client, dd_vis_trigger_block)



#########################################################################################
# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def hello_slackbotprod():
    return handle_hello_request(client)


#########################################################################################
# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
