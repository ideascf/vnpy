# encoding: utf-8
from __future__ import print_function
import os
import sys
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CUR_DIR))

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


class Marketing(object):
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
        self.mainEngine.exit()

    def _connectGateway(self, gatewayList):
        for gateway in gatewayList:
            # Marketing不需要对账户信息和交易信息进行查询
            self.mainEngine.gatewayDict[gateway].setQryEnabled(False)
            self.mainEngine.connect(gateway)

            printLog('Gateway(%s) connect finished.' % (gateway,))

g_marketing = None
def signal_handler(signum, frame):
    if signum in (signal.SIGINT, signal.SIGTERM):
        if g_marketing is not None:
            g_marketing.isRunning = False

# ----------------------------------------------------------------------
def runServer():
    """运行服务器"""
    global g_marketing
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    g_marketing = Marketing(
        config.MARKETING_REQ_ADDR,
        config.MARKETING_PUB_ADDR,
    )

    g_marketing.start([
        vtConstant.EXCHANGE_CHBTC,
    ])


if __name__ == '__main__':
    runServer()