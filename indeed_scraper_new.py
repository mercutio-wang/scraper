import urllib
import requests
import csv
import datetime 
import BeautifulSoup
import re
import json
import time
import random
import sys
import os
        
def get_indeed_url(cntry, query, location, start = 0, post_age = 1):
    base_URL = 'http://www.indeed.'+cntry+'/jobs?'

    #if query not empty add q= to the url string
    if query:
        base_URL = base_URL + 'q=' + query      

    #same deal with location3s
    if location: 
        base_URL = base_URL + '&l=' + location     

    base_URL = base_URL + '&fromage=' + str(post_age) + "&limit=100&start="+ str(start) + "&sort=date"

    return base_URL
        
def main(argv):
    if len(argv) > 1:
        if argv[1] == 'test':   #set constant value for testing
            Bsize = 20
            cntry = 'ca'
            province = 'SK'
            tgturl = 'http://www.indeed.ca/jobs?l=ON&fromage=1&limit=100&start=0&sort=date'
            job_parser(cntry,province,Bsize,0)
            #print get_saved_nids('indeed')
        elif argv[1] == 'run':
            post_num = 0
            start_time = time.time()
            
            #Read in queries from file
            qfile = open('indeed_queries.txt','r')
            queries = qfile.read().split('\n')
            qfile.close()
            
            for q in queries:
                if time.time()-start_time > 7000:
                    break
                parameters = q.split(',')
                if len(parameters) == 4:
                    post_num += job_parser(parameters[0],parameters[1],int(parameters[2]),int(parameters[3]))
                    
            print '\n------------Completed scraping Indeed jobs -------------'
            print '{} job posts acquired, total run time is {} seconds.'.format(post_num, time.time()-start_time)
        else:
            print 'Unidentified use of arguments. Please use argument "run" or "test"'
    else:
        print 'Wrong number of arguments. Please use argument "run" or "test"'
        sys.exit()
    

def job_parser(cntry, province, Bsize, post_age):
    neemo_request_url = 'https://www.neemo.ca/batch'
    headers = {"Content-Type":"application/json"}
    tgturl = get_indeed_url(cntry, '', province, 0, post_age)
    
    try:    
        code = urllib.urlopen(tgturl).read()
        soup = BeautifulSoup.BeautifulSoup(code)
        count = indeed_result_size(soup)
        print 'Total number of job posts today:', count, 'in', province
    except:
        print 'Cannot open url: ', tgturl
        return 0
    new_nids = indeed_full_nid(cntry, province, soup, count, post_age)
    nids = list(new_nids - get_saved_nids('indeed'))
    #nids = list(indeed_full_nid(cntry, province, soup, count, post_age))

    if len(nids) >0:
        batches = nid_split(nids, Bsize)
        fnum = 0
        for pbatch in batches:
            posts = []
            for i in pbatch:
                try:
                    indi_post =indeed_indi_post(cntry, i)
                except:
                    print 'Error: cannot parse post - {}'.format(i)
                if indi_post is not None:
                        posts.append(indi_post)
                time.sleep(random.random()*3)
       
            #REST post the posts into neemo server - NOT in use any more. 
            #if len(posts) > 0:
            #    response = requests.post(neemo_request_url, data=json.dumps(posts), headers=headers)
            

    else:
        print 'Warning: no posts found in ', province
    print len(nids), 'new job posts recorded\n'
    return len(nids)

def indeed_result_size(soup):
    count_tag = soup.find('div',{'id':'searchCount'})
    line = str(count_tag.contents)
    count = int(re.findall('of ([,0-9]*)',line)[0].replace(',',''))
    return count 

def get_nid(soup):
    rows = soup.findAll('div',{'class':'  row  result'})
    nids = []
    for result in rows:
        t = result.attrMap['data-jk']
        nids.append(str(t))
    return nids

