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

import slack

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
from backgroundworker import wordcloud_shape_block2


load_dotenv()


# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)


client = slack_app.client


#########################################################################################
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
    stmt = "SELECT * FROM digital_demand WHERE (gt_category = 13) AND (country = 'DE') and (date >= '2022-01-01');" #date updated to 2022 jan 1
    
    df_dd_raw = pd.read_sql(sqlalctext(stmt), connection) #edit st 2023-03-07
    df_dd_raw['date'] = pd.to_datetime(df_dd_raw['date'])
    
    connection.close()
    
    return df_dd_raw

#storing df_digital_demand in variable df_raw to maintain code in viz generator
df_raw_22_onwards = load_dd_df()


# loading data from a blob container called csv that contains digital demand data from 2010 to 2022
container_string=os.environ["CONNECTION_STRING"]
storage_account_name = "storage4slack"
container_name = "csv"
blob_service_client = BlobServiceClient.from_connection_string (container_string)
container_client = blob_service_client.get_container_client(container_name)
filename = "split_df_raw.csv"
blob_client = container_client.get_blob_client(filename)
blob_name= filename


blob_client = blob_service_client.get_blob_client(container_name, blob_name)
blob_data = blob_client.download_blob().readall()

# Open the csv file and read its contents
# with open(filename, 'rb') as file:
#     file_data = file.read()

# Download the CSV file to a local temporary file
with open(filename, "wb") as my_blob:
    download_stream = blob_client.download_blob()
    my_blob.write(download_stream.readall())

# file_data is our new csv
df_raw_10_21 = pd.read_csv(filename)

# creating a list of dataframes to be merged
frames = [df_raw_10_21, df_raw_22_onwards]

# merging the dataframes
df_raw = pd.concat(frames)

# converting date to datetime object
df_raw['date'] = pd.to_datetime(df_raw['date'])
#######################################################__________________________________

#########################################################################################
############################# VIS FUNCTIONS #############################################
def add_indexing(df,var,index_date):
    '''
    Adding indexes to the var in a dataframe 
    so that we don't get values between 0 to 1
    and instead obtain results in our own scale
    
    i.e if vl_value in 1st Jan 2022 (index_date) in 0.01
    then we can set vl_value_ref to the vl_value in that row
    and then if we find a vl_value in any other date 
    we compare this to vl_value_ref by scaling it using vl_value_ref 
    (vl_value/vl_value_ref * 100) to obtain value for vl_value_index column
    (always grouped by keyword, country, category)
    
    Parameters:
        df(dataframe)
        
        var(str) : string of a numeric column of the dataframe 
        
        index_date(str): date string
    
    Returns:
        df: dataframe with a new column which is called var_index
        i.e vl_value_index
    '''
    var_ref = var +'_ref'                                      #variable for index computation
    var_new = var +'_index'                                    #new index variable to be added to df  
    df_ref = df[df['date']==index_date]                        #create reference df with values from indexdate
    df_ref = df_ref.rename(columns={var : var_ref})            #rename to avoid confusion
    #Add values of indexdate to original dataframe and compute index values
    df_w_index = pd.merge(df, df_ref[['keyword',
                                      'country',
                                      'gt_category',
                                      var_ref]],
                          how="left",
                          on=['keyword',
                              'country',
                              'gt_category'
                             ])
    df_w_index[var_new] = (df_w_index[var]/df_w_index[var_ref])*100
    return df_w_index


#indexing avg function
def add_indexing_by_avg(df,var):
    '''
    Adding indexes to the var in a dataframe 
    so that we don't get values between 0 to 1
    and instead obtain results in our own scale
    (always grouped by keyword, country, category)
    
    i.e 
    here we are obtaining the mean value for a given keyword, country, category combination
    and using that as a reference to create values for the var_index_avg column
    
    Parameters:
        df(dataframe)
        
        var(str) : string of a numeric column of the dataframe 
    
    Returns:
        df: dataframe with a new column which is called var_index_avg
        i.e vl_value_index_avg
    '''
    var_ref = var +'_ref_avg'
    var_new = var +'_index_avg'
    df_index = df.copy()
    df_index[var_ref] = df_index.groupby(['keyword',
                                          'country',
                                          'gt_category'
                                         ])[var].transform(lambda x: x.mean())    #compute moving average
    df_index[var_new] = (df_index[var]/df_index[var_ref])*100
    return df_index



