import boto3
import os
import time
import datetime

today = datetime.date.today()
del_file_count = 0
print today, '- Cleaner start!'
#sync with AWS S3, upload all new files
os.system('aws s3 sync csv/ s3://neemoscraper/csv')
os.system('aws s3 sync logs/ s3://neemoscraper/logs')
os.system('aws s3 sync html/ s3://neemoscraper/html')
time.sleep(300)

#clean up csv folder
csvlist = os.listdir('csv')
for c in csvlist:
    if c.startswith('.'):
        continue
    date = datetime.datetime.strptime(c.split('.')[0].split('_')[1],'%Y-%m-%d').date()
    if today - date > datetime.timedelta(7):
        try:
            os.remove('csv/'+c)
            del_file_count += 1
        except:
            print today, '- Cannot remove file:', c
    

#clean up logs folder
loglist = os.listdir('logs')
for log in loglist:
    if log.startswith('.'):
        continue
    date = datetime.datetime.strptime(log.split('.')[0].split('_')[1],'%Y-%m-%d').date()
    if today - date > datetime.timedelta(7):
        try:
            os.remove('logs/'+log)
            del_file_count += 1
        except:
            print today, '- Cannot remove file:', log

#clean up html folder
loglist = os.listdir('html')
for log in loglist:
    if log.startswith('.'):
        continue
    date = datetime.datetime.strptime(log.split('.')[0].split('_')[1],'%Y-%m-%d').date()
    if today - date > datetime.timedelta(7):
        try:
            os.remove('html/'+log)
            del_file_count += 1
        except:
            print today, '- Cannot remove file:', log

print today, '- Cleaner work completed. In total, {} files are deleted. \n\n'