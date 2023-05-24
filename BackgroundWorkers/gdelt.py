
# Background worker for creating csv from gdelt data (we are not using gdelt package)
import os
import requests
import json
import numpy as np
import pandas as pd

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter


def backgroundworker_gdelt_csv_trigger(client, gdelt_text, response_url, channel_id):

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
