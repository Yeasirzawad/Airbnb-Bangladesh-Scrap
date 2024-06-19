import pandas as pd
import numpy as np

import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


from selenium.webdriver.common.action_chains import ActionChains


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from notebooks.helper import result_count_maker
from notebooks.helper import load_json


def scrape_review(url):
    driver = webdriver.Chrome()
    driver.maximize_window()
    try:
        driver.get(url)
        time.sleep(3)  
        
        review_data = []
        
        reviews = driver.find_elements(By.XPATH, "//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div")
        
        for i, review in enumerate(reviews, start=1):
            review_dict = {
                'review_link': url,
                'reviewer_name': None,
                'reviewer_profile_link': None,
                'info': None,
                'rating_comment': None,
                'rating_extra': None
            }
            
            try:
                reviewer_name_tag = review.find_element(By.XPATH, f"//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div[{i}]/div/section/div/div/h2")
                reviewer_name = reviewer_name_tag.text if reviewer_name_tag else 'None'
                review_dict['reviewer_name'] = reviewer_name
            except Exception as e:
                print("User name not fetched", e)
                
            try:
                rating_extra_tag = review.find_element(By.XPATH, f"//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div[{i}]/div/section/div/div/div")
                rating_extra = rating_extra_tag.text if rating_extra_tag else 'None'
                review_dict['rating_extra'] = rating_extra
            except Exception as e:
                print("No extra rating")
                
            try:
                profile_link_elem = driver.find_element(By.XPATH, f"//a[@aria-label='{review_dict['reviewer_name']}']")
                review_dict['reviewer_profile_link'] = profile_link_elem.get_attribute('href')
            except:
                print('Reviewer profile link not found')
                
            try:
                parent_div = review.find_element(By.XPATH, './/div[@class="s78n3tv atm_c8_1w0928g atm_g3_1dd5bz5 atm_cs_9dzvea atm_9s_1txwivl atm_h_1h6ojuz dir dir-ltr"]')
                full_text = parent_div.get_attribute('textContent').strip()
                info_text = full_text.split('\n')[-1].strip()
                review_dict['info'] = info_text
            except:
                print("Review time not fetched")
                
            try:
                rating_comment_tag = review.find_element(By.XPATH, f"(.//div[@class='r1bctolv atm_c8_1sjzizj atm_g3_1dgusqm atm_26_lfmit2_13uojos atm_5j_1y44olf_13uojos atm_l8_1s2714j_13uojos dir dir-ltr']/div/span/span)")
                rating_comment = rating_comment_tag.text if rating_comment_tag else 'N/A'
                review_dict['rating_comment'] = rating_comment
            except Exception as e:
                print("Rating comment not fetched", e)
                
            review_data.append(review_dict)

        driver.quit()
        return review_data

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        driver.quit()
        return []

def scrape_reviews_for_listings(listing_links):
    all_reviews = []
    for url in listing_links:
        reviews = scrape_review(url)
        all_reviews.extend(reviews)
    return pd.DataFrame(all_reviews)

def scrap_airbnb_listing(location_list,xpath_filename):
    
    main_link = "https://www.airbnb.com/s/"

    xpaths = load_json(xpath_filename)
    
   
    
    total_dict = []

    for location in location_list:

        driver = webdriver.Chrome()
        driver.maximize_window()
        
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


def scrap_host(host_links:pd.Series,xpath_filename:str,start):

    xpaths = load_json(xpath_filename)
   
    total_host = []
    driver = webdriver.Chrome()
    driver.maximize_window()
    j = start
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


