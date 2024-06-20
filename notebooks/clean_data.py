import pandas as pd
import numpy as np
import os
import re



import pandas as pd
import numpy as np
import re
from helper import convert_to_months, extract_lat_lng, get_base_url, remove_unavailable

mapping = {
    "hdtv": "tv",
    "stove": "stove",
    "wifi": "wifi",
    "disney+": "disney+",
    "amazon prime video": "amazon prime video",
    "netflix": "netflix",
    "hbo max": "hbo max",
    "apple tv": "apple tv",
    "soap": "soap",
    "shampoo": "shampoo",
    "conditioner": "conditioner",
    "view": "has view",
    "oven": "oven",
    "clothing storage": "clothing storage",
    "fireplace": "fireplace",
    "refrigerator": "refrigerator",
    "air conditioning": "air conditioning",
    "pool": "pool",
    "gym": "gym",
    "housekeeping": "housekeeping",
    "free parking": "free parking",
    "paid parking": "paid parking",
    "washer": "washer",
    "dryer": "dryer",
    "children’s books and toys": "children’s books and toys",
    "coffee maker": "coffee maker",
    "bbq grill": "bbq grill",
    "exercise equipment": "exercise equipment",
    "sound system": "sound system",
    "security cameras": "security cameras",
    "golf": "golf",
    "sauna": "sauna",
    "bathtub": "bathtub",
    "board games": "board games",
    "game console": "game console",
    "smoke alarm": "smoke alarm",
    "fire alarm": "fire alarm",
    "fire extinguisher": "fire extinguisher",
    "view":"view"
}

