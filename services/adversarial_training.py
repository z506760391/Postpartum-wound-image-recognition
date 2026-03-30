from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch未安装，对抗训练功能将不可用")


class AdversarialTrainingModule:
    """对抗训练模块：FGSM / PGD 攻击与混合训练"""

    def generate_fgsm_examples(self, model, images, labels, epsilon=0.03):
        """
        FGSM对抗样本生成
        
        Args:
            model: PyTorch模型
            images: 输入图像张量
            labels: 真实标签张量
            epsilon: 扰动幅度
        Returns:
            对抗样本张量，或原始图像（PyTorch不可用时）
        """
        if not TORCH_AVAILABLE:
            return images

        try:
            images = images.clone().detach().requires_grad_(True)
            criterion = nn.CrossEntropyLoss()

            model.eval()
            outputs = model(images)
            loss = criterion(outputs, labels)
            model.zero_grad()
            loss.backward()

            perturbation = epsilon * images.grad.sign()
            adv_images = (images + perturbation).detach().clamp(0, 1)
            return adv_images
        except Exception as e:
            logger.error(f"FGSM生成失败: {e}")
            return images

    def generate_pgd_examples(self, model, images, labels,
                               epsilon=0.03, alpha=0.01, steps=10):
        """
        PGD对抗样本生成（投影梯度下降）
        
        Args:
            model: PyTorch模型
            images: 输入图像张量
            labels: 真实标签张量
            epsilon: 最大扰动幅度
            alpha: 每步步长
            steps: 迭代步数
        Returns:
            对抗样本张量
        """
        if not TORCH_AVAILABLE:
            return images

        try:
            criterion = nn.CrossEntropyLoss()
            ori_images = images.clone().detach()
            adv_images = images.clone().detach()

            # 随机初始化
            adv_images = adv_images + torch.empty_like(adv_images).uniform_(-epsilon, epsilon)
            adv_images = adv_images.clamp(0, 1).detach()

            model.eval()
            for _ in range(steps):
                adv_images.requires_grad_(True)
                outputs = model(adv_images)
                loss = criterion(outputs, labels)
                model.zero_grad()
                loss.backward()

                adv_images = adv_images.detach() + alpha * adv_images.grad.sign()
                delta = torch.clamp(adv_images - ori_images, -epsilon, epsilon)
                adv_images = (ori_images + delta).clamp(0, 1).detach()

            return adv_images
        except Exception as e:
            logger.error(f"PGD生成失败: {e}")
            return images

    def adversarial_training_step(self, model, optimizer, criterion,
                                   clean_batch, adversarial_ratio=0.3):
        """
        混合对抗训练步骤：部分样本替换为对抗样本
        
        Args:
            model: PyTorch模型
            optimizer: 优化器
            criterion: 损失函数
            clean_batch: (images, labels) 元组
            adversarial_ratio: 对抗样本比例
        Returns:
            本步骤损失值
        """
        if not TORCH_AVAILABLE:
            return 0.0

        try:
            images, labels = clean_batch
            batch_size = images.size(0)
            adv_count = max(1, int(batch_size * adversarial_ratio))

            adv_images = self.generate_fgsm_examples(model, images[:adv_count], labels[:adv_count])

            mixed_images = torch.cat([adv_images, images[adv_count:]], dim=0)
            mixed_labels = labels

            model.train()
            optimizer.zero_grad()
            outputs = model(mixed_images)
            loss = criterion(outputs, mixed_labels)
            loss.backward()
            optimizer.step()

            return loss.item()
        except Exception as e:
            logger.error(f"对抗训练步骤失败: {e}")
            return 0.0

    def evaluate_robustness(self, model, test_loader, epsilon=0.03) -> float:
        """
        评估模型对抗鲁棒性
        
        Args:
            model: PyTorch模型
            test_loader: 测试数据加载器
            epsilon: 扰动幅度
        Returns:
            鲁棒性评分（对抗样本准确率，0-1）
        """
        if not TORCH_AVAILABLE:
            return 0.0

        try:
            correct = 0
            total = 0
            model.eval()

            for images, labels in test_loader:
                adv_images = self.generate_fgsm_examples(model, images, labels, epsilon=epsilon)
                with torch.no_grad():
                    outputs = model(adv_images)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)

            score = correct / max(total, 1)
            logger.info(f"鲁棒性评分: {score:.4f} (epsilon={epsilon}, 样本数={total})")
            return round(score, 4)
        except Exception as e:
            logger.error(f"鲁棒性评估失败: {e}")
            return 0.0
