# encoding: utf-8
import urllib
import hashlib
import hmac
from collections import OrderedDict
from functools import partial

import json
import requests
from time import time, sleep
from Queue import Queue, Empty
from threading import Thread
import threadpool
import websocket


# 常量定义
COINTYPE_BTC = 'btc'
COINTYPE_LTC = 'ltc'
COINTYPE_ETC = 'etc'
COINTYPE_ETH = 'eth'

TRADETYPE_BUY = 1
TRADETYPE_SELL = 0

CURRENCY_BTCCNY = 'btc_cny'
CURRENCY_LTCCNY = 'ltc_cny'
CURRENCY_ETCCNY = 'etc_cny'
CURRENCY_ETHCNY = 'eth_cny'


ACCOUNTTYPE_CNY = 1
ACCOUNTTYPE_USD = 2

LOANTYPE_CNY = 1
LOANTYPE_BTC = 2
LOANTYPE_LTC = 3
LOANTYPE_USD = 4

MARKETTYPE_CNY = 'cny'
MARKETTYPE_USD = 'usd'

SYMBOL_BTCCNY = 'BTCCNY'
SYMBOL_LTCCNY = 'LTCCNY'
SYMBOL_ETCCNY = 'ETCCNY'
SYMBOL_ETHCNY = 'ETHCNY'

PERIOD_1MIN = '001'
PERIOD_5MIN = '005'
PERIOD_15MIN = '015'
PERIOD_30MIN = '030'
PERIOD_60MIN = '060'
PERIOD_DAILY = '100'
PERIOD_WEEKLY = '200'
PERIOD_MONTHLY = '300'
PERIOD_ANNUALLY = '400'

# API相关定义

# 功能代码
FUNCTIONCODE_ORDER = 'order'
FUNCTIONCODE_CANCELORDER = 'cancelOrder'
FUNCTIONCODE_ORDERINFO = 'getOrder'
FUNCTIONCODE_GETORDERS = 'getOrdersIgnoreTradeType'
_FUNCTIONCODE_GETORDERSNEW = 'getOrdersNew'
FUNCTIONCODE_GETACCOUNTINFO = 'getAccountInfo'
FUNCTIONCODE_WITHDRAWCOIN = 'withdraw'

# UNUSE
FUNCTIONCODE_GETORDERIDBYTRADEID = 'getOrder'
FUNCTIONCODE_GETNEWDEALORDERS = 'get_new_deal_orders'
FUNCTIONCODE_BUY = 'buy'
FUNCTIONCODE_SELL = 'sell'
FUNCTIONCODE_BUYMARKET = 'buy_market'
FUNCTIONCODE_SELLMARKET = 'sell_market'
FUNCTIONCODE_CANCELWITHDRAWCOIN = 'cancel_withdraw_coin'
FUNCTIONCODE_GETWITHDRAWCOINRESULT = 'get_withdraw_coin_result'
FUNCTIONCODE_TRANSFER = 'transfer'
FUNCTIONCODE_LOAN = 'loan'
FUNCTIONCODE_REPAYMENT = 'repayment'
FUNCTIONCODE_GETLOANAVAILABLE = 'get_loan_available'
FUNCTIONCODE_GETLOANS = 'get_loans'

METHOD2URL = {
    FUNCTIONCODE_ORDER: 'https://trade.chbtc.com/api/cancelOrder',
    FUNCTIONCODE_CANCELORDER: 'https://trade.chbtc.com/api/cancelOrder',
    FUNCTIONCODE_ORDERINFO: 'https://trade.chbtc.com/api/getOrder',
    FUNCTIONCODE_GETORDERS: 'https://trade.chbtc.com/api/getOrdersIgnoreTradeType',
    FUNCTIONCODE_GETACCOUNTINFO: 'https://trade.chbtc.com/api/getAccountInfo',
    FUNCTIONCODE_WITHDRAWCOIN: 'https://trade.chbtc.com/api/withdraw',
}

