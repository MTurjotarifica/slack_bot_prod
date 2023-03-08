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

##################################################################
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
    metadata = MetaData()
    
    #loading the digital_demand table #edit pik 2023-03-07
    df_dd_raw_table = Table('digital_demand',
                            metadata
			   )
    
    #this is the query to be performed #edit st 2023-03-07
    stmt = "SELECT * FROM digital_demand WHERE (gt_category = 13) AND (country = 'DE');"
    
    df_dd_raw = pd.read_sql(sqlalctext(stmt), connection) #edit st 2023-03-07
    df_dd_raw['date'] = pd.to_datetime(df_dd_raw['date'])
    
    connection.close()
    
    return df_dd_raw

#storing df_digital_demand in variable df_raw to maintain code in viz generator
df_raw = load_dd_df()



##################################################________________________________________

#################################################
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


#######################################_________________________



# Handle incoming slash command requests
@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    # Parse the command and its parameters from the request
    command = request.form.get("command")
    text = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Execute the appropriate function based on the command
    if command == "/example":
        client.chat_postMessage(channel='#slack_bot_prod', text="it worksssss!")
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


    # Return an empty response to Slack
    return make_response("", 200)
#...........

#######################################
def backgroundworker_mp3(text, response_url):
    
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
        response = client.files_upload(channels='#slack_bot_prod',
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


#mp3 trigger slash command which creates mp3 and posts to slack
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


    client.chat_postMessage(channel='#slack_bot_prod',
                            text="MP3 loading. Please wait."
                            )


    #triggering backgroundworker1 
    thr = Thread(target=backgroundworker_mp3, args=[text, response_url])
    thr.start()


    #returning empty string with 200 response
    return f'{greeting_message}', 200


#######################################_________________________

#background worker for deep l where only file is provided
def backgroundworker_deepl_text_lang(text_lang_to, text_to_translate, response_url,channel_id):

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
                       response_url,channel_id
                      ]
                 )

    thr.start()


    #returning empty string with 200 response
    return f'{greeting_message}', 200

#######################################_______________________________________________



#######################################

def backgroundworker3_ddviz(text, init_date, index_date, response_url, channel_id):

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
        if out_type == 'svg':
            fig.write_image(os.path.expanduser(f"~/Desktop/{key}_single_timeseries.svg"))
        elif out_type == 'html':
            fig.write_html(os.path.expanduser(f"~/Desktop/{key}_single_timeseries.html"))
        else:
            container_string=os.environ["CONNECTION_STRING"]
            storage_account_name = "storage4slack"
            container_name = "visfunc"
            blob_service_client = BlobServiceClient.from_connection_string (container_string) 
            container_client = blob_service_client.get_container_client(container_name)
            blob_name = f"{text}.png"
            filename = f"{text}.png"
            
            with open(filename, "rb") as data:
                blob_client.upload_blob(data)
                
#             fig.write_image(os.path.expanduser(f"{text}.png"))
            
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
        out_type = 'png'
    )
    
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    
    #uploading the file to slack using bolt syntax for py
    try:
        # Download the blob as binary data
        blob_client = blob_service_client.get_blob_client(container_name, blob_name)
        blob_data = blob_client.download_blob().readall()
        
        # Open the image file and read its contents
        with open(filename, 'rb') as file:
            file_data = file.read()
        
#         filename=f"{text}.png"
        response = client.files_upload(channels=channel_id,
                                        file=file_data,
                                        initial_comment="Visualization: ")
        assert response["file"]  # the uploaded file
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")
        
    context_block = [
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
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "mrkdwn",
					"text": "*Usage Hint:* \nPlease use the slash command again to generate a new visualization."
				}
			]
		}
	]
    
    #sending kw_value and language selection dropdown
    client.chat_postMessage(channel=channel_id,
                            text="sending kw_value",
                            blocks=context_block
                            )
    
    requests.post(response_url,data=json.dumps(payload))


#creating an empty list for condition branching on wordcloud
condition_list = []

#creating an empty list for condition branching on dd_vis_trigger
condition_list_dd_vis = []

# st edit mar 08, 2023 fixed indentation using vs code
# indendation errors are being caused by spyder (the ide I use)
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
        client.chat_postMessage(channel="#slack_bot_prod", 
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
        client.chat_postMessage(channel="#slack_bot_prod",
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
        
        thr = Thread(target=backgroundworker3_ddviz, args=[condition_list_dd_vis[-3], 
                                                           condition_list_dd_vis[-2], 
                                                           condition_list_dd_vis[-1], 
                                                           response_url, 
                                                           channel_id])
        thr.start()
        
        client.chat_postMessage(channel="#slack_bot_prod",
                                text="dd_vis_blocks_indexdate_act working"
                                )    
        
    
    else:
        pass
        
        
    
    return ' ', 200

# @app.route('/dd_vis_trigger', methods=['POST'])
# def dd_vis_trigger():
#     data = request.form
#     #we are usging data2 to parse the information
#     data2 = request.form.to_dict()
#     #print(data)
#     user_id = data.get('user_id')
#     channel_id = data.get('channel_id')
#     text = data.get('text')
#     response_url = data.get("response_url")
#     #event = payload.get('event', {})
#     #text = event.get('text')
#     greeting_message = "Processing your request. Please wait."
#     ending_message = "Process executed successfully"

#     #utilizing threading
#     #thr = Thread(target=backgroundworker, args=[text,response_url])
#     #thr.start()

#     #this creates the text prompt in slack block kit
#     dd_vis_trigger_block = [
#         {
#            "type": "divider"
#            },
#         {
#             "dispatch_action": True,
#             "type": "input",
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "dd_vis_trigger_act"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Please type the keyword for the visualization ",
#                 "emoji": True
#             }
#         }
#     ]

#     client.chat_postMessage(channel=channel_id, 
#                                         text="Visualization:  ",
#                                         blocks = dd_vis_trigger_block
#                                         )


#     #returning empty string with 200 response
#     return '', 200
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
    return '', 200

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
