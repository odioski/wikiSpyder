import requests
import re

from bs4 import BeautifulSoup
# parse wikipedia page Reference sections

# Highly simplified with CoPilot, yet did need a bit of tailoring.

def get_external_links(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    external_links = []

    for ref in soup.find_all('span', class_='reference-text'):
        for link in ref.find_all('a', class_='external text', href=True):
            external_links.append(link['href'])

    return external_links

def get_images_from_link(link):
    try:
        response = requests.get(link)
        soup = BeautifulSoup(response.content, 'html.parser')

        images = []
        
        for img in soup.find_all('img', src=True):
            images.append(img['src'])

        return images
    
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {link}: {e}")
        return []

wikipedia_url = input("Enter a wikipedia search result...\n\n")
external_links = get_external_links(wikipedia_url)

print("External Links and Images:")

for link in external_links:
    print(f"Link: {link}")
    images = get_images_from_link(link)
    
    for img in images:
        real_img = re.compile(img)
        real_img = re.match(r'[\b.png]+[\b.jpg]+[\b.jpeg]+[\b.gif]+[\b.webp]', img)
        # just a tiny haircut, that's all ... so far.

        print(f"  Image: {real_img}")

