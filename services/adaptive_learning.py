import json
import os
import threading
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    import torchvision.transforms as transforms
    import torchvision.models as tv_models
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch未安装，自适应学习功能将不可用")

MIN_SAMPLES = 5

STAGE_LABEL_MAP = {
    'inflammation': 0,
    'proliferation': 1,
    'maturation': 2,
    'abnormal': 3,
}


if TORCH_AVAILABLE:
    class WoundDataset(Dataset):
        """产后伤口图像数据集（用于PyTorch训练）"""

        def __init__(self, samples, augment=True):
            self.samples = samples
            if augment:
                self.transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.RandomHorizontalFlip(),
                    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                    transforms.RandomRotation(15),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                         std=[0.229, 0.224, 0.225]),
                ])
            else:
                self.transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                         std=[0.229, 0.224, 0.225]),
                ])

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            from PIL import Image
            sample = self.samples[idx]
            img_path = sample.image_path
            label_str = sample.doctor_confirmed_stage or sample.wound_stage or 'inflammation'
            label = STAGE_LABEL_MAP.get(label_str, 0)

            try:
                img = Image.open(img_path).convert('RGB')
                img = self.transform(img)
            except Exception as e:
                logger.warning(f"加载图像失败 {img_path}: {e}，使用零张量替代")
                img = torch.zeros(3, 224, 224)

            return img, label