def clean_airbnb_(filename):

    df = pd.read_csv(f'./{filename}')
    df.reset_index(inplace=True)


    # Duplicate and clean 'title_bed_bats_review' column
    df['title_bed_bats_review_copy'] = df['title_bed_bats_review'].str.replace('·', ',').str.title()

    # Split the column by delimiter
    split_cols = df['title_bed_bats_review_copy'].str.split(',', expand=True)
    split_cols.columns = [f"title_bed_bats_review_copy.{i+1}" for i in range(split_cols.shape[1])]

    # Concatenate the split columns back to the dataframe
    df = pd.concat([df, split_cols], axis=1)

    # Rename columns
    df = df.rename(columns={
        "title_bed_bats_review_copy.2": "Bedroom",
        "title_bed_bats_review_copy.3": "Beds",
        "title_bed_bats_review_copy.4": "Baths"
    })

    # Process Bedroom and Ratings
    df['Bedroom'] = df['Bedroom'].str.replace('★', '')

    df['Bedroom_Main'] = df.apply(lambda x: x['Bedroom'] if 'Bed' in str(x['Bedroom']) else None, axis=1)
    df['Ratings'] = df.apply(lambda x: x['Bedroom'] if x['Bedroom_Main'] is None else None, axis=1)

    df['Main_Bedroom'] = df.apply(lambda x: x['Beds'] if x['Bedroom_Main'] is None else x['Bedroom_Main'], axis=1)

    # Process Beds and Baths
    df['Beds'] = df['Beds'].str.replace('Bedroom ', 'Bedrooms')
    df['Beds_main'] = df.apply(lambda x: x['Baths'] if 'Bedrooms' in str(x['Beds']) else x['Beds'], axis=1)

    df = df.drop(columns=['Bedroom', 'Bedroom_Main'])

    df['Main_Beds'] = df.apply(lambda x: x['Beds_main'] if 'Bath' not in str(x['Beds_main']) else None, axis=1)
    df = df.drop(columns=['Beds'])

    df['Bath_Main'] = df.apply(lambda x: x['Beds_main'] if pd.isnull(x['Baths']) else x['Baths'], axis=1)
    df['Main_Baths'] = df.apply(lambda x: x['Bath_Main'] if pd.isnull(x['title_bed_bats_review_copy.5']) else x['title_bed_bats_review_copy.5'], axis=1)

    df = df.drop(columns=['Beds_main', 'Baths', 'title_bed_bats_review_copy.5', 'Bath_Main'])

    # Clean up unwanted strings in columns
    replace_patterns = [
        ("Bedroom", ""), ("s", ""), ("Beds", ""), ("Bed", ""),
        ("Bath", ""), ("Private", ""), ("Shared", ""), ("Half", "1"),
        ("-", ""), ("Shared Bath", ""), ("Studio", "")
    ]

    for old, new in replace_patterns:
        df['Main_Bedroom'] = df['Main_Bedroom'].str.replace(old, new)
        df['Main_Beds'] = df['Main_Beds'].str.replace(old, new)
        df['Main_Baths'] = df['Main_Baths'].str.replace(old, new)

    # Rename columns
    df = df.rename(columns={"title_bed_bats_review_copy.1": "Title"})
    df.rename(columns={"Title": "listing_title",
                       "Ratings": "listing_rating",
                       "Main_Bedroom": "bedrooms",
                       "Main_Beds": "beds",
                       "Main_Baths": "baths"}, inplace=True)

    # Base URL extraction
    df['base_urls'] = df['listing_link'].apply(get_base_url)

    # Clean price_per_night column
    if 'price_per_night' in df.columns:
        df['price_per_night'] = df['price_per_night'].replace('[\$,]', '', regex=True).astype(float)

    # Clean host_response_rate column
    if 'host_response_rate' in df.columns:
        df['host_response_rate'] = df['host_response_rate'].str.split(":", expand=True)[1].str.replace("%", "").astype(float)

    # Clean review_count column
    if 'review_count' in df.columns:
        df['review_count'] = df['review_count'].str.extract('(\d+)')
        df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').fillna(0).astype(int)

    # Extract latitude and longitude
    if 'google_map_location_link' in df.columns:
        df[['latitude', 'longitude']] = df['google_map_location_link'].apply(lambda x: pd.Series(extract_lat_lng(x)))

   

    # Apply the function to the 'facilities' column
    df['facilities'] = df['facilities'].apply(remove_unavailable)
    unique_facilities_list = list(mapping.keys())
   
    for f in unique_facilities_list:
        df[f] = 0
        df.loc[df['facilities'].str.contains(f, case=False, na=False, regex=True),f] = 1
 
    unique_facilities_list.insert(0,'base_urls')
    unique_facilities_list.insert(1,'facilities')

    facilities_df = df[unique_facilities_list]
    
    # Process host_confirmed_information
    if 'host_confirmed_information' in df.columns:
        info_types = ['Identity', 'Email address', 'Phone number', 'Work email']
        for info in info_types:
            df[info] = df['host_confirmed_information'].apply(lambda x: info in x).astype(int)

    # Convert host_hosting_duration to months
    if 'host_hosting_duration' in df.columns:
        df['host_hosting_duration_months'] = df['host_hosting_duration'].apply(convert_to_months)

    df.drop(columns=['Unnamed: 0_x','index','searched_location','title_bed_bats_review','host_confirmed_information','google_map_location_link','host_hosting_duration','title_bed_bats_review_copy','Unnamed: 0_y'],inplace=True)

    return df[['listing_link','base_urls','listing_title', 'listing_rating', 'bedrooms', 'beds',
       'baths', 'latitude', 'longitude', 'price_per_night', 'review_count', 'review_count_link',
       'listing_description','host_link','cleanliness_ratings', 'accuracy_ratings', 'check-in_ratings',
       'communication_ratings', 'location_ratings', 'value_ratings', 'facilities',   
       'host_name', 'host_rating', 'host_response_rate',
       'host_no_of_review', 'Identity', 'Email address', 'Phone number', 'Work email', 'host_hosting_duration_months','host_no_of_listing', 'host_listing_links',
       'host_about',]],facilities_df
