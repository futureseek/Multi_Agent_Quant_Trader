"""
主页面路由
负责处理页面渲染相关的路由
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@main_bp.route('/health')
def health_check():
    """健康检查接口"""
    return {'status': 'ok', 'service': 'web_layer'}