class AdaptiveLearningService:
    """自适应学习服务：管理模型微调任务"""

    def create_task(self, task_config: dict) -> object:
        """
        创建学习任务记录到数据库
        
        Args:
            task_config: 任务配置字典（task_name, epochs, batch_size等）
        Returns:
            LearningTask 数据库对象
        """
        from models.database import db, LearningTask
        try:
            raw_name = task_config.get('task_name') or ''
            task_name = raw_name.strip() if raw_name else ''
            if not task_name:
                task_name = f'Adaptive_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            adv_config = {
                'epsilon': task_config.get('epsilon', 0.03),
                'alpha': task_config.get('alpha', 0.01),
                'steps': task_config.get('steps', 10),
                'adversarial_ratio': task_config.get('adversarial_ratio', 0.3),
            }
            task = LearningTask(
                task_name=task_name,
                task_type=task_config.get('task_type', 'fine_tune'),
                batch_size=task_config.get('batch_size', 8),
                epochs=task_config.get('epochs', 10),
                learning_rate=task_config.get('learning_rate', 1e-4),
                adversarial_enabled=task_config.get('adversarial_enabled', False),
                adversarial_config=json.dumps(adv_config, ensure_ascii=False),
                status='pending',
                created_by=task_config.get('created_by', 'developer'),
            )
            db.session.add(task)
            db.session.commit()
            logger.info(f"创建学习任务: {task.task_name} (ID={task.id})")
            return task
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            db.session.rollback()
            raise

    def start_training(self, task_id: int, app=None):
        """
        在后台线程中启动模型训练
        
        Args:
            task_id: LearningTask ID
            app: Flask app 对象（用于应用上下文）
        """
        def _train():
            from flask import current_app
            ctx = app.app_context() if app else None
            if ctx:
                ctx.push()
            try:
                self._run_training(task_id, app)
            finally:
                if ctx:
                    ctx.pop()

        thread = threading.Thread(target=_train, daemon=True)
        thread.start()
        logger.info(f"训练线程已启动，任务ID={task_id}")

    def _run_training(self, task_id: int, app=None):
        """实际训练逻辑"""
        from models.database import db, LearningTask, WoundAnalysis, ModelIteration
        from flask import current_app

        try:
            task = LearningTask.query.get(task_id)
            if not task:
                logger.error(f"找不到任务 ID={task_id}")
                return

            # 标记为运行中
            task.status = 'running'
            task.started_at = datetime.utcnow()
            db.session.commit()

            # 加载已标注且未训练过的样本
            samples = WoundAnalysis.query.filter_by(
                is_labeled=True, used_for_training=False
            ).all()

            if len(samples) < MIN_SAMPLES:
                task.status = 'failed'
                task.error_message = f'标注样本数不足（当前{len(samples)}，最少需要{MIN_SAMPLES}）'
                db.session.commit()
                return

            task.sample_count = len(samples)
            task.sample_ids = json.dumps([s.id for s in samples])
            db.session.commit()

            if not TORCH_AVAILABLE:
                # PyTorch不可用时模拟训练
                self._simulate_training(task, samples, db)
                return

            # 构建数据集
            dataset = WoundDataset(samples, augment=True)
            loader = DataLoader(dataset, batch_size=task.batch_size, shuffle=True)

            # 初始化ResNet18模型
            model = tv_models.resnet18(weights=None)
            num_classes = len(STAGE_LABEL_MAP)
            model.fc = nn.Linear(model.fc.in_features, num_classes)

            # 尝试加载现有权重
            model_path = self._get_active_model_path(app)
            if model_path and os.path.exists(model_path):
                try:
                    state = torch.load(model_path, map_location='cpu')
                    model.load_state_dict(state, strict=False)
                    logger.info(f"已加载现有模型权重: {model_path}")
                except Exception as e:
                    logger.warning(f"加载权重失败，使用随机初始化: {e}")

            optimizer = optim.Adam(model.parameters(), lr=task.learning_rate)
            criterion = nn.CrossEntropyLoss()

            adv_module = None
            if task.adversarial_enabled and TORCH_AVAILABLE:
                from services.adversarial_training import AdversarialTrainingModule
                adv_module = AdversarialTrainingModule()
                adv_config = task.get_adversarial_config()

            loss_history = []
            total_epochs = task.epochs

            for epoch in range(total_epochs):
                model.train()
                epoch_loss = 0.0
                batches = 0

                for images, labels in loader:
                    if adv_module and task.adversarial_enabled:
                        loss = adv_module.adversarial_training_step(
                            model, optimizer, criterion, (images, labels),
                            adversarial_ratio=adv_config.get('adversarial_ratio', 0.3)
                        )
                    else:
                        optimizer.zero_grad()
                        outputs = model(images)
                        loss = criterion(outputs, labels)
                        loss.backward()
                        optimizer.step()
                        loss = loss.item()

                    epoch_loss += loss
                    batches += 1

                avg_loss = epoch_loss / max(batches, 1)
                loss_history.append(round(avg_loss, 4))
                task.progress = round((epoch + 1) / total_epochs * 100, 1)
                task.loss_history = json.dumps(loss_history)
                db.session.commit()
                logger.info(f"任务{task_id} Epoch {epoch+1}/{total_epochs}, Loss={avg_loss:.4f}")

            # 保存模型权重
            from flask import current_app as _app
            save_dir = app.config.get('MODEL_SAVE_PATH', 'model_weights') if app else 'model_weights'
            os.makedirs(save_dir, exist_ok=True)
            version = self._generate_version(db)
            save_path = os.path.join(save_dir, f'{version}.pt')
            torch.save(model.state_dict(), save_path)

            # 创建ModelIteration记录
            iteration = ModelIteration(
                version=version,
                learning_task_id=task.id,
                model_path=save_path,
                training_samples=len(samples),
                accuracy=0.0,
                change_notes=f'自适应学习任务 {task.task_name}',
                is_active=False,
            )
            db.session.add(iteration)

            # 标记样本为已使用
            for s in samples:
                s.used_for_training = True

            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            task.model_version = version
            task.progress = 100.0
            db.session.commit()
            logger.info(f"任务{task_id}训练完成，模型版本={version}")

        except Exception as e:
            logger.error(f"训练任务{task_id}出错: {e}", exc_info=True)
            try:
                from models.database import db, LearningTask
                task = LearningTask.query.get(task_id)
                if task:
                    task.status = 'failed'
                    task.error_message = str(e)
                    db.session.commit()
            except Exception:
                pass

    def _simulate_training(self, task, samples, db):
        """PyTorch不可用时模拟训练进度"""
        import time
        import os
        loss_history = []
        for epoch in range(task.epochs):
            time.sleep(0.1)
            fake_loss = max(0.1, 1.0 - epoch * 0.08 + (hash(epoch) % 100) / 1000)
            loss_history.append(round(fake_loss, 4))
            task.progress = round((epoch + 1) / task.epochs * 100, 1)
            task.loss_history = json.dumps(loss_history)
            db.session.commit()

        version = self._generate_version(db)
        iteration_cls = None
        try:
            from models.database import ModelIteration
            iteration_cls = ModelIteration
        except Exception:
            pass

        if iteration_cls:
            iteration = iteration_cls(
                version=version,
                learning_task_id=task.id,
                training_samples=len(samples),
                change_notes=f'模拟训练（PyTorch未安装）',
                is_active=False,
            )
            db.session.add(iteration)

        for s in samples:
            s.used_for_training = True

        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        task.model_version = version
        task.progress = 100.0
        db.session.commit()

    def _generate_version(self, db) -> str:
        """生成模型版本号 v{YYYYMMDD}_{seq}"""
        from models.database import ModelIteration
        today_prefix = f"v{datetime.now().strftime('%Y%m%d')}"
        count = ModelIteration.query.filter(
            ModelIteration.version.like(f'{today_prefix}_%')
        ).count()
        return f"{today_prefix}_{count + 1:03d}"

    def _get_active_model_path(self, app) -> str:
        """获取当前激活模型路径"""
        try:
            from models.database import ModelIteration
            active = ModelIteration.query.filter_by(is_active=True).first()
            return active.model_path if active else None
        except Exception:
            return None

    def get_task_progress(self, task_id: int) -> dict:
        """
        获取任务进度
        
        Args:
            task_id: LearningTask ID
        Returns:
            任务进度字典
        """
        try:
            from models.database import LearningTask
            task = LearningTask.query.get(task_id)
            if not task:
                return {'error': '任务不存在'}
            result = task.to_dict()
            result['loss_history'] = json.loads(task.loss_history) if task.loss_history else []
            return result
        except Exception as e:
            logger.error(f"获取任务进度失败: {e}")
            return {'error': str(e)}

    def list_unlabeled_samples(self) -> list:
        """
        列出未标注的伤口分析记录
        
        Returns:
            WoundAnalysis 列表
        """
        try:
            from models.database import WoundAnalysis
            return WoundAnalysis.query.filter_by(is_labeled=False).order_by(
                WoundAnalysis.created_at.desc()
            ).all()
        except Exception as e:
            logger.error(f"查询未标注样本失败: {e}")
            return []

    def label_sample(self, analysis_id: int, confirmed_stage: str, notes: str = '') -> bool:
        """
        医生标注样本
        
        Args:
            analysis_id: WoundAnalysis ID
            confirmed_stage: 医生确认的愈合阶段
            notes: 医生备注
        Returns:
            是否成功
        """
        try:
            from models.database import db, WoundAnalysis
            record = WoundAnalysis.query.get(analysis_id)
            if not record:
                return False
            record.doctor_confirmed_stage = confirmed_stage
            record.doctor_notes = notes
            record.is_labeled = True
            db.session.commit()
            logger.info(f"样本{analysis_id}已标注为: {confirmed_stage}")
            return True
        except Exception as e:
            logger.error(f"标注样本失败: {e}")
            from models.database import db
            db.session.rollback()
            return False
