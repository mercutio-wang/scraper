import csv
import datetime
import os
import requests
import time
import json

def upload_posts(filename, Bsize,log):
    HEADERS = set(['job_title', 'company', 'location', 'url', 'time','description','native_id'])
    post_header = {"Content-Type":"application/json"}
    neemo_request_url = 'https://www.neemo.ca/batch'
    batch = []
    post_count = 0
    log.write('\n{} -- Start uploading from result file: {}\n'.format(datetime.datetime.now(),filename))
    
    with open('csv/'+filename,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        header_check = 0
        for row in reader:
            if row['description'].strip() == '':
                continue
            post_count += 1
            if header_check == 0:
                temp = row.keys()
                if HEADERS.issubset(set(row.keys())):
                    header_check = 1
                else:
                    log.write({} -- 'Fatal Error: Unexpected output format!\n'.format(datetime.datetime.now()))
                    break
            if 'source' in row.keys():
                del(row['source'])
            if len(batch) == Bsize:
                #print batch
                response = requests.post(neemo_request_url, data=json.dumps(batch), headers=post_header)
                res_code = str(response.status_code)
                if res_code.startswith('4') or res_code.startswith('5'):
                    log.write('{} -- Warning: Bad request made. \n'.format(datetime.datetime.now()))
                time.sleep(30)
                batch = []
            batch.append(row)
            #if post_count > 30:    #for test purposes
            #    break
    log.write('{} -- File upload completed. Total number of posts scraped: {}\n'.format(datetime.datetime.now(),post_count))
    csvfile.close()
    return

#############Program Starts###################

yesterday = str(datetime.date.today() + datetime.timedelta(-1))
log = open('logs/upload-log_{}.txt'.format(yesterday),'w')
filelist = os.listdir('csv')
if len(filelist) > 0:
    log.write('{} -- ***  Uploading started   ***.\n'.format(datetime.datetime.now()))
    #log.close()
    fcount = 0
else:
     log.write('{} -- Fatal Error: could not find files in target location!'.format(datetime.datetime.now()))
for fname in filelist:
    #print fname
    try: 
        fdate = fname.split('.')[0].split('_')[1]
    except:
        log.write('{} -- Warning: not valid csv file format, skipping file: {}\n'.format(datetime.datetime.now(),fname))
        continue
    if fdate == yesterday: #'2017-01-31': #test
        upload_posts(fname, 10,log)
        fcount += 1
if fcount == 0 :
    log.write('{} -- Error: No result file has been found.\n'.format(datetime.datetime.now()))
else:
    log.write('{} -- Result uploading completed. Uploaded {} files this time. '.format(fcount))
log.write('{} -- ***  Uploading ended   ***.\n'.format(datetime.datetime.now()))
log.close()