#########################################################################################
#background worker for creating wordcloud from wikipedia api and provides selection of shape
# for wiki_csv trigger
import wikipedia
from nltk import tokenize #wiki sentences

import nltk
nltk.download('punkt')
import stylecloud
from stop_words import get_stop_words

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
import requests
import json

def backgroundworker_wordcloud_shape(client, wordcloud_lang_to, wordcloud_lang_kw, wordcloud_shape_kw, wordcloud_color_kw, response_url, channel_id):
    
    
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
    


    requests.post(response_url,data=json.dumps(payload))
#######################################################__________________________________
