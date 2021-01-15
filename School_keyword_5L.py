from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import urljoin
import os, multiprocessing, logging, requests, re, asyncio, aiohttp , redis

f = open('www.edu_tw.txt', "r", encoding="utf-8")
school_names = f.read().split('\n')
school_names = school_names
f.close()

load_dotenv(encoding="utf-8")
redis_r = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), db=os.getenv('REDIS_DB'),
                            decode_responses=True)
token = 'TN3vwuHrTafuPVewmgemICiUfICGPkWIaKRT4WBiH1w'

async def lineNotifyMessage(token, msg):
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type' : 'application/x-www-form-urlencoded'
        }
    payload = {'message': msg}
    r = requests.post('https://notify-api.line.me/api/notify', headers = headers, params = payload)
    return r.status_code

async def Keyword(edu_url):
    timeout = aiohttp.ClientTimeout()
    async with aiohttp.ClientSession(timeout=timeout) as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
        }
        url_list = []
        verify = {}
        url_list.append(edu_url)
        verify[str(edu_url)] = edu_url
        school_key = re.search(r'(?<=\.).*edu.tw',edu_url).group(0)
        if school_key.count('.') > 2:
            school_key = re.search(r'(?<=\.).*edu.tw', school_key).group(0)
        for n in range(0,5):
            len_url_list = len(url_list)
            for url in url_list[0:len_url_list]:
                url_list.pop()
                try:
                    async with session.get(url, headers = headers) as res:
                        if 'text/html' in res.headers['Content-Type'] and res.status == 200:
                            res.encoding = 'utf-8'
                            res = await res.text('utf-8','ignore')
                            soup_a = BeautifulSoup(res ,'html.parser').findAll('a')
                        else :
                            continue
                        for i in soup_a:
                            if i.get('title') == None:
                                title = i.string
                            else:
                                title = i.get('title')
                            if i.get('href') != None:
                                href = i.get('href')
                            else:
                                continue
                            if re.match(r'http.*',href) == None:
                                href = urljoin(url , href)
                            if '#' in href:
                                href = str(href)[0:href.find('#')]
                            if href not in verify.values() and 'load' not in href:
                                if re.search(r'/en/',str(href)) != None : continue
                                if re.search(r'https?://(\w{0,15}\.?)' + school_key + r'(\.?\w{0,15}){0,3}/?|https?://www\.(\w{0,15}\.)' + school_key + r'(\.?\w{0,15}){0,3}/?', str(href)) != None :
                                    url_list.append(href)
                                    verify[str(href)] = href
                                else:
                                    continue
                            else:
                                continue
                            if os.getenv('keyword') in title:
                                if title not in redis_r.keys('keyword') and '.exe' not in href:
                                    redis_r.hset("keyword" , title , href)
                                    msg = '{}{}{}{}\n{} : {}'.format("關鍵字是",'《',os.getenv('keyword'),'》',title , href)
                                    await lineNotifyMessage(token , msg)
                except Exception as e:
                    continue
    return url_list
start  = datetime.now()
loop = asyncio.get_event_loop()
tasks = []
for school_name in school_names:
    tasks.append(loop.create_task(Keyword(school_name)))
loop.run_until_complete(asyncio.wait(tasks))
end = datetime.now()
print("花費幾秒:"+str((end-start).seconds))
