#################################### Note: ##############################################
# WIKI_CSV_TRIGGER uses parameter names wordcloud_lang_to, wordcloud_lang_kw which are 
# unrelated to wordcloud features
# they are essentially wiki_csv_lang_to, and wiki_csv_keyword
#########################################################################################
# for wiki_csv trigger
import wikipedia
from nltk import tokenize #wiki sentences
import numpy as np
import pandas as pd
import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

import requests
import json

# Background worker for creating csv from wikipedia api
def backgroundworker_wiki_csv_trigger(client, wordcloud_lang_to, wordcloud_lang_kw, response_url, channel_id):

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