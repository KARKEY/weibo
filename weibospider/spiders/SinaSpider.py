from scrapy import Spider,Request
import re
from scrapy import Selector
from weibospider.items import BaseInfoItem,BaseinfoMap,TweetsInfoItem,TweetsItem
from urllib import parse
import time
import logging



class sinaSpider(Spider):
    name = "weibo"
    host = "https://weibo.cn"
    redis_key = "weiboSpider:start_urls"
    time = time.clock()
    infocount=0
    tweetscount=0
    requestcount=0

    def timed_task(self, dalay):
        if time.clock()-self.time >= dalay:
            self.time=time.clock()
            msg='获取用户信息{}条 ，获取微博{}条，向引擎提交请求{}次 '.format(self.infocount,self.tweetscount,self.requestcount)
            logging.info(msg)

    def start_requests(self):
        url='https://weibo.cn/1809887200/info'
        yield Request(url,callback=self.parse_user_info)


    def parse_user_info(self, response):
        self.timed_task(10)
        if response.status==200:
            selector=Selector(response)
            userinfo=BaseInfoItem()
            try:
                temp=re.search(r'(\d+)/info', response.url)
                if temp:
                    ID = temp[1]
                else:
                    return
                infotext=";end".join(selector.xpath('body/div[@class="c"]//text()').extract())  # 获取标签里的所有text
                for key in BaseinfoMap.keys():
                    value=BaseinfoMap.get(key)
                    temp=re.search('{}:(.*?);end'.format(value), infotext)
                    if temp:
                        userinfo[key]= temp[1]
                Viplevel=re.search('会员等级.+?(\d{1,2})级\s+;end', infotext)
                if Viplevel:
                    userinfo['Viplevel']=int(Viplevel[1])
                else:
                    userinfo['Viplevel']=0
                userinfo['Id']= ID
                yield Request(url="https://weibo.cn/u/{}?page=1".format(ID), callback=self.parse_tweets,meta={'baseitem':userinfo},dont_filter=True,priority=12)
                yield Request(url="https://weibo.cn/{}/follow".format(ID), callback=self.parse_relationship, dont_filter=True)
                yield Request(url="https://weibo.cn/{}/fans".format(ID), callback=self.parse_relationship, dont_filter=True)
                self.requestcount+=3

            except Exception as e:
                logging.info(e)

    def parse_tweets(self, response):
        if response.status==200:
            selector = Selector(response)
            max_crawl_page=200
            try:
                Id=re.search(r'u/(\d+)', response.url)[1]
                current_page = int(re.search(r'page=(\d*)', response.url)[1])
                if current_page == 1:                                        #抽取微博数量信息
                    item = response.meta['baseitem']
                    infotext=''.join(selector.xpath('//div[@class="tip2"]//text()').extract())
                    Tweets = re.search('微博\[(\d+)\]', infotext)[1]  # 微博数
                    Follows = re.search('关注\[(\d+)\]', infotext)[1]  # 关注数
                    Fans = re.search('粉丝\[(\d+)\]', infotext)[1]  # 粉丝数
                    for key in TweetsInfoItem.fields:
                        try:
                            item[key]=eval(key)
                        except NameError:
                            logging.info('Field is Not Defined', key)
                    yield item
                    self.infocount+=1


                divs = selector.xpath('body/div[@class="c" and @id]')
                for weibo in divs:
                    weiboitem=TweetsItem()
                    id = Id+'-'+weibo.xpath('@id').extract_first()
                    IsTransfer = bool(weibo.xpath('.//span[@class="cmt"]').extract_first())
                    Content=''.join(weibo.xpath('.//span[@class="ctt"]//text()').extract())
                    Like=int(weibo.xpath('.//a[contains(text(), "赞[")]/text()').re_first('赞\[(.*?)\]'))
                    Transfer = int(weibo.xpath('.//a[contains(text(), "转发[")]/text()').re_first('转发\[(.*?)\]'))
                    # Comment = weibo.xpath('//a[contains(text(), "评论[") and not(contains(text(), "原文"))]//text()').re_first('评论\[(.*?)\]')
                    Comment = int(weibo.xpath('.//a[re:test(text(),"^评论\[")]/text()').re_first('评论\[(.*?)\]'))
                    timeandtools=weibo.xpath('div/span[@class="ct"]/text()')
                    if re.search('来自',''.join(timeandtools.extract())):          #有的微博网页发的 没有来自.....
                        PubTime=timeandtools.re_first('(.*?)\\xa0')
                        Tools=timeandtools.re_first('来自(.*)')
                    else:
                        PubTime=''.join(timeandtools.extract())
                        Tools=''
                    Co_oridinates=weibo.xpath('div/a[re:test(@href,"center=([\d.,]+)")]').re_first("center=([\d.,]+)")
                    for key in weiboitem.fields:
                        try:
                            weiboitem[key] = eval(key)
                        except NameError:
                            logging.info('Field is Not Defined', key)
                    yield weiboitem
                    self.tweetscount+=1
                if current_page<max_crawl_page:              #持续获取下一页直到max页面限制
                    next_page=selector.xpath('body/div[@class="pa" and @id="pagelist"]//a[contains(text(),"下页")]/@href').extract_first()
                    if next_page:
                        next_page=parse.urljoin(response.url,next_page)
                        yield Request(next_page, callback=self.parse_tweets,dont_filter=True,priority=13)
                        self.requestcount+=1
            except Exception as e:
                logging.info(e)

    def parse_relationship(self, response):
        if response.status==200:
            selector = Selector(response)
            try:
                urls = selector.xpath('//a[text()="关注他" or text()="关注她"]/@href').extract()
                uids = re.findall('uid=(\d+)', ";".join(urls), re.S)
                for uid in uids:
                    yield Request(url="https://weibo.cn/{}/info".format(uid), callback=self.parse_user_info)
                    self.requestcount += 1
                next_url = selector.xpath('//a[text()="下页"]/@href').extract_first()
                if next_url:
                    next_url=parse.urljoin(response.url,next_url)
                    yield Request(next_url, callback=self.parse_relationship, dont_filter=True)
                    self.requestcount += 1

            except Exception as e:
                logging.info(e)



