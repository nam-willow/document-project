# str_predictor.py
# ─────────────────────────────────────────────────────────────────────────────
# deep-text-recognition-benchmark를 개인 프로젝트에서 사용하기 위한 Wrapper
# 원본 레포 파일을 수정하지 않고, 이 파일만 추가하면 된다.
#
# 지원 입력 타입:
#   - str  : 이미지 파일 경로 (e.g. "/tmp/word.png")
#   - Path : pathlib.Path 객체
#   - PIL.Image.Image : 이미 열린 PIL 이미지
#   - numpy.ndarray   : OpenCV로 읽은 BGR 배열
#   - bytes           : 파일을 바이트로 읽은 경우 (API multipart 수신 시)
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Union, List

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

# ── 원본 레포 모듈 (레포 루트가 sys.path에 있어야 함) ──
from app.ml.deep_text_recognition_benchmark.model import Model
from app.ml.deep_text_recognition_benchmark.utils import AttnLabelConverter, CTCLabelConverter
from app.ml.deep_text_recognition_benchmark.dataset import AlignCollate

logger = logging.getLogger(__name__)

# ── 지원 입력 타입 alias ──
ImageInput = Union[str, Path, Image.Image, np.ndarray, bytes]


@dataclass
class STRResult:
    """STR 추론 결과 단일 레코드"""
    text: str           # 예측 텍스트
    confidence: float   # 0.0 ~ 1.0 사이 신뢰도
    elapsed_ms: float   # 추론 소요 시간(ms)


