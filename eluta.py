import json
import sys, os
from lxml import html
import lxml
import requests
import time
import re
import BeautifulSoup
import csv
from datetime import datetime, date
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from cStringIO import StringIO
import urllib
#from textblob import TextBlob

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = file(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return str

def days_since(d1):
    d1 = d1.encode('ascii', errors='ignore')
    d1 = d1.replace('Postedon ', '')
    d1 = datetime.strptime(d1, "%B%d,%Y")
    d2 = datetime.fromtimestamp(time.time())
    return abs((d2 - d1).days)

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
            cleaned = cleaned.replace('&#39;',"'")
            cleaned = cleaned.encode('ascii','ignore')
            results.append(cleaned)
        return results;
    else:
        cleaned = uni_content.replace(u'\u2019', "'")
        cleaned = cleaned.replace(u'\u2013', "-")
        cleaned = cleaned.replace(u'\xe9', "e")
        cleaned = cleaned.replace('&amp;','&')
        cleaned = cleaned.replace('&#039;',"'")
        cleaned = cleaned.replace('&nbsp;'," ")
        cleaned = cleaned.replace('&quot;','"')
        cleaned = cleaned.replace('&lsquo;',"'")
        cleaned = cleaned.replace('&rsquo;',"'")
        cleaned = cleaned.replace('&bull;','\n\t')
        cleaned = cleaned.encode('ascii','ignore')
        return cleaned;

def isFloat(string):
    try:
        float(string)
        return True
    except:
        return False

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


def to_s(string):
    tp = str(string)
    return tp.replace(" ", "");

def eluta_search_url(location, page_num):
    return "http://www.eluta.ca/search?q=radius%3A50+location%3A" + str(location) + "&pg=" + str(page_num);

def eluta_num_jobs(location):
    start_url = eluta_search_url(location, 1)
    headers = {'Accept-Encoding': None}
    try:
        page = requests.get(start_url, headers = headers, timeout=60)
    except:
        print 'Error: Cannot access url,', start_url
        return 0
    tree = html.fromstring(page.content)
    num_jobs = tree.xpath('//div[@id="job-count"]/text()')
    num_jobs = num_jobs[2]
    p = re.compile("([0-9]+)[+]?\s?$")
    return int(p.findall(num_jobs)[0]);

def eluta_html_list(location):
    num_limit = min(2000, eluta_num_jobs(location))
    if (num_limit == 0):
        return [];
    else:
        num_pages = num_limit/10 + 1
        results = []
        for i in xrange(1,num_pages):
            results.append(eluta_search_url(location, i))
        return results;

def eluta_page(page_url):
    # grabing all non-sponsored ads
    headers = {'Accept-Encoding': None}
    try:
        page = requests.get(page_url, headers = headers, verify=False, timeout=60)
    except:
        print 'Error: Cannot access url,', page_url
        return None
    tree = html.fromstring(page.content)
    results = tree.xpath("//div[@id='organic-jobs']/div")
    if (len(results) >= 1):
        results = results[0]
    else:
        print("error")
        results = None
    return results;

def eluta_article(article_html):
    job_titles = article_html.xpath("//span[@class='lk-job-title']/text()")
    t_t = time.strftime("%d/%m/%Y")
    locations = article_html.xpath("//span[@class='location']/text()")
    companies = article_html.xpath("//span[@class='employer lk-employer']/text()")
    onclicks = article_html.xpath("//span[@class='lk-job-title']/@onclick")
    updated_times = article_html.xpath("//span[@class='lk lastseen']/text()")
    p = re.compile("[0-9a-zA-Z]*\s*days?\s*[0-9a-zA-Z]*")
    results = list()
    for i in xrange(0,len(job_titles)-1):
        job_title = encode_cleanup(job_titles[i])
        location = encode_cleanup(locations[i])
        company = encode_cleanup(companies[i])
        onclick = encode_cleanup(onclicks[i])
        update_time = encode_cleanup(updated_times[i])
        url = "http://www.eluta.ca/" + onclick[9:-2]
        source = "Eluta"
        native_id = onclick[20:-2]
        if (p.match(update_time)):
            flag = 0
        else:
            flag = 1
        results.append({"job_title": job_title, "time": t_t, "location": location, "company": company, "source": source, "native_id": native_id, "url": url, "continue_flag": flag})
    return results;

def _to_int(strs):
    if (type(strs) is list):
        results = []
        for string in strs:
            results.append(int(string))
        return results;
    else:
        return int(strs);

def next_siblings(tag):
    l = []
    sib = tag.nextSibling
    while sib is not None:
        l.append(sib)
        sib = sib.nextSibling
    return l

def progressive_search_content(header):
    set1 = next_siblings(header)
    txt = get_text_from_list(set1)
    if (txt != ""):
        return txt.replace('"', '').replace(',', '')
    set2 = next_siblings(header.parent)
    txt = get_text_from_list(set2)
    if (txt != ""):
        return txt.replace('"', '').replace(',', '')
    set3 = next_siblings(header.parent.parent)
    txt = get_text_from_list(set3)
    
    return txt.encode('ascii',errors='ignore')

def total_length(list_of_text):
    return sum(len(x) for x in list_of_text);

def is_tag(data):
    try:
        data.text
        return True
    except:
        return False

def get_text_from_html(data):
    if is_tag(data):
        return data.text;
    else:
        return str(encode_cleanup(data));

def get_text_from_list(list_of_html):
    temp = " ".join(get_text_from_html(x) for x in list_of_html)
    temp2 = temp.replace(" ", "")
    temp2 = temp2.replace(".", "")
    if (len(temp2) < 50):
        return "";
    else:
        return temp;

def dedupe_dict_list(l):
    return [dict(t) for t in set([tuple(d.items()) for d in l])];

def general_full_desc_parser(parsed_data):
    # default parser for all other pages, used for all eluta sources
    # first determine if content type is html or pdf or else
    # lookup_strings = [parsed_data['job_title'], 'description']
    url = parsed_data['url']
    try:
        r = requests.get(url, timeout=60, verify=False)
    except:
        print 'Error opening url:', url
        return None
    # print(r.headers)
    if (r.headers['Content-Type'] == 'application/pdf'):
        # use pdf parser
        with open('/tmp/temp.pdf', 'wb') as f:
            f.write(r.content)
        text = convert_pdf_to_txt("/tmp/temp.pdf")
        text = (text[:7500] + '..') if len(text) > 7500 else text
        try: 
            text = text.encode('ascii','ignore')
        except:
            text = ''
            print 'Error in encoding text from PDF'
        parsed_data['description'] = text
        os.remove("/tmp/temp.pdf")
        return parsed_data

    else:
        soup = BeautifulSoup.BeautifulSoup(r.text)
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

def eluta_full_ids(location):
    pages = eluta_html_list(location)
    all_data = list()
    for page in pages:
        article = eluta_page(page)
        time.sleep(5)
        if (article is not None):
            data = eluta_article(article)
            # print(data)
            if len(data)== 0:
                print("empty page")
            elif (data[0]['continue_flag'] == 0):
                print("exceeded 1 day")
                break
            else:
                all_data = all_data + data
            print("page finished")
    return dedupe_dict_list(all_data);

def eluta_collection_module(path_to_bin):
    file_name = path_to_bin + "/el_result_" + time.strftime("%Y%m%d") + ".csv"
    provinces = ['AB'] #, 'ON', 'BC', 'MB', 'NB', 'NF', 'NT', 'NS', 'NU', 'PE', 'SK', 'YT']
    for province in provinces:
        full_list = eluta_full_ids(province)
        fieldnames = ["description", "url", "company", "source", "native_id", "location", "time", "job_title"]
        with open(file_name, 'ab') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames = fieldnames, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for item in full_list:
                del(item['continue_flag'])
                try:
                    result = new_parser(item) #general_full_desc_parser(item)
                except:
                    continue
                if result is not None:
                    writer.writerow(result)

def new_parser(parsed_data):
# default parser for all other pages, used for all eluta sources
    # first determine if content type is html or pdf or else
    # lookup_strings = [parsed_data['job_title'], 'description']
    url = parsed_data['url']
    try:
        r = requests.get(url, timeout=60, verify=False)
    except:
        print 'Error opening url:', url
        return None
    if (r.headers['Content-Type'] == 'application/pdf'):
        # use pdf parser
        with open('/tmp/temp.pdf', 'wb') as f:
            f.write(r.content)
        text = convert_pdf_to_txt("/tmp/temp.pdf")
        text = (text[:7500] + '..') if len(text) > 7500 else text
        try: 
            text = text.encode('ascii','ignore')
        except:
            text = ''
            print 'Error in encoding text from PDF'
        parsed_data['description'] = text
        os.remove("/tmp/temp.pdf")
        return parsed_data    
    else:
        soup = BeautifulSoup.BeautifulSoup(r.text)
        for elem in soup.findAll(['script', 'style']):
            elem.extract()
        result = []
        regex_str = re.compile(r'[a-z\s]*((description)|(summary)|(outline)|(detail)|(requirement)|(duty|i)|(qualifcation))[a-z\s]*', flags=re.IGNORECASE)
        # title_find = soup.find(text=re.compile('Legal secretary'), flags=re.IGNORECASE)
        # header_find = soup.body.findAll(text=re.compile('(description)|(summary)|(outline)', flags=re.IGNORECASE))
        article_find = soup.findAll("article")
        if len(article_find) > 0 :
            for article in article_find:
                if jd_check(article.text):
                    result.append(article.text)
            if len(result) > 0:
                return final_result(result, parsed_data)
        else:        
            p_found = soup.findAll('p')
            if len(p_found) > 0:
                for p in p_found:
                    if jd_check(p):
                        result.append(p.text)
        if len(result) == 0:
            regex_str = re.compile(r'[a-z\s]*((description)|(summary)|(outline)|(detail)|(requirement)|(duty|i)|(qualifcation))[a-z\s]*', flags=re.IGNORECASE)
            header_find = soup.findAll(re.compile("(h[1-5])", flags=re.IGNORECASE))
            for h in header_find:
                if regex_str.match(h.text):
                    result = find_sibling(h)
            
        return final_result(result,parsed_data)
        
def find_sibling(tag):
    result = []
    while tag.nextSibling is BeautifulSoup.Tag:
        r = tag.nextSibling.text
        if jd_check(r):
            result.append(r)
        tag = tag.nextSibling
    return result 

def jd_check(tag):
    MAGIC_WORDS = ['experience',
                   'require',
                   'work',
                   'position',
                   'client',
                   'training',
                   'development',
                   'candidate',
                   'part time',
                   'full time',
                   'manage',
                   'communicat',
                   'abilit',
                   'duties',
                   'report to']
    text = tag.text
    blob = TextBlob(text)
    regstr = '('+'|'.join(MAGIC_WORDS)+')'
    #criteria 1: don't contain many sibling tags
    if tag.nextSibling is not None:
        if tag.nextSibling.nextSibling is not None:
            #if tag.nextSibling.nextSibling.nextSibling is not None:
            return False
    #criteria 2: have enough words and sentences in the text
    if len(blob.words) < 20:    
        return False
    #criteria 3: contain magic words, the more the better
    elif len(re.findall(regstr,text)) == 0:
        return False
    return True

def final_result(result, parsed_data):
    text = '\n'.join(result)
    #print text
    #Could also add a further cleaning step to make sure words and punctuations are in right place
    parsed_data['description'] = encode_cleanup(text)
    return parsed_data

def test():
    #url = 'http://trr.tbe.taleo.net/trr01/ats/careers/requisition.jsp?org=CNRL&cws=1&rid=10484'
    url = 'http://www.eluta.ca/direct/p?i=b595f9ff997196fb3f578493d4ea9b5c' # cibc testing
    #url = 'http://www.eluta.ca/direct/p?i=8049a2e323204febb5894f5887149d03'
    #url = 'http://www.eluta.ca/direct/p?i=abc67abe42f7d4890c639257193e7f87'  #Alberta Health Service stuffed result, need to look into
    test_dict = {'url':url, 'description':''}
    test = general_full_desc_parser(test_dict)
    return 

def main():
    #test()
    eluta_collection_module("test")
    print 'Job done!'

if __name__ == '__main__':
    test()
    #main()


