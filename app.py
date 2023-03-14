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
import scipy.signal

import slack

from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07

from stop_words import get_stop_words
import wikipedia
import stylecloud
import pillow

# from vis_functions import *


load_dotenv()


# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)


client = slack_app.client



##########################################################
#slack limits options to 100
#block that contains all wordcloud shapes fron font awesome
wordcloud_shape_block2 = [{"type": "input",
  "element": {"type": "static_select",
              "placeholder": {
                "type": "plain_text",
                "text": "Select an item",
                "emoji": True
              },
              "options": [
                  {"text": {
                      "type": "plain_text",
                      "text": "500 PX",
                      "emoji": True
                  },
                   "value": "fab fa-500px"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "Accusoft",
                        "emoji": True
                    },
                   "value": "fab fa-accusoft"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "Coffee",
                        "emoji": True
                  },
                   "value": "fas fa-coffee"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Amazon",
                        "emoji": True
                  },
                   "value": "fab fa-amazon"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Android",
                        "emoji": True
                      },
                   "value": "fab fa-android"
                   },
                  
                  {"text": {
                        "type": "plain_text",
                        "text": "App-Store-IOS",
                        "emoji": True
                      },
                   "value": "fab fa-app-store-ios"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Apple",
                        "emoji": True
                      },
                   "value": "fab fa-apple"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Apple Pay",
                        "emoji": True
                      },
                   "value": "fab fa-apple-pay"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Audible",
                        "emoji": True
                      },
                   "value": "fab fa-audible"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "AWS",
                        "emoji": True
                      },
                   "value": "fab fa-aws"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Bitbucket",
                        "emoji": True
                    },
                   "value": "fab fa-bitbucket"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "Bitcoin",
                        "emoji": True
                  },
                   "value": "fab fa-bitcoin"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Bookmark",
                        "emoji": True
                  },
                   "value": "fas fa-bookmark"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Bluetooth",
                        "emoji": True
                  },
                   "value": "fab fa-bluetooth"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Amex",
                        "emoji": True
                      },
                   "value": "fab fa-cc-amex"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Discover",
                        "emoji": True
                      },
                   "value": "fab fa-cc-discover"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Mastercard",
                        "emoji": True
                      },
                   "value": "fab fa-cc-mastercard"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Paypal",
                        "emoji": True
                      },
                   "value": "fab fa-cc-paypal"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Circle solid",
                        "emoji": True
                      },
                   "value": "fas fa-circle"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "far fa-circle",
                        "emoji": True
                      },
                   "value": "Circle"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Chrome",
                        "emoji": True
                      },
                   "value": "fab fa-chrome"
                   },
                  
                  {"text": {
                        "type": "plain_text",
                        "text": "Cloud",
                        "emoji": True
                      },
                   "value": "fas fa-cloud"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Comment",
                        "emoji": True
                      },
                   "value": "fas fa-comment"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Docker",
                        "emoji": True
                      },
                   "value": "fab fa-docker"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Dropbox",
                        "emoji": True
                      },
                   "value": "fab fa-dropbox"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Edge",
                        "emoji": True
                    },
                   "value": "fab fa-edge"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "File",
                        "emoji": True
                  },
                   "value": "fas fa-file"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Facebook",
                        "emoji": True
                  },
                   "value": "fab fa-facebook"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Facebook -f",
                        "emoji": True
                      },
                   "value": "fab fa-facebook-f"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Facebook Messenger",
                        "emoji": True
                      },
                   "value": "fab fa-facebook-messenger"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Firefox",
                        "emoji": True
                      },
                   "value": "fab fa-firefox"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Folder",
                        "emoji": True
                      },
                   "value": "fas fa-folder"
                   },
                  
                  {"text": {
                        "type": "plain_text",
                        "text": "Github",
                        "emoji": True
                      },
                   "value": "fab fa-github"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Goodreads",
                        "emoji": True
                      },
                   "value": "fab fa-goodreads"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Google",
                        "emoji": True
                      },
                   "value": "fab fa-google"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Google Drive",
                        "emoji": True
                      },
                   "value": "fab fa-google-drive"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Heart",
                        "emoji": True
                      },
                   "value": "fas fa-heart"
                   },
                                    
                  {"text": {
                      "type": "plain_text",
                      "text": "IMDB",
                      "emoji": True
                  },
                   "value": "fab fa-imdb"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "Instagram",
                        "emoji": True
                    },
                   "value": "fab fa-instagram"
                  },
                  {"text": {
                        "type": "plain_text",
                        "text": "Internet Explorer",
                        "emoji": True
                  },
                   "value": "fab fa-internet-explorer"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Itunes",
                        "emoji": True
                  },
                   "value": "fab fa-itunes"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Itunes Note",
                        "emoji": True
                  },
                   "value": "fab fa-itunes-note"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "Jenkins",
                        "emoji": True
                  },
                   "value": "fab fa-jenkins"
                },
                  {"text": {
                        "type": "plain_text",
                        "text": "JS",
                        "emoji": True
                      },
                   "value": "fab fa-js"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "JS fiddle",
                        "emoji": True
                      },
                   "value": "fab fa-jsfiddle"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Kickstarter",
                        "emoji": True
                      },
                   "value": "fab fa-kickstarter"
                   },
                  
                  {"text": {
                        "type": "plain_text",
                        "text": "LinkedIn",
                        "emoji": True
                      },
                   "value": "fab fa-linkedin"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "LinkedIn-IN",
                        "emoji": True
                      },
                   "value": "fab fa-linkedin-in"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Linux",
                        "emoji": True
                  },
                   "value": "fab fa-linux"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Lyft",
                        "emoji": True
                      },
                   "value": "fab fa-lyft"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Map Marker",
                        "emoji": True
                      },
                   "value": "fas fa-map-marker"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Microsoft",
                        "emoji": True
                      },
                   "value": "fab fa-microsoft"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Nintendo Switch",
                        "emoji": True
                      },
                   "value": "fab fa-nintendo-switch"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Opera",
                        "emoji": True
                      },
                   "value": "fab fa-opera"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Play button",
                        "emoji": True
                      },
                   "value": "fas fa-play"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Pinterest P",
                        "emoji": True
                      },
                   "value": "fab fa-pinterest-p"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Playstation",
                        "emoji": True
                      },
                   "value": "fab fa-playstation"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Python",
                        "emoji": True
                      },
                   "value": "fab fa-python"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Quora",
                        "emoji": True
                      },
                   "value": "fab fa-quora"
                   },                  
                  {"text": {
                        "type": "plain_text",
                        "text": "Reddit",
                        "emoji": True
                      },
                   "value": "fab fa-reddit"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Reddit-Alien",
                        "emoji": True
                      },
                   "value": "fab fa-reddit-alien"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Shapes",
                        "emoji": True
                      },
                   "value": "fas fa-shapes"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Skype",
                        "emoji": True
                      },
                   "value": "fab fa-skype"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Square",
                        "emoji": True
                      },
                   "value": "far fa-square"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Slack Hash",
                        "emoji": True
                      },
                   "value": "fab fa-slack-hash"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Snapchat Ghost",
                        "emoji": True
                      },
                   "value": "fab fa-snapchat-ghost"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Square solid",
                        "emoji": True
                      },
                   "value": "fas fa-square"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Spotify",
                        "emoji": True
                      },
                   "value": "fab fa-spotify"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Star solid",
                        "emoji": True
                      },
                   "value": "fas fa-star"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Steam",
                        "emoji": True
                      },
                   "value": "fab fa-steam"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Steam Symbol",
                        "emoji": True
                      },
                   "value": "fab fa-steam-symbol"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Star",
                        "emoji": True
                      },
                   "value": "far fa-star"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Telegram",
                        "emoji": True
                      },
                   "value": "fab fa-telegram"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Telegram plane",
                        "emoji": True
                      },
                   "value": "fab fa-telegram-plane"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Trello",
                        "emoji": True
                      },
                   "value": "fab fa-trello"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Tumblr",
                        "emoji": True
                      },
                   "value": "fab fa-tumblr"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Twitch",
                        "emoji": True
                      },
                   "value": "fab fa-twitch"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Twitter",
                        "emoji": True
                      },
                   "value": "fab fa-twitter"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Uber",
                        "emoji": True
                      },
                   "value": "fab fa-uber"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Viber",
                        "emoji": True
                      },
                   "value": "fab fa-viber"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Vimeo",
                        "emoji": True
                      },
                   "value": "fab fa-vimeo"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Vine",
                        "emoji": True
                      },
                   "value": "fab fa-vine"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Vk",
                        "emoji": True
                      },
                   "value": "fab fa-vk"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Weibo",
                        "emoji": True
                      },
                   "value": "fab fa-weibo"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Whatsapp",
                        "emoji": True
                      },
                   "value": "fab fa-whatsapp"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Wikipedia",
                        "emoji": True
                      },
                   "value": "fab fa-wikipedia-w"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Windows",
                        "emoji": True
                      },
                   "value": "fab fa-windows"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Wordpress",
                        "emoji": True
                      },
                   "value": "fab fa-wordpress"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Xbox",
                        "emoji": True
                      },
                   "value": "fab fa-xbox"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Xing",
                        "emoji": True
                      },
                   "value": "fab fa-xing"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Yahoo",
                        "emoji": True
                      },
                   "value": "fab fa-yahoo"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Yelp",
                        "emoji": True
                      },
                   "value": "fab fa-yelp"
                   },
                  {"text": {
                        "type": "plain_text",
                        "text": "Youtube",
                        "emoji": True
                      },
                   "value": "fab fa-youtube"
                   },
              ],
              "action_id": "wordcloud_shape_act"
             },
  "label": {"type": "plain_text",
            "text": "Select shape for Wordcloud",
            "emoji": True}}]
