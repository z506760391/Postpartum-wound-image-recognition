from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.database import db, Patient, WoundAnalysis, ModelIteration, LearningTask
from utils.logger import get_logger

logger = get_logger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
def dashboard():
    try:
        total_patients = Patient.query.count()
        total_analyses = WoundAnalysis.query.count()
        total_models = ModelIteration.query.count()
        active_model = ModelIteration.query.filter_by(is_active=True).first()
        pending_tasks = LearningTask.query.filter(
            LearningTask.status.in_(['pending', 'running'])
        ).count()
        return render_template(
            'admin/dashboard.html',
            total_patients=total_patients,
            total_analyses=total_analyses,
            total_models=total_models,
            active_model=active_model,
            pending_tasks=pending_tasks,
        )
    except Exception as e:
        logger.error(f"管理后台首页错误: {e}")
        flash('加载失败', 'danger')
        return render_template('admin/dashboard.html',
                               total_patients=0, total_analyses=0,
                               total_models=0, active_model=None, pending_tasks=0)


@admin_bp.route('/models')
def model_records():
    try:
        models = ModelIteration.query.order_by(ModelIteration.created_at.desc()).all()
        return render_template('admin/model_records.html', models=models)
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        flash('获取模型列表失败', 'danger')
        return render_template('admin/model_records.html', models=[])


@admin_bp.route('/models/<version>/activate', methods=['POST'])
def activate_model(version):
    try:
        # 取消所有激活
        ModelIteration.query.update({'is_active': False})
        # 激活指定版本
        model = ModelIteration.query.filter_by(version=version).first_or_404()
        model.is_active = True
        db.session.commit()
        flash(f'模型 {version} 已激活', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"激活模型失败: {e}")
        flash('激活失败', 'danger')
    return redirect(url_for('admin.model_records'))


@admin_bp.route('/models/<version>/detail')
def model_detail(version):
    try:
        model = ModelIteration.query.filter_by(version=version).first_or_404()
        task = None
        if model.learning_task_id:
            task = LearningTask.query.get(model.learning_task_id)
        return render_template('admin/model_detail.html', model=model, task=task)
    except Exception as e:
        logger.error(f"获取模型详情失败: {e}")
        flash('获取模型详情失败', 'danger')
        return redirect(url_for('admin.model_records'))
