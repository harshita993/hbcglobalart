import os
import sys
from bs4 import BeautifulSoup
import json
from lxml import html
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print(root_dir)
sys.path.append(root_dir)

retry_threshold = 3

class ProcessProjectDriver:

    def __init__(self, project_id):
        self.project_id = project_id

    def process_artist_page(self, artist_page, artist_additional_info):

        soup = BeautifulSoup(artist_page, 'html.parser')
        new_soup = html.fromstring(artist_page)
        try:
            artist_name = soup.find('div',class_="inner-wrap").find('h1').text.strip()
        except:
            artist_name = ''
            pass


        return {
            'name': artist_name,
            'first_name': '',
            'last_name': '',
            'avatar_web_url': '',
            'date_of_birth': None,
            'date_of_birth_string': '',
            'date_of_death': None,
            'date_of_death_string': '',
            'domiciled_in': '',
            'citizenship': '',
            'gender': '',
            'bio': '',
            'media_links': None,
            'ranking': -1,
            'additional_properties': []
        }

    def process_asset_page(self, scrape_asset_page, scrape_asset_additional_properties):
        collection_soup = BeautifulSoup(scrape_asset_page, "html.parser")



        try:
            div_tag = collection_soup.find('div', class_='col span_9')
            first_slide = collection_soup.find('div', class_='swiper-slide')
            if first_slide:
                image_bg = first_slide.find('div', class_='image-bg')
                style = image_bg.get('style', '')

                start = style.find('url(') + 4
                end = style.find(')', start)
                asset_image_url = style[start:end]

            elif div_tag:
                image_tag = div_tag.find('img')
                if image_tag and image_tag.get('src'):
                    asset_image_url = image_tag['src']
        except:
            asset_image_url = ''

            project_detail = collection_soup.find_all('div', class_='project-meta')
            for detail in project_detail:
                try:
                    title_element = detail.find('h4').text.strip().replace(" ", "_")
                    value_element = detail.find('p').text.strip()
                    if title_element== 'Location':
                        asset_location=value_element
                    elif title_element== 'Title':
                        asset_title=value_element
                    elif title_element== 'Type':
                        asset_type=value_element
                    elif title_element== 'Year':
                        asset_year=value_element
                    elif title_element== 'Medium':
                        asset_medium=value_element
                    elif title_element== 'Edition':
                        asset_edition=value_element
                    elif title_element== 'Dimension':
                        asset_dimension=value_element
                    elif title_element== 'Copyright':
                        asset_copyright=value_element
                except:
                    pass


        return {
            'description': '',
            'medium': asset_medium,
            'method_of_publication': '',
            'published_date': asset_year,
            'published_date_string': '',
            'style': '',
            'subject': asset_title,
            'created_date': None,
            'created_date_string': '',
            'created_location': '',
            'copyright_information': asset_copyright,
            'provenance': '',
            'edition': asset_edition,
            'credit_line': '',
            'restrictions': '',
            'price_range': '',
            'note': '',
            'tags': '',
            'title': '',
            'website_image_url': asset_image_url,
            'type_name': asset_type,
            'metadata_dimension': asset_dimension,
            'metadata_location': asset_location,
            'metadata_exhibition_history': '',
            'metadata_condition': '',
            'metadata_authentication': '',
            'metadata_explicit_content': False,
            'additional_properties': None,
            'seller_name': '',
            'total_product_count': 0,
            'avg_product_price': '',
            'scraped_asset_pdf_s3_original': None
        }


