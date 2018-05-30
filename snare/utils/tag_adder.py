from bs4 import BeautifulSoup
import os

def add_meta_tag(page_dir, index_page, config):
    google_content = config['WEB-TOOLS']['google']
    bing_content = config['WEB-TOOLS']['bing']

    if not google_content and not bing_content:
        return

    main_page_path = os.path.join('/opt/snare/pages/', page_dir, index_page)
    with open(main_page_path) as main:
        main_page = main.read()
    soup = BeautifulSoup(main_page, 'html.parser')

    if (google_content and soup.find("meta", attrs={"name": "google-site-verification"}) is None):
        google_meta = soup.new_tag('meta')
        google_meta.attrs['name'] = 'google-site-verification'
        google_meta.attrs['content'] = google_content
        soup.head.append(google_meta)
    if (bing_content and soup.find("meta", attrs={"name": "msvalidate.01"}) is None):
        bing_meta = soup.new_tag('meta')
        bing_meta.attrs['name'] = 'msvalidate.01'
        bing_meta.attrs['content'] = bing_content
        soup.head.append(bing_meta)

    html = soup.prettify("utf-8")
    with open(main_page_path, "wb") as file:
        file.write(html)
