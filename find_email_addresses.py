from selenium import webdriver
import requests
import re
import sys

def crawl(domain):
    #Domains can have thousands of pages. this allows the script to spit out what
    #emails it currently has after a variable number of page requests in
    #lieu of waiting a tremoundously long time to crawl the entire domain.
    PAGESUNTILPROMPT= 20

    #In general an url to access a web page will look this:http://domain[path]
    #I have decided to not include sub-domains and websites that are outside the current domain
    #This pattern will help distinguish between relative and absolute urls
    urlPattern = r"https?://.*"+ domain
    urlRegex = re.compile(urlPattern)

    httpPattern = r"https?://"
    httpRegex = re.compile(httpPattern)

    #an email address is formated as local@domain.
    #99 percent of the time the local part is comprised of digits and letters
    #and a couple of special characters
    #for the domain, it is constricted to the standard domain format.
    #The domain format is a collection of letters and digits and hypens seperated by dots
    #The root domain name is at least 2 characters as there are no root domains with less than 2 characters.
    emailAddressPattern = r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"
    emailRegex = re.compile(emailAddressPattern)

    #when crawling through the web, we do not want to cycle through urls.
    #so we remember where we have been by storing pages in a set
    visitedUrls = set()
    nextUrls = set()

    #we treat urls starting with http or https as different
    homeUrl = "http://"+domain
    nextUrls.add(homeUrl)
    visitedUrls.add(homeUrl)

    homeUrl = "https://"+domain
    nextUrls.add(homeUrl)
    visitedUrls.add(homeUrl)

    #want unique email addresses only
    emailAddresses = set()

    try:
        #if you would like a visual of the web crawler doing its job and firefox is installed,
        #uncomment the line below and comment out the phantomjs line
        #browser = webdriver.Firefox()
        browser = webdriver.PhantomJS()
    except:
        print "Error creating browser environment."
        return emailAddresses

    #to avoid fancy css rules that hide content based on the size of a window
    browser.maximize_window()

    #Here I took a BFS approach when navigating links
    pagesVisited = 0
    while len(nextUrls) > 0:
        #this allows me to remove urls while traversing
        copyUrls = list(nextUrls)
        for url in copyUrls:
            nextUrls.remove(url)
            emailAddresses.update(helperCrawl(url,nextUrls,visitedUrls,urlRegex,httpRegex,emailRegex,browser))
            pagesVisited+=1
            if pagesVisited == PAGESUNTILPROMPT:
                pagesVisited =0
                print "Not done yet. Here are all the email addresses I have found so far:"
                print "\n".join(emailAddresses)
    return emailAddresses

def helperCrawl(url,nextUrls,visitedUrls,urlRegex,httpRegex,emailRegex,browser):
    emailAddresses = set()

    try:
        response = requests.get(url)
    except:
        return emailAddresses

    #only visit pages with success status code
    if response.status_code != 200:
        return emailAddresses

    currentUrl= response.url

    #we add the url again just in case of a potential redirect
    visitedUrls.add(currentUrl)

    browser.get(currentUrl)
    content = browser.page_source

    newEmails = collectEmailAddresses(content,emailRegex)
    emailAddresses.update(newEmails)

    links =[]
    #there is a potential exception when parsing html
    try:
        links = [tag.get_attribute('href') for tag in browser.find_elements_by_tag_name("a")]
    except:
        return emailAddresses

    for link in links:
        #want to avoid empty links and links leading with '#'(which lead to the same page)
        if link == None or len(link) == 0 or link[0] == '#':
            continue

        #here we combine url and links together
        #depending on the format of a link
        linkedUrl = None

         #absolute url(within domain):replace current url
        if httpRegex.match(link):
            if urlRegex.match(link):
                linkedUrl = link

        #relative url:add after last '/' in current url
        elif link[0] != '/' and link[0]!='.':
            insertPoint = currentUrl.rfind('/')
            linkedUrl= currentUrl[:insertPoint+1] + link

         #relative url(like '/' or '../'):add to current url
        else:
            lastIndex = len(currentUrl) -1

            #if current url has trailing '/', remove it by ignoring it.
            if currentUrl[lastIndex] == '/':
                linkedUrl = currentUrl[:lastIndex]+link
            else:
                linkedUrl = currentUrl + link

        if linkedUrl != None:
            httpMatch = httpRegex.match(linkedUrl)
            nonHttpPortion = linkedUrl[httpMatch.end():]
            if nonHttpPortion not in visitedUrls:
                nextUrls.add("http://"+ nonHttpPortion)
                visitedUrls.add("http://"+ nonHttpPortion)
                nextUrls.add("https://"+ nonHttpPortion)
                visitedUrls.add("https://"+ nonHttpPortion)

    return emailAddresses

#use the email regular expression to find all email addresses on a web page
def collectEmailAddresses(content,emailRegex):
    emailAddresses = emailRegex.findall(content)
    return emailAddresses

domain = sys.argv[1]
emailAddresses = crawl(domain)

print "I'm done. Here are all the email addresses I found:"
print "\n".join(emailAddresses)
