# encoding: utf-8
from __future__ import print_function

from datetime import datetime
import signal
from time import sleep
from vtServer import VtServer
import vtConstant
from vtEngine import MainEngine
from service import config


def printLog(content):
    """打印日志"""
    print(datetime.now().strftime("%H:%M:%S"), '\t', content)


class Trade(object):
    def __init__(self, reqAddress, pubAddress):
        self.reqAddr = reqAddress
        self.pubAddr = pubAddress
        self.mainEngine = None
        self.isRunning = False

    def start(self, gatewayList):
        """
        
        :param gatewayList: such as ['CHBTC', 'HUOBI'] 
        :type gatewayList: 
        :return: 
        :rtype: 
        """

        if self.isRunning:
            return
        self.isRunning = True

        # 创建主引擎对象
        self.mainEngine = MainEngine(enableCtaEngine=False, enableDrEngine=True, enableRmEngine=False)

        # 启动server
        server = VtServer(self.reqAddr, self.pubAddr, self.mainEngine)
        server.start()
        self._connectGateway(gatewayList)


        printLog('-' * 50)
        printLog(u'marketing服务器已启动')
        # 进入主循环
        while self.isRunning:
            printLog(u'请输入Ctrl-C来关闭服务器')
            sleep(1)

        server.stopServer()

    def _connectGateway(self, gatewayList):
        for gateway in gatewayList:
            # Marketing不需要对账户信息和交易信息进行查询
            self.mainEngine.gatewayDict[gateway].setQryEnabled(False)
            self.mainEngine.connect(gateway)

            printLog('Gateway(%s) connect finished.' % (gateway,))

g_trade = None
def signal_handler(signum, frame):
    if signum in (signal.SIGINT, signal.SIGTERM):
        if g_trade is not None:
            g_trade.isRunning = False

# ----------------------------------------------------------------------
def runServer():
    """运行服务器"""
    global g_trade
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    g_trade = Trade(
        config.TRADE_REQ_ADDR,
        config.TRADE_PUB_ADDR,
    )
    g_trade.start([
        vtConstant.EXCHANGE_CHBTC,
    ])


if __name__ == '__main__':
    runServer()