#moving average function
def add_ma(df,var,window):
    '''
    Adding moving avg column to the dataframe
    (always grouped by keyword, country, category)
        
    Parameters:
        df(dataframe)
        
        var(str) : string of a numeric column of the dataframe
        
        window(int): moving average window 
        i.e if 7 (will calculate from the 7th day and obtain NAN for days 1 to 6)
        
    
    Returns:
        df: dataframe with a new column which is called var_ma_{windowint}
        i.e vl_value_ma7
    '''

    
    var_new = var + '_ma'                                       #new ma variable to be added to df
    df = df.sort_values(by=['keyword',
                            'gt_category',
                            'country',
                            'date'
                           ])
    df[var_new] = df.groupby(['keyword',
                              'country',
                              'gt_category'
                             ])[var].transform(lambda x: x.rolling(window).mean())    #compute moving average
    
    df = df.rename(columns={var_new: var_new+str(window)})
    return df


#standard deviation function
def add_std(df,var,window):
    '''
    Adding standard_deviation of the moving average to the dataframe in a new column
    (always grouped by keyword, country, category)
    
    Parameters:
        df(dataframe)
        
        var(str) : string of a numeric column of the dataframe
        
        window(int): moving average window 
        i.e if 7 (will calculate from the 7th day and obtain NAN for days 1 to 6)
        
    
    Returns:
        df: dataframe with a new column which is called var_std_{windowint}
        i.e vl_value_std7
    '''
        
    var_new = var + '_std'                                       #new ma variable to be added to df
    df = df.sort_values(by=['keyword',
                            'gt_category',
                            'country',
                            'date'
                           ])
    df[var_new] = df.groupby(['keyword',
                              'country',
                              'gt_category'
                             ])[var].transform(lambda x: 2*x.rolling(window).std())    #compute moving average
    df = df.rename(columns={var_new: var_new+str(window)})
    return df


#smoother function
def add_smoother(df,var,cutoff):
    '''
    Adding smooth values for var in the dataframe in a new column
    (always grouped by keyword, country, category)
    
    Parameters:
        df(dataframe)
        
        var(str) : string of a numeric column of the dataframe
        
        cutoff(float): cutoff value for smoothing and expects values in between 0 to 1
        degree of smoothing 
        i.e we are currently choosing 0.02
        refernce: https://swharden.com/blog/2020-09-23-signal-filtering-in-python/
        
    
    Returns:
        df: dataframe with a new column which is called var_smooth
        i.e vl_value_smooth
    '''
    b, a = scipy.signal.butter(3, cutoff)
    var_new = var + '_smooth'                                       #new ma variable to be added to df
    df = df.sort_values(by=['keyword',
                            'gt_category',
                            'country',
                            'date'
                           ])
    df[var_new] = df.groupby(['keyword',
                              'country',
                              'gt_category'
                             ])[var].transform(lambda x: scipy.signal.filtfilt(b, a, x))    #compute moving average
    return df

############################# END OF VIS FUNCTIONS ######################################
#######################################################__________________________________

