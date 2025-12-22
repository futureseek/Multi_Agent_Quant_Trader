"""
Multi-Agent Quant Trader Web Layer
Flask应用入口文件
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import os

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境需要更改
    
    # 初始化SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # 注册路由
    from routes.main_routes import main_bp
    from routes.api_routes import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app, socketio

# 创建应用实例
app, socketio = create_app()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

if __name__ == '__main__':
    print("🚀 Multi-Agent Quant Trader Web Layer 启动中...")
    print("📱 访问地址: http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
