import requests
import re
# For spider

from bs4 import BeautifulSoup
# parse wikipedia page Reference sections

from urlextract import URLExtract
# initial link extraction


def start_app():

    global wiki_data

    wiki_page = input("Enter a Wikipedia search result URL... \n\n")

    spider = requests.get(wiki_page)

    wiki_data = spider.text    

def extract_urls():

    global urls

    soup = BeautifulSoup(wiki_data, 'html.parser')

    bowl = soup.find_all("a", class_="external text")

    spoon = soup.decode_contents(bowl)

    extractor = URLExtract()

#   There is much in a DOM, URLExtract filters everything leaving URL's...although, the practice would sharpen your RegEx skills.
    
    urls = extractor.find_urls(spoon)

# new_photos = ["NULL"]

# print(urls, "\n\n")   ... solved

# def scrape_photo_links():

#     for item in urls:

#         finds = re.match('[\W+\w+]+[\b.jpg]+', item)

#         if finds:

#             new_photos.append(finds)
        
#     print("\n\n")

#     new_photos.pop(0)
        
#     for item in new_photos:

#         print(item[0])

    
new_links = ['NULL']

def scrape_links():

    for item in urls:
            
        finds = re.match('[^pinnable.]+[^upload.]+[https://]+[\w+\W+]+[^.j]+[^.png]+[^.sv]+[^.svg]+', item)

        if finds:

            new_links.append(finds)

    print("\n\n")

    new_links.pop(0)
    
    for item in new_links:

        print(item[0])

    total_links = len(new_links)

    print("\n\n" + str(total_links) + " Links. ")

#  Need to write these to a file as well.


# # def print_urls():

#     print(".....................................................................................................\n"
#                 + ".....................................................................................................\n"
#                 + "....... The following are the links from the Reference section of your Wikipedia search result ......\n"
#                 + ".....................................................................................................\n"
#                 + ".....................................................................................................\n")
    
#     print(second_bowl)

#     print("........................................................................................\n"
#                 + "........................................................................................\n"
#                 + "..................... Found " + str(total_urls) + " links in References ....................................\n"
#                 + "........................................................................................\n"
#                 + "........................................................................................\n")
    

# def launch_spider():

#      for item in new_links:
          
#             spider = requests.get(item)

#             loaded_spider = spider.text

#             soup = BeautifulSoup(loaded_spider, 'html.parser')
            
#             bowl = re.compile(r"")

#             bowl = soup.find_all(["p", "li",  "div"])

#             print(str(bowl) + "\n\n")

#             for next_term in search_terms:

#                 term_search_pattern = re.compile(r'')

#                 found_terms = term_search_pattern.match(next_term, bowl)

start_app()

extract_urls()

# scrape_photo_links()

scrape_links()

# print_urls()

# launch_spider()


