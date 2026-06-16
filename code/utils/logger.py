import logging
 
# 配置日志器: 只写文件，不输出到终端
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # DEBUG 太吵，INFO 只保留关键事件
logger.propagate = False       # 不传播到 root logger，避免终端刷屏
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler = logging.FileHandler('livetalking.log')
fhandler.setFormatter(formatter)
fhandler.setLevel(logging.INFO)
logger.addHandler(fhandler)

# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# sformatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# handler.setFormatter(sformatter)
# logger.addHandler(handler)