#----------------------------------------------------------------------
def signature(params, secret):
    """生成签名"""

    msg = urllib.urlencode(params)
    sign = hmac.new(secret, msg).hexdigest()

    return sign
    

########################################################################
class TradeApi(object):
    """交易接口"""
    DEBUG = True

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.accessKey = ''
        self.secretKey = ''
        
        self.active = False         # API工作状态   
        self.reqID = 0              # 请求编号
        self.reqQueue = Queue()     # 请求队列
        self.reqThread = Thread(target=self.processQueue)   # 请求处理线程        
    
    #----------------------------------------------------------------------
    def processRequest(self, req):
        """处理请求"""
        # 读取方法和参数
        method = req['method']
        params = req['params']
        url = METHOD2URL[method]
        
        # 在参数中增加必须的字段
        params['accesskey'] = self.accessKey

        # 添加签名
        sign = signature(params, self.secretKey)

        print params, json.dumps(params)
        payload = urllib.urlencode(params)
        payload += '&sign={sign}&reqTime={reqTime}'.format(
            sign=sign,
            reqTime=int(time() * 1000)  # 毫秒
        )

        print 'request: ', url, payload
        r = requests.get(url, params=payload)
        if r.status_code == 200:
            data = r.json()
            print 'response: ', json.dumps(data, ensure_ascii=False)

            return data
        else:
            return None        
    
    #----------------------------------------------------------------------
    def processQueue(self):
        """处理请求队列中的请求"""
        while self.active:
            try:
                req = self.reqQueue.get(block=True, timeout=1)  # 获取请求的阻塞为一秒
                callback = req['callback']
                reqID = req['reqID']
                
                data = self.processRequest(req)
                if data is None:
                    print '处理请求失败'
                    continue

                # parse code
                if isinstance(data, dict):
                    code = data.get('code')
                else:
                    code = None

                # 请求成功
                # 这里的错误代码是整形
                if code is None or code == 1000:
                    if self.DEBUG:
                        print callback.__name__
                    callback(data, req, reqID)
                elif code == 3001 and req['method'] == FUNCTIONCODE_GETORDERS:
                    # 没有找到订单，返回空列表
                    callback([], req, reqID)
                # 请求失败
                else:
                    error = u'错误信息：%s' %data.get('message', '无错误信息')
                    self.onError(error, req, reqID)

                
            except Empty:
                pass    
            
    #----------------------------------------------------------------------
    def sendRequest(self, method, params, callback, optional=None):
        """发送请求"""
        # 请求编号加1
        self.reqID += 1
        
        # 生成请求字典并放入队列中
        req = {}
        req['method'] = method
        req['params'] = params
        req['callback'] = callback
        req['optional'] = optional
        req['reqID'] = self.reqID
        self.reqQueue.put(req)
        
        # 返回请求编号
        return self.reqID
        
    ####################################################
    ## 主动函数
    ####################################################    
    
    #----------------------------------------------------------------------
    def init(self, accessKey, secretKey):
        """初始化"""
        self.accessKey = accessKey

        h = hashlib.sha1()
        h.update(secretKey)
        self.secretKey = h.hexdigest()

        self.active = True
        self.reqThread.start()
        
    #----------------------------------------------------------------------
    def exit(self):
        """退出"""
        self.active = False
        
        if self.reqThread.isAlive():
            self.reqThread.join()    
    
    #----------------------------------------------------------------------
    def getAccountInfo(self, market='cny'):
        """查询账户"""
        method = FUNCTIONCODE_GETACCOUNTINFO
        callback = self.onGetAccountInfo

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''

        return self.sendRequest(method, params, callback)
    
    #----------------------------------------------------------------------
    def getOrders(self, currency=CURRENCY_BTCCNY, pageIndex=0, pageSize=90):
        """查询委托"""
        method = FUNCTIONCODE_GETORDERS
        callback = self.onGetOrders

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''
        params['currency'] = currency
        params['pageIndex'] = pageIndex
        params['pageSize'] = pageSize

        return self.sendRequest(method, params, callback)

    def _getOrdersNew(self, tradeType, currency=CURRENCY_BTCCNY, pageIndex=1, pageSize=90):
        """查询委托-支持tradeType过滤"""
        method = _FUNCTIONCODE_GETORDERSNEW
        callback = self.onGetOrders

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''
        params['tradeType'] = tradeType
        params['currency'] = currency
        params['pageIndex'] = pageIndex
        params['pageSize'] = pageSize

        return self.sendRequest(method, params, callback)

    def orderInfo(self, id_, currency=CURRENCY_BTCCNY):
        """获取委托详情"""
        method = FUNCTIONCODE_ORDERINFO
        callback = self.onOrderInfo

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''
        params['id'] = id_
        params['currency'] = currency

        return self.sendRequest(method, params, callback)
    
    #----------------------------------------------------------------------
    def buy(self, price, amount, currency=CURRENCY_BTCCNY):
        """委托买入"""
        callback = self.onBuy
        return self._order(price, amount, currency, TRADETYPE_BUY, callback)

    def sell(self, price, amount, currency=CURRENCY_BTCCNY):
        """委托卖出"""
        callback = self.onSell
        return self._order(price, amount, currency, TRADETYPE_SELL, callback)

    def _order(self, price, amount, currency, tradeType, callback):
        """下单"""
        method = FUNCTIONCODE_ORDER

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''
        params['price'] = price
        params['amount'] = amount
        params['tradeType'] = tradeType
        params['currency'] = currency

        return self.sendRequest(method, params, callback)
    
    #----------------------------------------------------------------------
    def buyMarket(self, amount, coinType=COINTYPE_BTC, 
                  tradePassword='', tradeId = '', market='cny'):
        """市价买入"""
        raise NotImplementedError('Not support.')
    
    #----------------------------------------------------------------------
    def sellMarket(self, amount, coinType=COINTYPE_BTC, 
                  tradePassword='', tradeId = '', market='cny'):
        """市价卖出"""
        raise NotImplementedError('Not support.')
    
    #----------------------------------------------------------------------
    def cancelOrder(self, id_, currency=CURRENCY_BTCCNY):
        """撤销委托"""
        method = FUNCTIONCODE_CANCELORDER
        callback = self.onCancelOrder

        params = OrderedDict()
        params['method'] = method
        params['accesskey'] = ''
        params['id'] = id_
        params['currency'] = currency

        return self.sendRequest(method, params, callback)

    #----------------------------------------------------------------------
    def getNewDealOrders(self, market='cny'):
        """查询最新10条成交"""
        raise NotImplementedError('Not support.')

    #----------------------------------------------------------------------
    def getOrderIdByTradeId(self, id_, currency=CURRENCY_BTCCNY):
        """通过成交编号查询委托编号"""
        raise NotImplementedError('Not support.')
    
    #----------------------------------------------------------------------
    def withdrawCoin(self, withdrawAddress, withdrawAmount,
                     coinType=COINTYPE_BTC, tradePassword='', withdrawFee=0.0001):
        """提币"""
        method = FUNCTIONCODE_WITHDRAWCOIN
        callback = self.onWithdrawCoin

        params = OrderedDict()
        params['accesskey'] = ''
        params['amount'] = withdrawAmount,
        params['currency'] = coinType
        """
        比特币最低是0.0003
        莱特币最低是0.001
        以太币最低是0.01
        ETC最低是0.01
        """
        params['fees'] = withdrawFee
        params['itransfer'] = 0  # 0 不同意， 1 同意。 默认不同意
        params['method'] = method
        params['receiveAddr'] = withdrawAddress
        params['safePwd'] = tradePassword

        return self.sendRequest(method, params, callback)
    
    def cancelWithdrawCoin(self, id_, market='cny'):
        """取消提币"""
        raise NotImplementedError('Not support.')
    
    #----------------------------------------------------------------------
    def transfer(self, amountFrom, amountTo, amount, 
                 coinType=COINTYPE_BTC ):
        """账户内转账"""
        raise NotImplementedError('Not support.')


    #----------------------------------------------------------------------
    def loan(self, amount, loan_type=LOANTYPE_CNY,
             market=MARKETTYPE_CNY):
        """申请杠杆"""
        raise NotImplementedError('Not support.')
    
    def repayment(self, id_, amount, repayAll=0,
                  market=MARKETTYPE_CNY):
        """归还杠杆"""
        raise NotImplementedError('Not support.')
    
    def getLoanAvailable(self, market='cny'):
        """查询杠杆额度"""
        raise NotImplementedError('Not support.')
    
    def getLoans(self, market='cny'):
        """查询杠杆列表"""
        raise NotImplementedError('Not support.')
    
    ####################################################
    ## 回调函数
    ####################################################
    
    #----------------------------------------------------------------------
    def onError(self, error, req, reqID):
        """错误推送"""
        print error, reqID    

    #----------------------------------------------------------------------
    def onGetAccountInfo(self, data, req, reqID):
        """查询账户回调"""
        print data
    
    #----------------------------------------------------------------------
    def onGetOrders(self, data, req, reqID):
        """查询委托回调"""
        print data
        
    #----------------------------------------------------------------------
    def onOrderInfo(self, data, req, reqID):
        """委托详情回调"""
        print data

    #----------------------------------------------------------------------
    def onBuy(self, data, req, reqID):
        """买入回调"""
        print data
        
    #----------------------------------------------------------------------
    def onSell(self, data, req, reqID):
        """卖出回调"""
        print data    
        
    #----------------------------------------------------------------------
    def onBuyMarket(self, data, req, reqID):
        """市价买入回调"""
        print data
        
    #----------------------------------------------------------------------
    def onSellMarket(self, data, req, reqID):
        """市价卖出回调"""
        print data        
        
    #----------------------------------------------------------------------
    def onCancelOrder(self, data, req, reqID):
        """撤单回调"""
        print data
    
    #----------------------------------------------------------------------
    def onGetNewDealOrders(self, data, req, reqID):
        """查询最新成交回调"""
        print data    
        
    #----------------------------------------------------------------------
    def onGetOrderIdByTradeId(self, data, req, reqID):
        """通过成交编号查询委托编号回调"""
        print data    
        
    #----------------------------------------------------------------------
    def onWithdrawCoin(self, data, req, reqID):
        """提币回调"""
        print data
        
    #----------------------------------------------------------------------
    def onCancelWithdrawCoin(self, data, req, reqID):
        """取消提币回调"""
        print data      
        
    #----------------------------------------------------------------------
    def onGetWithdrawCoinResult(self, data, req, reqID):
        """查询提币结果回调"""
        print data           
        
    #----------------------------------------------------------------------
    def onTransfer(self, data, req, reqID):
        """转账回调"""
        print data
        
    #----------------------------------------------------------------------
    def onLoan(self, data, req, reqID):
        """申请杠杆回调"""
        print data      
        
    #----------------------------------------------------------------------
    def onRepayment(self, data, req, reqID):
        """归还杠杆回调"""
        print data    
    
    #----------------------------------------------------------------------
    def onLoanAvailable(self, data, req, reqID):
        """查询杠杆额度回调"""
        print data      
        
    #----------------------------------------------------------------------
    def onGetLoans(self, data, req, reqID):
        """查询杠杆列表"""
        print data        
        

