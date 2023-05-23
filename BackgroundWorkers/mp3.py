# Backgroundworker for mp3 post on slack
import os
import requests
import json
import numpy as np
import pandas as pd

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

import azure.cognitiveservices.speech as speechsdk

def backgroundworker_mp3(client, text, response_url, channel_id):
    
    # your task
    # The environment variables named "SPEECH_KEY" and "SPEECH_REGION"
     
    # Subscription and speech_region values are obtained from azure portal
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
