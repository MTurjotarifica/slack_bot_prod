import pandas as pd
import mysql.connector as mysql
import numpy as np
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07

def generate_trend_block(df):
    trend_block = [
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Test block with multi static select"
            },
            "accessory": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select options",
                    "emoji": True
                },
                "options": [],
                "action_id": "trend-select"
            }
        }
    ]
    # Load the Excel file into a DataFrame
    df = pd.read_csv('unique_provider.csv')

    # Now you can work with the DataFrame
    # For example, you can print the first few rows
    # print(df.head())

    # Iterate over the DataFrame and create option dictionaries
    options = []
    for keyword in df['provider']:
        option = {
            "text": {
                "type": "plain_text",
                "text": keyword,
                "emoji": True
            },
            "value": keyword
        }
        options.append(option)

    # Update the options in the trend_block variable
    trend_block[1]['accessory']['options'] = options

    return trend_block
