# Postpartum-wound-image-recognition
postpartum_wound_care/
├── app.py                          # Flask主应用入口
├── config.py                       # 系统配置
├── requirements.txt                # 依赖包
├── models/
│   ├── __init__.py
│   ├── database.py                 # 数据库模型
│   └── schemas.py                  # 数据验证模式
├── services/
│   ├── __init__.py
│   ├── baidu_ai.py                 # 百度AI接口封装
│   ├── wound_analyzer.py           # 伤口分析核心服务
│   ├── care_guidance.py            # 护理指导生成服务
│   ├── adaptive_learning.py        # 自适应学习模块
│   └── adversarial_training.py     # 对抗训练模块
├── routes/
│   ├── __init__.py
│   ├── patient.py                  # 产妇相关路由
│   ├── analysis.py                 # 图像分析路由
│   ├── learning.py                 # 自适应学习路由
│   └── admin.py                    # 管理员路由
├── utils/
│   ├── __init__.py
│   ├── image_processor.py          # 图像预处理工具
│   ├── humancare_generator.py      # 人文关怀内容生成
│   └── logger.py                   # 日志工具
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── upload.html
│   ├── result.html
│   ├── learning.html
│   └── admin/
│       ├── dashboard.html
│       └── model_records.html
└── static/
    ├── css/style.css
    └── js/main.js
