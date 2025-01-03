import time
import random
import undetected_chromedriver as uc
import os
import sys
import json
from lxml import html
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests


root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.append(root_dir)

from scraping_virtual_machine_utils.GeneralScraper import GeneralScraper
from scraping_virtual_machine_utils.ScrapeEnum import ProjectType, ProjectInitialOrModify, ProjectStatus
from scraping_virtual_machine_utils.ScrapeProject import check_if_start_scraping_project, \
    complete_scraping_all_assets, complete_scraping_all_artists
from scraping_virtual_machine_utils.ScrapeArtist import save_scrape_artist_link, \
    save_scrape_artist_page_for_link, save_scrape_artist_asset_links
from scraping_virtual_machine_utils.ScrapeAsset import get_all_scrape_assets_no_page_weblinks_paginated, \
    save_scraped_asset_page_for_link

retry_threshold = 3
chunk_size = 50

PROJECT_CONFIG = {
    'project_name': 'HBC Global Art Collection',
    'website_link': 'https://hbcglobalartcollection.com/',
    'script_version': 0,
    'project_type': ProjectType.SEEDING.value,
    'initial_or_modify': ProjectInitialOrModify.INITIAL.value
}
fake_artist_total_count = 100

class HBCGlobalArt(GeneralScraper):

    def __init__(self):
        super().__init__(**PROJECT_CONFIG)
        self.driver = uc.Chrome()

    def randomSleep(self, start_time=5, end_time=10):
        time.sleep(random.randint(start_time, end_time))

    def chunk_list(self,data_list, chunk_size):
        for i in range(0, len(data_list), chunk_size):
            yield data_list[i:i + chunk_size]

    
    def start_scraping(self):
        project_id, project_status, _, _ = check_if_start_scraping_project(self.project_name,
                                                                           self.website_link,
                                                                           self.project_type,
                                                                           self.initial_or_modify,
                                                                           self.script_version,
                                                                           self.logger)

        self.project_id = project_id

       
        if (project_status == ProjectStatus.CREATED.value
                or project_status == ProjectStatus.ARTIST_SCRAPING.value
                or project_status == ProjectStatus.ALL_SCRAPING.value):
            self.logger.info("scraping all artists")
            self.scrape_all_artists()
            complete_scraping_all_artists(self.project_id)
            self.scrape_all_assets()
            complete_scraping_all_assets(self.project_id)
        elif project_status == ProjectStatus.ASSET_SCRAPING.value:
            self.logger.info("scraping all assets because all artists are already scraped")
            self.scrape_all_assets()
            complete_scraping_all_assets(self.project_id)
        else:
            print('Project Status:', project_status, 'No action required, stopping scraping process')
    
    def scrape_all_artists(self):
        soup=BeautifulSoup(self.driver.page_source,'html.parser')
        all_artist_urls = []
        for link in soup.find_all('a', href=True):
            if 'artist' in link['href']:
                all_artist_urls.append(link)

        
        for artist_url in all_artist_urls:
           
            save_status, message, artist_id, is_page_scraped, is_asset_scraped = save_scrape_artist_link(
                self.project_id, artist_url)

            if not save_status:
                self.logger.error(f"Failed to save scraped artist link with message: {message}")
                time.sleep(5)
                continue
            self.logger.info(f"Now handling artist: {artist_url}")
            # Extract information of artist information
            if not is_page_scraped:
                self.extract_artist_page(artist_id, artist_url)
            else:
                self.logger.info(f"Artist {artist_url} page already scraped, skipping...")

            if not is_asset_scraped:
                self.loop_artist_assets(artist_id, artist_url)
            else:
                self.logger.info(f"Artist {artist_url} assets already scraped, skipping...")




    def extract_artist_page(self, _artist_id, _artist_url, retry: int = retry_threshold):
        if retry == 0:
            self.logger.error(f"Failed to extract artist page for {_artist_url} after {retry_threshold} retries")
            return
        check_data = False
        try:
            self.driver.get(_artist_url)
            self.randomSleep()
            html_page = self.driver.page_source
            soup = BeautifulSoup(html_page, 'html.parser')
            new_soup = html.fromstring(html_page)
            try:
                artist_name_tag = soup.find('h1').text
                title = artist_name_tag
                check_data = True
            except:
                pass

            if not check_data:
                self.logger.error(f"Not getting any data from HTML in validation")
                return self.extract_artist_page(_artist_id, _artist_url, retry - 1)
            save_status, message, _ = \
                save_scrape_artist_page_for_link(self.project_id, _artist_id, _artist_url, html_page,
                                                 self.initial_or_modify, artist_page_file_extension="html")
            if not save_status:
                self.logger.error(f"Failed to save scraped artist page for link {_artist_url} with message: {message}")
                time.sleep(5)
                return self.extract_artist_page(_artist_id, _artist_url, retry - 1)

        except Exception as err:
            self.logger.error(f"!!! Fetch Artist URL Error, retrying remaining {retry} times, error: {str(err)}")
            return self.extract_artist_page(_artist_id, _artist_url, retry - 1)

    def loop_artist_assets(
            self,
            _artist_id: str,
            artist_url: str,
            retry: int = retry_threshold
        ):
        if retry == 0:
            return
        try:
            collection_urls = []
            self.driver.get(artist_url)
            artist_soup=BeautifulSoup(self.driver.page_source, 'html.parser')
            collection_elements = artist_soup.find_all('article', class_='result')

            for collection in collection_elements:
                collection_link = collection.find('a')
                if collection_link:
                    collection_url = collection_link.get('href')
                    collection_urls.append(collection_url)

            for chunk in self.chunk_list(collection_urls, chunk_size):
                save_status, message = save_scrape_artist_asset_links(self.project_id, _artist_id, chunk)
                if not save_status:
                    self.logger.error(
                        f"Failed to save scraped artist asset links for artist {artist_url} with message: {message}")
                    time.sleep(5)
                    return self.loop_artist_assets(_artist_id, artist_url, retry - 1)

        except Exception as err:
            self.logger.error(f"!!! Fetch Asset URL Error, retrying remaining {retry} times, error: {str(err)}")
            return self.loop_artist_assets(_artist_id, artist_url, retry - 1)


    def scrape_all_assets(self):
        scraped_assets = 0
        page, page_size = 1, 30

        status, message, id_links, total_assets, total_pages, current_page, has_next, has_previous = get_all_scrape_assets_no_page_weblinks_paginated(
            self.project_id, page=page, page_size=page_size)

        self.logger.info(f"Total Assets: {total_assets}")

        if not status:
            self.logger.error(f"Failed to get all scrape assets weblinks with no page with message: {message}")
            return False

        while True:
            for idx, asset_id_link in enumerate(id_links):
                self.logger.info(f"Now handling asset: {asset_id_link['asset_web_link']}, {idx + 1}/{len(id_links)}")
                asset_id = asset_id_link['asset_id']
                asset_link = asset_id_link['asset_web_link']
                save_status = False
                # Retry logic for driver.get()
                max_retries = 3
                check_data = False
                for attempt in range(max_retries):
                    try:
                        self.driver.get(asset_link)
                        html_page = self.driver.page_source
                        collection_soup = BeautifulSoup(html_page, 'html.parser')
                        try:
                            div_tag = collection_soup.find("div", class_="col span_6 section-title no-date")
                            asset_name= div_tag.find('h1').text
                            check_data = True
                        except:
                            pass
                        try:
                            div_tag = collection_soup.find('div', class_='col span_9')
                            first_slide = collection_soup.find('div', class_='swiper-slide')

                            
                            if first_slide:
                                image_bg = first_slide.find('div', class_='image-bg')
                                style = image_bg.get('style', '')
                                
                                start = style.find('url(') + 4
                                end = style.find(')', start)
                                image_url = style[start:end]
                                
                            elif div_tag:
                                image_tag = div_tag.find('img')
                                if image_tag and image_tag.get('src'):
                                    image_url = image_tag['src']
                                    

                            check_data = True
                        except:
                            pass

                        if not check_data:
                            self.logger.warning(
                                f"Not getting from HTML in validation on attempt {attempt + 1} for asset link: {asset_link}")
                            if attempt < max_retries:
                                time.sleep(5)  # Wait before retrying
                                continue
                            else:
                                self.logger.error(
                                    f"Failed to load asset link after {max_retries} attempts: {asset_link}")
                                break
                        save_status, message = save_scraped_asset_page_for_link(self.project_id,
                                                                                asset_id,
                                                                                asset_link,
                                                                                html_page,
                                                                                self.initial_or_modify,
                                                                                asset_page_file_extension="html")
                        break  # Exit retry loop if successful
                    except:
                        self.logger.warning(f"Timeout error on attempt {attempt + 1} for asset link: {asset_link}")
                        if attempt < max_retries:
                            time.sleep(5)  # Wait before retrying
                        else:
                            self.logger.error(f"Failed to load asset link after {max_retries} attempts: {asset_link}")
                        pass

                if not save_status:
                    self.logger.error(
                        f"Failed to save scraped asset page for link {asset_link} with message: {message}")
                    time.sleep(5)
                    continue
                scraped_assets += 1
            if has_next:
                status, message, id_links, total_assets, total_pages, current_page, has_next, has_previous = get_all_scrape_assets_no_page_weblinks_paginated(
                    self.project_id, page=current_page, page_size=page_size)
                if not status:
                    self.logger.error(f"Failed to get all scrape assets weblinks with no page with message: {message}")
                    return False
            else:
                self.logger.info(
                    f"All pages has been scraped. scraped_assets: {scraped_assets}, total_asset_db: {total_assets}")
                break
        return True


if __name__ == '__main__':
    scraper = HBCGlobalArt()
    scraper.start_scraping()
