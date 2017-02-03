import json
import sys, os
from lxml import html
import lxml
import requests
import time
import re
import BeautifulSoup
import csv
import codecs
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
    sources = article_html.xpath("//span[@class='domain']/text()")
    p = re.compile("[0-9a-zA-Z]*\s*days?\s*[0-9a-zA-Z]*")
    results = list()
    for i in xrange(0,len(job_titles)-1):
        job_title = encode_cleanup(job_titles[i])
        location = encode_cleanup(locations[i])
        company = encode_cleanup(companies[i])
        onclick = encode_cleanup(onclicks[i])
        update_time = encode_cleanup(updated_times[i])
        url = "http://www.eluta.ca/" + onclick[9:-2]
        source = sources[i]
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
    file_name = path_to_bin + "/el-result_" + time.strftime("%Y-%m-%d") + ".csv"
    provinces = ['ON' 'AB', 'BC', 'MB', 'NB', 'NF', 'NT', 'NS', 'NU', 'PE', 'SK', 'YT']
    for province in provinces:
        full_list = eluta_full_ids(province)
    
    with open(file_name, 'ab') as csvfile:
        fieldnames = ["html_file", "url", "company", "source", "native_id", "location", "time", "job_title"]
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for province in provinces:
            full_list = eluta_full_ids(province)
            for item in full_list:
                del(item['continue_flag'])
                result = item #general_full_desc_parser(item)
                result['html_file'] = encode_cleanup(get_html(result))
                if result is not None:
                    writer.writerow(result)
                    
def get_html(entry):
    url = entry['url']
    try:
        r = requests.get(url, timeout=30)
    except:
        print 'Error opening url:', url
        return ''
    fname = 'html/'+entry['native_id']+'.txt'
    with codecs.open(fname,'w', 'utf-8') as hfile:
        hfile.write(r.text)
    return fname

def desc_parser(parsed_data):
    url = parsed_data['url']
    try:
        r = requests.get(url, timeout=60)
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
        temp = r.text
        soup = BeautifulSoup.BeautifulSoup(temp)
        result = parsed_data
        if parsed_data['source'] == 'www.cibc.com':
            result['description'] = cibc_parser(soup)
        elif parsed_data['source'] == 'www.rbc.com':
            result['description'] = rbc_parser(soup)
        elif parsed_data['source'] == 'www.td.com':
            result['description'] = ''
        elif parsed_data['source'] == 'www.bmo.com':
            result['description'] = ''
        elif parsed_data['source'] == 'www.bell.ca':
            result['description'] = ''
        elif parsed_data['source'] == 'www.telus.com':
            result['description'] = ''
        elif parsed_data['source'] == 'www.rogers.com':
            result['description'] = ''
        elif parsed_data['source'] == 'www.shaw.ca':
            result['description'] = ''
        return result

def rbc_parser(soup):
    body = soup.findAll('span',{'itemprop':'description'})
    tag = body[0].nextSibling
    while tag is not None:
        if type(tag) is BeautifulSoup.Tag:
            print encode_cleanup(tag.text)
        tag = tag.nextSibling
    return

def cibc_parser(soup):
    t = soup.body.text
    body = soup.findAll('span',{'class':'text'})
    for i in body:
        test = encode_cleanup(i.text)
    
    return

def test():
    #url = 'http://www.eluta.ca/direct/p?i=b595f9ff997196fb3f578493d4ea9b5c' # cibc
    url = 'http://www.eluta.ca/direct/p?i=9ab9030f5d190d30c7cfb3667003ab18' # rbc
    #url = 'http://www.eluta.ca/direct/p?i=8049a2e323204febb5894f5887149d03'
    #url = 'http://www.eluta.ca/direct/p?i=abc67abe42f7d4890c639257193e7f87'  #Alberta Health Service stuffed result, need to look into
    test_dict = {'url':url, 'description':'','source':'www.rbc.com'}
    test = desc_parser(test_dict)
    return 

def main():
    #test()
    eluta_collection_module("test")
    print 'Job done!'

if __name__ == '__main__':
    main()


