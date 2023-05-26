import os
import requests
import numpy as np
import pandas as pd
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
import requests
import json

import plotly.graph_objects as go
def backgroundworker_zenserp_trends(client, text, response_url, channel_id):

    # Define API KEY
    headers = { 
        "apikey": "ea6d7b00-fa4e-11ed-a261-ab10ed32af2f"}

    # Define parameters of query
    keys = ['o2','telekom','vodafone','congstar','1und1']
    category = 13
    country = 'DE'
    tf = "today 5-y"

    # Add parameters to query
    params = (
        ("keyword[]", keys[0]),
        ("keyword[]", keys[1]),
        ("keyword[]", keys[2]),
        ("keyword[]", keys[3]),
        ("keyword[]", keys[4]),
        ("cat",str(category)),
        ("hl","de"),
        ("geo",country),
        ("timeframe",tf),
    )

    # Get response object
    response = requests.get('https://app.zenserp.com/api/v1/trends', headers=headers, params=params);

    # Get dictionary object from response json
    dict_gt = response.json()

    # Get trends from dictionary
    dict_gt1 = dict_gt[keys[0]]['trends']

    # Get dataframe from dictionary
    df1 = pd.DataFrame.from_dict(dict_gt1)

    # Transpose dataframe
    df = df1.T

    # Get date as a column in datetime format
    df['date_raw'] = df.index
    df.index = range(0,len(df))
    df['date'] = pd.to_datetime(df['date_raw'], format='%Y-%m-%dT%H:%M:%S.000Z')

    # Drop original date_raw column
    df = df.drop(['date_raw'], axis=1)

    # Define colors of lines
    cols = ['#9C0046','#0050B7','#789098','#00EF99','#FF6F00']

    # Plot the columns of the dataframe
    def plot(keys):
        fig = go.Figure()
        for i in range(0,len(keys)):
            fig.add_trace(
                go.Scatter( 
                    x=df['date'], 
                    y=df[keys[i]], 
                    name=keys[i], 
                    mode='lines',
                    opacity = 1,
                    line=dict(color = cols[i],width=4,shape='spline'),
                    showlegend =  True
            ))
        fig.update_layout(
            xaxis={'title': None,'titlefont':{'color':'#BFBFBF', 'family': 'Avenir'}, 'tickfont':{'color':'#002A34','size':25, 'family': 'Avenir'},
                    'ticklen':5,'dtick': 'M6','tickformat': '%b %y','gridcolor': '#4A4A4A','linecolor': '#000000','showgrid':False},
                yaxis={'title': 'Index' ,'titlefont':{'color':'#002A34','size':50, 'family': 'Avenir'}, 
                    'tickfont':{'color':'#002A34','size':25, 'family': 'Avenir'},'showgrid':False,'zeroline':False},
                margin={'l': 140, 'b': 100, 't': 40, 'r': 60},
                title={'text': 'Google Trends Evolution' + ' (Category: ' + str(category) + '; Country: ' + country + ')', 'font':{'color':'#000000', 'size':30, 'family': 'Avenir'},'yanchor':"top",'xanchor':"center"},
                legend={'font':{'size':20, 'color':'#333', 'family': 'Avenir'},'yanchor':"top",'xanchor':"center",'y':0.95,'x':.95,'orientation':'v',
                        },
                template = 'none',
                hovermode='closest',
                width = 1920,
                height = 1080
        )
        fig.write_image(os.path.expanduser(f"zenserp_trends_plot/plot.png"))

    plot(keys)

    #uploading the file to slack using bolt syntax for py
    try:
        filename=f"zenserp_trends_plot/plot.png"
        response = client.files_upload(channels= channel_id,
                                        file=filename,
                                        initial_comment=f"Plot generated for trends: ")
        assert response["file"]  # the uploaded file
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")    
    
    requests.post(response_url,data=json.dumps(payload))

    # your task
    client.chat_postMessage(channel= channel_id,
                            text=f"{text}   {response_url}"
                            )
    
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    

    requests.post(response_url,data=json.dumps(payload))