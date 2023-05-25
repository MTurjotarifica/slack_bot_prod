import os
import requests
import json

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

from Blocks.blocks import *
from vis_functions import *

# Backgroundworker for new combined flow
def backgroundworker3_ddviz(client, df_raw, text, init_date, index_date, output_type, response_url, channel_id):

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

    # Uploading the file to azure blob storage
    # Creating variable to use in blob_service_client
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    # Creating variable to use in container_client
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
