import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import mysql.connector as mysql
import numpy as np
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import text as sqlalctext #edit st 2023-03-07
import os

#########################################################################################
#function to create load difital demand as dataframe
def load_dd_df():
    '''
    loads digital demand dataframe for all dates
    where country is DE
    and gt_category 13
    returns:
        df_dd_raw (Dataframe)
    '''    
    #SQL ALCHEMY
    #creating the engine
    #syntax: dialect+driver://username:password@host:port/database
    engine = create_engine('mysql+pymysql://sandbox_read_only:zhsqehk23Xs8tVmVn3sSkyq5TvZumR5q@mysqldatabase.cmi5f1vp8ktf.us-east-1.rds.amazonaws.com:3306/sandbox')
    
    #creating a connection object
    connection = engine.connect()
    
    #creating the metadata object
    # metadata = MetaData()
    
    #loading the digital_demand table #edit pik 2023-03-07
    # df_dd_raw_table = Table('digital_demand',
    #                        metadata)
    
    #this is the query to be performed #edit st 2023-03-07
    stmt = "SELECT * FROM digital_demand WHERE (gt_category = 13) AND (country = 'DE') and (date >= '2022-01-01');" #date updated to 2022 jan 1
    
    df_dd_raw = pd.read_sql(sqlalctext(stmt), connection) #edit st 2023-03-07
    df_dd_raw['date'] = pd.to_datetime(df_dd_raw['date'])
    
    connection.close()
    
    #storing df_digital_demand in variable df_raw to maintain code in viz generator
    df_raw_22_onwards = df_dd_raw


    # loading data from a blob container called csv that contains digital demand data from 2010 to 2022
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    container_name = "csv"
    blob_service_client = BlobServiceClient.from_connection_string (container_string)
    container_client = blob_service_client.get_container_client(container_name)
    filename = "split_df_raw.csv"
    blob_client = container_client.get_blob_client(filename)
    blob_name= filename


    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    blob_data = blob_client.download_blob().readall()

    # Open the csv file and read its contents
    # with open(filename, 'rb') as file:
    #     file_data = file.read()

    # Download the CSV file to a local temporary file
    with open(filename, "wb") as my_blob:
        download_stream = blob_client.download_blob()
        my_blob.write(download_stream.readall())

    # file_data is our new csv
    df_raw_10_21 = pd.read_csv(filename)

    # creating a list of dataframes to be merged
    frames = [df_raw_10_21, df_raw_22_onwards]

    # merging the dataframes
    df_raw = pd.concat(frames)

    return df_raw