#########################################################################################
############################# BACKGROUNDWORKER3 #########################################
# backgroundworker for new combined flow
def backgroundworker3_ddviz(text, init_date, index_date, output_type, response_url, channel_id):

    missing_kw_block = [
		{
			"type": "divider"
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":mag_right: *Keyword* not in *Digital Demand* Database.\n\n Please try the command again with a _different keyword_.  "
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Insight Generation: :beta:",
					"emoji": True
				}
			]
		}
	]        

    #NEW ADDITION
    if text.lower() not in df_raw.keyword.unique().tolist():
        client.chat_postMessage(channel=channel_id,
                                text="Keyword not in Digital Demand Database. Please try the command again with a differenrent keyword. ",
                                blocks=missing_kw_block
                                            )
    else:
        pass
    
    #we are creating manuals parameter dictionary for function values at the moment
    params = {'key': f'{text.lower()}',
              'geo': 'DE',
              'cat': 13,
              'startdate': f'{init_date}',
              'index': True,
              'indexdate': f'{index_date}',
              'font_use': 'Roboto Mono Light for Powerline',
              'out_type': 'png'
             }
    
    #function that produces and saves the vis
    def single(key,geo,cat,startdate,index,indexdate,font_use,out_type):

        '''
        Creating a single time series visualization that includes raw_timeseries, trend, moving avg, smoothed trendlines
        
        Parameters:
            key(str): keyword in digital demand dataframe
            
            geo(str): country value in digital demand dataframe
            
            cat(int) : category value in digital demand dataframe
            
            startdate(str): gives us the start value for the visualization
            i.e '2010-01-01' - the vis would start at 1st Jan 2010
            
            index(bool): whether you want to add an indexed column to the dataframe and plot the column as well
            
            indexdate(str): reference for index column
            
            font_use(str): font you want in the plot
            
            out_type(str): the format of the output that you want
            i.e 'svg', 'html', 'png'
        
        Returns:
            a local copy of the visualization in the format you want (svg, png etc)
            saves it in desktop
        '''
        
        df_key = df_raw[(df_raw.keyword == f'{params.get("key")}')\
                        &(df_raw.country == f'{params.get("geo")}')\
                        &(df_raw.gt_category == int(f'{params.get("cat")}'))]
        if params.get("index")==True: 
            df_key = add_indexing(df_key,'vl_value',f'{params.get("indexdate")}')
            var_new = 'vl_value_index'
        else:
            var_new = 'vl_value'
            #running the functions we created to create moving average, smoother
        df_key = add_ma(df_key,var_new,14)
        df_key = add_smoother(df_key,var_new,0.02) 
        df = df_key[df_key.date>=f'{params["startdate"]}']
        fig = go.Figure()
        fig.add_trace(
            go.Scatter( 
                x=df.date, 
                y=df[var_new],
                name='original', 
                mode='lines',
                opacity = 0.3,
                line=dict(color='#024D83',
                          width=4),
                showlegend=True
        ))
        #creating the trendline values
        df_trend = df[['date',var_new]]         #i.e we need date and vl_value 
        df_trend0 = df_trend.dropna()           #dropping 0 because trendlines can't cope without numeric values
        x_sub = df_trend0.date    
        y_sub = df_trend0[var_new]
        x_sub_num = mdates.date2num(x_sub)      #transforming dates to numeric values, necessary for polynomial fitting
        z_sub = np.polyfit(x_sub_num, y_sub, 1) #polynomial fitting
        p_sub = np.poly1d(z_sub)
        #adding the trendline trace
        fig.add_trace(
            go.Scatter( 
                x=x_sub, 
                y=p_sub(x_sub_num), 
                name='trend', 
                mode='lines',
                opacity = 1,
                line=dict(color='green',
                          width=4,
                          dash='dash')
        ))
        #adding the 2 week's moving avg trace
        fig.add_trace(
            go.Scatter( 
                x=df.date, 
                y=df[var_new+'_ma'+str(14)],
                name=var_new+'_ma'+str(14), 
                mode='lines',
                opacity = 1,
                line=dict(color='red',
                          width=4),
                showlegend=True
        ))
        #adding the smoothed trace
        fig.add_trace(
            go.Scatter( 
                x=df.date, 
                y=df[var_new+'_smooth'],
                name='smoothed', 
                mode='lines',
                opacity = 1,
                line=dict(color='purple',
                          width=6),
                showlegend=True
        ))
        fig.update_layout(
            xaxis={'title': None,
                   'titlefont':{'color':'#BFBFBF', 
                                'family': font_use},
                   'tickfont':{'color':'#002A34',
                               'size':30, 
                               'family': font_use},
                   'gridcolor': '#4A4A4A',
                   'linecolor': '#000000',
                   'showgrid':False},
            yaxis={'title': 'Digital Demand'  ,
                   'titlefont':{'color':'#002A34',
                                'size':50, 
                                'family': font_use},
                   'tickfont':{'color':'#002A34',
                               'size':30, 
                               'family': font_use},
                   'showgrid':False,
                   'zeroline':False},
            margin={'l': 170, 
                    'b': 150, 
                    't': 150,
                    'r': 40},
            title={'text': f'{text}'.capitalize(), 
                   'font':{'color':'#000000', 
                           'size':40,
                           'family': font_use},
                   'yanchor':"top",
                   'xanchor':"center"},
            legend={'font':{'size':20, 
                            'color':'#333',
                            'family': font_use},
                    'yanchor':"top",
                    'xanchor':"center",
                    'y':0.9,
                    'x':.95,
                    'orientation':'v',
                    },
            template = 'none',
            hovermode='x unified',
            width = 1920,
            height = 1080     
        )

        # write image 
        if out_type == 'svg':
            fig.write_image(f"{text}.{output_type}")
        elif out_type == 'html':
            fig.write_html(f"{text}.{output_type}")
        else:
            fig.write_image(f"{text}.{output_type}")
            
        return 'vis completed'
    
    #this is running from vis_functions.py
    single(
        key = f'{text.lower()}', 
        geo = 'DE',
        cat = 13,
        startdate = f'{init_date}',
        index = True,
        indexdate = f'{index_date}',
        font_use = 'Roboto Mono Light for Powerline',
        out_type = f'{output_type}'
    )

    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}

    # uploading the file to azure blob storage
    # creating variable to use in blob_service_client
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    # creating variable to use in container_client
    container_name = "visfunc"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = f"{text}.{output_type}"
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename
    # upload the file
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)
    
    #uploading the file to slack using bolt syntax for py
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()
        
        # Open the audio file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
        
        # write image 
        if output_type == 'svg':
            # filename=f"{text}.png"
            response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        filename=filename,
                                        filetype="svg",
                                        initial_comment="Visualization: ")
            assert response["file"]  # the uploaded file
        elif output_type == 'html':
            # filename=f"{text}.png"
            response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        filename=filename,
                                        filetype="html",
                                        initial_comment="Visualization: ")
            assert response["file"]  # the uploaded file
        else:
            # filename=f"{text}.png"
            response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        filename=filename,
                                        filetype="png",
                                        initial_comment="Visualization: ")
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
########################### END OF BACKGROUNDWORKER3 ####################################
#######################################################__________________________________

