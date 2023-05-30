import json
import numpy as np
import pandas as pd
from threading import Thread

from flask import Flask, request, make_response, session
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

# Retrieve condition_list and condition_list_dd_vis from the session
condition_list =  []
condition_list_dd_vis = []

def interactive_trigger_route(client,
                                df_raw,
                                backgroundworker_wordcloud_shape, 
                                backgroundworker3_ddviz, 
                                backgroundworker_zenserp_trends,
                                wordcloud_lang_block, wordcloud_shape_block2, 
                                wordcloud_color_block, 
                                dd_vis_blocks_startdate, 
                                dd_vis_blocks_indexdate, 
                                dd_vis_blocks_outputtype):
    
    

    data = request.form
    data2 = request.form.to_dict()
    user_id = data.get('user_id')
    channel_id = json.loads(data2['payload'])['container']['channel_id']
    text = data.get('text')

    response_url = json.loads(data2['payload'])['response_url']
    actions = data.get("actions")
    actions_value = data.get("actions.value")
    action_id = json.loads(data2['payload'])['actions'][0]['action_id']

    if action_id == "trend-select":

        payload = json.loads(data2['payload'])
        selected_options = payload['actions'][0]['selected_options']
        selected_values = [option['value'] for option in selected_options]

        thr = Thread(target=backgroundworker_zenserp_trends, args=[client, text, response_url, channel_id, selected_values])
        thr.start()

    elif action_id == "wordcloud_kw_inp_act":

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
        print(condition_list)
        client.chat_postMessage(channel=channel_id,
                                text= str(condition_list))

        thr = Thread(target=backgroundworker_wordcloud_shape, args=[client,
                                                                    condition_list[-3], 
                                                                    condition_list[-4], 
                                                                    condition_list[-2],
                                                                    condition_list[-1],
                                                                    response_url,
                                                                    channel_id])
        thr.start()

        # Reset condition_list after using it for word cloud
        condition_list = []

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

        print(condition_list)
        client.chat_postMessage(channel=channel_id,
                                text= str(condition_list))



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
	
        # Reset condition_list after using it for word cloud
        condition_list = []
        #client.chat_postMessage(channel=channel_id, text=f"dd_vis_blocks_indexdate_act working kw: {condition_list_dd_vis[-3]} & startd: {condition_list_dd_vis[-2]} & indexd: {condition_list_dd_vis[-1]} & responseurl: {response_url} & chID:{channel_id}")
        
    else:
        client.chat_postMessage(channel=channel_id, text="Error: Please try again with different values.")
        #pass
        

    return 'interactive trigger works', 200
#######################################################__________________________________
