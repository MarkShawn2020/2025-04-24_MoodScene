# MoodSense - 环境识别与情绪感知系统

MoodSense 是一个综合性的环境识别与情绪感知系统，可以实时分析环境参数和用户状态，提供智能化的情绪和环境感知能力。系统通过多传感器融合和实时数据分析，为用户提供全方位的环境与情绪状态感知。

## 功能特点

- **实时音视频分析**：捕获并处理摄像头视频流和麦克风音频流
- **环境监测**：分析环境亮度、噪音水平、室内活动等参数
- **人体运动状态检测**：通过MediaPipe识别人体姿态和动作
- **面部情绪识别**：支持多种面部情绪检测方法（DeepFace/Face Recognition/OpenCV）
- **语音情绪分析**：基于音量、音调等特征分析说话情绪
- **用户行为监控**：分析打字速度、鼠标活动、屏幕内容变化等
- **综合情绪评估**：融合多模态数据提供整体情绪状态分析
- **实时数据可视化**：基于Web的实时交互式仪表盘（Flask+SocketIO）

## 系统架构

系统由以下核心模块组成：

1. **VideoAnalyzer**：视频捕获与分析，检测人脸、姿态和动作
2. **AudioAnalyzer**：音频捕获与分析，处理声音特征和语音情绪
3. **EnvironmentAnalyzer**：环境数据整合与分析，评估环境状态
4. **EmotionDetector**：多模态情绪识别，融合面部、语音和行为数据
5. **InputMonitor**：用户输入行为监控，分析打字和鼠标活动
6. **DataIntegrator**：数据整合与分析，提供综合评分和历史记录
7. **Dashboard**：Web仪表盘，可视化展示实时数据和趋势

## 系统需求

- Python 3.8+
- 摄像头和麦克风设备
- 支持OpenCV的操作系统（Windows/macOS/Linux）
- 安装依赖中列出的Python包

## 安装与运行

```bash
# 克隆仓库
git clone https://github.com/username/moodsense.git
cd moodsense

# 创建虚拟环境（可选但推荐）
python -m venv venv
source venv/bin/activate  # 在Windows上使用: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

启动后，系统将自动:
1. 初始化各个分析模块
2. 开始捕获音视频数据
3. 启动Web仪表盘服务（默认端口8080）
4. 访问 http://localhost:8080 查看实时数据可视化

## 依赖兼容性

系统经过多种环境测试，支持多种配置：
- 如未安装DeepFace，系统会自动降级使用Face Recognition或OpenCV进行面部分析
- 通过配置可适应不同的输入设备和计算能力

详细依赖列表请参见`requirements.txt`文件。

## Web仪表盘

系统提供基于Flask和SocketIO的实时Web仪表盘：
- 环境状态监控
- 用户情绪趋势图
- 生产力指标可视化
- 实时视频流显示

## 开发者信息

开发于 2025-04-24
版本：1.0.0