def scrape_review(url):
    driver = webdriver.Chrome()
    driver.maximize_window()
    try:
       
        driver.get(url)
        time.sleep(3)  
        
     
        review_data = []

        
        reviews = driver.find_elements(By.XPATH, "//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div")
        
        for i, review in enumerate(reviews, start=1):
            review_dict = {
                'review_link': url,
                'reviewer_name': None,
                'reviewer_profile_link':None,
                'info': None,
                'rating_comment': None,
                'rating_extra': None
            }
            
            
            try:
                reviewer_name_tag = review.find_element(By.XPATH, f"//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div[{i}]/div/section/div/div/h2")
                reviewer_name = reviewer_name_tag.text if reviewer_name_tag else 'None'
                review_dict['reviewer_name'] = reviewer_name
            except Exception as e:
                print("User name not fetched", e)

            
            
            try:
                rating_extra_tag = review.find_element(By.XPATH, f"//div[@data-testid='pdp-reviews-modal-scrollable-panel']/div[{i}]/div/section/div/div/div")
                rating_extra = rating_extra_tag.text if rating_extra_tag else 'None'
                review_dict['rating_extra'] = rating_extra
            except Exception as e:
                print("No extra rating")


            try:
                 profile_link_elem = driver.find_element(By.XPATH,f"//a[@aria-label='{review_dict['reviewer_name']}']")
                                                                                  
                 review_dict['reviewer_profile_link'] = profile_link_elem.get_attribute('href')
            except:
                 print('reviewer profile link not found')
            
            try:
                  
                    parent_div = review.find_element(By.XPATH, './/div[@class="s78n3tv atm_c8_1w0928g atm_g3_1dd5bz5 atm_cs_9dzvea atm_9s_1txwivl atm_h_1h6ojuz dir dir-ltr"]')
                   
                    full_text = parent_div.get_attribute('textContent').strip()
                    
                    info_text = full_text.split('\n')[-1].strip()

                    review_dict['info'] = info_text

            except:
                    print("review_time not fetched")

            try:
                rating_comment_tag = review.find_element(By.XPATH, f"(.//div[@class='r1bctolv atm_c8_1sjzizj atm_g3_1dgusqm atm_26_lfmit2_13uojos atm_5j_1y44olf_13uojos atm_l8_1s2714j_13uojos dir dir-ltr']/div/span/span)")
                rating_comment = rating_comment_tag.text if rating_comment_tag else 'N/A'
                review_dict['rating_comment'] = rating_comment
            except Exception as e:
                print("Rating comment not fetched", e)

            # Append the extracted data to the review_data list
            review_data.append(review_dict)

        driver.quit()
        return review_data

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        driver.quit()
        return []
    

def airbnb_data_scrap(listing_links,locations,xpath_filename):
    total_dict = []
    xpaths_dict = load_json(xpath_filename)
   
    driver = webdriver.Chrome()
    driver.maximize_window()


<<<<<<< HEAD
    j = start
=======
>>>>>>> 2da9140d206d786962b84ba550f8ebf5f6e1c696
    for listing,location in zip(listing_links,locations):
        dict_ = {

            "listing_link":listing,
            "searched_location":location,
            "title_bed_bats_review":None,
            "price_per_night":None,
            "review_count":None,
            "review_count_link":None,
            "host_link":None,
            "host_response_rate":None,
            "listing_description":None,
            "cleanliness_ratings": None,
            "accuracy_ratings":None,
            "check-in_ratings":None,
            "communication_ratings":None,
            "location_ratings":None,
            "value_ratings":None,
            "google_map_location_link":None

        }

        try:
            driver.get(listing)
            time.sleep(2)
            
            try:
                modal_close_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Close"]'))  # Adjust the XPath as needed
                )
                modal_close_button.click()
                print("Modal closed")
            except:
                print("No modal found")

            time.sleep(2)

            try:
                title_bed_bats_review = driver.find_element('xpath',xpaths_dict['title_bed_bats_review'])
                title_bed_bats_review = title_bed_bats_review.get_attribute('content')
                
                dict_["title_bed_bats_review"] = title_bed_bats_review
            except:
                print("no Meta")
                
            try:
                span_elements = driver.find_elements(By.CLASS_NAME, '_1y74zjx')

            
                k = 0
                for span in span_elements:
                    if k == 1:
                        dict_['price_per_night'] = span.text
                    k += 1

            except:
                print("Price Not Found")
            
            try:
                review_count_element = driver.find_element("xpath",xpaths_dict['review_count_xpath'])
                review_count = review_count_element.text
                review_count_link = review_count_element.get_attribute('href')
                dict_['review_count'] = review_count
                dict_['review_count_link'] = review_count_link
            except:

                print("review count not found")

            try:
                host_link_element = driver.find_element('xpath',xpaths_dict['host_link_Xpath'])
                host_link = host_link_element.get_attribute('href')
                dict_['host_link'] = host_link
            except:
                print("host not found")

            try:
                host_response_rate = driver.find_element('xpath',xpaths_dict["response_rate_Xpath"])
                dict_['host_response_rate'] = host_response_rate.text
            except:
                print("host response rate not found")
        

            for i in range(1,7):
                try:
                    ind_ratings = driver.find_element('xpath',f"({xpaths_dict['ind_rev_xpath']})[{i}]")
                    if i == 1:
                        dict_['cleanliness_ratings'] = ind_ratings.text
                    elif i == 2:
                        dict_['accuracy_ratings'] = ind_ratings.text
                    elif i == 3 :
                        dict_['check-in_ratings'] = ind_ratings.text
                    elif i == 4 :
                        dict_['communication_ratings'] = ind_ratings.text
                    elif i == 5 :
                        dict_['location_ratings'] = ind_ratings.text
                    elif i == 6 :
                        dict_['value_ratings'] = ind_ratings.text
            
            
                except:
                    pass
                

            
            element = WebDriverWait(driver, 10).until(        
            EC.presence_of_element_located((By.XPATH, "//div[@class='_1ctob5m']"))
            )
            
            try:
                # Scroll to the element slowly
                actions = ActionChains(driver)
                actions.move_to_element(element).perform()
                time.sleep(3)
            except:
                print("not able to scroll")
            # Wait for 3 seconds
            
            
            try:
                google_map_location = driver.find_element('xpath',xpaths_dict['lat-lon-link'])
                google_map_location_link = google_map_location.get_attribute('href')
                
                dict_['google_map_location_link'] = google_map_location_link
            
            except:
                print("no google map link")

            
            element2 = WebDriverWait(driver, 10).until(        
            EC.presence_of_element_located((By.XPATH,xpaths_dict['facilities_button_xpath']))
            )
            
            try:
                # Scroll to the element slowly
                actions = ActionChains(driver)
                actions.move_to_element(element2).perform()
                time.sleep(2)
            except:
                print("not able to scroll up")
            
            facilities_list = []
            try:
                show_all_facilities = driver.find_element('xpath',xpaths_dict['facilities_button_xpath'])
                show_all_facilities.click()
                for i in range(1,100):
                    try:
                        facility = driver.find_element('xpath',f"({xpaths_dict['facilities_xpath']})[{i}]")
                        facilities_list.append(facility.text)
                    except:
                        break
                
                dict_["facilities"] = facilities_list

                try:
                    modal_close_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Close"]'))  # Adjust the XPath as needed
                    )
                    modal_close_button.click()
                    print("facilities closed")
                except:
                    print("facilities not closed sorry")
            except:
                print("facilities not found")
            
            
            try:       
                button_element = driver.find_element(By.XPATH,xpaths_dict['description_show_all_Xpath'])
                button_element.click()
                time.sleep(1)
                description_section_element = driver.find_element(By.XPATH, xpaths_dict['description_xpath'])
                description_text = description_section_element.text
                
                dict_['listing_description'] = description_text
                time.sleep(1)

                    

            except:

                try:
                    description2_section_element = driver.find_element('xpath',xpaths_dict['description2_xpath'])
                    dict_['listing_description'] = description2_section_element.text
                except:
                    print("show all description button not found")

            total_dict.append(dict_)
        except:
            pass

        if j%5 == 0:
            df = pd.DataFrame(total_dict)
            df.to_csv(f"../data/csvs_2/airbnb_{j}.csv",index=False)
            total_dict = []
<<<<<<< HEAD
        j+=1
        
        
    

        
=======
        j+=1
>>>>>>> 2da9140d206d786962b84ba550f8ebf5f6e1c696
