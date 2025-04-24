// MoodSense 主JavaScript文件

// 全局变量
let emotionChart = null;
let environmentChart = null;
let socket = null;
let lastUpdate = new Date();

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('文档已加载，初始化应用...');
    
    // 初始化Socket.IO连接
    initSocketConnection();
    
    // 初始化图表
    initCharts();
    
    // 更新当前时间
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    
    // 注意: 视频初始化已移至socket连接后
});

// 初始化Socket.IO连接
function initSocketConnection() {
    // 连接到服务器
    socket = io();
    
    // 连接事件
    socket.on('connect', function() {
        console.log('已连接到服务器');
        document.getElementById('connection-status').textContent = '已连接';
        document.getElementById('status-indicator').className = 'badge bg-success';
        
        // 请求初始数据
        socket.emit('request_update');
        
        // 在连接成功后初始化视频流
        initVideoStream();
    });
    
    // 断开连接事件
    socket.on('disconnect', function() {
        console.log('已断开连接');
        document.getElementById('connection-status').textContent = '已断开连接';
        document.getElementById('status-indicator').className = 'badge bg-danger';
    });
    
    // 数据更新事件
    socket.on('data_update', function(data) {
        console.log('收到数据更新:', data);
        updateDashboard(data);
    });
    
    // 情绪历史数据更新事件
    socket.on('emotion_history_update', function(data) {
        updateEmotionChart(data);
    });
    
    // 环境历史数据更新事件
    socket.on('environment_history_update', function(data) {
        updateEnvironmentChart(data, 'environment');
    });
    
    // 生产力历史数据更新事件
    socket.on('productivity_history_update', function(data) {
        updateEnvironmentChart(data, 'productivity');
    });
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
    if (data.environment) {
        updateEnvironmentDisplay(data);
    }
    
    // 更新输入数据
    if (data.input) {
        updateInputDisplay(data);
    }
    
    // 更新视频相关数据
    if (data.video) {
        updateVideoDisplay(data.video);
    }
}

// 更新情绪显示
function updateEmotionDisplay(emotionData) {
    // 更新情绪标签
    const emotion = emotionData.emotion || 'neutral';
    document.getElementById('current-emotion').textContent = translateEmotion(emotion);
    
    // 更新情绪图标
    const emotionIcon = document.querySelector('.emotion-icon');
    emotionIcon.className = 'bi emotion-icon';
    
    // 根据情绪设置图标
    switch (emotion) {
        case 'happy':
            emotionIcon.classList.add('bi-emoji-smile');
            break;
        case 'sad':
            emotionIcon.classList.add('bi-emoji-frown');
            break;
        case 'angry':
            emotionIcon.classList.add('bi-emoji-angry');
            break;
        case 'surprise':
            emotionIcon.classList.add('bi-emoji-surprise');
            break;
        case 'fear':
            emotionIcon.classList.add('bi-emoji-dizzy');
            break;
        case 'disgust':
            emotionIcon.classList.add('bi-emoji-expressionless');
            break;
        default:
            emotionIcon.classList.add('bi-emoji-neutral');
    }
    
    // 更新情绪背景
    const emotionDisplay = document.getElementById('emotion-display');
    emotionDisplay.className = 'emotion-display';
    emotionDisplay.classList.add('emotion-' + emotion);
    
    // 更新情绪数值
    const valence = emotionData.valence || 0;
    const arousal = emotionData.arousal || 0;
    const intensity = emotionData.intensity || 0;
    
    document.getElementById('valence-value').textContent = valence.toFixed(2);
    document.getElementById('arousal-value').textContent = arousal.toFixed(2);
    document.getElementById('intensity-value').textContent = intensity.toFixed(2);
    
    // 更新情绪进度条
    const valenceBar = document.getElementById('valence-bar');
    valenceBar.style.width = (50 + valence * 50) + '%';
    if (valence > 0) {
        valenceBar.className = 'progress-bar bg-success';
    } else {
        valenceBar.className = 'progress-bar bg-danger';
    }
    
    document.getElementById('arousal-bar').style.width = (arousal * 100) + '%';
    document.getElementById('intensity-bar').style.width = (intensity * 100) + '%';
}

