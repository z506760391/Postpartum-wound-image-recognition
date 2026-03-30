from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.database import db, WoundAnalysis, Patient, LearningTask
from services.adaptive_learning import AdaptiveLearningService
from utils.image_processor import ImageProcessor
from utils.logger import get_logger

logger = get_logger(__name__)
learning_bp = Blueprint('learning', __name__, url_prefix='/learning')

_learning_service = AdaptiveLearningService()
_image_processor = ImageProcessor()


@learning_bp.route('/')
def index():
    try:
        unlabeled = _learning_service.list_unlabeled_samples()
        tasks = LearningTask.query.order_by(LearningTask.created_at.desc()).limit(20).all()
        from models.database import ModelIteration
        active_model = ModelIteration.query.filter_by(is_active=True).first()
        return render_template(
            'learning/index.html',
            unlabeled=unlabeled,
            tasks=tasks,
            active_model=active_model,
        )
    except Exception as e:
        logger.error(f"学习中心首页错误: {e}")
        flash('加载失败', 'danger')
        return render_template('learning/index.html', unlabeled=[], tasks=[], active_model=None)


@learning_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    patients = Patient.query.order_by(Patient.name).all()
    if request.method == 'GET':
        return render_template('learning/upload.html', patients=patients)

    patient_id = request.form.get('patient_id')
    image_file = request.files.get('image')
    wound_stage = request.form.get('wound_stage', 'inflammation')

    if not patient_id or not image_file or image_file.filename == '':
        flash('请选择产妇并上传图像', 'danger')
        return render_template('learning/upload.html', patients=patients)

    is_valid, err = _image_processor.validate_image(image_file)
    if not is_valid:
        flash(err, 'danger')
        return render_template('learning/upload.html', patients=patients)

    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        save_path = _image_processor.save_upload(image_file, upload_folder, int(patient_id))
        image_hash = _image_processor.compute_hash(save_path)

        record = WoundAnalysis(
            patient_id=int(patient_id),
            image_path=save_path,
            image_hash=image_hash,
            wound_stage=wound_stage,
            doctor_confirmed_stage=wound_stage,
            is_labeled=True,
            used_for_training=False,
            urgency_level='normal',
            confidence_score=1.0,
        )
        db.session.add(record)
        db.session.commit()
        flash('标注样本上传成功！', 'success')
        return redirect(url_for('learning.index'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"标注上传失败: {e}")
        flash('上传失败，请重试', 'danger')
        return render_template('learning/upload.html', patients=patients)


@learning_bp.route('/label/<int:analysis_id>', methods=['POST'])
def label_sample(analysis_id):
    confirmed_stage = request.form.get('confirmed_stage', '')
    notes = request.form.get('notes', '')

    if not confirmed_stage:
        flash('请选择愈合阶段', 'danger')
        return redirect(url_for('learning.index'))

    success = _learning_service.label_sample(analysis_id, confirmed_stage, notes)
    if success:
        flash('标注成功！', 'success')
    else:
        flash('标注失败', 'danger')
    return redirect(url_for('learning.index'))


@learning_bp.route('/task/create', methods=['POST'])
def create_task():
    try:
        task_config = {
            'task_name': request.form.get('task_name', '').strip() or None,
            'task_type': request.form.get('task_type', 'fine_tune'),
            'epochs': int(request.form.get('epochs', 10)),
            'batch_size': int(request.form.get('batch_size', 8)),
            'learning_rate': float(request.form.get('learning_rate', 1e-4)),
            'adversarial_enabled': request.form.get('adversarial_enabled') == 'on',
            'epsilon': float(request.form.get('epsilon', 0.03)),
            'alpha': float(request.form.get('alpha', 0.01)),
            'steps': int(request.form.get('steps', 10)),
            'adversarial_ratio': float(request.form.get('adversarial_ratio', 0.3)),
        }
        task = _learning_service.create_task(task_config)
        _learning_service.start_training(task.id, app=current_app._get_current_object())
        flash(f'训练任务 "{task.task_name}" 已启动！', 'success')
        return redirect(url_for('learning.task_detail', task_id=task.id))
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        flash(f'创建任务失败：{e}', 'danger')
        return redirect(url_for('learning.index'))


@learning_bp.route('/task/<int:task_id>')
def task_detail(task_id):
    try:
        task = LearningTask.query.get_or_404(task_id)
        return render_template('learning/task_detail.html', task=task)
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        flash('获取任务失败', 'danger')
        return redirect(url_for('learning.index'))


@learning_bp.route('/task/<int:task_id>/progress')
def task_progress(task_id):
    progress = _learning_service.get_task_progress(task_id)
    return jsonify(progress)