#########################################################################################

    # context_block = [
	# 	{
	# 		"type": "divider"
	# 	},
	# 	{
	# 		"type": "context",
	# 		"elements": [
	# 			{
	# 				"type": "plain_text",
	# 				"text": "Insight Generation: :beta:",
	# 				"emoji": True
	# 			}
	# 		]
	# 	},
	# 	{
	# 		"type": "context",
	# 		"elements": [
	# 			{
	# 				"type": "mrkdwn",
	# 				"text": "*Usage Hint:* \nPlease use the slash command again to generate a new visualization."
	# 			}
	# 		]
	# 	}
	# ]
    
    # #sending kw_value and language selection dropdown
    # client.chat_postMessage(channel=channel_id,
    #                         text="sending kw_value",
    #                         blocks=context_block
    #                         )
    
    # requests.post(response_url,data=json.dumps(payload))
#######################################################__________________________________

#########################################################################################
#creating an empty list for condition branching on wordcloud
condition_list = []

#creating an empty list for condition branching on dd_vis_trigger
condition_list_dd_vis = []
#######################################################__________________________________

#########################################################################################
######################## BLOCK KIT FOR WORD CLOUD START #################################
#slack limits options to 100
#block that contains all wordcloud shapes fron font awesome
# wordcloud_shape_block2 = [{"type": "input",
#   "element": {"type": "static_select",
#               "placeholder": {
#                 "type": "plain_text",
#                 "text": "Select an item",
#                 "emoji": True
#               },
#               "options": [
#                   {"text": {
#                       "type": "plain_text",
#                       "text": "500 PX",
#                       "emoji": True
#                   },
#                    "value": "fab fa-500px"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Accusoft",
#                         "emoji": True
#                     },
#                    "value": "fab fa-accusoft"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Coffee",
#                         "emoji": True
#                   },
#                    "value": "fas fa-coffee"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Amazon",
#                         "emoji": True
#                   },
#                    "value": "fab fa-amazon"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Android",
#                         "emoji": True
#                       },
#                    "value": "fab fa-android"
#                    },
                  
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "App-Store-IOS",
#                         "emoji": True
#                       },
#                    "value": "fab fa-app-store-ios"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Apple",
#                         "emoji": True
#                       },
#                    "value": "fab fa-apple"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Apple Pay",
#                         "emoji": True
#                       },
#                    "value": "fab fa-apple-pay"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Audible",
#                         "emoji": True
#                       },
#                    "value": "fab fa-audible"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "AWS",
#                         "emoji": True
#                       },
#                    "value": "fab fa-aws"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Bitbucket",
#                         "emoji": True
#                     },
#                    "value": "fab fa-bitbucket"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Bitcoin",
#                         "emoji": True
#                   },
#                    "value": "fab fa-bitcoin"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Bookmark",
#                         "emoji": True
#                   },
#                    "value": "fas fa-bookmark"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Bluetooth",
#                         "emoji": True
#                   },
#                    "value": "fab fa-bluetooth"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Amex",
#                         "emoji": True
#                       },
#                    "value": "fab fa-cc-amex"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Discover",
#                         "emoji": True
#                       },
#                    "value": "fab fa-cc-discover"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Mastercard",
#                         "emoji": True
#                       },
#                    "value": "fab fa-cc-mastercard"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Paypal",
#                         "emoji": True
#                       },
#                    "value": "fab fa-cc-paypal"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Circle solid",
#                         "emoji": True
#                       },
#                    "value": "fas fa-circle"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "far fa-circle",
#                         "emoji": True
#                       },
#                    "value": "Circle"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Chrome",
#                         "emoji": True
#                       },
#                    "value": "fab fa-chrome"
#                    },
                  
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Cloud",
#                         "emoji": True
#                       },
#                    "value": "fas fa-cloud"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Comment",
#                         "emoji": True
#                       },
#                    "value": "fas fa-comment"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Docker",
#                         "emoji": True
#                       },
#                    "value": "fab fa-docker"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Dropbox",
#                         "emoji": True
#                       },
#                    "value": "fab fa-dropbox"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Edge",
#                         "emoji": True
#                     },
#                    "value": "fab fa-edge"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "File",
#                         "emoji": True
#                   },
#                    "value": "fas fa-file"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Facebook",
#                         "emoji": True
#                   },
#                    "value": "fab fa-facebook"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Facebook -f",
#                         "emoji": True
#                       },
#                    "value": "fab fa-facebook-f"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Facebook Messenger",
#                         "emoji": True
#                       },
#                    "value": "fab fa-facebook-messenger"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Firefox",
#                         "emoji": True
#                       },
#                    "value": "fab fa-firefox"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Folder",
#                         "emoji": True
#                       },
#                    "value": "fas fa-folder"
#                    },
                  
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Github",
#                         "emoji": True
#                       },
#                    "value": "fab fa-github"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Goodreads",
#                         "emoji": True
#                       },
#                    "value": "fab fa-goodreads"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Google",
#                         "emoji": True
#                       },
#                    "value": "fab fa-google"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Google Drive",
#                         "emoji": True
#                       },
#                    "value": "fab fa-google-drive"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Heart",
#                         "emoji": True
#                       },
#                    "value": "fas fa-heart"
#                    },
                                    
