// MoodSense 主JavaScript文件

// 全局变量
let emotionChart = null;
let environmentChart = null;
let socket = null;
let lastUpdate = new Date();

// 安全更新方法 (使用与环境显示相同的方法)
const updateElement = (id, value, isText = true) => {
    const element = document.getElementById(id);
    if (element) {
        if (isText) {
            element.textContent = value;
        } else {
            element.style.width = value;
        }
    }
};

// 当文档加载完成时初始化
document.addEventListener('DOMContentLoaded', function () {
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
    socket.on('connect', function () {
        console.log('已连接到服务器');
        document.getElementById('connection-status').textContent = '已连接';
        document.getElementById('status-indicator').className = 'badge bg-success';

        // 请求初始数据
        socket.emit('request_update');

        // 在连接成功后初始化视频流
        initVideoStream();
    });

    // 断开连接事件
    socket.on('disconnect', function () {
        console.log('已断开连接');
        document.getElementById('connection-status').textContent = '已断开连接';
        document.getElementById('status-indicator').className = 'badge bg-danger';
    });

    // 数据更新事件
    socket.on('data_update', function (data) {
        console.log('收到数据更新:', data);
        updateDashboard(data);
    });

    // 情绪历史数据更新事件
    socket.on('emotion_history_update', function (data) {
        updateEmotionChart(data);
    });

    // 环境历史数据更新事件
    socket.on('environment_history_update', function (data) {
        updateEnvironmentChart(data, 'environment');
    });

    // 生产力历史数据更新事件
    socket.on('productivity_history_update', function (data) {
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
    try {
        // 提取环境数据
        const brightness = data.brightness || 0;
        const noiseLevel = data.noise_level || 0;
        const environmentType = data.environment?.environment_type || '未知';
        const environmentScore = data.environment_score || 0;

        // 更新文本内容
        updateElement('brightness-value', brightness.toFixed(2));
        updateElement('noise-value', noiseLevel.toFixed(2));
        updateElement('environment-type', environmentType);

        // 更新环境评分 - 检查两个可能的元素ID
        updateElement('environment-score', environmentScore.toFixed(2));
        updateElement('environment-score', Math.round(environmentScore * 100) + '/100');

        // 更新进度条
        updateElement('brightness-bar', (brightness * 100) + '%', false);
        updateElement('noise-bar', (noiseLevel * 100) + '%', false);

        // HTML中没有environment-score-bar元素，跳过这个更新
        // environment-score-bar保留以便将来可能添加
    } catch (error) {
        console.error('更新环境显示时出错:', error);
    }
}

// 更新输入显示
function updateInputDisplay(data) {
    try {
        // 提取输入数据
        const typingSpeed = data.input?.typing_speed || 0;
        const focusLevel = data.input?.focus_level || 0;
        const productivityScore = data.productivity_score || 0;



        // 更新显示
        updateElement('typing-speed', Math.round(typingSpeed));
        updateElement('typing-error-rate', (data.input?.typing_errors || 0).toFixed(2) + '%');
        updateElement('backspace-rate', (data.input?.backspace_rate || 0).toFixed(2) + '%');
        updateElement('focus-level', focusLevel.toFixed(2));

        // 下面的元素可能不存在，使用安全方法
        updateElement('productivity-score', productivityScore.toFixed(2));

        // 更新进度条
        updateElement('typing-speed-bar', Math.min(100, (typingSpeed / 300) * 100) + '%', false);
        updateElement('typing-error-bar', ((data.input?.typing_errors || 0) * 100) + '%', false);
        updateElement('backspace-rate-bar', ((data.input?.backspace_rate || 0) * 100) + '%', false);
        updateElement('focus-level-bar', (focusLevel * 100) + '%', false);
        updateElement('productivity-score-bar', (productivityScore * 100) + '%', false);
    } catch (error) {
        console.error('更新输入显示时出错:', error);
    }
}

// 更新视频显示
function updateVideoDisplay(videoData) {
    try {

        // 更新人脸检测状态
        const faceDetected = videoData.face_detected || false;
        updateElement('face-detection-status', faceDetected ? '已检测' : '未检测');

        // 更新运动水平
        const motionLevel = videoData.motion_level || 0;
        updateElement('motion-level', motionLevel.toFixed(2));

        // 如果有视频帧数据，更新视频显示
        if (videoData.frame_data) {
            updateVideoFrame(videoData.frame_data);
        }
    } catch (error) {
        console.error('更新视频显示时出错:', error);
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

    // 调试输出视频容器元素状态
    console.log('视频容器状态:', {
        placeholderDisplay: videoPlaceholder.style.display,
        canvasDisplay: videoCanvas.style.display,
        placeholderHeight: videoPlaceholder.style.height,
        parentElement: videoPlaceholder.parentElement.id
    });

    console.log('注册视频帧事件监听器');
    // 通过Socket.IO接收视频帧 - 增强版本
    socket.on('video_frame', function (frameData) {
        console.log('✅ 收到视频帧数据', frameData ? '有效' : '无效');

        if (frameData && frameData.data) {
            console.log(`✅ 视频帧数据长度: ${frameData.data.length} [时间: ${new Date().toISOString()}]`);

            // 测试直接显示图像 - 将base64数据设置为背景图片
            document.getElementById('video-container').style.backgroundImage = `url(data:image/jpeg;base64,${frameData.data})`;
            document.getElementById('video-container').style.backgroundRepeat = 'no-repeat';
            document.getElementById('video-container').style.backgroundPosition = 'center';
            document.getElementById('video-container').style.backgroundSize = 'contain';

            // 隐藏占位符
            if (videoPlaceholder) videoPlaceholder.style.display = 'none';

            // 更新人脸检测状态
            document.getElementById('face-detection-status').textContent = '摄像头工作中';
            document.getElementById('face-detection-status').style.color = '#28a745';

            // 同时也尝试使用Canvas方式显示
            try {
                updateVideoFrame(frameData.data);
            } catch (error) {
                console.error('使用Canvas更新视频帧失败:', error);
            }
        } else {
            console.warn('视频帧数据不可用或格式错误');
            // 显示错误状态
            if (videoPlaceholder) videoPlaceholder.style.display = 'flex';
            document.getElementById('face-detection-status').textContent = '无数据';
            document.getElementById('face-detection-status').style.color = '#dc3545';
        }
    });

    // 主动请求视频帧
    socket.emit('request_video_frame');

    // 初始化请求视频帧
    let videoFrameTimer = null;

    // 定时请求视频帧更新函数
    function startRequestingVideoFrames(interval = 500) {
        // 清除现有定时器
        if (videoFrameTimer) {
            clearInterval(videoFrameTimer);
        }

        console.log(`开始请求视频帧, 间隔: ${interval}ms`);

        // 立即请求第一帧
        socket.emit('request_video_frame');

        // 设置新的定时器
        videoFrameTimer = setInterval(function () {
            socket.emit('request_video_frame');
        }, interval);

        return videoFrameTimer;
    }

    // 接收服务器视频不可用的通知
    socket.on('no_server_video', function () {
        console.warn('服务器视频不可用');
        // 显示占位符
        if (videoPlaceholder) videoPlaceholder.style.display = 'flex';
        // 更新状态显示
        document.getElementById('face-detection-status').textContent = '摄像头不可用';
        document.getElementById('face-detection-status').style.color = '#dc3545';
    });

    // 启动视频帧请求
    startRequestingVideoFrames(500);
}

// 更新视频帧
function updateVideoFrame(frameData) {
    console.log('开始处理视频帧，数据长度:', frameData.length);

    // 获取视频元素
    const videoCanvas = document.getElementById('video-canvas');
    const videoPlaceholder = document.getElementById('video-placeholder');

    if (!videoCanvas) {
        console.error('无法找到canvas元素');
        return;
    }

    // 确保画布可见
    videoCanvas.style.display = 'block';

    // 如果有占位符，隐藏它
    if (videoPlaceholder) {
        videoPlaceholder.style.display = 'none';
    }

    const ctx = videoCanvas.getContext('2d');
    if (!ctx) {
        console.error('无法获取2D上下文');
        return;
    }

    // 先确保画布大小适合
    const containerWidth = videoCanvas.parentElement.clientWidth;
    videoCanvas.width = containerWidth;
    videoCanvas.height = Math.min(220, containerWidth * 0.75); // 高度为宽度的75%，最大220px

    console.log('设置画布尺寸:', videoCanvas.width, 'x', videoCanvas.height);

    // 创建新图像并加载视频帧
    const img = new Image();

    // 为原始图像添加事件处理
    img.onload = function () {
        console.log('✅ 视频帧图像加载成功，尺寸:', img.width, 'x', img.height);

        // 清除画布
        ctx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);

        // 计算纵横比保持的绘制区域
        const canvasRatio = videoCanvas.width / videoCanvas.height;
        const imgRatio = img.width / img.height;

        let drawWidth, drawHeight, offsetX = 0, offsetY = 0;

        if (canvasRatio > imgRatio) {
            // 画布更宽，适应高度
            drawHeight = videoCanvas.height;
            drawWidth = drawHeight * imgRatio;
            offsetX = (videoCanvas.width - drawWidth) / 2;
        } else {
            // 画布更高，适应宽度
            drawWidth = videoCanvas.width;
            drawHeight = drawWidth / imgRatio;
            offsetY = (videoCanvas.height - drawHeight) / 2;
        }

        // 绘制图像，保持纵横比
        ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

        // 添加时间戳
        ctx.font = '10px Arial';
        ctx.fillStyle = 'rgba(0, 255, 0, 0.7)';
        ctx.fillText(new Date().toLocaleTimeString(), 5, videoCanvas.height - 5);

        // 调试信息
        console.log('✅ 视频帧渲染完成');
    };

    img.onerror = function (err) {
        console.error('❌ 视频帧图像加载失败:', err);

        // 在画布上显示错误信息
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, videoCanvas.width, videoCanvas.height);
        ctx.font = '14px Arial';
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.fillText('视频帧加载失败', videoCanvas.width / 2, videoCanvas.height / 2 - 10);
        ctx.fillText('正在尝试重连...', videoCanvas.width / 2, videoCanvas.height / 2 + 10);
    };

    // 为确保 Base64 数据正确，检查并清理可能的空格或换行符
    let cleanedFrameData = frameData.trim();

    // 设置图像源
    const imgSrc = 'data:image/jpeg;base64,' + cleanedFrameData;
    console.log('设置图像源长度:', imgSrc.length);
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
