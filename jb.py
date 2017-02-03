import json
import sys, os
from lxml import html
import lxml
import requests
import time
import re
from BeautifulSoup import BeautifulSoup
import csv
from datetime import datetime, date
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from cStringIO import StringIO

def days_since(d1):
    d1 = d1.encode('ascii', errors='ignore')
    d1 = d1.replace('Postedon ', '')
    d1 = datetime.strptime(d1, "%B%d,%Y")
    d2 = datetime.fromtimestamp(time.time())
    return abs((d2 - d1).days)

def prov_num_translate(province):
    # return Job Bank code for each Canadian province
    if (province == 'ON'):
        return 35
    elif (province == "AB"):
        return 48
    elif (province == "BC"):
        return 59
    elif (province == "MB"):
        return 46
    elif (province == "NB"):
        return 13
    elif (province == "NF"):
        return 10
    elif (province == "NT"):
        return 61
    elif (province == "NS"):
        return 12
    elif (province == "NU"):
        return 62
    elif (province == "PE"):
        return 11
    elif (province == "QC"):
        return 24
    elif (province == "SK"):
        return 47
    elif (province == "YT"):
        return 60;

def encode_cleanup(uni_content):
    if (type(uni_content) is list):
        limit = len(uni_content)
        results = []
        for i in xrange(1, limit):
            content = uni_content[i-1]
            cleaned = content.replace(u'\u2019', "'")
            cleaned = cleaned.replace(u'\u2013', "-")
            cleaned = cleaned.replace(u'\xe9', "e")
            cleaned = cleaned.replace('&amp;','&')
            cleaned = cleaned.replace('&#039;',"'")
            cleaned = cleaned.encode('ascii','ignore')
            results.append(cleaned)
        return results;
    else:
        cleaned = uni_content.replace(u'\u2019', "'")
        cleaned = cleaned.replace(u'\u2013', "-")
        cleaned = cleaned.replace(u'\xe9', "e")
        cleaned = cleaned.replace('&amp;','&')
        cleaned = cleaned.replace('&#039;',"'")
        cleaned = cleaned.encode('ascii','ignore')
        return cleaned;

def job_bank_start(location_num):
    return "http://www.jobbank.gc.ca/job_search_results.do?page=1&action=s0&sort=M&id=10&d=50&fprov=" + str(location_num) + "&wid=bf&lang=en&fage=2";

def job_bank_html(location_num, page_num):
    return "http://www.jobbank.gc.ca/job_search_results.do?page=" + str(page_num) + "&d=50&fprov=" + str(location_num) + "&sort=D&action=s0&fage=2&lang=en&sid=20";

def num_results_found_jb(location):
    url = job_bank_start(prov_num_translate(location))
    try:
        page = requests.get(url,timeout=60)
    except:
        print 'Error in accessing url:', url
        return 0
    tree = html.fromstring(page.content)
    # print(page.text)
    results_found = tree.xpath("//span[@class='found']/text()")
    print(results_found)
    # if (results_found is list):
    results_found = results_found[0].replace(",", "")
    # else:
        # results_found = results_found.replace(",", "")
    return int(results_found);

def job_bank_html_list(location):
    num_limit = num_results_found_jb(location)
    if (num_limit == 0):
        return list();
    else:
        num_pages = num_limit/25 + 1
        results = list()
        location_num = prov_num_translate(location)
        for i in xrange(1,num_pages):
            results.append(job_bank_html(location_num, i))
        return results;

def isFloat(string):
    try:
        float(string)
        return True
    except:
        return False

def job_bank_page(page_url):
    try:
        page = requests.get(page_url, verify=False, timeout=60)
    except:
        print 'Error in opening url:', page_url
        return None
    tree = html.fromstring(page.content)
    results = tree.xpath("//article")
    if (len(results) >= 1):
        results = results[0]
    else:
        print("error")
        results = None
    return results;

# tt = job_bank_page("http://www.jobbank.gc.ca/job_search_results.do?action=s3&sort=D&sid=10&d=50&fprov=48&searchstring=Canada&lang=en")

def to_s(string):
    tp = str(string)
    return tp.replace(" ", "");

