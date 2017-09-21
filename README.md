# weibo
weibo spider based on scrapy and redis

基于Python3.6并需要安装相关依赖包

关于使用：

1.自行购买较多的微博白号，按格式放入到weibo.txt

2.项目基于win10平台开发，在cookie.py 的_init_browse方法中指定了游览器驱动的绝对路径，需要对应修改

3.根据实际场景修改setting中的相关配置


大量爬取几天后可能会被微博后端监控IP,需要加代理解决

项目经过反复测试及调试，在微博平台不大改版情况下能够稳定运行
