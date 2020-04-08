import sys
import time
import os
import subprocess
import re
import json
import pdb
import urllib.parse
import urllib.request
import uuid

# print( "This is the name of the script: ", sys.argv[0])
# print( "Number of arguments: ", len(sys.argv))
# print( "The arguments are: " , str(sys.argv))

# audio='test.wav'
# transcript='words.txt'

# ================= Settings START ======================

first_slide = {
    'auto': True,     # auto makes the first keyword appear at t=0
    'file': None,     # String, this setting works when auto == False
    'duration': None, # Number, this setting works when auto == False
}
last_slide = {
    'auto': True,     # auto makes the last keyword show till end of last word
    'file': None,     # String, this setting works when auto == False
    'duration': None, # Number, this setting works when auto == False
}
api_key = 'aegdnjfymkguklhgsv'
encoded_cx=urllib.parse.quote('32523453:fdspofi')

audio = '1audio.mp3'
transcript = '2words_all.txt'
out_file = 'output.mp4'

# ================= Settings END ========================

url = 'http://localhost:32768/transcriptions?async=false'
gentle_cmd = 'curl -F "audio=@{audio}" -F "transcript=@{transcript}" "{url}"'\
    .format(audio=audio, transcript=transcript, url=url)

# print(cmd)
gentle_out = json.loads(subprocess.check_output(gentle_cmd, shell=True))
# print(gentle_out)

"""
{
    ...
    "words": [
        {"alignedWord": 'qwe', "start": 2.3, ...}
        {"alignedWord": 'asd', "start": 2.5, ...}
        ...
    ]
}
"""


# get index of words starting with [
with open(transcript, "r") as f:
    transcript_2 = f.read()

words = re.split(r'\s', transcript_2)
non_empty_words = list(filter(lambda w: w if (w) else None, words))

indexes = []
# sindexes=set()
s_words = {}
inside = False
appended = False
for i, w in enumerate(non_empty_words):
    appended = False
    w_no_syms = re.sub(r'\[|\]|\.|,','', w)

    if re.search(r'\[', w):
        inside = True
        
        start = gentle_out['words'][i]['start']

        appended = True
        indexes.append({'id': i, 'words': w_no_syms, 'start': start})
    
    if inside and not appended:
        appended = True
        indexes[-1]['words'] += ' ' + w_no_syms


    if re.search(r'\]', w):
        inside=False
        
        if not appended:
            appended = True
            indexes[-1]['words'] = w_no_syms

print('indexes')
print(json.dumps(indexes, indent = 2))
print('indexes')
# ['this','is', '[test', 'with', '2 words]','ok']
# TODO handle - in words
# better structure, indexes:
"""
[
    {'id': 1, 'words': 'qwe asd zxc', 'start': 4.23}
    {'id': 11, 'words': 'rty fgh vbn', 'start': 8.23}
]
"""


ffmpeg_input_file = open('input.txt','w+')

def json_run(cmd):
    return json.loads(subprocess.check_output(cmd, shell=True))

def _gis(kws, options={}):
    encoded_kws = urllib.parse.quote(kws)
    cmd = f"curl 'https://www.googleapis.com/customsearch/v1?q={encoded_kws}&cx={encoded_cx}&num=1&searchType=image&key={api_key}' --header 'Accept: application/json' --compressed"
    print(cmd)
    return json_run(cmd)

# image is: o['items'][0]['link'] 
def gis(kws, options={}):
    return _gis(kws, options)['items'][0]['link']

gis_mock = [
    'https://upload.wikimedia.org/wikipedia/commons/a/aa/1604_Types_of_Cortical_Areas-02.jpg',
    'https://upload.wikimedia.org/wikipedia/en/8/80/HD_with_toasty_PCB.jpg',
    'https://www.somethingnew.org/wp-content/uploads/2019/09/SomethingNew-Logo-KO.png',
    'https://live.staticflickr.com/4836/44661017890_eb4f288ffe_b.jpg',
    'https://cdn.pixabay.com/photo/2017/06/22/20/33/quiz-2432440_960_720.png',
    'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Python.svg/1024px-Python.svg.png',
    'https://www.thebluediamondgallery.com/handwriting/images/practice.jpg',
    'https://cdn.pixabay.com/photo/2017/01/31/15/21/note-2025016_960_720.png',
    'https://cdn.pixabay.com/photo/2017/09/27/09/29/joining-together-2791493_960_720.png',
]


def slide_str(filename, duration):
    return f"""
        file '{filename}'
        duration {duration}
    """ 

# TODO add configurable folder, this folder is to save images
os.makedirs('img', exist_ok=True)

# for picno, i in []:
for picno, i in enumerate(indexes):
    # time.sleep(1)
    # url = gis(i['words'])
    url = 'https://picsum.photos/800/600'
    filename = 'img/' + str(picno) + '.jpg'
    
    try:
        x1=urllib.request.urlretrieve(url, filename)
    except:
        pass
        # pdb.set_trace()

    # First slide
    if picno == 0:
        if first_slide['auto']:
            duration = round(i['start'] * 2, 2)
        else:
            filename = first_slide['file']
            duration = first_slide['duration']

        ffmpeg_input_file.write(slide_str(filename, duration))

    # Intermediate slides
    elif picno >= 1 and picno <= len(indexes) - 2:
        duration = round(indexes[picno + 1]['start'] - i['start'], 2)

        ffmpeg_input_file.write(slide_str(filename, duration))

    
    # Last slide
    if picno == len(indexes) - 1:
        if last_slide['auto']:
            last_word_end = round(gentle_out['words'][-1]['end'], 2)
            duration = round(last_word_end - i['start'], 2)
        else:
            filename = last_slide['file']
            duration = last_slide['duration']
        
        ffmpeg_input_file.write(slide_str(filename, duration))
        # ffmpeg bug workaround, final image is duplicated
        # https://trac.ffmpeg.org/ticket/6128
        ffmpeg_input_file.write(slide_str(filename, duration))


sub_out = f'{uuid.uuid4()}.mp4'
ffmpeg_cmd = f'ffmpeg -f concat -i input.txt -vsync vfr -pix_fmt yuv420p {sub_out}'
subprocess.check_output(ffmpeg_cmd, shell=True)
ffmpeg_cmd_2 = f'ffmpeg -i {sub_out} -i {audio} -c copy -map 0:v:0 -map 1:a:0 {out_file}'
subprocess.check_output(ffmpeg_cmd_2, shell=True)
os.remove(sub_out)