########################################################################
class DataApi(object):
    """行情接口"""
    TICK_SYMBOL_URL = {
        SYMBOL_BTCCNY: 'http://api.chbtc.com/data/v1/ticker?currency=btc_cny',
        SYMBOL_LTCCNY: 'http://api.chbtc.com/data/v1/ticker?currency=ltc_cny',
        SYMBOL_ETCCNY: 'http://api.chbtc.com/data/v1/ticker?currency=etc_cny',
        SYMBOL_ETHCNY: 'http://api.chbtc.com/data/v1/ticker?currency=eth_cny',
    }

    HISTORY_SYMBOL_URL = {
        SYMBOL_BTCCNY: 'http://api.chbtc.com/data/v1/trades?currency=btc_cny',
        SYMBOL_LTCCNY: 'http://api.chbtc.com/data/v1/trades?currency=ltc_cny',
        SYMBOL_ETCCNY: 'http://api.chbtc.com/data/v1/trades?currency=etc_cny',
        SYMBOL_ETHCNY: 'http://api.chbtc.com/data/v1/trades?currency=eth_cny',
    }  
    
    DEPTH_SYMBOL_URL = {
        SYMBOL_BTCCNY: 'http://api.chbtc.com/data/v1/depth?currency=btc_cny',
        SYMBOL_LTCCNY: 'http://api.chbtc.com/data/v1/depth?currency=ltc_cny',
        SYMBOL_ETCCNY: 'http://api.chbtc.com/data/v1/depth?currency=etc_cny',
        SYMBOL_ETHCNY: 'http://api.chbtc.com/data/v1/depth?currency=eth_cny',
    }    
    
    KLINE_SYMBOL_URL = {
        SYMBOL_BTCCNY: 'http://api.chbtc.com/data/v1/kline?currency=btc_cny',
        SYMBOL_LTCCNY: 'http://api.chbtc.com/data/v1/kline?currency=ltc_cny',
        SYMBOL_ETCCNY: 'http://api.chbtc.com/data/v1/kline?currency=etc_cny',
        SYMBOL_ETHCNY: 'http://api.chbtc.com/data/v1/kline?currency=eth_cny',
    }        
    
    DEBUG = True
    POOL_SIZE = 10

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.active = False
        
        self.taskInterval = 0                       # 每轮请求延时
        self.taskList = []                          # 订阅的任务列表
        self.taskThread = Thread(target=self.run)   # 处理任务的线程
    
    #----------------------------------------------------------------------
    def init(self, interval, debug):
        """初始化"""
        self.taskInterval = interval
        self.DEBUG = debug
        
        self.active = True
        self.taskThread.start()
        
    #----------------------------------------------------------------------
    def exit(self):
        """退出"""
        self.active = False
        
        if self.taskThread.isAlive():
            self.taskThread.join()
        
    #----------------------------------------------------------------------
    def _excutor(self, url, callback):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                if self.DEBUG:
                    print callback.__name__
                callback(data)
        except Exception, e:
            print e

    def run(self):
        """连续运行"""
        p = threadpool.ThreadPool(self.POOL_SIZE)
        while self.active:
            for url, callback in self.taskList:
                req = threadpool.WorkRequest(
                    self._excutor,
                    (url, callback)
                )
                p.putRequest(req)

            st = time()
            p.wait()
            elapse = time() - st

            need_sleep = max(self.taskInterval-elapse, 0)
            print '####', elapse, need_sleep
            sleep(need_sleep)

    #----------------------------------------------------------------------
    def subscribeTick(self, symbol):
        """订阅实时成交数据"""
        url = self.TICK_SYMBOL_URL[symbol]
        task = (url, partial(self.onTick, symbol))
        self.taskList.append(task)
        
    #----------------------------------------------------------------------
    def subscribeDepth(self, symbol, merge=0.1):
        """订阅深度数据"""
        url = self.DEPTH_SYMBOL_URL[symbol]
        url += '&merge=%s' % (merge,)

        task = (url, partial(self.onDepth, symbol))
        self.taskList.append(task)        
        
    #----------------------------------------------------------------------
    def onTick(self, symbol, data):
        """实时成交推送"""
        print data
    
    #----------------------------------------------------------------------
    def onDepth(self, symbol, data):
        """实时深度推送"""
        print data        

    #----------------------------------------------------------------------
    def getKline(self, symbol, period, length=0):
        """查询K线数据"""
        url = self.KLINE_SYMBOL_URL[symbol]
        url = url.replace('[period]', period)
        
        if length:
            url = url + '?length=' + str(length)
            
        try:
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                return data
        except Exception, e:
            print e
            return None


