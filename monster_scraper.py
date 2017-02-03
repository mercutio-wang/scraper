import urllib2
import json
import feedparser
import BeautifulSoup
import csv
import datetime
import os
import requests
import time
import random
import re

def monster_listing_url(cntry, per_page, page):
    base_URL = 'http://rss.jobsearch.monster.com/rssquery.ashx?rad_units=km&cy='+cntry.upper()
    
    if page:
        base_URL = base_URL + "&pg=" + str(page) 
    if per_page:
        base_URL = base_URL + "&pp=" + str(per_page)
    base_URL = base_URL + "&tm=0" 
    base_URL = base_URL + "&sort=dt.rv.di&baseurl=jobview.monster."

    if cntry == "ca":
        base_URL = base_URL + "ca"
    elif cntry=="us":
        base_URL = base_URL + "com"
    else:
        print 'Error: unexpected country code. Only US and CA are available right now'
        return None
    return base_URL

def Mparser(cntry, per_page, page, Bsize):
    neemo_request_url = 'https://www.neemo.ca/batch'
    headers = {"Content-Type":"application/json"}
    url = monster_listing_url(cntry,per_page, page)
    try:    
        mfeed = feedparser.parse(url)
    except:
        print 'Error: Cannot open feed -', url
        return None
    print mfeed.feed.title
    
    posts_meta = get_meta(mfeed.entries, cntry)
    posts_meta = dedup(posts_meta)
    print '----------Start scraping Monster posts----------'
    batches = batch_split(posts_meta, Bsize)
    
    for batch in batches:
        posts = []
        for meta in batch:
            result = monster_indi_result(meta)       
            if result is not None:
                if 'Location' in result.keys():
                    loc = result['Location']
                else:
                    loc = ''
                rest_results = {'job_title':result['Job title'],
                                'company':result['Company'],
                                'location':loc,
                                'url':meta['link'],
                                'time':result['Post date'],
                                'description':result['Job description'],
                                'native_id':meta['id']
                                         }
                posts.append(rest_results)
                write_csv(result, meta['id'],cntry)
            
            time.sleep(3+random.random()*3)
        #REST post the posts into neemo server
        if len(posts) > 0: 
            response = requests.post(neemo_request_url, data=json.dumps(posts), headers=headers)
        #if datetime.datetime.now().minute > 45:
        #    exit()

def dedup(metas):
    saved_ids = get_saved_nids('monster')
    result = []
    for p in metas:
        if p['id'] not in saved_ids:
            result.append(p)
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
            test = str(today)
            if fdate == str(today) and fsource == source:
                saved_nids = readcsv(f)
                break
    return set(saved_nids)

def readcsv(filename):
    nids = []
    with open('csv/'+filename,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            nids.append(row['Native ID'])
    csvfile.close()
    return nids


def write_csv(result_dict, nid,cntry = 'ca'):
    fieldnames = ['Job title',
                  'Company',
                  'Location',
                  'Industries',
                  'Job type',
                  'Job description',
                  'Salary',
                  'Career level',
                  'Education level',
                  'Post date',
                  'Posted',
                  'Reference code',
                  'Native ID']
    result_dict.update({'Native ID': nid})
    fname = 'monster-result-'+cntry+'_'+str(datetime.date.today())+'.csv'
    if fname not in os.listdir('csv/'):
        with open('csv/'+fname, 'wb') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(result_dict)
    else:
        with open('csv/'+fname, 'ab') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(result_dict)
    return

def batch_split(metas, size):
    for i in range(0, len(metas),size):
        yield metas[i : i + size]
        
def get_meta(entries, cntry):
    metas = []
    for item in entries:
        try:
            url = 'http://jobview.monster.' + cntry + '/v2/job/View?JobID=' +item.id
            indi_meta = {'title':encode_check(item.title), 'link':url, 'id':item.id, 'published':item.published}
            metas.append(indi_meta)
        except:
            print 'Warning: error in processing metas'
    return metas

def monster_indi_result(pmeta):
    url = pmeta['link']
    print 'Processing post from url: {}'.format(url)
    try:
        sourcecode = urllib2.urlopen(pmeta['link']).read()
    except:
        print 'Error: Cannot open url - ', pmeta['link']
        return None
    sourcecode = re.sub('<br\s*?>', ' ', sourcecode)
    soup = BeautifulSoup.BeautifulSoup(sourcecode)
    
    comp_tag = soup.find('meta',{'itemprop':'hiringOrganization'})
    if comp_tag == None:
        company = ''
    else:
        company = encode_check(comp_tag.attrMap['content'])
    date_tag = soup.find('meta',{'itemprop':'datePosted'})
    if date_tag == None:
        post_date = ''
    else:
        post_date = date_tag.attrMap['content']
    
    #print 'break point'
    smr_dict = dict()
    smr_dict.update({'Job title': pmeta['title'],'Company': company,'Post date':post_date})
    summaries = soup.findAll('section',{'class':'summary-section'})
    for section in summaries:
        key = section.find('h2').text
        value = encode_check(section.find('h3').text)
        smr_dict.update({key:value})
        
    jd = soup.find('div',{'id':'JobDescription'})
    if jd is None:
        body = ''
    else:
        body = encode_check(jd.text)
    smr_dict.update({'Job description':body})
    
    return smr_dict
    #print mfeed.entries[0].title
    #print mfeed.entries[0].link
    #print mfeed.entries[0].id
    #print mfeed.entries[0].published

def encode_check(uni_content):
    cleaned = uni_content.replace(u'\u2019', "'")
    cleaned = cleaned.replace(u'\u2013', "-")
    cleaned = cleaned.replace(u'\xe9', "e")
    cleaned = cleaned.replace('&amp;','&')
    cleaned = cleaned.replace('&#039;',"'")
    cleaned = cleaned.encode('ascii','ignore')
    return cleaned
    
if __name__ == '__main__':
    testurl = 'http://rss.jobsearch.monster.com/rssquery.ashx?rad_units=km&cy=CA&pg=1&pp=200&tm=1&&sort=dt.rv.di&baseurl=jobview.monster.ca'
    #Read in configure
    #qfile = open('monster_queries.txt','r')
    #queries = qfile.read().split('\n')
    #qfile.close()
    queries = ['ca, 2000, 1, 20','us, 2000, 1, 20']        
    for q in queries:
        parameters = q.split(',')
        if len(parameters) == 4:
            Mparser(parameters[0],int(parameters[1]),int(parameters[2]),int(parameters[3]))
        else:
            print 'Error: Wrong number of query arguments. Please check query file.'
    
    print '----------------- Job Done! -----------------'