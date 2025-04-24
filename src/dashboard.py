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
        # logger.debug(f'[update data] {data}')
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
                frame_length = len(self.last_video_frame) if isinstance(self.last_video_frame, str) else 'unknown type'
                logger.info(f"发送视频帧给客户端: {request.sid}, 帧大小: {frame_length}")
                # 检查获取到的视频帧数据类型
                logger.info(f"视频帧数据类型: {type(self.last_video_frame)}")
                # 检查数据前后部分
                if isinstance(self.last_video_frame, str) and len(self.last_video_frame) > 20:
                    logger.info(f"视频帧数据开头: {self.last_video_frame[:20]}")
                    logger.info(f"视频帧数据结尾: {self.last_video_frame[-20:]}")
                    
                # 发送视频帧数据给前端
                self.socketio.emit('video_frame', {'data': self.last_video_frame})
            else:
                logger.warning(f"无视频帧可用，通知客户端: {request.sid}")
                self.socketio.emit('no_server_video')
    
    def _emit_update(self):
        """发送数据更新到客户端"""
        try:
            # 创建一个只包含可序列化数据的副本
            safe_data = self._prepare_safe_data(self.latest_data)
            
            # 发送最新数据
            self.socketio.emit('data_update', safe_data)
            
            # 发送历史数据（限制数量以避免数据包过大）
            if self.emotion_history:
                # 确保历史数据可序列化
                safe_emotion_history = [self._prepare_safe_data(item) for item in self.emotion_history[-10:]]
                self.socketio.emit('emotion_history_update', safe_emotion_history)
            
            if self.environment_history:
                safe_env_history = [self._prepare_safe_data(item) for item in self.environment_history[-10:]]
                self.socketio.emit('environment_history_update', safe_env_history)
            
            if self.productivity_history:
                safe_prod_history = [self._prepare_safe_data(item) for item in self.productivity_history[-10:]]
                self.socketio.emit('productivity_history_update', safe_prod_history)
                
            # 检查视频数据是否可用，如果有则发送（减小帧大小以避免数据包过大）
            if 'video' in self.latest_data and hasattr(self, 'last_video_frame') and self.last_video_frame is not None:
                # 限制视频数据大小
                if len(self.last_video_frame) > 100000:  # 如果超过100KB
                    logger.info(f"视频帧过大 ({len(self.last_video_frame)} 字节)，跳过本次发送")
                else:
                    self.socketio.emit('video_frame', {'data': self.last_video_frame})
            else:
                # 通知前端没有服务器视频流，可以尝试使用本地摄像头
                self.socketio.emit('no_server_video')
        except Exception as e:
            logger.error(f"发送更新时出错: {str(e)}")
    
    def _prepare_safe_data(self, data):
        """
        准备可以安全序列化为JSON的数据
        
        Args:
            data: 原始数据对象
            
        Returns:
            可以安全序列化的数据
        """
        if data is None:
            return None
            
        if isinstance(data, (str, int, float, bool)):
            return data
            
        if isinstance(data, dict):
            safe_dict = {}
            for key, value in data.items():
                # 跳过函数和方法
                if not callable(value):
                    try:
                        # 尝试用JSON序列化来检测是否可序列化
                        json.dumps(value)
                        safe_dict[key] = value
                    except (TypeError, OverflowError):
                        # 如果不能序列化，递归处理
                        safe_dict[key] = self._prepare_safe_data(value)
            return safe_dict
            
        if isinstance(data, (list, tuple)):
            return [self._prepare_safe_data(item) for item in data]
            
        # 如果是其他类型，尝试转换为字符串
        try:
            return str(data)
        except:
            return None
    
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
        pass # 不需要，已经有了，减少文件体积
    
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
            logger.info("静态文件已存在")
            return
        
        logger.info("创建静态文件...")
        
        # 创建CSS文件
        css_content = '''
/* MoodSense 样式表 */

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f8f9fa;
    color: #333;
}

.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card {
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    margin-bottom: 20px;
    border: none;
}

.card-header {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 600;
}

.emotion-display {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background-color: #f0f0f0;
    margin: 0 auto 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.emotion-icon {
    font-size: 2.5rem;
    color: #666;
}

.progress {
    height: 10px;
    border-radius: 5px;
    margin-bottom: 15px;
}

.placeholder {
    width: 100%;
    height: 300px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: #f0f0f0;
    border-radius: 8px;
    color: #666;
}

.placeholder i {
    font-size: 3rem;
    margin-bottom: 10px;
}

.footer {
    border-top: 1px solid #eee;
    color: #666;
}

/* 情绪图标样式 */
.emotion-happy {
    color: #28a745;
}

.emotion-sad {
    color: #6c757d;
}

.emotion-angry {
    color: #dc3545;
}

.emotion-fear {
    color: #ffc107;
}

.emotion-surprise {
    color: #17a2b8;
}

.emotion-disgust {
    color: #6610f2;
}

.emotion-neutral {
    color: #6c757d;
}
'''
        
        # 写入CSS文件
        with open(os.path.join(static_css_path, 'style.css'), 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        logger.info("CSS文件创建完成")
        
        # 创建JavaScript文件
        js_content = '''
// MoodSense 主JavaScript文件

// 全局变量
let emotionChart = null;
let environmentChart = null;
let socket = null;
let lastUpdate = new Date();

// 当文档加载完成时初始化
document.addEventListener("DOMContentLoaded", function() {
    console.log("文档已加载，初始化应用...");
    
    // 初始化Socket.IO连接
    initSocketConnection();
    
    // 初始化图表
    initCharts();
    
    // 更新当前时间
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
});

// 初始化Socket.IO连接
function initSocketConnection() {
    // 连接到服务器
    socket = io();
    
    // 连接事件
    socket.on("connect", function() {
        console.log("已连接到服务器");
        document.getElementById("connection-status").textContent = "已连接";
        document.getElementById("status-indicator").className = "badge bg-success";
        
        // 请求初始数据
        socket.emit("request_update");
        
        // 在连接成功后初始化视频流
        initVideoStream();
    });
    
    // 断开连接事件
    socket.on("disconnect", function() {
        console.log("已断开连接");
        document.getElementById("connection-status").textContent = "已断开连接";
        document.getElementById("status-indicator").className = "badge bg-danger";
    });
    
    // 数据更新事件
    socket.on("data_update", function(data) {
        console.log("收到数据更新:", data);
        updateDashboard(data);
    });
    
    // 情绪历史数据更新事件
    socket.on("emotion_history_update", function(data) {
        console.log("收到情绪历史更新:", data);
        updateEmotionChart(data);
    });
    
    // 环境历史数据更新事件
    socket.on("environment_history_update", function(data) {
        console.log("收到环境历史更新:", data);
        updateEnvironmentChart(data, "environment");
    });
    
    // 生产力历史数据更新事件
    socket.on("productivity_history_update", function(data) {
        console.log("收到生产力历史更新:", data);
        updateEnvironmentChart(data, "productivity");
    });
    
    // 视频帧更新事件
    socket.on("video_frame", function(data) {
        updateVideoFrame(data.data);
    });
    
    // 无服务器视频事件
    socket.on("no_server_video", function() {
        useLocalCamera();
    });
    
    // 每5秒请求一次更新
    setInterval(function() {
        if (socket.connected) {
            socket.emit("request_update");
        }
    }, 5000);
}

// 初始化图表
function initCharts() {
    // 情绪图表
    const emotionCtx = document.getElementById('emotion-chart').getContext('2d');
    emotionChart = new Chart(emotionCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '情绪效价',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: '情绪唤醒度',
                    data: [],
                    borderColor: 'rgb(255, 159, 64)',
                    backgroundColor: 'rgba(255, 159, 64, 0.2)',
                    tension: 0.3,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm:ss'
                        }
                    },
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    min: -1,
                    max: 1,
                    title: {
                        display: true,
                        text: '情绪效价'
                    }
                }
            }
        }
    });
    
    // 环境与生产力图表
    const environmentCtx = document.getElementById('environment-chart').getContext('2d');
    environmentChart = new Chart(environmentCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '亮度',
                    data: [],
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.2)',
                    tension: 0.2,
                    yAxisID: 'y'
                },
                {
                    label: '噪音',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.2,
                    yAxisID: 'y'
                },
                {
                    label: '生产力',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.2,
                    yAxisID: 'y'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm:ss'
                        }
                    },
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    min: 0,
                    max: 1,
                    title: {
                        display: true,
                        text: '数值'
                    }
                }
            }
        }
    });
}

// 更新仪表盘数据
function updateDashboard(data) {
    // 更新最后更新时间
    lastUpdate = new Date();
    document.getElementById('last-update-time').textContent = formatDateTime(lastUpdate);
    
    // 更新情绪数据
    if (data.emotion) {
        updateEmotionDisplay(data.emotion);
    }
    
    // 更新环境数据
    updateEnvironmentDisplay(data);
    
    // 更新输入数据
    updateInputDisplay(data);
    
    // 更新视频数据
    if (data.video) {
        updateVideoDisplay(data.video);
    }
}
'''
        
        # 添加更多Javascript函数实现
        js_content_part2 = '''
// 更新情绪显示
function updateEmotionDisplay(emotionData) {
    let emotion = "neutral";
    let valence = 0;
    let arousal = 0;
    let intensity = 0;
    
    // 根据数据类型处理
    if (typeof emotionData === 'string') {
        // 如果只有情绪名称
        emotion = emotionData;
    } else {
        // 如果是完整的情绪对象
        emotion = emotionData.emotion || "neutral";
        valence = emotionData.valence || 0;
        arousal = emotionData.arousal || 0;
        intensity = emotionData.intensity || 0;
    }
    
    // 更新情绪图标
    const emotionIcon = document.querySelector("#emotion-display i");
    const iconClass = getEmotionIconClass(emotion);
    
    // 移除所有情绪类
    emotionIcon.className = "";
    emotionIcon.classList.add("bi", iconClass, "emotion-icon");
    
    // 更新情绪名称
    document.getElementById("current-emotion").textContent = translateEmotion(emotion);
    
    // 更新情绪状态条
    document.getElementById("valence-value").textContent = valence.toFixed(2);
    document.getElementById("arousal-value").textContent = arousal.toFixed(2);
    document.getElementById("intensity-value").textContent = intensity.toFixed(2);
    
    // 更新进度条
    document.getElementById("valence-bar").style.width = `${((valence + 1) / 2 * 100)}%`;
    document.getElementById("arousal-bar").style.width = `${arousal * 100}%`;
    document.getElementById("intensity-bar").style.width = `${intensity * 100}%`;
    
    // 根据情绪效价设置颜色
    if (valence > 0.3) {
        document.getElementById("valence-bar").className = "progress-bar bg-success";
    } else if (valence < -0.3) {
        document.getElementById("valence-bar").className = "progress-bar bg-danger";
    } else {
        document.getElementById("valence-bar").className = "progress-bar bg-info";
    }
}

// 获取情绪对应的图标类
function getEmotionIconClass(emotion) {
    switch(emotion.toLowerCase()) {
        case "happy":
            return "bi-emoji-smile emotion-happy";
        case "sad":
            return "bi-emoji-frown emotion-sad";
        case "angry":
            return "bi-emoji-angry emotion-angry";
        case "fear":
            return "bi-emoji-dizzy emotion-fear";
        case "surprise":
            return "bi-emoji-astonished emotion-surprise";
        case "disgust":
            return "bi-emoji-expressionless emotion-disgust";
        case "neutral":
        default:
            return "bi-emoji-neutral emotion-neutral";
    }
}

// 更新环境显示
function updateEnvironmentDisplay(data) {
    // 获取环境数据
    const brightness = data.brightness || 0;
    const noiseLevel = data.noise_level || 0;
    const environmentType = data.environment?.environment_type || "未知";
    const environmentScore = data.environment_score || 0;
    
    // 更新显示
    document.getElementById("brightness-value").textContent = brightness.toFixed(2);
    document.getElementById("noise-value").textContent = noiseLevel.toFixed(2);
    document.getElementById("environment-type").textContent = environmentType;
    document.getElementById("environment-score").textContent = environmentScore.toFixed(2);
    
    // 更新进度条
    document.getElementById("brightness-bar").style.width = `${brightness * 100}%`;
    document.getElementById("noise-bar").style.width = `${noiseLevel * 100}%`;
    document.getElementById("environment-score-bar").style.width = `${environmentScore * 100}%`;
}

// 更新输入显示
function updateInputDisplay(data) {
    // 获取输入数据
    const typingSpeed = data.input?.typing_speed || 0;
    const focusLevel = data.input?.focus_level || 0;
    const productivityScore = data.productivity_score || 0;
    
    // 更新显示
    document.getElementById("typing-speed").textContent = Math.round(typingSpeed);
    document.getElementById("focus-level").textContent = focusLevel.toFixed(2);
    document.getElementById("productivity-score").textContent = productivityScore.toFixed(2);
    
    // 更新进度条
    document.getElementById("typing-speed-bar").style.width = `${Math.min(100, typingSpeed / 3)}%`;
    document.getElementById("focus-level-bar").style.width = `${focusLevel * 100}%`;
    document.getElementById("productivity-score-bar").style.width = `${productivityScore * 100}%`;
}
'''

        # 视频和图表相关函数
        js_content_part3 = '''
// 更新视频显示
function updateVideoDisplay(videoData) {
    // 检查是否有人脸检测
    const faceDetected = videoData.face_detected || false;
    const motionLevel = videoData.motion_level || 0;
    
    // 更新人脸检测状态
    document.getElementById("face-detection-status").textContent = faceDetected ? "已检测" : "未检测";
    document.getElementById("face-detection-status").className = faceDetected ? "text-success" : "text-secondary";
    
    // 更新运动水平
    document.getElementById("motion-level").textContent = motionLevel.toFixed(2);
}

// 初始化视频流
function initVideoStream() {
    const videoElement = document.getElementById('video-stream');
    const canvasElement = document.getElementById('video-canvas');
    const placeholderElement = document.getElementById('video-placeholder');
    
    // 先尝试从服务器获取视频帧
    socket.emit('request_video_frame');
    
    // 函数: 使用本地摄像头
    window.useLocalCamera = function() {
        console.log("尝试使用本地摄像头...");
        // 检查浏览器支持
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            // 请求摄像头权限
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(function(stream) {
                    // 显示视频元素
                    videoElement.style.display = 'block';
                    canvasElement.style.display = 'none';
                    placeholderElement.style.display = 'none';
                    
                    // 设置视频源
                    videoElement.srcObject = stream;
                    console.log("本地摄像头已激活");
                })
                .catch(function(error) {
                    console.error("无法获取摄像头访问权限:", error);
                    // 显示占位符
                    videoElement.style.display = 'none';
                    canvasElement.style.display = 'none';
                    placeholderElement.style.display = 'flex';
                });
        } else {
            console.error("浏览器不支持getUserMedia API");
            // 显示占位符
            videoElement.style.display = 'none';
            canvasElement.style.display = 'none';
            placeholderElement.style.display = 'flex';
        }
    };
}

// 更新视频帧
function updateVideoFrame(frameData) {
    if (!frameData) {
        console.error("没有接收到视频帧数据");
        return;
    }
    
    const videoElement = document.getElementById('video-stream');
    const canvasElement = document.getElementById('video-canvas');
    const placeholderElement = document.getElementById('video-placeholder');
    const ctx = canvasElement.getContext('2d');
    
    // 创建图像对象
    const img = new Image();
    img.onload = function() {
        // 设置Canvas大小与图像匹配
        canvasElement.width = img.width;
        canvasElement.height = img.height;
        
        // 绘制图像到Canvas
        ctx.drawImage(img, 0, 0);
        
        // 显示Canvas，隐藏其他元素
        videoElement.style.display = 'none';
        canvasElement.style.display = 'block';
        placeholderElement.style.display = 'none';
    };
    
    // 设置图像源
    img.src = "data:image/jpeg;base64," + frameData;
}

// 更新情绪图表
function updateEmotionChart(data) {
    if (!data || !data.length || !emotionChart) return;
    
    // 清空数据
    emotionChart.data.labels = [];
    emotionChart.data.datasets[0].data = []; // 效价
    emotionChart.data.datasets[1].data = []; // 唤醒度
    
    // 添加新数据
    data.forEach(item => {
        const timestamp = new Date(item.timestamp);
        emotionChart.data.labels.push(timestamp);
        
        // 效价数据
        emotionChart.data.datasets[0].data.push({
            x: timestamp,
            y: item.valence
        });
        
        // 唤醒度数据
        emotionChart.data.datasets[1].data.push({
            x: timestamp,
            y: item.arousal
        });
    });
    
    // 更新图表
    emotionChart.update();
}

// 更新环境图表
function updateEnvironmentChart(data, type) {
    if (!data || !data.length || !environmentChart) return;
    
    if (type === "environment") {
        // 清空环境数据
        environmentChart.data.labels = [];
        environmentChart.data.datasets[0].data = []; // 亮度
        environmentChart.data.datasets[1].data = []; // 噪音
        
        // 添加新数据
        data.forEach(item => {
            const timestamp = new Date(item.timestamp);
            environmentChart.data.labels.push(timestamp);
            
            // 亮度数据
            environmentChart.data.datasets[0].data.push({
                x: timestamp,
                y: item.brightness
            });
            
            // 噪音数据
            environmentChart.data.datasets[1].data.push({
                x: timestamp,
                y: item.noise_level
            });
        });
    } else if (type === "productivity") {
        // 生产力数据
        environmentChart.data.datasets[2].data = [];
        
        // 添加新数据
        data.forEach(item => {
            const timestamp = new Date(item.timestamp);
            
            // 生产力数据
            environmentChart.data.datasets[2].data.push({
                x: timestamp,
                y: item.productivity_score
            });
        });
    }
    
    // 更新图表
    environmentChart.update();
}

// 更新当前时间
function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = formatDateTime(now);
}

// 格式化日期时间
function formatDateTime(date) {
    const options = { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit',
        hour12: false
    };
    return date.toLocaleString('zh-CN', options);
}

// 翻译情绪名称
function translateEmotion(emotion) {
    const translations = {
        "happy": "高兴",
        "sad": "悲伤",
        "angry": "愤怒",
        "fear": "恐惧",
        "surprise": "惊讶",
        "disgust": "厌恶",
        "neutral": "中性"
    };
    
    return translations[emotion.toLowerCase()] || "未知";
}
'''

        # 合并所有JavaScript代码
        full_js_content = js_content + js_content_part2 + js_content_part3

        # 写入JavaScript文件
        with open(os.path.join(static_js_path, 'main.js'), 'w', encoding='utf-8') as f:
            f.write(full_js_content)

        logger.info("JavaScript文件创建完成")