def full_url_from_ids_and_source(post_id, source):
    if (source == 'Job Bank'):
        return "http://www.jobbank.gc.ca/jobposting.do?lang=en&button.submit=Search&sort=M&source=searchresults&id=" + to_s(post_id);
    elif (source == "Monster"):
        return "http://jobview.monster.ca/v2/job/View?JobID=" + to_s(post_id);
    elif (source == 'Workopolis'):
        return "http://www.workopolis.com/jobsearch/job/" + to_s(post_id);
    elif (source == 'jobs.gc.ca'):
        post_id = re.sub(r'[A-Za-z]', '', post_id)
        return "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page1000?poster=" + to_s(post_id) + "&toggleLanguage=en";
    elif (source == 'Canada Post'):
        return "HTTPS://CPC.NJOYN.COM/CGI/XWEB/XWEB.ASP?CLID=23060&PAGE=JOBDETAILS&JOBID=" + to_s(post_id) + "&BRID=510055&SBDID=977";
    elif (source == 'workBC'):
        return "https://www.workbc.ca/Jobs-Careers/Find-Jobs/Jobs/Job-Posting.aspx?jobid=" + to_s(post_id);
    elif (source == 'SaskJobs'):
        return "http://www.saskjobs.ca/jsp/joborder/detail.jsp?job_order_id=" + to_s(post_id);

def parse_job_bank_full_description(url):
    try:
        page = requests.get(url, timeout=60)
    except:
        print 'Error in accessing url:', url
        return ''
    tree = html.fromstring(page.content)
    if (tree is not None):
        desc = tree.xpath('//div[@class="job-posting-detail-requirements"]/p//text()')
    else:
        print("Job Bank url problem")
    result = '. '.join(str(encode_cleanup(x)) for x in desc)
    return encode_cleanup(result)

def parse_monster_full_description(url):
    try:
        page = requests.get(url, timeout=60)
    except:
        print 'Error in accessing url:', url
        return ''
    soup = BeautifulSoup(page.text, "lxml")
    # print(soup)
    result = []
    for tt in soup.select('article'):
        result.append(encode_cleanup(tt.get_text()))
    for tt in soup.select('div#JobSummary'):
        result.append(encode_cleanup(tt.get_text()))
    result = ". ".join(str(x) for x in result)
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in result.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = ' . '.join(chunk for chunk in chunks if chunk)
    return text;


def parse_workopolis_full_description(url):
    try:
        page = requests.get(url, timeout=60)
    except:
        print 'Error in accessing url:', url
        return ''
    result = list()
    tree = html.fromstring(page.content)
    if (tree is not None):
        result = tree.xpath("//main/section/section/descendant::*/text()")
        text = ' . '.join(encode_cleanup(chunk) for chunk in result if chunk)
    else:
        print("Workopolis url problem")
    return text;

def parse_workBC_full_description(url):
    # grab the duties section, and you are done
    try:
        page = requests.get(url, timeout=60, verify=False)
    except:
        print 'Error in accessing url:', url
        return ''
    result = list()
    tree = html.fromstring(page.content)
    if (tree is not None):
        result = tree.xpath("//main//div[@id='job-detail-page']/descendant::*/text()")
        text = ' . '.join(encode_cleanup(chunk) for chunk in result if chunk)
    else:
        print("workBC url problem")
    return text;

# parse_workBC_full_description(full_url_from_ids_and_source(338658, "workBC"))

def parse_canada_post_full_description(url):
    headers = {'Accept-Encoding': None}
    try:
        page = requests.get(url, timeout=60, headers = headers, verify = False)
    except:
        print 'Error in accessing url:', url
        return ''
    tree = html.fromstring(page.content)
    if (tree is not None):
        result = tree.xpath("//div[@id='njoynPageContainer']/div/descendant::*/text()")
        text = ' . '.join(encode_cleanup(chunk) for chunk in result if chunk)
    else:
        print("Canada Post url problem")
    return text;

# parse_canada_post_full_description(full_url_from_ids_and_source("J1216-0842", "Canada Post"))

def parse_canada_govt_full_description(url):
    headers = {'Accept-Encoding': None}
    try:
        page = requests.get(url, timeout=60, headers = headers)
    except:
        print 'Error in accessing url:', url
        return ''
    tree = html.fromstring(page.content)
    if (tree is not None):
        desc = tree.xpath('string(//main/div/h2[text()="Duties"]/following-sibling::p)')
    else:
        print("Canada Govt url problem")
    return encode_cleanup(desc);

def parse_saskjobs_full_description(url):
    headers = {'Accept-Encoding': None}
    try:
        page = requests.get(url, timeout=60, headers = headers)
    except:
        print 'Error in accessing url:', url
        return ''
    tree = html.fromstring(page.content)
    if (tree is not None):
        result = tree.xpath('//div[@class="jobDescAndSkill"]/descendant::*/text()')
        text = ' . '.join(encode_cleanup(chunk) for chunk in result if chunk)
    else:
        print("Saskjob url problem")
    return text;

def general_full_desc_parser(parsed_data):
    # default parser for all other pages, used for all eluta sources
    # first determine if content type is html or pdf or else
    # lookup_strings = [parsed_data['job_title'], 'description']
    url = parsed_data['url']
    try:
        r = requests.get(url, timeout=60, verify=False)
    except:
        print 'Error opening url:', url
        return ''
    # print(r.headers)
    if (r.headers['Content-Type'] == 'application/pdf'):
        # use pdf parser
        with open('/tmp/temp.pdf', 'wb') as f:
            f.write(r.content)
        text = convert_pdf_to_txt("/tmp/temp.pdf")
        text = (text[:7500] + '..') if len(text) > 7500 else text
        try: 
            text = text.encode('ascii','replace')
        except:
            text = ''
            print 'Error in encoding text from PDF'
        # print(text)
        parsed_data['description'] = text
        os.remove("/tmp/temp.pdf")
        return parsed_data
        # except:
        #     parsed_data['description'] = ""
        #     os.remove("/tmp/temp.pdf")
        #     return parsed_data
    else:
        # page = requests.get(url, headers = headers)
        soup = BeautifulSoup(r.text)
        for elem in soup.findAll(['script', 'style']):
            elem.extract()
        result = []
        regex_str = re.compile(r'[a-z\s]*((description)|(summary)|(outline)|(detail)|(requirement)|(duty|i)|(qualifcation))[a-z\s]*', flags=re.IGNORECASE)
        # title_find = soup.find(text=re.compile('Legal secretary'), flags=re.IGNORECASE)
        # header_find = soup.body.findAll(text=re.compile('(description)|(summary)|(outline)', flags=re.IGNORECASE))
        article_find = soup.findAll("article") ########################################   exception 
        if (len(article_find) == 0):
            header_find = soup.body.findAll(re.compile("(h[1-5])", flags=re.IGNORECASE))
            # print(header_find)
            for h in header_find:
                if (total_length(result) > 750):
                    break
                if regex_str.match(h.text):
                    result.append(progressive_search_content(h))
        else:
            for article in article_find:
                result.append(article.text)
        text = ' . '.join(encode_cleanup(chunk) for chunk in result if chunk)
        if (type(text) is str):
            text = (text[:7500] + '..') if len(text) > 7500 else text
            parsed_data['description'] = text
            return parsed_data;
        else:
            parsed_data['description'] = ''
            return parsed_data;

def job_bank_article(article_html):
    continue_flag = 1
    job_titles = encode_cleanup(article_html.xpath("//h3[@class='title']//span[@class='noctitle']//text()"))
    t_t = time.strftime("%d/%m/%Y")
    posted_dates = article_html.xpath("//span[@class='date']/text()")
    flags = list()
    for date in posted_dates:
        if (days_since(posted_dates[0]) > 1):
            flags.append(0)
        else:
            flags.append(1)
    locations = encode_cleanup(article_html.xpath('//span[@class="location"]/text()'))
    companies = encode_cleanup(article_html.xpath('//span[@class="business"]/text()'))
    # need to cleanup the 'by ' part
    salaries = article_html.xpath('//span[@class="salary"]/text()')
    # need to replace 'not available' with 0
    sources = article_html.xpath("//img/@alt")
    native_ids = article_html.xpath("//span[@class='source']/text()")
    urls = article_html.xpath("//a[@class='resultJobItem']/@href")
    temp_urls = article_html.xpath('//a[@class="resultJobItem"]/@href')
    results = list()
    for i in xrange(0, len(job_titles)-1):
        job_title = job_titles[i]
        continue_flag = flags[i]
        location = locations[i].replace("Location ", "")
        company = companies[i].replace("by ", "")
        s = salaries[i]
        native_id = native_ids[i]
        if (s == 'Not available'):
            salary = -999
        else:
            salary = wage_extraction(salaries[i])
        source = sources[i]
        if (source == "Job Bank"):
            url = "http://www.jobbank.gc.ca/" + urls[i]
        elif (source == 'SaskJobs'):
            temp_url = temp_urls[i]
            temp_url = 'http://www.jobbank.gc.ca/' + temp_url
            try:
                tp = requests.get(temp_url, timeout=60)
            except:
                print 'Error - Bad url requests:', temp_url
                return []
            tree = html.fromstring(tp.content)
            if (tree is not None):
                url = tree.xpath('//a[@id="externalJobLink"]/@href')[0]
            else:
                print("Saskjob url problem")
                url = temp_url
        elif (source == 'jobs.gc.ca'):
            temp_url = temp_urls[i]
            try:
                tp = requests.get(temp_url, timeout=60)
            except:
                print 'Error: bad url request.'
                continue
            tree = html.fromstring(tp.content)
            if (tree is not None):
                url = tree.xpath('//a[@id="externalJobLink"]/@href')[0]
            else:
                print("Canada govt url problem")
                url = temp_url
        else:
            url = full_url_from_ids_and_source(native_id, source)
        # All non-monster jobs will be appended
        if (source != "Monster"):
            results.append({"job_title": job_title, "time": t_t, "location": location, "company": company, "salary": salary, "source": source, "native_id": native_id, "url": url, "continue_flag": continue_flag})
    return results;

