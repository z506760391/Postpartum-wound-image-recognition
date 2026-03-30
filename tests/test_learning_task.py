"""
tests/test_learning_task.py
回归测试：验证自适应学习任务在 task_name 缺失/空白时也能成功创建。
"""
import sys
import os
import json
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def app():
    """创建测试用 Flask 应用（SQLite 内存数据库）"""
    from app import create_app
    test_app = create_app('development')
    test_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    with test_app.app_context():
        from models.database import db
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def learning_service(app):
    """在应用上下文内返回 AdaptiveLearningService 实例"""
    from services.adaptive_learning import AdaptiveLearningService
    with app.app_context():
        yield AdaptiveLearningService()


# ─────────────────────── 服务层测试 ────────────────────────


class TestCreateTaskService:
    """直接测试 AdaptiveLearningService.create_task"""

    def test_create_task_with_explicit_name(self, app):
        """提供任务名称时，应原样存储"""
        from services.adaptive_learning import AdaptiveLearningService
        from models.database import LearningTask
        with app.app_context():
            svc = AdaptiveLearningService()
            task = svc.create_task({'task_name': '第1轮微调', 'epochs': 3, 'batch_size': 4})
            assert task is not None
            assert task.task_name == '第1轮微调'
            # 数据库中确实存在
            stored = LearningTask.query.get(task.id)
            assert stored is not None
            assert stored.task_name == '第1轮微调'

    def test_create_task_with_empty_name_generates_default(self, app):
        """task_name 为空字符串时，应自动生成以 'Adaptive_' 开头的名称"""
        from services.adaptive_learning import AdaptiveLearningService
        from models.database import LearningTask
        with app.app_context():
            svc = AdaptiveLearningService()
            task = svc.create_task({'task_name': '', 'epochs': 3})
            assert task is not None
            assert task.task_name  # 不为空
            assert task.task_name.startswith('Adaptive_'), (
                f"期望以 'Adaptive_' 开头，实际得到: {task.task_name!r}"
            )
            stored = LearningTask.query.get(task.id)
            assert stored is not None
            assert stored.task_name == task.task_name

    def test_create_task_with_none_name_generates_default(self, app):
        """task_name 为 None 时，应自动生成默认名称，不应引发 IntegrityError"""
        from services.adaptive_learning import AdaptiveLearningService
        from models.database import LearningTask
        with app.app_context():
            svc = AdaptiveLearningService()
            task = svc.create_task({'task_name': None, 'epochs': 2})
            assert task is not None
            assert task.task_name  # 不为空/None
            stored = LearningTask.query.get(task.id)
            assert stored is not None

    def test_create_task_without_name_key_generates_default(self, app):
        """task_config 完全不含 task_name 键时，应自动生成默认名称"""
        from services.adaptive_learning import AdaptiveLearningService
        from models.database import LearningTask
        with app.app_context():
            svc = AdaptiveLearningService()
            task = svc.create_task({'epochs': 2, 'batch_size': 4})
            assert task is not None
            assert task.task_name
            stored = LearningTask.query.get(task.id)
            assert stored is not None

    def test_create_task_with_whitespace_only_name_generates_default(self, app):
        """task_name 仅含空白字符时，应自动生成默认名称"""
        from services.adaptive_learning import AdaptiveLearningService
        with app.app_context():
            svc = AdaptiveLearningService()
            task = svc.create_task({'task_name': '   ', 'epochs': 2})
            assert task is not None
            assert task.task_name.strip()  # 不应为纯空白


# ─────────────────────── 路由层测试 ────────────────────────


class TestCreateTaskRoute:
    """测试 POST /learning/task/create 接口"""

    def _post_create(self, client, form_data):
        return client.post(
            '/learning/task/create',
            data=form_data,
            follow_redirects=True
        )

    def test_route_with_task_name(self, client, app):
        """提交含 task_name 的表单，页面不应出现错误"""
        with app.app_context():
            resp = self._post_create(client, {
                'task_name': '测试任务',
                'task_type': 'fine_tune',
                'epochs': '3',
                'batch_size': '4',
                'learning_rate': '0.0001',
            })
        # 重定向后成功（不论训练本身是否需要样本）
        assert resp.status_code == 200

    def test_route_without_task_name_no_integrity_error(self, client, app):
        """提交不含 task_name 的表单时，不应出现 IntegrityError，而应优雅处理"""
        with app.app_context():
            resp = self._post_create(client, {
                'task_name': '',
                'task_type': 'fine_tune',
                'epochs': '2',
                'batch_size': '4',
                'learning_rate': '0.0001',
            })
        assert resp.status_code == 200
        # 确认响应中没有 IntegrityError 字样
        body = resp.data.decode('utf-8', errors='ignore')
        assert 'IntegrityError' not in body
        assert 'NOT NULL constraint' not in body


# ─────────────────────── 模型层测试 ────────────────────────


class TestLearningTaskModel:
    """验证 LearningTask ORM 模型层 default"""

    def test_model_default_task_name(self, app):
        """直接构造 LearningTask 不传 task_name，ORM default 应生效"""
        from models.database import db, LearningTask
        with app.app_context():
            task = LearningTask(
                task_type='fine_tune',
                epochs=5,
                batch_size=8,
                learning_rate=1e-4,
                status='pending',
                created_by='test',
            )
            db.session.add(task)
            db.session.commit()
            assert task.task_name  # default 已填充
            assert task.id is not None