// 更新环境显示
function updateEnvironmentDisplay(data) {
    // 提取环境数据
    const brightness = data.brightness || 0;
    const noiseLevel = data.noise_level || 0;
    const environmentType = data.environment?.environment_type || '未知';
    const environmentScore = data.environment_score || 0;
    
    // 更新显示
    document.getElementById('brightness-value').textContent = brightness.toFixed(2);
    document.getElementById('noise-value').textContent = noiseLevel.toFixed(2);
    document.getElementById('environment-type').textContent = environmentType;
    document.getElementById('environment-score').textContent = environmentScore.toFixed(2);
    
    // 更新进度条
    document.getElementById('brightness-bar').style.width = (brightness * 100) + '%';
    document.getElementById('noise-bar').style.width = (noiseLevel * 100) + '%';
    document.getElementById('environment-score-bar').style.width = (environmentScore * 100) + '%';
}

// 更新输入显示
function updateInputDisplay(data) {
    // 提取输入数据
    const typingSpeed = data.input?.typing_speed || 0;
    const focusLevel = data.input?.focus_level || 0;
    const productivityScore = data.productivity_score || 0;
    
    // 更新显示
    document.getElementById('typing-speed').textContent = Math.round(typingSpeed);
    document.getElementById('focus-level').textContent = focusLevel.toFixed(2);
    document.getElementById('productivity-score').textContent = productivityScore.toFixed(2);
    
    // 更新进度条
    document.getElementById('typing-speed-bar').style.width = Math.min(100, (typingSpeed / 300) * 100) + '%';
    document.getElementById('focus-level-bar').style.width = (focusLevel * 100) + '%';
    document.getElementById('productivity-score-bar').style.width = (productivityScore * 100) + '%';
}

// 更新视频显示
function updateVideoDisplay(videoData) {
    // 更新人脸检测状态
    const faceDetected = videoData.face_detected || false;
    document.getElementById('face-detection-status').textContent = faceDetected ? '已检测' : '未检测';
    
    // 更新运动水平
    const motionLevel = videoData.motion_level || 0;
    document.getElementById('motion-level').textContent = motionLevel.toFixed(2);
    
    // 如果有视频帧数据，更新视频显示
    if (videoData.frame_data) {
        updateVideoFrame(videoData.frame_data);
    }
}

// 初始化视频流
function initVideoStream() {
    console.log('初始化视频流');
    const videoPlaceholder = document.getElementById('video-placeholder');
    const videoElement = document.getElementById('video-stream');
    const videoCanvas = document.getElementById('video-canvas');
    
    if (!videoPlaceholder || !videoElement || !videoCanvas) {
        console.error('视频元素不存在！', {
            placeholder: videoPlaceholder,
            video: videoElement,
            canvas: videoCanvas
        });
        return;
    }
    
    console.log('注册视频帧事件监听器');
    // 通过Socket.IO接收视频帧
    socket.on('video_frame', function(frameData) {
        console.log('收到视频帧数据', frameData ? '有效' : '无效');
        if (frameData && frameData.data) {
            // 隐藏占位符，显示视频
            videoPlaceholder.style.display = 'none';
            videoCanvas.style.display = 'block';
            
            // 更新视频帧
            updateVideoFrame(frameData.data);
        }
    });
    
    // 主动请求视频帧
    socket.emit('request_video_frame');
    
    // 定时请求视频帧更新
    setInterval(function() {
        socket.emit('request_video_frame');
    }, 1000); // 每秒请求一次
    
    // 显示静态图片代替摄像头
    function displayStaticImage() {
        console.log('显示静态演示图片');
        const staticImgUrl = 'https://placehold.co/600x400/4287f5/ffffff?text=MoodSense+演示画面';
        
        const img = new Image();
        img.onload = function() {
            const canvas = document.getElementById('video-canvas');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                
                // 添加演示文字
                ctx.font = '20px Arial';
                ctx.fillStyle = 'white';
                ctx.textAlign = 'center';
                ctx.fillText('命令行启动时系统可提供真实视频画面', canvas.width/2, canvas.height/2 + 30);
                
                // 显示canvas并隐藏占位符
                canvas.style.display = 'block';
                videoPlaceholder.style.display = 'none';
            }
        };
        img.src = staticImgUrl;
    }
    
    // 尝试从本地摄像头获取视频
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        // 仅在未收到服务器视频流时尝试
        socket.on('no_server_video', function() {
            console.log('尝试使用本地摄像头');
            
            // 首先尝试使用本地摄像头
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                } 
            })
            .then(function(stream) {
                videoElement.srcObject = stream;
                videoElement.style.display = 'block';
                videoPlaceholder.style.display = 'none';
                console.log('成功获取摄像头数据流');
            })
            .catch(function(error) {
                console.error('无法访问摄像头:', error);
                // 如果无法访问摄像头，显示静态演示图片
                displayStaticImage();
            });
        });
    } else {
        // 如果浏览器不支持摄像头API，直接显示静态演示图片
        console.warn('浏览器不支持摄像头API');
        socket.on('no_server_video', displayStaticImage);
    }
}