#                   {"text": {
#                       "type": "plain_text",
#                       "text": "IMDB",
#                       "emoji": True
#                   },
#                    "value": "fab fa-imdb"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Instagram",
#                         "emoji": True
#                     },
#                    "value": "fab fa-instagram"
#                   },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Internet Explorer",
#                         "emoji": True
#                   },
#                    "value": "fab fa-internet-explorer"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Itunes",
#                         "emoji": True
#                   },
#                    "value": "fab fa-itunes"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Itunes Note",
#                         "emoji": True
#                   },
#                    "value": "fab fa-itunes-note"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Jenkins",
#                         "emoji": True
#                   },
#                    "value": "fab fa-jenkins"
#                 },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "JS",
#                         "emoji": True
#                       },
#                    "value": "fab fa-js"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "JS fiddle",
#                         "emoji": True
#                       },
#                    "value": "fab fa-jsfiddle"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Kickstarter",
#                         "emoji": True
#                       },
#                    "value": "fab fa-kickstarter"
#                    },
                  
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "LinkedIn",
#                         "emoji": True
#                       },
#                    "value": "fab fa-linkedin"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "LinkedIn-IN",
#                         "emoji": True
#                       },
#                    "value": "fab fa-linkedin-in"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Linux",
#                         "emoji": True
#                   },
#                    "value": "fab fa-linux"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Lyft",
#                         "emoji": True
#                       },
#                    "value": "fab fa-lyft"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Map Marker",
#                         "emoji": True
#                       },
#                    "value": "fas fa-map-marker"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Microsoft",
#                         "emoji": True
#                       },
#                    "value": "fab fa-microsoft"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Nintendo Switch",
#                         "emoji": True
#                       },
#                    "value": "fab fa-nintendo-switch"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Opera",
#                         "emoji": True
#                       },
#                    "value": "fab fa-opera"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Play button",
#                         "emoji": True
#                       },
#                    "value": "fas fa-play"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Pinterest P",
#                         "emoji": True
#                       },
#                    "value": "fab fa-pinterest-p"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Playstation",
#                         "emoji": True
#                       },
#                    "value": "fab fa-playstation"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Python",
#                         "emoji": True
#                       },
#                    "value": "fab fa-python"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Quora",
#                         "emoji": True
#                       },
#                    "value": "fab fa-quora"
#                    },                  
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Reddit",
#                         "emoji": True
#                       },
#                    "value": "fab fa-reddit"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Reddit-Alien",
#                         "emoji": True
#                       },
#                    "value": "fab fa-reddit-alien"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Shapes",
#                         "emoji": True
#                       },
#                    "value": "fas fa-shapes"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Skype",
#                         "emoji": True
#                       },
#                    "value": "fab fa-skype"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Square",
#                         "emoji": True
#                       },
#                    "value": "far fa-square"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Slack Hash",
#                         "emoji": True
#                       },
#                    "value": "fab fa-slack-hash"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Snapchat Ghost",
#                         "emoji": True
#                       },
#                    "value": "fab fa-snapchat-ghost"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Square solid",
#                         "emoji": True
#                       },
#                    "value": "fas fa-square"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Spotify",
#                         "emoji": True
#                       },
#                    "value": "fab fa-spotify"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Star solid",
#                         "emoji": True
#                       },
#                    "value": "fas fa-star"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Steam",
#                         "emoji": True
#                       },
#                    "value": "fab fa-steam"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Steam Symbol",
#                         "emoji": True
#                       },
#                    "value": "fab fa-steam-symbol"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Star",
#                         "emoji": True
#                       },
#                    "value": "far fa-star"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Telegram",
#                         "emoji": True
#                       },
#                    "value": "fab fa-telegram"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Telegram plane",
#                         "emoji": True
#                       },
#                    "value": "fab fa-telegram-plane"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Trello",
#                         "emoji": True
#                       },
#                    "value": "fab fa-trello"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Tumblr",
#                         "emoji": True
#                       },
#                    "value": "fab fa-tumblr"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Twitch",
#                         "emoji": True
#                       },
#                    "value": "fab fa-twitch"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Twitter",
#                         "emoji": True
#                       },
#                    "value": "fab fa-twitter"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Uber",
#                         "emoji": True
#                       },
#                    "value": "fab fa-uber"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Viber",
#                         "emoji": True
#                       },
#                    "value": "fab fa-viber"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Vimeo",
#                         "emoji": True
#                       },
#                    "value": "fab fa-vimeo"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Vine",
#                         "emoji": True
#                       },
#                    "value": "fab fa-vine"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Vk",
#                         "emoji": True
#                       },
#                    "value": "fab fa-vk"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Weibo",
#                         "emoji": True
#                       },
#                    "value": "fab fa-weibo"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Whatsapp",
#                         "emoji": True
#                       },
#                    "value": "fab fa-whatsapp"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Wikipedia",
#                         "emoji": True
#                       },
#                    "value": "fab fa-wikipedia-w"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Windows",
#                         "emoji": True
#                       },
#                    "value": "fab fa-windows"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Wordpress",
#                         "emoji": True
#                       },
#                    "value": "fab fa-wordpress"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Xbox",
#                         "emoji": True
#                       },
#                    "value": "fab fa-xbox"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Xing",
#                         "emoji": True
#                       },
#                    "value": "fab fa-xing"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Yahoo",
#                         "emoji": True
#                       },
#                    "value": "fab fa-yahoo"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Yelp",
#                         "emoji": True
#                       },
#                    "value": "fab fa-yelp"
#                    },
#                   {"text": {
#                         "type": "plain_text",
#                         "text": "Youtube",
#                         "emoji": True
#                       },
#                    "value": "fab fa-youtube"
#                    },
#               ],
#               "action_id": "wordcloud_shape_act"
#              },
#   "label": {"type": "plain_text",
#             "text": "Select shape for Wordcloud",
#             "emoji": True}}]
#######################################################__________________________________

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
        
        #block to select language in wordcloud
        wordcloud_lang_block =  [
    		{
    			"type": "input",
    			"element": {
    				"type": "static_select",
    				"placeholder": {
    					"type": "plain_text",
    					"text": "Select an item",
    					"emoji": True
    				},
    				"options": [
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "English",
    							"emoji": True
    						},
    						"value": "en"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "German",
    							"emoji": True
    						},
    						"value": "de"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Spanish",
    							"emoji": True
    						},
    						"value": "es"
    					}
    				],
    				"action_id": "wordcloud_kw_lang_act"
    			},
    			"label": {
    				"type": "plain_text",
    				"text": "Select Language for Wordcloud",
    				"emoji": True
    			}}]
        
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
        
        #creating a block color scheme pick
        wordcloud_color_block=[
    		{
    			"type": "divider"
    		},
    		{
    			"type": "input",
    			"element": {
    				"type": "static_select",
    				"placeholder": {
    					"type": "plain_text",
    					"text": "Select an item",
    					"emoji": True
    				},
    				"options": [
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Blue-Green",
    							"emoji": True
    						},
    						"value": "BluGrn_4"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Blue-Yellow",
    							"emoji": True
    						},
    						"value": "BluYl_3"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Brown-Yellow",
    							"emoji": True
    						},
    						"value": "BrwnYl_2"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Burgundy",
    							"emoji": True
    						},
    						"value": "Burg_2"
    					}
    				],
    				"action_id": "wordcloud_color_act"
    			},
    			"label": {
    				"type": "plain_text",
    				"text": "Please choose a color palette",
    				"emoji": True
    			}
    		}
    	]
        
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
                                                
        thr = Thread(target=backgroundworker_wordcloud_shape, args=[condition_list[-3], 
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
        

        dd_vis_blocks_outputtype = [
		{
			"type": "input",
			"element": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Select an item",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "html",
							"emoji": True
						},
						"value": "html"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "png",
							"emoji": True
						},
						"value": "png"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "svg",
							"emoji": True
						},
						"value": "svg"
					}
				],
				"action_id": "dd_vis_blocks_image_export_action"
			},
			"label": {
				"type": "plain_text",
				"text": "Select output file format",
				"emoji": True
			}
		}]
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
        
        thr = Thread(target=backgroundworker3_ddviz, args=[condition_list_dd_vis[-4],
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

################################################
# edit mar 08, 2023 fixed indentation using vs code
# indendation errors are being caused by spyder (the ide I use)

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

#################################### Note: ##############################################
# WIKI_CSV_TRIGGER uses parameter names wordcloud_lang_to, wordcloud_lang_kw which are 
# unrelated to wordcloud features
# they are essentially wiki_csv_lang_to, and wiki_csv_keyword
#########################################################################################
#background worker for creating csv from wikipedia api
def backgroundworker_wiki_csv_trigger(wordcloud_lang_to, wordcloud_lang_kw, response_url, channel_id):

    # your task
    def wikisentences(key,geo):
        """ Get Wikipedia Raw Text for Specific Keyword in Specific Language (https://en.wikipedia.org/wiki/List_of_Wikipedias#Lists)
        
        Args:
            key (str): Keyword
            geo (str): Geo WP Code ('de')
        
        Returns:
            df: Dataframe with Sentences from Content of Wiki Site
        """
        # Set Wikipedia language to geo
        wikipedia.set_lang(geo)
        # Get all suggested results for the query of key in wiki
        all_results = wikipedia.search(key) 
        # Select the first suggested result
        key_original = all_results[0]
        # Get the resulting wikipedia page for key_original
        result = wikipedia.page(key_original, auto_suggest=False)
        # Get the Content of the result
        content_raw = result.content
        # Split content_raw into sentences
        sentences = tokenize.sent_tokenize(content_raw)
        # Put the sentences into a dataframe
        df = pd.DataFrame(data={'text': sentences})
        
        return df

    
    # Generate csv from wikipedia keyword and language pair
    wikisentences(wordcloud_lang_kw, wordcloud_lang_to).to_csv('wiki_sentences.csv', 
                                                               index_label='index') #column name is set to index
    
    
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    
    #uploading the file to azure blob storage
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    container_name = "wikicsv"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = 'wiki_sentences.csv'
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)
        
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()
        
	# Download the CSV file to a local temporary file
        # with open(filename, "wb") as my_blob:
        #     download_stream = blob_client.download_blob()
        #     my_blob.write(download_stream.readall())
	
        # Open the audio file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
            
        
        #         filename=f"{(text[:3]+text[-3:])}.mp3"
        response = client.files_upload(channels=channel_id,
                                        filename=filename, # added filename parameter and updated formatting edit mar 15, 2023
                                        file=file_data, 
                                        filetype="csv", 
                                        initial_comment=f"CSV generated for language-keyword: \n{wordcloud_lang_to.upper()} *{wordcloud_lang_kw.title()}*: ")
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

#################################### Note: ##############################################
# WIKI_CSV_TRIGGER uses parameter names wordcloud_lang_to, wordcloud_lang_kw which are 
# unrelated to wordcloud features
# they are essentially wiki_csv_lang_to, and wiki_csv_keyword
#########################################################################################
#wiki_csv trigger slash command which creates csv from Wikipedia API 
#and posts to slack
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
                 args=[wordcloud_lang_to,
                       wordcloud_lang_kw,
                       response_url,
                       channel_id]
                 )
    
    thr.start()
    
    #returning empty string with 200 response
    return f'{greeting_message}', 200