class STRPredictor:
    """
    deep-text-recognition-benchmark 모델을 단일 이미지/배치 입력으로 사용할 수 있는 Wrapper.

    사용 예:
        predictor = STRPredictor(
            saved_model="app/ml/deep_text_recognition_benchmark/saved_models/TPS-ResNet-BiLSTM-Attn.pth",
            Transformation="TPS",
            FeatureExtraction="ResNet",
            SequenceModeling="BiLSTM",
            Prediction="Attn",
        )
        result = predictor.predict("path/to/image.png")
        print(result.text, result.confidence)
    """

    def __init__(
        self,
        saved_model: str,
        Transformation: str = "TPS",
        FeatureExtraction: str = "ResNet",
        SequenceModeling: str = "BiLSTM",
        Prediction: str = "Attn",
        imgH: int = 32,
        imgW: int = 100,
        batch_max_length: int = 25,
        character: str = "0123456789abcdefghijklmnopqrstuvwxyz",
        num_fiducial: int = 20,
        input_channel: int = 1,
        output_channel: int = 512,
        hidden_size: int = 256,
        device: str | None = None,
    ):
        # ── 디바이스 설정 ──────────────────────────────────────────────────
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        logger.info(f"[STRPredictor] device={self.device}")

        # ── argparse 대신 내부 opt 객체로 파라미터 관리 ──────────────────
        # 원본 코드가 opt.XXX 형태로 파라미터를 참조하므로 동일 구조 유지
        class _Opt:
            pass

        opt = _Opt()
        opt.Transformation = Transformation
        opt.FeatureExtraction = FeatureExtraction
        opt.SequenceModeling = SequenceModeling
        opt.Prediction = Prediction
        opt.imgH = imgH
        opt.imgW = imgW
        opt.batch_max_length = batch_max_length
        opt.character = character
        opt.num_fiducial = num_fiducial
        opt.input_channel = input_channel
        opt.output_channel = output_channel
        opt.hidden_size = hidden_size
        opt.sensitive = False  # 소문자 정규화 (True면 대소문자 구분)
        opt.PAD = False
        self.opt = opt

        # ── LabelConverter 초기화 ─────────────────────────────────────────
        # Attn: [GO], [s] 토큰 포함 / CTC: 기본 문자셋만
        if Prediction == "Attn":
            self.converter = AttnLabelConverter(opt.character)
        else:
            self.converter = CTCLabelConverter(opt.character)
        opt.num_class = len(self.converter.character)

        # ── 이미지 전처리기 초기화 ────────────────────────────────────────
        self.align_collate = AlignCollate(
            imgH=imgH, imgW=imgW, keep_ratio_with_pad=opt.PAD
        )

        # ── 모델 빌드 + 가중치 로드 ───────────────────────────────────────
        self.model = Model(opt)
        self.model = torch.nn.DataParallel(self.model).to(self.device)

        print(f"saved_model: {saved_model}")
        saved_path = Path(saved_model)
        if not saved_path.exists():
            raise FileNotFoundError(f"모델 파일 없음: {saved_path}")

        state_dict = torch.load(saved_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()  # ← 반드시 eval() 호출 (BN/Dropout 추론 모드)
        logger.info(f"[STRPredictor] 모델 로드 완료: {saved_path}")

    # ── 핵심 public 메서드 ────────────────────────────────────────────────

    def predict(self, image: ImageInput) -> STRResult:
        """
        단일 이미지를 받아 텍스트 예측 결과를 반환한다.

        Args:
            image: 파일경로(str/Path), PIL Image, numpy array, bytes 중 하나

        Returns:
            STRResult(text, confidence, elapsed_ms)

        Raises:
            ValueError: 지원하지 않는 입력 타입일 때
            RuntimeError: 모델 추론 실패 시
        """
        t0 = time.perf_counter()
        pil_img = self._to_pil(image)
        tensor = self._preprocess(pil_img)

        with torch.no_grad():
            text_for_pred, _ = self.converter.encode(
                [""], batch_max_length=self.opt.batch_max_length
            )
            preds = self.model(tensor, text_for_pred, is_train=False)

            # ── Attention 디코딩 ──────────────────────────────────────────
            if self.opt.Prediction == "Attn":
                preds_prob = F.softmax(preds, dim=2)
                preds_max_prob, preds_index = preds_prob.max(dim=2)

                # [s] (EOS) 토큰 이전까지만 사용
                pred_str = self.converter.decode(
                    preds_index[:, 1:], torch.IntTensor([preds_index.size(1) - 1])
                )[0]

                # EOS 이전 confidence 누적곱
                pred_eos = pred_str.find("[s]")
                pred_str = pred_str[:pred_eos] if pred_eos != -1 else pred_str
                conf = (
                    preds_max_prob[0, : len(pred_str)].cumprod(dim=0)[-1].item()
                    if pred_str
                    else 0.0
                )

            # ── CTC 디코딩 ────────────────────────────────────────────────
            else:
                preds_size = torch.IntTensor([preds.size(1)])
                _, preds_index = preds.max(2)
                preds_index = preds_index.view(-1)
                pred_str = self.converter.decode(preds_index, preds_size)[0]
                conf = 0.0  # CTC는 confidence 계산 별도 구현 필요

        elapsed = (time.perf_counter() - t0) * 1000
        logger.debug(f"[STRPredictor] '{pred_str}' conf={conf:.4f} ({elapsed:.1f}ms)")
        return STRResult(text=pred_str, confidence=round(conf, 4), elapsed_ms=round(elapsed, 2))

    def predict_batch(self, images: List[ImageInput]) -> List[STRResult]:
        """
        여러 이미지를 배치로 처리한다. 단건 반복 대비 GPU 활용률이 높다.

        주의: 배치 크기가 크면 VRAM OOM 발생 가능 → batch_size 32 이하 권장
        """
        t0 = time.perf_counter()
        pil_images = [self._to_pil(img) for img in images]

        # AlignCollate는 list를 받아 배치 텐서를 반환한다
        tensor, _ = self.align_collate([(img, "") for img in pil_images])
        tensor = tensor.to(self.device)

        with torch.no_grad():
            length_for_pred = torch.IntTensor([self.opt.batch_max_length] * len(images))
            text_for_pred = torch.LongTensor(
                len(images), self.opt.batch_max_length + 1
            ).fill_(0).to(self.device)

            preds = self.model(tensor, text_for_pred, is_train=False)

        results = []
        if self.opt.Prediction == "Attn":
            preds_prob = F.softmax(preds, dim=2)
            preds_max_prob, preds_index = preds_prob.max(dim=2)
            pred_strs = self.converter.decode(preds_index[:, 1:], length_for_pred)
            for i, pred_str in enumerate(pred_strs):
                eos = pred_str.find("[s]")
                text = pred_str[:eos] if eos != -1 else pred_str
                conf = (
                    preds_max_prob[i, : len(text)].cumprod(dim=0)[-1].item()
                    if text
                    else 0.0
                )
                results.append(
                    STRResult(text=text, confidence=round(conf, 4), elapsed_ms=0.0)
                )
        else:
            preds_size = torch.IntTensor([preds.size(1)] * len(images))
            _, preds_index = preds.max(2)
            preds_index = preds_index.view(-1)
            pred_strs = self.converter.decode(preds_index, preds_size)
            results = [STRResult(text=s, confidence=0.0, elapsed_ms=0.0) for s in pred_strs]

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[STRPredictor] batch={len(images)} ({elapsed:.1f}ms)")
        return results

    # ── 내부 유틸 메서드 ──────────────────────────────────────────────────

    def _to_pil(self, image: ImageInput) -> Image.Image:
        """다양한 입력 타입을 PIL 그레이스케일 이미지로 통일한다."""
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"이미지 파일 없음: {path}")
            return Image.open(path).convert("L")

        if isinstance(image, Image.Image):
            return image.convert("L")

        if isinstance(image, np.ndarray):
            # OpenCV BGR → PIL grayscale
            if image.ndim == 3:
                image = image[:, :, ::-1]  # BGR → RGB
            return Image.fromarray(image).convert("L")

        if isinstance(image, bytes):
            return Image.open(BytesIO(image)).convert("L")

        raise ValueError(
            f"지원하지 않는 이미지 타입: {type(image)}. "
            "str/Path/PIL.Image/np.ndarray/bytes 중 하나를 사용하세요."
        )

    def _preprocess(self, pil_img: Image.Image) -> torch.Tensor:
        """PIL 이미지 → 모델 입력 텐서 (AlignCollate 활용)"""
        tensor, _ = self.align_collate([(pil_img, "")])
        return tensor.to(self.device)