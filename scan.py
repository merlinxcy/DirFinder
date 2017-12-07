#! -*-coding:utf-8-*-
#! author:steven.xeldax
#  ip池收集采用cpu密集多进程模式
#  目录爆破采用io密集多线程
#  queue理论上会自动加Q锁，所以程序运行时应该不会产生死锁
import requests
import re
import random
import time
import random
import Queue
import multiprocessing
import os
from lxml import etree
import threading
deep_path = 4#设置爬虫深度[!!]
time_out = 3#设置校验ip时的超时时间[!]
thread_num = 5#设置允许线程的数目
mutex = threading.Lock()#该变量为线程锁，用来控制并发请求文件锁造成的问题
ip_pool = []#全局ip池，供给全部变量使用

class IpPool(threading.Thread):
    def __init__(self,mq=None):
        threading.Thread.__init__(self)
        self.headers = {'User_Agent':'as'}
        self.ip_pool_source = {}
        self.mq = mq

    def get_ip_pool_xici(self):
        headers = {'User-Agent':'as'}
        r=requests.get('http://www.xicidaili.com/wt',headers=headers)
        page = r.content
        print page
        maxpage = re.findall(r'<a href="/wt/.*?">(.*?)</a>',page)
        print "[+]find maxpages: "+ str(maxpage)
        maxpage = max(int(i) for i in maxpage)
        result = re.findall(r'<td>(.*?)</td>',page)
        proxylist = list()
        for i in range(0,len(result)/5):
            ip = result[i*5]
            port = result[i*5+1]
            proxylist.append({ip:port})
        ##获取全部ip池
        if maxpage>1:
            for i in range(2,deep_path):
                url='http://www.xicidaili.com/wt/'+str(i)
                #time.sleep(2)
                #print url
                r = requests.get(url,headers=headers)
                page = r.content
                #print page
                result = re.findall(r'<td>(.*?)</td>',page)
                for i in range(0,len(result)/5):
                    ip = result[i*5]
                    port = result[i*5+1]
                    proxylist.append({ip:port})
        ##范式化
        ip_proxylist = []
        for i in proxylist:
        	ip_proxylist.append("http://"+str(i.keys()[0])+":"+str(i.values()[0]))
        return ip_proxylist

    def get_ip_pool_usproxy(self):
        headers = {'User-Agent':'as'}
        r = requests.get('https://www.us-proxy.org/',headers=headers)
        page = r.content
        #print page
        #result = re.findall(r'<td>',page) no the bes
        lxml_handle = etree.HTML(page)
        result_ip = lxml_handle.xpath('//*[@id="proxylisttable"]/tbody/*/td[1]')
        result_port = lxml_handle.xpath('//*[@id="proxylisttable"]/tbody/*/td[2]')
        #print result[0].text
        result = []
        for i,j in enumerate(result_ip):
            tmp = 'http://'+str(j.text)+':'+str(result_port[i].text)
            result.append(tmp)
        return result

    def check_useful(self,proxy_dic):
        useful_proxy = []
        #print proxy_dic
        for i in proxy_dic:
            try:
                proxy = {'http':i}
                new = requests.get('http://httpbin.org/ip',proxies=proxy,timeout=time_out)
                content = new.content
                if content.find('origin') != -1:
                    print '[*]ip works'
                    useful_proxy.append(i)
            except:
                pass
        return useful_proxy

    def check_userful_inruning(self,proxy_dic,checked_mq):
        for i in proxy_dic:
            try:
                proxy = {'http':i}
                new = requests.get('http://httpbin.org/ip',proxies=proxy,timeout=time_out)
                content = new.content
                if content.find('origin') != -1:
                    print '[*]ip works'
                    checked_mq.put(i)
                    ip_pool.append(i)
            except:
                pass
        return True

    def run(self):
        ip_pool_t = self.get_ip_pool_usproxy()
        self.check_userful_inruning(ip_pool_t,self.mq)


class IpGet:
    def __init__(self):
        pass

    def get_random_proxy(self):
        while True:
            if len(ip_pool):#如果ip池小于3等待
                break
        pool_length = len(ip_pool)
        return ip_pool[random.randint(0,pool_length-1)]

'''
rand=random.randint(0,len_proxylist)
print a[rand]
proxy={'http':a[rand]}
new=requests.get('http://httpbin.org/ip',proxies=proxy)
print new.content
'''
class RequestHandle(threading.Thread):
    def __init__(self,ip_handle,url_handle):
        threading.Thread.__init__(self)
        self.url_handle = url_handle
        self.ip_handle = ip_handle

    @staticmethod
    def get(url,proxy):
        try:
            r = requests.get(url,proxies=proxy,timeout=time_out)
            status = str(r.status_code)
            return status
        except Exception as e:
            status = 'failed'
            print e
            return status

    def run(self):
        while True:
            proxy = self.ip_handle.get_random_proxy()
            proxy = {'http':proxy}
            path = self.url_handle.next()
            print proxy
            print path
            if path == False:
                return 'Done'
            print self.get('http://xeldax.top/'+path,proxy)


class DictionaryHandle(object):
    def __init__(self,file_path,path_mq):
        self.file_path = file_path
        self.path_mq = path_mq
        if os.path.exists(file_path):
            self.file_handle = open(file_path,'r')
        else:
            raise '[-]dict fail not found'

    def __iter__(self):
        return self

    def next(self):
        mutex.acquire()
        path = self.file_handle.readline()
        if path:
            mutex.release()
            return path
        mutex.release()
        return False


# class Fuzzer:
#     def __init__(self,thread_num):
#         self.thread_num = thread_num
#
#     def run()

if __name__ == '__main__':
    #IpPool run
    ip_mq = Queue.Queue(maxsize=1024)
    handle = IpPool(ip_mq)
    handle.daemon = True
    handle.start()#启动子进程爬虫模块
    #Dic set
    dic_handle = DictionaryHandle('1.dic',None)
    #IpGet Handle
    ipget_handle = IpGet()
    #Request Handle
    thread_pool = []
    thread_pool.append(RequestHandle(ipget_handle,dic_handle))
    # for i in range(0,thread_num):
        # thread_pool.append(RequestHandle(ipget_handle,dic_handle))
    #启动线程池
    for i in thread_pool:
        i.daemon = True
        i.start()
    ##等待结束
    handle.join()
    for i in thread_pool:
        i.join()

if __name__ == '__ma11in__':
    ip_mq = Queue.Queue(maxsize=1024)
    handle = IpPool(ip_mq)
    handle.start()#ip_mq队列中存放了代理
    dic_handle = DictionaryHandle('dicc.txt')
    a = RequestHandle(ip_mq,dic_handle)
    '''
    for i in range(0,thread_num):
        thread_pool.append(RequestHandle(ip_mq,path_mq))

    #启动线程池
    handle.start()#ip_mq队列中存放了代理
    for i in thread_pool:
        i.start()
    '''
if __name__ == '__maain__':
    # handle = IpPool()
    #print handle.get_ip_pool_xici()
    q = Queue.Queue(maxsize=1024)
    handle = IpPool(q)
    # handle.check_userful_inruning(handle.get_ip_pool_usproxy(),q)
    handle.start()
    while True:
        print 1
        print q.get()