class DataApiWS(object):
    HOST = 'wss://api.chbtc.com:9999/websocket'
    TICK_SYMBOL_CHANNEL = {
        SYMBOL_BTCCNY: 'btc_cny_ticker',
        SYMBOL_LTCCNY: 'ltc_cny_ticker',
        SYMBOL_ETCCNY: 'etc_cny_ticker',
        SYMBOL_ETHCNY: 'eth_cny_ticker',
    }
    DEPTH_SYMBOL_CHANNEL = {
        SYMBOL_BTCCNY: 'btc_cny_depth',
        SYMBOL_LTCCNY: 'ltc_cny_depth',
        SYMBOL_ETCCNY: 'etc_cny_depth',
        SYMBOL_ETHCNY: 'eth_cny_depth',
    }

    def __init__(self):
        self.active = False
        self.wsConnected = False
        self.taskInterval = 0  # 每轮请求延时
        self.thread = None
        self.ws = None
        self.cbDict = {}

        self.initCallback()

    def _connect(self):
        self.ws = websocket.WebSocketApp(
            self.HOST,
            on_message=self.onMessage,
            on_error=self.onError,
            on_close=self.onClose,
            on_open=self.onOpen,
        )
        self.thread = Thread(target=self.ws.run_forever)
        self.thread.start()

    def _reconnect(self):
        """重新连接"""
        # 首先关闭之前的连接
        self._close()
        # 再执行重连任务
        self._connect()

    def _close(self):
        """关闭接口"""
        if self.thread and self.thread.isAlive():
            self.ws.close()
            self.thread.join()

    def onMessage(self, ws, event):
        resp = json.loads(event)
        channel = resp['channel']
        callback = self.cbDict[channel]
        callback(event)

        print 'onMessage, channel: ', channel

    def onError(self, ws, event):
        pass

    def onClose(self, ws):
        self.wsConnected = False

    def onOpen(self, ws):
        self.wsConnected = True

    def init(self, interval, debug):
        websocket.enableTrace(debug)
        self.active = True

    def exit(self):
        """退出"""
        self.active = False

        if self.thread.isAlive():
            self.thread.join()

    def initCallback(self):
        self.cbDict['btc_cny_ticker'] = self.onTick
        self.cbDict['ltc_cny_ticker'] = self.onTick
        self.cbDict['etc_cny_ticker'] = self.onTick
        self.cbDict['eth_cny_ticker'] = self.onTick

        self.cbDict['btc_cny_depth'] = self.onDepth
        self.cbDict['ltc_cny_depth'] = self.onDepth
        self.cbDict['etc_cny_depth'] = self.onDepth
        self.cbDict['eth_cny_depth'] = self.onDepth

    def subscribeTick(self, symbol):
        """订阅实时成交数据"""
        channel = self.TICK_SYMBOL_CHANNEL[symbol]
        req = {
            'event': 'addChannel',
            'channel': channel,
        }
        self._send(req)

    def subscribeDepth(self, symbol, merge=0.1):
        """订阅深度数据"""
        channel = self.DEPTH_SYMBOL_CHANNEL[symbol]
        req = {
            'event': 'addChannel',
            'channel': channel,
        }
        self._send(req)

    def onTick(self, symbol, data):
        print symbol, data

    def onDepth(self, symbol, data):
        print symbol, data

    def _send(self, data):
        try:
            self.ws.send(json.dumps(data))
        except websocket.WebSocketConnectionClosedException as e:
            print e
            pass

