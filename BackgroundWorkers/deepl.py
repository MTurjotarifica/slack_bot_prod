import os
import requests
import json
import numpy as np
import pandas as pd

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

import deepl

# Background worker for deep l 
def backgroundworker_deepl_text_lang(client, text_lang_to, text_to_translate, response_url, channel_id):

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

