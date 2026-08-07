"""
RankInfoNet — Kaggle-PC 0.8956 model architecture.
Uses a ResNet50 backbone with a ranking head for score prediction.
"""
import torch.nn as nn
from torchvision import models


class RankInfoNet(nn.Module):
    def __init__(self, dropout_rate=0.5):
        super(RankInfoNet, self).__init__()
        self.backbone = models.resnet50(weights=None)
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        self.rank_head = nn.Sequential(
            nn.Linear(num_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(128, 1),
        )

    def forward(self, x):
        features = self.backbone(x)
        score = self.rank_head(features)
        return score.squeeze(-1)