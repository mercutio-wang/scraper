from __future__ import division
import boto3
import os
import re
import datetime

def main():
    print '{}\nReporter start.'.format(datetime.datetime.now())
    yesterday = str(datetime.date.today() + datetime.timedelta(-1))
    loglist = os.listdir('logs')
    
    if len(loglist) == 0:
        print 'Fatal Error: no logs has been found.'
    result = []
    indeed_msg = ['\n--------  Indeed scraper updates  --------\n','Run hour   Total error   Bad urls   Posts acq\n']
    for log in loglist:
        #print log
        if log.startswith('.'):   #takes care of system file/folders
            continue
        try: 
            log_meta = log.split('.')[0].split('_')
            log_source = log_meta[0].split('-')[0]
            log_date = log_meta[1].split(' ')[0]
        except:
            print 'Error: wrong log name format'
        if log_date == '2016-12-22': #yesterday:
            log_file = open('logs/'+log,'r')
            text = log_file.read()
            if log_source == 'controller':
                result.append(proc_cntl(text))
            elif log_source == 'uploader-log':
                continue
                #result.append(proc_upld(text))
            elif log_source == 'Indeed':
                indeed_msg.append(proc_indd(text,log))
            elif log_source == 'jb':
                continue
            elif log_source == 'eluta':
                continue
            else:
                print 'SpecialNote: Unexpected log files found: {}'.format(log)
            log_file.close()
        else:
            continue
    result.append('\n'.join(indeed_msg))
    body = 'Hi Chris, here is the scraper daily report for {}\n'.format(yesterday) + '\n'.join(result) + '\n\nBest,\nNeemo'
    #print body
    send_email(body)
    print 'Reporter Job Done! \n'

def proc_cntl(text):
    num_scripts = set(re.findall('found ([0-9]) scripts',text))
    sources = set(re.findall('posts from: ([a-zA-Z]*)\n',text))
    run_times = re.findall('([A-Za-z]*), runtime [ a-z]*([.0-9]*)[ a-z]*',text)
    errors = re.findall('Error - ([A-Za-z ]*)',text)
    notes = []
    if len(num_scripts) > 1:
        notes.append('Fatal Error: inconsistent num of scripts\n')
    num_err = len(errors)
    source_list = set(zip(*run_times)[0])
    #rt_dict = {}
    script_run_info = []
    try:
        for s in source_list:
            rt = []
            for r in run_times:
                if r[0] == s:
                    rt.append(float(r[1]))
            #rt_dict.update({s:rt})
            script_run_info.append('{}: run {} times, runtime avg:{}s / max:{}s / min:{}s'.format(s, len(rt), round(sum(rt)/len(rt),2), round(max(rt),2), round(min(rt),2)))
    except:
        notes.append('Error in processing runtimes.\n')
    
    #result = {'Type':'Controller', 'NumScripts':len(num_scripts),'NumErr':num_err, 'RuntimeBySource':rt_dict,'Notes':''.join(notes)}
    rst_str = '\n--------  Controller updates  --------\n\n' + 'Total scripts run: {}\n'.format(len(num_scripts)) + 'Total errors encountered: {}\n\n'.format(num_err) + 'Script execution info: \n' + '\n'.join(script_run_info)
    #print rst_str
    return rst_str


def proc_upld(text):
    
    return


def proc_indd(text,log_name):
    run_hour = log_name.split('.')[0].split('_')[2].split('-')[0]+'H'
    errors = str(len(re.findall('Error',text)))
    url_err = str(len(re.findall('Cannot open url',text)))
    try:
        posts_acq = re.findall('([0-9]*) job posts acquired',text)[0]
    except:
        posts_acq = 'Error'
    #result = {'Type':'Indeed', 'NumErr':errors, 'BrokenUrl':url_err, 'PostsAcqired':posts_acq}
    #result = '\tStart time:{}\n'.format(run_hour) + '\tTotal errors encountered: {}\n'.format(errors) + '\tBad urls: {}\n'.format(url_err) +'\tPosts acquired: {}\n'.format(posts_acq)
    result = ' '*6 + run_hour+' '*14+errors+' '*16 +url_err+' '*12 + posts_acq
    return result

def send_email(body):
    client = boto3.client('ses')
    addr = client.list_verified_email_addresses()['VerifiedEmailAddresses']
    sender = 'chris@neemo.ca'
    res = 'mercutio_wang@icloud.com'
    cc = 'admin@neemo.ca'
    
    if not set([sender,res,cc]).issubset(set(addr)):
        print 'Error: SES emails are not properly setup.'
        return
    subject = 'Neemo Scrapers Daily Report'
    
    response = client.send_email(       
        Source= sender,
        Destination={
            'ToAddresses': [res],
            'CcAddresses': [cc], 
            'BccAddresses': []
        },
        Message={
            'Subject': {
                'Data': subject,
                'Charset': 'ascii'
            },
            'Body': {
                'Text': {
                    'Data': body,
                    'Charset': 'ascii'
                }
            }
        },
    )
    #print 'Job done!'
    return

if __name__ == '__main__':
    main()