#######################################################__________________________________

#########################################################################################
#background worker for creating wordcloud from wikipedia api and provides selection of shape
def backgroundworker_wordcloud_shape(wordcloud_lang_to, wordcloud_lang_kw, wordcloud_shape_kw, wordcloud_color_kw, response_url, channel_id):
    
    
    # your task
    def wikitext(key,lang):
        """ Get Wikipedia Raw Text for Specific Keyword in Specific Language (https://en.wikipedia.org/wiki/List_of_Wikipedias#Lists)
    
        Args:
            key (str): Keyword
            lang (str): Wikipedia Geo WP Code ('de')
    
        Returns:
            str: Content of Wiki Site
        """
        # Set Wikipedia language to geo
        wikipedia.set_lang(lang)
        # Get all suggested results for the query of key in wiki
        all_results = wikipedia.search(key) 
        # Select the first suggested result
        key_original = all_results[0]
        # Get the resulting wikipedia page for key_original
        result = wikipedia.page(key_original, auto_suggest=False)
        # Return the Content of the result
        return result.content

    def cloud(txt, words,lang,col_palette,name, icon_name):
        
        """ Plots Wordcloud and saves png to Desktop
    
        Args:
            txt (str): Input text
            words (list): List of additional Stopwords
            lang (str): Language of text/ to be used for stopwords
            col_palette (str): Color palette from https://jiffyclub.github.io/palettable/ example: cartocolors.sequential.Burg_6
            name (str): Filename,
            icon_name (str): icon shape parameter
        """
        # Set color palette for wordcloud
        if col_palette == None:
            col_palette = 'cartocolors.sequential.Burg_6'
        else:
            pass
        # Get list of stopwords in considered language
        stop_words = get_stop_words(lang)
        # Add additional words to stopwords
        for elem in words:
            stop_words.append(elem)
        # Generate wordcloud
        style_cloud_img = stylecloud.gen_stylecloud(
                            text=txt,
                            icon_name= f"{wordcloud_shape_kw}",
                            palette=col_palette,
                            background_color='black',
                            output_name="file.png",
                            collocations=False,
                            max_font_size=400,
                            size=512,
                            custom_stopwords=stop_words
                            )
        
        return style_cloud_img
    
    # Define input
    keyword = f'{wordcloud_lang_kw}'
    language = f'{wordcloud_lang_to}'
    palette = f'cartocolors.sequential.{wordcloud_color_kw}'
    addwords = []
    icon_name = f'{wordcloud_shape_kw}'
    
    # Generate text from wikipedia article
    text = wikitext(wordcloud_lang_kw, wordcloud_lang_to)
    
    # Generate wordcloud
    cloud(text,addwords,language,palette,keyword+'_'+language, icon_name)
    
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}

    # uploading the file to azure blob storage
    # creating variable to use in blob_service_client
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    # creating variable to use in container_client
    container_name = "wordcloud"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = "file.png"
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)    

    
    #uploading the file to slack using bolt syntax for py
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()

        # Open the wordcloud file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
        # filename=f"wordcloud/file.png"
        response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        initial_comment=f"Wordcloud generated for language-keyword: \n{wordcloud_lang_to.upper()} *{wordcloud_lang_kw.title()}*:")
        assert response["file"]  # the uploaded file

        # Delete the blob
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()

    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")    
    
    # client.chat_postMessage(channel='#asb_dd_top10_changes',
    #                         text="*Usage Hint*: \nPlease use the slash command again to generate new Visualization."
    #                         )
    

    requests.post(response_url,data=json.dumps(payload))
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
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    #getting language to form wordclouds from
    #wordcloud_lang_to = data.get('text').split()[0].lower()
    #wordcloud_lang_kw = ' '.join(data.get('text').split()[1:])
    
    
    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"
    
    #block to obtain wordcloud keyword
    word_cloud_kw_block = [
		{
			"type": "divider"
		},
		{
			"dispatch_action": True,
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "wordcloud_kw_inp_act"
			},
			"label": {
				"type": "plain_text",
				"text": "Please provide the keyword for Wordcloud",
				"emoji": True
			}
		}
	]
    
    
    
    client.chat_postMessage(channel=channel_id,
                            text=f"Please provide the keyword for wordcloud",
                            blocks=word_cloud_kw_block
                            )
    
    return f'{greeting_message}', 200
#######################################################__________________________________

#########################################################################################
# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)
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
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


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
#######################################################__________________________________

#########################################################################################
# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