def wage_extraction(string):
    string = string.replace("$", "Dollars") # this makes regex easier to read, slightly
    # hourly wage:
    # example: $200.00 to $300.00 per hourly
    # $200.00+ per hour
    #
    pattern1 = re.compile("[A-Za-z0-9\s\+\-\'\/*]*(Dollars\s?([0-9,]{1,4}([.][0-9]{2,3})?)\+?)\s?((to|-)\s?((Dollars)?\s?([0-9,]{1,4}([.][0-9]{2,3})?)))?([/]?[\s-]*(per)?\s?(hr|hour(ly)?|h))([A-Za-z0-9\s\+\-\'\/*]*)", re.IGNORECASE)
    test1 = pattern1.match(string)
    if (test1 is not None) and (isFloat(test1.group(2))) and (isFloat(test1.group(7))):
        return (float(test1.group(2)) + float(test1.group(7))) * 1040
    elif (test1 is not None) and (isFloat(test1.group(2))):
        return float(test1.group(2)) * 2080
    # hourly wage
    # 200.00$ to 300.00$ per hourly
    # 200.00$ per hourly
    #
    pattern2 = re.compile("[A-Za-z\s\+\-\'\/*]*(([0-9,]{1,4}([.][0-9]{2,3})?)\+?Dollars)\s?((to|-)\s?(\s?([0-9,]{1,4}([.][0-9]{2,3})?))(Dollars)?)?([/]?[\s-]*(per)?\s?(hr|hour(ly)?|h))([A-Za-z0-9\s\+\-\'\/*]*)", re.IGNORECASE)
    test2 = pattern2.match(string)
    if (test2 is not None) and (isFloat(test2.group(2))) and (isFloat(test2.group(7))):
        return (float(test2.group(2)) + float(test2.group(7))) * 1040
    elif (test2 is not None) and (isFloat(test2.group(2))):
        return float(test2.group(2)) * 2080
    #
    # annual wage
    # $40k-$50k per year
    # $40K per year
    pattern3 = re.compile("[A-Za-z\s\+\-\'\/*]*(Dollars\s?([0-9]{2,3})K?\+?\s?(to|\-)?\s?(Dollars)?([0-9]{2,3}?\s?)K[/+\s]?)([A-Za-z0-9\s\+\-\'\/*]*)", re.IGNORECASE)
    test3 = pattern3.match(string)
    if (test3 is not None) and (isFloat(test3.group(2))) and (isFloat(test3.group(4))):
        return (float(test3.group(2)) + float(test3.group(4))) * 500
    elif (test3 is not None) and (isFloat(test3.group(2))):
        return float(test3.group(2)) * 1000
    #
    # annual wage
    # 40-50k$ annually
    # 40k$ per year
    pattern4 = re.compile("[A-Za-z\s\+\-\'\/*]*(([0-9]{2,3})K?\+?(Dollars)?\s?\-?([0-9]{2,3}?\s?)K[/+\s]?Dollars)([A-Za-z0-9\s\+\-\'\/*]*)", re.IGNORECASE)
    test4 = pattern4.match(string)
    if (test4 is not None) and (isFloat(test4.group(2))) and (isFloat(test4.group(3))):
        return (float(test4.group(2)) + float(test4.group(3))) * 500
    elif (test4 is not None) and (isFloat(test4.group(2))):
        return float(test4.group(2)) * 1000
    #
    # annual wage
    # $40,000-50,000 per year
    # 40,000 per year
    pattern5 = re.compile("[A-Za-z\s\+\-\'\/*]*(Dollars)?\s?([0-9]{1,3}[,\s]?[0-9]{3}([.\s][0-9]{1,2})?)\+?(\s?(to|-)\s?(Dollars\s?)?([0-9]{1,3}[,\s]?[0-9]{3}([.\s][0-9]{1,2})?))?([A-Za-z\s\+\-\'\/*]*)", re.IGNORECASE)
    test5 = pattern5.match(string)
    if (test5 is not None) and (test5.group(2) is not None) and (test5.group(7) is not None):
        group1 = test5.group(2).replace(",", "").replace(" ", "")
        group2 = test5.group(7).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2))/2
        elif (isFloat(group1)):
            return float(group1)
    #
    # annual wage
    # string = "40,000$ to 50,000$ annually"
    # string = "40 000 per year"
    #
    pattern6 = re.compile("[A-Za-z\s\+\-\'\/*]*([0-9]{1,3}[,\s]?[0-9]{3}([.\s][0-9]{1,2})?)\s?(Dollars)?\+?(\s?(to|-)\s?([0-9]{1,3}[,\s]?[0-9]{3}([.\s][0-9]{1,2})?))?(\s?Dollars)?([A-Za-z\s\+\-\'\/*]*)", re.IGNORECASE)
    test6 = pattern6.match(string)
    if (test6 is not None) and (test6.group(1) is not None) and (test6.group(6) is not None):
        group1 = test6.group(1).replace(",", "").replace(" ", "")
        group2 = test6.group(6).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2))/2
        elif (isFloat(group1)):
            return float(group1)
    #
    # weekly wage
    # $300.00+ per week
    # $300.00 to $400.00 per week
    #
    pattern7 = re.compile("[A-Za-z\s\+\-\'\/*]*(Dollars)?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2,3})?)\+?(\s?(\-|to)\s?(Dollars)?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2,3})?))?\s?(per week|weekly|wk|week)[A-Za-z0-9\s\+\-\'\/*]*", re.IGNORECASE)
    test7 = pattern7.match(string)
    if (test7 is not None) and (test7.group(2) is not None) and (test7.group(9) is not None):
        group1 = test7.group(2).replace(",", "").replace(" ", "")
        group2 = test7.group(9).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2)) * 26
        elif (isFloat(group1)):
            return float(group1) * 52
    #
    # monthly wage
    # 3000.00$ to 4000.00 per month
    # 4000 monthly
    pattern8 = re.compile("([A-Za-z\+\-\'\/*]*\s)*(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?)\s?(Dollars)?\+?(\s?(\-|to)\s?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?)Dollars)[/\s+]?(per)?\s?(monthly|mth|month)[A-Za-z0-9\s\+\-\'\/*]*", re.IGNORECASE)
    test8 = pattern8.match(string)
    if (test8 is not None) and (test8.group(2) is not None) and (test8.group(9) is not None):
        group1 = test8.group(2).replace(",", "").replace(" ", "")
        group2 = test8.group(9).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2)) * 6
        elif (isFloat(group1)):
            return float(group1) * 12
    #
    # monthly wage
    # $3000 monthly
    # $3,000 to 8,000 monthly
    pattern9 = re.compile("[A-Za-z\s\+\-\'\/]*(Dollars)?\s?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?)\+?(\s?(\-|to)\s?(Dollars)?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?))[/\s+]?(per)?\s?(monthly|mth|month)[A-Za-z0-9\s\+\-\'\/*]*", re.IGNORECASE)
    test9 = pattern9.match(string)
    if (test9 is not None) and (test9.group(2) is not None) and (test9.group(9) is not None):
        group1 = test9.group(2).replace(",", "").replace(" ", "")
        group2 = test9.group(9).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2)) * 6
        elif (isFloat(group1)):
            return float(group1) * 12
    #
    # biweekly wage
    # $2000 bi-weekly
    # $2000 to $3000 bi-weekly
    pattern10 = re.compile("[A-Za-z\s\+\-\'\/*]*(Dollars)?\s?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?)\+?(\s?(to|\-)\s?)(Dollars)?\s?(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?)?[/+\s]?Bi[-]?(weekly|week|wk)[A-Za-z0-9\s\+\-\'\/*]*", re.IGNORECASE)
    test10 = pattern10.match(string)
    if (test10 is not None) and (test10.group(2) is not None) and (test10.group(9) is not None):
        group1 = test10.group(2).replace(",", "").replace(" ", "")
        group2 = test10.group(9).replace(",", "").replace(" ", "")
        if (isFloat(group1)) and (isFloat(group2)):
            return (float(group1) + float(group2)) * 6
        elif (isFloat(group1)):
            return float(group1) * 12
    # pattern11 = re.compile("[A-Za-z\s\+\-\'\/*]*([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?\s?Dollars[\-\s]*(([0-9]{1,2})?[,]?([0-9]{3})([.][0-9]{2})?\s?Dollars)?[/+\s]?Bi[-]?(weekly|week|wk)[A-Za-z0-9\s\+\-\'\/*]*", re.IGNORECASE)
    # Default if nothing worked
    return -999

