# config.py - 系统全局配置
import os
from datetime import timedelta

class Config:
    # ========== 基础配置 ==========
    SECRET_KEY = os.environ.get('SECRET_KEY', 'postpartum-care-secret-2026')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # ========== 数据库配置 ==========
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///postpartum_care.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ========== 文件上传配置 ==========
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'webp'}
    
    # ========== 百度AI配置 ==========
    BAIDU_API_KEY = os.environ.get('BAIDU_API_KEY', 'your_baidu_api_key_here')
    BAIDU_SECRET_KEY = os.environ.get('BAIDU_SECRET_KEY', 'your_baidu_secret_key_here')
    BAIDU_TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
    BAIDU_IMAGE_CLASSIFY_URL = 'https://aip.baidubce.com/rest/2.0/image-classify/v2/advanced_general'
    BAIDU_BODY_ANALYSIS_URL = 'https://aip.baidubce.com/rest/2.0/image-classify/v1/body_attr'
    BAIDU_TOKEN_EXPIRE = timedelta(days=29)  # token有效期留1天余量
    
    # ========== 模型配置 ==========
    MODEL_SAVE_PATH = os.path.join(os.path.dirname(__file__), 'model_weights')
    MODEL_ITERATION_LOG = os.path.join(os.path.dirname(__file__), 'logs', 'model_iterations.json')
    
    # ========== 自适应学习配置 ==========
    LEARNING_BATCH_SIZE = 8
    LEARNING_EPOCHS = 10
    LEARNING_LR = 1e-4
    MIN_SAMPLES_FOR_TRAINING = 5  # 最少样本数才触发训练
    
    # ========== 对抗训练配置 ==========
    ADVERSARIAL_EPSILON = 0.03       # FGSM扰动幅度
    ADVERSARIAL_ALPHA = 0.01         # PGD步长
    ADVERSARIAL_STEPS = 10           # PGD迭代步数
    ADVERSARIAL_RATIO = 0.3          # 对抗样本占训练集比例
    
    # ========== 伤口识别阶段定义 ==========
    WOUND_STAGES = {
        'inflammation': {
            'name': '炎症期',
            'days': '1-5天',
            'description': '伤口处于早期愈合阶段，轻微红肿属正常现象',
            'color': '#FF6B6B'
        },
        'proliferation': {
            'name': '增生期',
            'days': '5-21天',
            'description': '新生组织开始生长，伤口逐渐收缩',
            'color': '#FFD93D'
        },
        'maturation': {
            'name': '成熟期',
            'days': '21天以上',
            'description': '伤口基本愈合，瘢痕组织形成',
            'color': '#6BCB77'
        },
        'abnormal': {
            'name': '异常状态',
            'days': '需及时就医',
            'description': '伤口出现感染、裂开等异常情况',
            'color': '#FF0000'
        }
    }
    
    # ========== 伤口感染启发式检测配置 ==========
    # 颜色比例阈值（HSV色调范围内像素占总像素比例）
    INFECTION_RED_RATIO_THRESHOLD = 0.15      # 红色区域占比超过此值提示炎症
    INFECTION_YELLOW_GREEN_RATIO_THRESHOLD = 0.08  # 黄绿色区域占比超过此值提示化脓
    INFECTION_HIGH_SATURATION_THRESHOLD = 0.20     # 高饱和局部区域比例超过此值
    # 综合感染风险评分阈值（0-1），超过此值标记为 infection 异常
    INFECTION_RISK_SCORE_THRESHOLD = 0.45
    # 色彩特征权重（各分量对最终感染风险评分的权重，合计应≤1）
    INFECTION_WEIGHT_RED = 0.40
    INFECTION_WEIGHT_YELLOW_GREEN = 0.40
    INFECTION_WEIGHT_HIGH_SATURATION = 0.20

    # ========== 日志配置 ==========
    LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'logs')
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False

class ProductionConfig(Config):
    DEBUG = False

config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}