##########################################################_____________________________________

##########################################################
condition_list=[]

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
        
        
        #creating a block for shape selection
        wordcloud_shape_block=[
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
    							"text": "500 PX",
    							"emoji": True
    						},
    						"value": "fab fa-500px"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Accessible Icon",
    							"emoji": True
    						},
    						"value": "fab fa-accessible-icon"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Accusoft",
    							"emoji": True
    						},
    						"value": "fab fa-accusoft"
    					},
    					{
    						"text": {
    							"type": "plain_text",
    							"text": "Coffee",
    							"emoji": True
    						},
    						"value": "fas fa-coffee"
    					},
    				],
    				"action_id": "wordcloud_shape_act"
    			},
    			"label": {
    				"type": "plain_text",
    				"text": "Select shape for Wordcloud",
    				"emoji": True
    			}
    		}
    	]
        
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

        return ' ', 200
###########################################################________________________________________________


###########################################################
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
                            output_name=os.path.expanduser(f"file.png"),
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

        # filename=f"wordcloud/file.png"
        response = client.files_upload(channels= channel_id,
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
###########################################################________________________________________________

###################################################################################
#wordcloud_shape_trigger slash command which creates csv from Wikipedia API 
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
    
    
    #triggering backgroundworker for deepl with arguments lang to translate from
    #translate to and text to translate
    # thr = Thread(target=backgroundworker_wordcloud_shape, 
    #              args=[wordcloud_lang_to,
    #                    wordcloud_lang_kw,
    #                    wordcloud_shape,
    #                    response_url]
    #              )
    
    # thr.start()
    return f'{greeting_message}', 200

###########################################################________________________________________________


#######################################################__________________________________
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
        client.chat_postMessage(channel=channel_id, text="it worksssss! ")
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


    # Return an empty response to Slack
    return make_response("", 200)
#######################################################__________________________________

#######################################################__________________________________
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



#######################################################__________________________________
# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
