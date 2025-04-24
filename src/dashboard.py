#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
仪表盘模块
负责创建Web仪表盘，展示系统收集的所有数据
"""

import os
import logging
import threading
import time
from datetime import datetime
import json
import pandas as pd
import numpy as np
from queue import Queue

# Web应用框架
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

logger = logging.getLogger("MoodSense.Dashboard")

class Dashboard:
    """
    仪表盘类，负责创建Web界面展示系统数据
    
    使用Flask+SocketIO创建实时更新的仪表盘
    """
    
    def __init__(self, host='0.0.0.0', port=8080, debug=False):
        """
        初始化仪表盘
        
        Args:
            host: 服务器主机
            port: 服务器端口
            debug: 是否开启调试模式
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.running = False
        
        # 创建Flask应用
        # 使用基于文件当前位置的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        templates_path = os.path.join(project_root, 'templates')
        static_path = os.path.join(project_root, 'static')
        
        self.app = Flask(
            __name__, 
            template_folder=templates_path,
            static_folder=static_path
        )
        
        # 配置
        self.app.config['SECRET_KEY'] = 'moodsense-secret-key'
        self.app.config['JSON_AS_ASCII'] = False
        
        # 创建SocketIO实例
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 数据缓存
        self.latest_data = {}
        self.emotion_history = []
        self.environment_history = []
        self.productivity_history = []
        self.last_video_frame = None  # 存储最新的视频帧
        
        # 最后更新时间
        self.last_update = time.time()
        
        # 设置路由
        self._setup_routes()
        
        # 设置SocketIO事件
        self._setup_socketio_events()
        
        logger.info("仪表盘初始化完成")
    
    def start(self):
        """启动仪表盘服务器"""
        if self.running:
            logger.warning("仪表盘已在运行")
            return
        
        logger.info(f"启动仪表盘服务器 (http://{self.host}:{self.port})...")
        self.running = True
        
        # 确保模板和静态文件目录存在
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        templates_path = os.path.join(project_root, 'templates')
        static_path = os.path.join(project_root, 'static')
        static_css_path = os.path.join(static_path, 'css')
        static_js_path = os.path.join(static_path, 'js')
        
        os.makedirs(templates_path, exist_ok=True)
        os.makedirs(static_css_path, exist_ok=True)
        os.makedirs(static_js_path, exist_ok=True)
        
        # 创建基本模板和静态文件
        self._create_template_files()
        self._create_static_files()
        
        # 启动更新线程
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # 启动Socket.IO服务器
        self.server_thread = threading.Thread(
            target=self.socketio.run,
            args=(self.app,),
            kwargs={
                'host': self.host,
                'port': self.port,
                'debug': self.debug,
                'use_reloader': False
            },
            daemon=False  # 不设置为守护线程，使服务器能继续运行
        )
        self.server_thread.start()
        
        logger.info("仪表盘服务器已启动")
    
    def stop(self):
        """停止仪表盘服务器"""
        if not self.running:
            return
        
        logger.info("正在停止仪表盘服务器...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=1.0)
        
        logger.info("仪表盘服务器已停止")
    
    def update_data(self, data):
        """
        更新仪表盘数据
        
        Args:
            data: 新的数据字典
        """
        # data = json.loads(data)
        logger.info(f'[update data] {data}')
        self.latest_data = data
        self.last_update = time.time()
        
        # 提取关键数据添加到历史记录
        timestamp = datetime.now()
        
        # 情绪数据
        if 'emotion' in data:
            emotion_data = {
                'timestamp': timestamp,
                'emotion': data['emotion'] if isinstance(data['emotion'], str) else data.get('emotion', {}).get('emotion', 'neutral'),
                'valence': data.get('valence', 0.0) if isinstance(data.get('emotion'), str) else data.get('emotion', {}).get('valence', 0.0),
                'arousal': data.get('arousal', 0.0) if isinstance(data.get('emotion'), str) else data.get('emotion', {}).get('arousal', 0.0),
                'mood_score': data.get('mood_score', 0.0)
            }
            self.emotion_history.append(emotion_data)
            # 保持历史数据在合理范围内
            if len(self.emotion_history) > 100:
                self.emotion_history.pop(0)
        
        # 环境数据
        if 'environment' in data:
            env_data = {
                'timestamp': timestamp,
                'brightness': data.get('brightness', 0.0),
                'noise_level': data.get('noise_level', 0.0),
                'environment_score': data.get('environment_score', 0.5)
            }
            self.environment_history.append(env_data)
            if len(self.environment_history) > 100:
                self.environment_history.pop(0)
        
        # 生产力数据
        if 'input' in data:
            prod_data = {
                'timestamp': timestamp,
                'typing_speed': data.get('input', {}).get('typing_speed', 0.0),
                'focus_level': data.get('input', {}).get('focus_level', 0.5),
                'productivity_score': data.get('productivity_score', 0.5)
            }
            self.productivity_history.append(prod_data)
            if len(self.productivity_history) > 100:
                self.productivity_history.pop(0)
        
        # 如果有视频帧数据，保存它
        if 'video' in data and 'frame_data' in data['video']:
            self.last_video_frame = data['video']['frame_data']
        
        # 通过Socket.IO发送更新
        self._emit_update()
    
    def _setup_routes(self):
        """设置Flask路由"""
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/data')
        def get_data():
            return jsonify(self.latest_data)
        
        @self.app.route('/history/emotion')
        def get_emotion_history():
            return jsonify(self.emotion_history)
        
        @self.app.route('/history/environment')
        def get_environment_history():
            return jsonify(self.environment_history)
        
        @self.app.route('/history/productivity')
        def get_productivity_history():
            return jsonify(self.productivity_history)
    
    def _setup_socketio_events(self):
        """设置Socket.IO事件"""
        @self.socketio.on('connect')
        def handle_connect():
            logger.info(f"客户端已连接: {request.sid}")
            # 发送最新数据
            self._emit_update()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info(f"客户端已断开连接: {request.sid}")
        
        @self.socketio.on('request_update')
        def handle_request_update():
            self._emit_update()
            
        @self.socketio.on('request_video_frame')
        def handle_request_video_frame():
            # 仅发送视频帧数据
            if hasattr(self, 'last_video_frame') and self.last_video_frame is not None:
                logger.debug(f"发送视频帧给客户端: {request.sid}")
                self.socketio.emit('video_frame', {'data': self.last_video_frame})
            else:
                logger.debug(f"无视频帧可用，通知客户端: {request.sid}")
                self.socketio.emit('no_server_video')
    
    def _emit_update(self):
        """发送数据更新到客户端"""
        try:
            # 发送最新数据
            self.socketio.emit('data_update', self.latest_data)
            
            # 发送历史数据
            if self.emotion_history:
                self.socketio.emit('emotion_history_update', self.emotion_history[-20:])
            
            if self.environment_history:
                self.socketio.emit('environment_history_update', self.environment_history[-20:])
            
            if self.productivity_history:
                self.socketio.emit('productivity_history_update', self.productivity_history[-20:])
                
            # 检查视频数据是否可用，如果有则发送
            if 'video' in self.latest_data and hasattr(self, 'last_video_frame') and self.last_video_frame is not None:
                self.socketio.emit('video_frame', {'data': self.last_video_frame})
            else:
                # 通知前端没有服务器视频流，可以尝试使用本地摄像头
                self.socketio.emit('no_server_video')
        except Exception as e:
            logger.error(f"发送更新时出错: {str(e)}")
    
    def _update_loop(self):
        """更新循环，模拟从其他模块获取数据"""
        # 每个模块的数据队列，实际应用中会由各模块写入数据
        video_queue = Queue()
        audio_queue = Queue()
        environment_queue = Queue()
        emotion_queue = Queue()
        input_queue = Queue()
        integrated_queue = Queue()
        
        while self.running:
            try:
                # 检查是否有新的综合数据
                try:
                    # 非阻塞方式获取数据
                    data = integrated_queue.get_nowait()
                    # 更新数据
                    self.update_data(data)
                except:
                    # 如果没有新数据，继续
                    pass
                
                # 等待一段时间
                time.sleep(0.1)
                
            except Exception as e:
                if self.running:  # 只在运行时记录错误
                    logger.error(f"更新循环错误: {str(e)}")
                time.sleep(1.0)
    
    def _create_template_files(self):
        """创建基本的HTML模板文件，如果不存在"""
        # 计算模板目录的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        templates_dir = os.path.join(project_root, 'templates')
        
        # 如果模板已存在，不需要创建
        if os.path.exists(os.path.join(templates_dir, 'index.html')):
            return
        
        logger.info("创建HTML模板文件...")
        
        # 创建index.html已在之前完成
    
    def _create_static_files(self):
        """创建基本的静态文件，如果不存在"""
        # 计算静态文件目录的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        static_css_path = os.path.join(project_root, 'static', 'css')
        static_js_path = os.path.join(project_root, 'static', 'js')
        
        # 如果静态文件已存在，不需要创建
        if os.path.exists(os.path.join(static_css_path, 'style.css')) and \
           os.path.exists(os.path.join(static_js_path, 'main.js')):
            return
        
        logger.info("创建静态文件...")
        
        # 创建CSS和JS文件已在之前完成
