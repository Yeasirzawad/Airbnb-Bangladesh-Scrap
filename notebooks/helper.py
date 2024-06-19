import pandas as pd
import numpy as np
import os
import re
import json
import ast 

def load_json(json_filename):
    with open(f"{json_filename}") as f:
        xpaths = json.load(f)

    return xpaths

def convert_to_months(duration):
    
    if pd.isna(duration):
        return np.nan
    num, unit = duration.split()
    num = int(num)
    if unit == 'years':
        return num * 12
    elif unit == 'months':
        return num
    else:
        return np.nan  

def extract_lat_lng(url):
    if isinstance(url, str):  
        params = url.split('?')[1].split('&')
        latitude = None
        longitude = None
        for param in params:
            key_value = param.split('=')
            if key_value[0] == 'll':
                lat_lng = key_value[1].split(',')
                latitude = float(lat_lng[0])
                longitude = float(lat_lng[1])
                break
        return latitude, longitude
    else:
        return None, None  


def merge_files(foldername):
    
    df_list = []

    for c in os.listdir(f'{foldername}'):
        df = pd.read_csv(f'{foldername}/'+c)
        df_list.append(df)

    return pd.concat(df_list)

def result_count_maker(string):  
    numbers = ""
    for char in string:
        if char.isdigit():
            numbers += char 

    return int(numbers)

def get_base_url(url):
    return url.split('?', 1)[0]

# Function to map and filter facilities based on mapping dictionary
def map_and_filter_facilities(facilities, mapping):
        mapped = []
        for facility in facilities:
            # Convert facility to lowercase and check if it exists in the mapping
            facility_lower = facility.lower()
            if facility_lower in mapping:
                mapped.append(mapping[facility_lower])
        return mapped

# Function to clean facilities string into a list
def clean_facilities(facilities_str):
        try:
            # Convert the string representation of list to an actual list
            facilities = ast.literal_eval(facilities_str)
            # Remove any "Unavailable" items
            cleaned_facilities = [item for item in facilities if not item.startswith('Unavailable')]
            return cleaned_facilities
        except ValueError:  # Handle ValueError specifically for NaN
            return []
        except Exception as e:
            print(f"Error processing: {facilities_str}, error: {e}")
            return []