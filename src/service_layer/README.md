# 服务端启动指南

## 🚀 快速开始

### 1. 安装依赖
如果有环境了可以跳过这里的部分
```bash
cd /home/ligenghao/Multi_Agent_Quant_Trader/src/service_layer
conda create -n MAtrader python=3.10 -y  
conda activate MAtrader 
pip install -r requirements.txt
```

### 2. 启动应用
```bash
python src/service_layer/main.py
```

### 3.启动web端，查看web_layer相应内容