// 更新视频帧
function updateVideoFrame(frameData) {
    const videoCanvas = document.getElementById('video-canvas');
    if (!videoCanvas) {
        console.error('无法找到canvas元素');
        return;
    }
    
    const ctx = videoCanvas.getContext('2d');
    if (!ctx) {
        console.error('无法获取2D上下文');
        return;
    }
    
    console.log('开始处理视频帧数据');
    // 创建图像数据
    const img = new Image();
    
    // 设置图像源前添加错误处理
    img.onerror = function(e) {
        console.error('图像加载错误:', e);
    };
    
    img.onload = function() {
        console.log('图像已加载，尺寸:', img.width, 'x', img.height);
        // 设置canvas尺寸与图像一致
        videoCanvas.width = img.width;
        videoCanvas.height = img.height;
        
        // 绘制图像
        ctx.drawImage(img, 0, 0, videoCanvas.width, videoCanvas.height);
        
        // 显示canvas
        videoCanvas.style.display = 'block';
        // 隐藏占位符
        document.getElementById('video-placeholder').style.display = 'none';
    };
    
    // 设置图像源
    const imgSrc = 'data:image/jpeg;base64,' + frameData;
    console.log('设置图像源:', imgSrc.substring(0, 50) + '...');
    img.src = imgSrc;
}

// 更新情绪图表
function updateEmotionChart(data) {
    if (!emotionChart || !data || data.length === 0) return;
    
    // 准备数据
    const labels = [];
    const valenceData = [];
    const arousalData = [];
    
    // 解析数据
    data.forEach(item => {
        const time = new Date(item.timestamp);
        labels.push(time);
        valenceData.push({
            x: time,
            y: item.valence || 0
        });
        arousalData.push({
            x: time,
            y: item.arousal || 0
        });
    });
    
    // 更新图表数据
    emotionChart.data.labels = labels;
    emotionChart.data.datasets[0].data = valenceData;
    emotionChart.data.datasets[1].data = arousalData;
    
    // 更新图表
    emotionChart.update();
}

// 更新环境图表
function updateEnvironmentChart(data, type) {
    if (!environmentChart || !data || data.length === 0) return;
    
    // 准备数据
    const labels = [];
    const brightnessData = [];
    const noiseData = [];
    const productivityData = [];
    
    // 解析数据
    data.forEach(item => {
        const time = new Date(item.timestamp);
        labels.push(time);
        
        if (type === 'environment') {
            brightnessData.push({
                x: time,
                y: item.brightness || 0
            });
            noiseData.push({
                x: time,
                y: item.noise_level || 0
            });
        }
        
        if (type === 'productivity') {
            productivityData.push({
                x: time,
                y: item.productivity_score || 0
            });
        }
    });
    
    // 更新图表数据
    environmentChart.data.labels = labels;
    
    if (type === 'environment') {
        environmentChart.data.datasets[0].data = brightnessData;
        environmentChart.data.datasets[1].data = noiseData;
    }
    
    if (type === 'productivity') {
        environmentChart.data.datasets[2].data = productivityData;
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
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 翻译情绪名称
function translateEmotion(emotion) {
    const translations = {
        'happy': '高兴',
        'sad': '悲伤',
        'angry': '生气',
        'surprise': '惊讶',
        'fear': '恐惧',
        'disgust': '厌恶',
        'neutral': '中性'
    };
    
    return translations[emotion] || '未知';
}
