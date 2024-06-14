import pandas as pd
import numpy as np

import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from helper import result_count_maker
from helper import load_json

def scrap_airbnb_listing(location_list,xpath_filename):
    
    main_link = "https://www.airbnb.com/s/"

    xpaths = load_json(xpath_filename)
    
    driver = webdriver.Chrome()
    driver.maximize_window()
    
    total_dict = []

    for location in location_list:
        
        main_link = f"https://www.airbnb.com/s/{location}/homes"
        driver.get(main_link)
        time.sleep(2)
    
    
        for i in range(1,19):
            
            dict_ = {
                "location":location,
                "listing_link": None,

                }
            
            try:
                listing_link = driver.find_element('xpath',f"{xpaths['apartment_link_xpath']}[{i}]")
                dict_['listing_link'] = listing_link.get_attribute('href')
                total_dict.append(dict_)
            
            except:
                print("No more listings in ", location)
                break
            
            try:
                result_count_string = driver.find_element('xpath',xpaths['result_count_xpath']).text
                result_count = result_count_maker(result_count_string)
                print(result_count ," results in ", location)
            except:
                print("No results of ",location)
                continue
            
            page_count = result_count // 18
            
            if(page_count >= 15):
                page_count = 15

            while(page_count > 0):

            
                try:

                    next_page_link = driver.find_element('xpath',xpaths['next_page_xpath'])
                    print(next_page_link.get_attribute('href'))
                    
                    next_page_link.click()
                    time.sleep(2)
                    
                    for i in range(1,19):
            
                        dict_ = {
                            "location":location,
                            "listing_link": None,

                        }
                        
                        try:
                            listing_link = driver.find_element('xpath',f"{xpaths['apartment_link_xpath']}[{i}]")
                            dict_['listing_link'] = listing_link.get_attribute('href')
                            total_dict.append(dict_)
            
                        except:
                            print("No more listings in ", location)
                            break

                except:
                    print("no next")
                    break
                

                page_count = page_count - 1

    return pd.DataFrame(total_dict)


def scrap_host(host_links:pd.Series,xpath_filename:str):

    xpaths = load_json(xpath_filename)
   
    total_host = []
    driver = webdriver.Chrome()
    driver.maximize_window()
    j = 0
    k = 1

    for host_link in host_links:
        
        host_dict = {
            "host_link": host_link,
            "host_name": None,
            "host_rating": None,
            "host_no_of_review": None,
            "host_hosting_duration": None,
            "host_no_of_listing": None,
            "host_listing_links": None,
            "host_about": None,
            "host_confirmed_information": None,
        }

        print(f"Fetching link {k} :  ", host_link)
        try:
            driver.get(host_link)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            # Extract host name
            try:
                host_name_element = driver.find_element(By.XPATH, xpaths['host_name_xpath'])
                host_dict['host_name'] = host_name_element.text
            except:
                print(f"Host name not found")

            # Extract number of reviews and hosting duration
            try:
            
                span_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@class ='s1yopat4 atm_9s_1txwivl atm_ar_1bp4okc atm_cx_1lkvw50 atm_h_1y6m0gg atm_fc_1h6ojuz atm_cs_1fw03zg atm_c8_sz6sci atm_g3_17zsb9a atm_fr_kzfbxz dir dir-ltr']/span"))
                )

            
                for span in span_elements:
                    
                    try:
                        data_testid = span.get_attribute('data-testid')
                
                        if data_testid in [ 'Reviews-stat-heading' , 'Review-stat-heading' ]:
                            host_dict['host_no_of_review'] = span.text
                        elif data_testid in ['Years hosting-stat-heading','Year hosting-stat-heading' ,'Months hosting-stat-heading','Months hosting-stat-heading']:
                            duration = span.text + (" years" if "Year" in data_testid else " months")
                            host_dict['host_hosting_duration'] = duration
                    except:
                        pass
                
            except:
                print(f"Review count or hosting duration not found")
            
            # Extract host rating
            try:
                host_rating_element = driver.find_element(By.XPATH, xpaths['host_ratings_xpath'])
                host_dict['host_rating'] = host_rating_element.text
            except:
                print(f"Host rating not fetched")

            # Extract host listing links
            try:
                host_listing_links_elements = driver.find_elements(By.XPATH, xpaths['host_listing_link_xpath'])
                host_listing_links = [listing.get_attribute('href') for listing in host_listing_links_elements]
                host_dict['host_listing_links'] = host_listing_links
            except:
                print(f"Host listings not fetched")

            host_dict['host_no_of_listing'] = len(host_listing_links)
        
            # Extract host confirmed information
            try:
                host_confirmed_info_elements = driver.find_elements(By.XPATH, xpaths['host_confirmed_info_xpath'])
                host_confirmed_info_list = [elem.text for elem in host_confirmed_info_elements if elem.text]
                host_dict['host_confirmed_information'] = host_confirmed_info_list
            except:
                print(f"No more host confirmed info")

            total_host.append(host_dict)

            try:
            
                div_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='dbk58ns atm_9s_1txwivl atm_ar_1bp4okc atm_cx_1od0ugv dir dir-ltr']"))
                )
                
            
                child_elements = div_element.find_elements(By.XPATH, "./*")
                all_about = ""
            
                for child in child_elements:
                    text = child.text
                    if text: 
                        all_about += " " +  text

                host_dict['host_about'] = all_about
            except:
                print(f"about not found")

        except:
            print(f"Linked fetching failed")

        if j % 10 == 0:
            host_df = pd.DataFrame(total_host)
            host_df.to_csv(f'./host_csvs/airbnb_host_{j}.csv',index=False)
            total_host = []

        j += 1
        k += 1