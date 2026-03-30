# models/database.py - 数据库模型定义
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json
import uuid

db = SQLAlchemy()

class Patient(db.Model):
    """产妇信息模型"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, comment='姓名')
    age = db.Column(db.Integer, nullable=False, comment='年龄')
    delivery_method = db.Column(db.String(20), nullable=False, comment='分娩方式: vaginal/cesarean')
    delivery_date = db.Column(db.Date, nullable=False, comment='分娩日期')
    health_conditions = db.Column(db.Text, default='', comment='身体状况（糖尿病/高血压等）')
    allergies = db.Column(db.Text, default='', comment='过敏史')
    bmi = db.Column(db.Float, comment='BMI指数')
    gravidity = db.Column(db.Integer, default=1, comment='妊娠次数')
    parity = db.Column(db.Integer, default=1, comment='分娩次数')
    contact_phone = db.Column(db.String(20), comment='联系电话')
    emotional_state = db.Column(db.String(20), default='stable', comment='情绪状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联分析记录
    analyses = db.relationship('WoundAnalysis', backref='patient', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'delivery_method': self.delivery_method,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'health_conditions': self.health_conditions,
            'bmi': self.bmi,
            'gravidity': self.gravidity,
            'parity': self.parity
        }


class WoundAnalysis(db.Model):
    """伤口分析记录模型"""
    __tablename__ = 'wound_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False, comment='图像存储路径')
    image_hash = db.Column(db.String(64), comment='图像MD5哈希')
    
    # 伤口分析结果
    wound_stage = db.Column(db.String(30), comment='愈合阶段')
    confidence_score = db.Column(db.Float, comment='置信度')
    anomaly_detected = db.Column(db.Boolean, default=False, comment='是否检测到异常')
    anomaly_types = db.Column(db.Text, comment='异常类型JSON列表')
    baidu_raw_result = db.Column(db.Text, comment='百度API原始返回JSON')
    
    # 护理指导
    care_guidance = db.Column(db.Text, comment='个性化护理指导')
    humancare_message = db.Column(db.Text, comment='人文关怀内容')
    urgency_level = db.Column(db.String(10), default='normal', comment='紧急程度: low/normal/high/emergency')
    
    # 医生确认（用于自适应学习）
    doctor_confirmed_stage = db.Column(db.String(30), comment='医生确认的愈合阶段')
    doctor_notes = db.Column(db.Text, comment='医生备注')
    is_labeled = db.Column(db.Boolean, default=False, comment='是否已标注（用于训练）')
    used_for_training = db.Column(db.Boolean, default=False, comment='是否已用于训练')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_anomaly_types(self):
        if self.anomaly_types:
            return json.loads(self.anomaly_types)
        return []
    
    def set_anomaly_types(self, types_list):
        self.anomaly_types = json.dumps(types_list, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'wound_stage': self.wound_stage,
            'confidence_score': self.confidence_score,
            'anomaly_detected': self.anomaly_detected,
            'anomaly_types': self.get_anomaly_types(),
            'care_guidance': self.care_guidance,
            'humancare_message': self.humancare_message,
            'urgency_level': self.urgency_level,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class LearningTask(db.Model):
    """自适应学习任务模型"""
    __tablename__ = 'learning_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(
        db.String(100), nullable=False,
        default=lambda: f'Task-{uuid.uuid4().hex[:8]}',
        comment='任务名称'
    )
    task_type = db.Column(db.String(30), default='fine_tune', comment='任务类型: fine_tune/adversarial/full_retrain')
    
    # 训练配置
    batch_size = db.Column(db.Integer, default=8)
    epochs = db.Column(db.Integer, default=10)
    learning_rate = db.Column(db.Float, default=1e-4)
    adversarial_enabled = db.Column(db.Boolean, default=False, comment='是否启用对抗训练')
    adversarial_config = db.Column(db.Text, comment='对抗训练配置JSON')
    
    # 数据集信息
    sample_count = db.Column(db.Integer, default=0, comment='训练样本数')
    sample_ids = db.Column(db.Text, comment='参与训练的样本ID列表JSON')
    
    # 任务状态
    status = db.Column(db.String(20), default='pending', comment='pending/running/completed/failed')
    progress = db.Column(db.Float, default=0.0, comment='训练进度 0-100')
    
    # 训练结果
    accuracy_before = db.Column(db.Float, comment='训练前准确率')
    accuracy_after = db.Column(db.Float, comment='训练后准确率')
    loss_history = db.Column(db.Text, comment='损失历史JSON')
    model_version = db.Column(db.String(50), comment='生成的模型版本')
    error_message = db.Column(db.Text, comment='错误信息')
    
    created_by = db.Column(db.String(50), default='developer', comment='创建者')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, comment='开始训练时间')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    
    def get_adversarial_config(self):
        if self.adversarial_config:
            return json.loads(self.adversarial_config)
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_name': self.task_name,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'sample_count': self.sample_count,
            'adversarial_enabled': self.adversarial_enabled,
            'accuracy_before': self.accuracy_before,
            'accuracy_after': self.accuracy_after,
            'model_version': self.model_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class ModelIteration(db.Model):
    """模型迭代记录模型"""
    __tablename__ = 'model_iterations'
    
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(50), unique=True, nullable=False, comment='模型版本号')
    learning_task_id = db.Column(db.Integer, db.ForeignKey('learning_tasks.id'), comment='来源任务ID')
    
    # 模型性能指标
    accuracy = db.Column(db.Float, comment='准确率')
    precision = db.Column(db.Float, comment='精确率')
    recall = db.Column(db.Float, comment='召回率')
    f1_score = db.Column(db.Float, comment='F1分数')
    adversarial_robustness = db.Column(db.Float, comment='对抗鲁棒性评分')
    
    # 模型信息
    model_path = db.Column(db.String(500), comment='模型权重路径')
    training_samples = db.Column(db.Integer, comment='训练样本数')
    is_active = db.Column(db.Boolean, default=False, comment='是否为当前激活版本')
    change_notes = db.Column(db.Text, comment='版本变更说明')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'version': self.version,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'adversarial_robustness': self.adversarial_robustness,
            'training_samples': self.training_samples,
            'is_active': self.is_active,
            'change_notes': self.change_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }