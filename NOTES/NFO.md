# wikiSpyder

Advanced Wikipedia Search Tool

# ABOUT wikiSpyder

The goal of this app/utility is to assist users, researchers and investigators of any kind, as well as students, journalists, or anyone who likes to use Wikipedia while searching for information. 
What it will do is scrape the REFERENCES section posted last in most Wikipedia search result pages. After which wikiSpyder can be deployed to crawl the URLs (websites) or the list of links that were scraped from the REFERENCE sections.
While on the hunt, it will search for user provided search terms, keep a tally of how many times the search terms was found on the landing page of each link, notify the user of which page each search terms was found, and list how many times a search terms was found per visited URL.

It can speed up the search process considerably for working professionals or anyone who may know precisely what information they are looking for if the information (search terms) is linked or appears on the landing page of the targeted URLs.
From there the user can peruse an filtered manifest of links with search terms in the URLs. Beneath the results a tally with the count of how many times a search terms(s) was found per link along with the tallied search term and the correlated link.
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


# Future renditions

If successful or if wikiSpyder becomes likeable or valuable, I'll extend it's range to other sources of info such as social networks.

i.e..:
    mySpyder
    xSpyder
    fSpyder
    InstaSpyder
    spotiSpyder
    and so on...and so forth.


# How wikiSpyder works

    - wikiSpyder uses RegEx and Beautiful Soup to perform most of it's tasks. The rest is provided by PyQt in order to make it look good and add a little sizzle to the application. 


# Gifts

If you'd like to buy me a cup of coffee that would be very kind of you.

Donations are accepted here:    PAYPAL  |   If you'd like to remain TOTALLY anonymous it's completely UNDERSTOOD by me. Such proceeds are accepted here:  BITCOIN WALLET

If you would like to see additional features added or have a suggestion, you can send me a note: score+@bookmotives.com


# How Spiders Work

Spiders, crawlers, scrapers, copiers, and most search agents have roughly the same foundations. Usually the initial spawn of their capabilities can be traced back to RegEx, a suite of tools and symbols used to create regular expressions (an introductory math tool)which are useful when creating search patterns. As far as traversal and movement, the spider merely visits the webpage much like a browser and copies (reads, as well, or merely streams) the DOM of the landing page. RegEx comes into play as the spider decides where to visit next based on what's LINKED in the DOM. Back at the launch site, regular expressions are employed again to find what if any which was desired if it's within the pages that were visited. RegEx is exemplary when pursuing strings, but the theory can be applied to any object which includes practically any file found in almost any accessible computer system.

An object, its realm and what it is within the sphere of a computer system is what you might get from this passage/essay/sales attempt. Everything...which connects or is accessible by the microprocessor of your machine is indeed interpreted as an file or an object. A few bits and an address somewhere in memory it has access to (which is not always RAM) and where to push those bits next is all a microprocessor does. It does this at a rate which would be considered astronomical back in 89 when I was still a teen and jokes like that were good. Today, and for you, it's wise to spend some time on that. Remember, the speed at which a microprocessor operates is what gives it such capabiltiy.

    What I mean:
    - A file is an object.
    - A connected device is also an object/file (not just printers and cameras, the keyboard, the monitor, the MMU and Cache RAM which is internal to the machine, the acutal RAM as well as ROM in some systems and the BIOS, the motherboard it resides on...EVERYTHING IT HAS ACCESS TO OR COMMUNICATES WITH)
    - The YouTube video and the screen you watch it on, via smartphone or TV, are actually individual objects in the real physical world they exist in, which is the memory of that particluar device you pervey such.
    - EVERYTHI8NG WIHIN THE OS OR COMPUTER SYSTEM YOU USE IS AN OBJECT. OR, FILE. EVERYTHING!!
    
# The Difference Between Spiders

All spiders are similar in the sense that they all crawl websites and that the main job is to report what they find. The real difference is the scope and focus each spider has.

    - Scrapers are usually focused on particular types of media (objects, files) like audio and video, sometimes both, as well as photo images. Their scope is well defined usually, only a handful of sites are normally visited, and one, maybe two or three types     of media are ever in focus.
    - The Copiers goal is to grab everything available from the site so to replicate or clone the targeted site.
    - Spiders can do what all the others do although storing data is far less important than finding it. Such is somewhat counterintuitive to the nature of a spider so as a crawler they're more acceptable.
    - Search agents are usually spiders in whole. They operate on a planetary scale and their scope is trained on the entire expanse of the World Wide Web.
    - All in all, the differences in functionality are negligible since any of them can easily be re-engineered to perform the other's task. However, depending on the assigned task the number of resources required can be astronomical.
