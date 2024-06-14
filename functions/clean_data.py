import pandas as pd
import numpy as np
import os
import re

from helper import convert_to_months
from helper import extract_lat_lng


def clean_airbnb_data(filename):

    df = pd.read_csv(f'./{filename}')
    df.reset_index(inplace=True)
    
    df['price_per_night'] = df['price_per_night'].replace('[\$,]', '', regex=True).astype(float)
    
    df['host_response_rate'] = df['host_response_rate'].str.split(":",expand=True)[1]
    df['host_response_rate'] = df['host_response_rate'].str.replace("%","")
   
    df[['latitude', 'longitude']] = df['google_map_location_link'].apply(lambda x: pd.Series(extract_lat_lng(x)))

    return df



def clean_host_data(filename):

    host_df = pd.read_csv(f'./{filename}')
    info_types = ['Identity', 'Email address', 'Phone number', 'Work email']


    for info in info_types:
        host_df[info] = host_df['host_confirmed_information'].apply(lambda x: info in x).astype(int)

    host_df.drop(columns=['host_confirmed_information'],inplace=True)

    host_df['host_hosting_duration_months'] = host_df['host_hosting_duration'].apply(convert_to_months)

    return host_df