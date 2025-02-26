# wikiSpyder

Advanced Wikipedia Search Tool

# ABOUT wikiSpyder

The goal of this app/utility is to assist users, researchers and investigators of any kind, as well as students, journalists, or anyone who likes to use Wikipedia while searching for information. 
What it will do is scrape the REFERENCES section posted last in most Wikipedia search result pages. After which wikiSpyder can be deployed to crawl the URLs (websites) or the list of links that were scraped from the REFERENCE sections.
While on the hunt, it will search for user provided search terms, keep a tally of how many times the search terms was found on the landing page of each link, notify the user of which page each search terms was found, and list how many times a search terms was found per visited URL.

It can speed up the search process considerably for working professionals or anyone who may know precisely what information they are looking for if the information (search terms) is linked or appears on the landing page of the targeted URLs.
From there the user can peruse an additional manifest of links annotated with a count of how many times each search terms(s) was found per link along with the tallied search term.
If you like, wikiSpyder will continue to crawl until you've narrowed down the site with the information you were looking for.

    - Sites where no search termss were found, or anomalies where the landing page is mostly video or audio presentations are marked as NULL. They can still be accessed manually for eyes-on investigations. Just click the highlighted link to explore with your browser.
    - wikiSpyder has a button which will release it to crawl recursively into each listed website if permitted or plausible, and as deep as the target will allow.
    - Additional sources (i.e.. URLs, web addresses) can be added/removed before and during deployments.
    - wikiSpyder can save all images automatically, if Save Images is checked.
    - For now, all data pulled by wikiSpyder which isn't saved is purged once the program is exited.

# Installation

    - wikiSpyder-1.0 works with Python 3.12 
    - re (RegEx module), pyQt, and other imported modules will be downloaded if not on the system upon first launch.
    - Use the Installer found in /INSTALLER if on Windows or python.exe -m setup.py if on Mac or Linux. setup.py can be found in the root of wikiSpyder.

# Gifts

If you'd like to buy me a cup of coffee that would be very kind of you.

Donations are accepted here: PAYPAL | If you'd like to remain TOTALLY anonymous it's completely UNDERSTOOD by me. Such proceeds are accepted here: BITCOIN WALLET

<img src="paypal.png" alt="paypal QR" width="200" height="200" style="margin-right: 10px;"> <img src="wallet.png" alt="Bitcoin wallet QR" width="200" height="200">

If you would like to see additional features added or have a suggestion, you can send me a note: score+@bookmotives.com