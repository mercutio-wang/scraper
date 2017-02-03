import boto3
import os
import sys
import botocore
import time
import datetime

def initialize(logfile):
    ADMIN_EMAIL = set(['admin@neemo.ca','chris@neemo.ca','mercutio_wang@icloud.com'])
    logfile.write(str(datetime.datetime.now())+' Scraper initialization begins.\n')
    
    if createdir():
        logfile.write(str(datetime.datetime.now())+' Folders created for output.\n')
    else:
        logfile.write(str(datetime.datetime.now())+' Error - Initialization failed. Please check log for details.\n')
        sys.exit()
        
    #Check connection with aws s3 and ec2
    
    s3 = boto3.resource('s3')
    try:
        s3.meta.client.head_bucket(Bucket='neemoscraper')
    except botocore.exceptions.ClientError as e:
    # If a client error is thrown, then check that it was a 404 error.
    # If it was a 404 error, then the bucket does not exist.
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logfile.write(str(datetime.datetime.now())+' Bucket does not exist, creating the bucket\n')
            try:
                s3.create_bucket(Bucket='scraper')
                logfile.write(str(datetime.datetime.now())+' S3 bucket <scraper> is created. \n')
            except:
                logfile.write(str(datetime.datetime.now())+' Cannot create bucket, please check aws settings.\n')
    except:
        logfile.write(str(datetime.datetime.now())+' Unexpected error connecting with AWS\n')
    
    if not file_check():
        sys.exit()
    
    emailclient = boto3.client('ses')
    addr = set(emailclient.list_verified_email_addresses()['VerifiedEmailAddresses'])
    if not ADMIN_EMAIL.issubset(addr):
        logfile.write(str(datetime.datetime.now())+' Warning - Eamil list is not correctly set up on SES.\n')
      
    logfile.write(str(datetime.datetime.now())+' Initialization completed. Ready to run scripts.\n')
    return 

def file_check():
    flist = os.listdir('.')
    if 'setup.txt' not in flist:
        print 'Error - could not find configure file: setup.txt'
        return False
    scripts = [] 
    for f in flist:
        if f.endswith('.py'):
            scripts.append(f)
    
    if len(scripts) == 0:
        print 'Error - could not find python scripts to run'
        return False
    return True
   
def createdir():
    dirlist = os.listdir('.')
    try: 
        if 'logs' not in dirlist:
            os.mkdir('logs')
        if 'csv' not in dirlist:
            os.mkdir('csv')
        return True
    except:
        print 'Error - Unexpected error in creating directries. \n'
        return False

def get_cmd():
    setup_file = open('setup_sample.txt','r')
    parser_cmds = setup_file.read().split('\n')
    setup_file.close()
    cmd_rst = []
    
    for pcmd in parser_cmds:
        argvs = pcmd.split(':')
        if len(argvs) is not 2:
            print 'Error - Incorrect format of setup line:', pcmd
        else:
            cmd_rst.append({'name':argvs[0],'cmd':argvs[1]})
        
    return cmd_rst

def check_script(cmd):
    filename = cmd.split(' ')[1]
    if not os.path.isfile(filename):
        print 'Error - Unable to find script:', filename
        return False
    else:
        return True

def change_instance_ip(ec2, instance, old_addr):

    new_addr = ec2.allocate_address()
    assc_id = ec2.associate_address(AllocationId=new_addr['AllocationId'],InstanceId=instance['InstanceId'])    
    ec2.release_address(AllocationId=old_addr['AllocationId'])
    
    return assc_id

if __name__ == '__main__':
    cntl_log = open('logs/controller_{}.txt'.format(str(datetime.date.today())),'a')
    initialize(cntl_log)

    #test = change_instance_ip(ec2, instance, addr)
    #loopcntl = 0
    cntl_log = open('logs/controller_{}.txt'.format(str(datetime.date.today())),'a')
    cmds = get_cmd()
    cntl_log.write('----------------------Scraper back to work---------------------\n')
    cntl_log.write(str(datetime.datetime.now())+' Scraper starts, found {} scripts to run.\n'.format(len(cmds)))
    for c in cmds:
        cmdline = c['cmd']
        #logfile = 'logs/'+datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.txt'
        if check_script(cmdline):
            logfile = 'logs/'+c['name']+'_'+datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.txt'
            cntl_log.write(str(datetime.datetime.now())+' Script starts, getting posts from: '+c['name'])
            start_time = time.time()
            try:
                os.system('python '+cmdline+' > '+logfile)
            except:
                cntl_log.write(str(datetime.datetime.now())+' Error in running script: {}\n'.format(c['name']))
            cntl_log.write(str(datetime.datetime.now())+' Finished scraping {}, runtime is {} seconds.\n'.format(c['name'],time.time()-start_time))        
    #sys.exit()   
    cntl_log.write('\n--------------Job done. Going into sleep now.-----------------\n')
    cntl_log.close()
