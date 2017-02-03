import os
import csv
#from textblob import TextBlob
from wordcloud import WordCloud 
import matplotlib.pyplot as plot

def get_text(filename):
    texts = []
    with open(filename,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            texts.append(row['description'])
    return texts

posts = []
dirlist = os.listdir('csv')
for cfile in dirlist:
    if cfile.endswith('.csv'):
        posts += get_text(cfile)
        #print len(posts)
tgt_str = '\n'.join(posts)

cloud = WordCloud().generate(tgt_str)
plot.imshow(cloud)
plot.axis("off")
#frequences = blob.word_counts

print 'Job Done!'