def indeed_full_nid(cntry, loc, soup, count, post_age = 0):
    nids = get_nid(soup)
    if count > 100:
        maxpage = min(count/100 + 1, 10) #11 is the max pages that can be viewed on indeed. use 10 since already loaded 1st page
    
        for pindex in range(maxpage):
            # Read in new pages
            start = (pindex + 1) * 100
            url = get_indeed_url(cntry,'',loc, start, post_age)
            try:
                code = urllib.urlopen(url).read()
            except:
                print 'Cannot open url: ', url
                return set()
                
            try:
                soup = BeautifulSoup.BeautifulSoup(code)
                newnid = get_nid(soup)
            except:
                print 'Error in parsing out result on page: ', url
            nids.extend(newnid)

    return set(nids)

def nid_split(nids, size):
    for i in range(0, len(nids),size):
        yield nids[i : i + size]
 
def indeed_indi_post(cntry, nid):
    tgturl = 'http://www.indeed.' + cntry + '/viewjob?jk=' + nid   #test: http://www.indeed.ca/viewjob?jk=bcd7fd1249b04f68
    print 'Processing post url: ', tgturl
    try:
        sourcecode = urllib.urlopen(tgturl).read()
        sourcecode = re.sub('<br\s*?>', ' ', sourcecode)
        soup = BeautifulSoup.BeautifulSoup(sourcecode)
    except:
        print 'Error in opening url:', tgturl
        return None
    
    header = soup.find('div',{'data-tn-component':'jobHeader'})
    tag_title = header.find('b')
    tag_company = header.find('span',{'class':'company'}) # may contain recommend jobs, could consider scrape them as well
    tag_location = header.find('span',{'class':'location'}) # may contain recommend jobs
    
    job_title = str(encode_check(tag_title.text))
    company = str(encode_check(tag_company.text))
    location = str(encode_check(tag_location.text))
    post_time = str(datetime.date.today())

    body = soup.find('span',{'id':'job_summary','class':'summary'})
    if len(body.contents) == 0:
        sibling = body.nextSibling
        lines = []
        while len(sibling.contents) > 0 and type(sibling) is BeautifulSoup.Tag:
            lines.append(sibling.text)
            sibling = sibling.nextSibling
            if type(sibling) is BeautifulSoup.NavigableString:
                break
        content = str(encode_check('\n'.join(lines)))
    else:
        content = str(encode_check(body.text))   #tags are stripped, might have some issue with <br>
    #print str(encode_check(content))

    result = {'job_title':job_title, 'company':company, 'location':location, 'url':tgturl, 'time':post_time, 'description':content, 'native_id':nid}
    writecsv(result)
    
    #o = open('csv/indeed_job_result_' + str(datetime.date.today()) + '.csv','ab')
    #wr = csv.writer(o,quoting=csv.QUOTE_ALL)
    #wr.writerow(result.values())
    #o.close()
    
    return result

def get_saved_nids(source):
    today = datetime.date.today()
    flist = os.listdir('csv/')
    saved_nids = []
    #print flist
    for f in flist:
        felement = f.split('.')[0].split('_')
        if len(felement) > 1:
            fdate = felement[1]
            fsource = felement[0].split('-')[0]
            yesterday = today + datetime.timedelta(-1)
            if fsource == source:
                if fdate == str(today) or fdate == str(yesterday):
                    saved_nids.extend(readcsv(f))
                    #print 'Lenth: ', len(saved_nids)
    return set(saved_nids)

def readcsv(filename):
    nids = []
    with open('csv/'+filename,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            nids.append(row['native_id'])
    csvfile.close()
    return nids

def writecsv(result_dict):
    fieldnames = ['job_title','company','location','time','url','description','native_id']
    fname = 'indeed-job-result_' + str(datetime.date.today()) + '.csv'
    if fname not in os.listdir('csv/'):
        with open('csv/'+fname, 'wb') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(result_dict)
    else:
        with open('csv/'+fname, 'ab') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(result_dict)    
    csvfile.close()
    return

def encode_check(uni_content):
    cleaned = uni_content.replace(u'\u2019', "'")
    cleaned = cleaned.replace(u'\u2013', "-")
    cleaned = cleaned.replace(u'\xe9', "e")
    cleaned = cleaned.replace('&amp;','&')
    cleaned = cleaned.replace('&#039;',"'")
    cleaned = cleaned.encode('ascii','ignore')
    return cleaned

if __name__ == '__main__':
    main(sys.argv)