def job_bank_article_full_desc(parsed_data):
    # take parsed data so far, find the source, get full description
    try:
        text = ''
        result = list()
        if (parsed_data['source'] == 'Job Bank'):
            text = parse_job_bank_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'Monster'):
            #text = parse_monster_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'Workopolis'):
            #text = parse_workopolis_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'jobs.gc.ca'):
            #text = parse_canada_govt_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'Canada Post'):
            #text = parse_canada_post_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'workBC'):
            #text = parse_workBC_full_description(parsed_data['url'])
        #elif (parsed_data['source'] == 'SaskJobs'):
            #text = parse_saskjobs_full_description(parsed_data['url'])
        #if (text == ''):
            #text = general_full_desc_parser(parsed_data)
        else:
            return None
        if (type(text) is str):
            text = (text[:7500] + '..') if len(text) > 7500 else text
            parsed_data['description'] = text.encode('ascii', 'ignore')
            return parsed_data;
        else:
            #parsed_data['description'] = ''
            return None
    except:
        print("error while processing url " + parsed_data['url'])
        parsed_data['description'] = ''
        return parsed_data

def dedupe_dict_list(l):
    return [dict(t) for t in set([tuple(d.items()) for d in l])];

def job_bank_full_ids(location):
    # location_num = prov_num_translate(location)
    pages = job_bank_html_list(location)
    all_data = list()
    for page in pages:
        # print(page)
        article = job_bank_page(page)
        time.sleep(5)
        if (article is not None):
            data = job_bank_article(article)
            if len(data) == 0:
                print("empty page")
            elif (data[0]['continue_flag'] == 0):
                print("exceeded 1 day")
                break
            else:
                all_data = all_data + data
            print("page finished")
    return dedupe_dict_list(all_data);

def job_bank_collection_module(path_to_bin):
    # iterate over all provinces
    # execute the search, scrap, and collate
    # this should happen once every day
    provinces = ['AB', 'ON', 'BC', 'MB', 'NB', 'NF', 'NT', 'NS', 'NU', 'PE', 'SK', 'YT']
    file_name = path_to_bin + "/jb-result_" + time.strftime("%Y-%m-%d") + ".csv"
    with open(file_name,'ab') as csvfile:
        fieldnames = ['job_title','company','location','time','url','description','native_id','source','salary']
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for province in provinces:
            full_list = job_bank_full_ids(province)
            #["salary", "description", "native_id", "location", "source", "url", "company", "time", "job_title"]
            for item in full_list:
                del(item['continue_flag'])
                try:
                    result = job_bank_article_full_desc(item)
                except:
                    pass
                if result is not None:
                    writer.writerow(result)

def main():
    job_bank_collection_module("test")
    print 'Job done!'

if __name__ == '__main__':
    main()