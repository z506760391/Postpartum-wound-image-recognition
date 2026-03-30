/* 产后伤口智能护理系统 - 主要JavaScript */

document.addEventListener('DOMContentLoaded', function () {
    initDropZone();
    initProgressAnimation();
});

// ---- 拖拽上传与预览 ----
function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('imageInput');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const fileName = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const analysisForm = document.getElementById('analysisForm');

    if (!dropZone) return;

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, e => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            imageInput.files = files;
            showPreview(files[0]);
        }
    });

    dropZone.addEventListener('click', () => imageInput.click());

    if (imageInput) {
        imageInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                showPreview(this.files[0]);
            }
        });
    }

    function showPreview(file) {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = e => {
            if (imagePreview) imagePreview.src = e.target.result;
            if (fileName) fileName.textContent = `已选择：${file.name}（${file.size >= 1048576 ? (file.size / 1048576).toFixed(1) + ' MB' : (file.size / 1024).toFixed(1) + ' KB'}）`;
            if (previewContainer) previewContainer.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
    }

    // 表单提交时显示进度条
    if (analysisForm) {
        analysisForm.addEventListener('submit', function () {
            if (uploadProgress) uploadProgress.classList.remove('d-none');
            if (submitBtn) submitBtn.disabled = true;
            animateProgressBar(progressBar, 0, 90, 3000);
        });
    }
}

// ---- 进度条动画 ----
function animateProgressBar(bar, from, to, duration) {
    if (!bar) return;
    const start = performance.now();
    function step(now) {
        const elapsed = now - start;
        const progress = Math.min(from + (to - from) * (elapsed / duration), to);
        bar.style.width = progress + '%';
        if (elapsed < duration) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

function initProgressAnimation() {
    document.querySelectorAll('.progress-bar[data-animate]').forEach(bar => {
        const target = parseFloat(bar.dataset.animate) || 0;
        animateProgressBar(bar, 0, target, 800);
    });
}

// ---- AJAX产妇搜索 ----
function searchPatients(query) {
    if (query.length < 1) return;
    fetch(`/patients/?q=${encodeURIComponent(query)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(r => r.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const tbody = doc.querySelector('tbody');
            const localTbody = document.querySelector('tbody');
            if (tbody && localTbody) localTbody.innerHTML = tbody.innerHTML;
        })
        .catch(console.error);
}

// ---- 训练进度轮询（由 task_detail.html 使用） ----
function pollTrainingProgress(taskId, intervalMs, onUpdate) {
    return setInterval(function () {
        fetch(`/learning/task/${taskId}/progress`)
            .then(r => r.json())
            .then(data => onUpdate(data))
            .catch(console.error);
    }, intervalMs);
}
