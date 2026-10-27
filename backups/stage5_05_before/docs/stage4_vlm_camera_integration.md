# Stage 4 - Camera -> SmolVLM2 RKNN + RKLLM MVP

This archive integrates the previously verified `vlm_joint_smoke.cpp` backend into the CLI application. It is a proposed patch, **not board-verified**.

## On RK3576

Install as a replacement or copy changes into your existing project only after backing up the original source tree.
The model files stay outside this archive; do not delete existing `models/`.

```bash
cd ~/projects/RK3576/rk3576_multimodal
cmake -S . -B build/vlm_stage4 -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=OFF -DBUILD_WITH_VLM=ON -DBUILD_WITH_RKLLM=OFF -DENABLE_SHERPA_ASR=OFF
cmake --build build/vlm_stage4 --parallel 4
./build/vlm_stage4/rk3576_multimodal \
 --device /dev/video11 \
 --vlm-model models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm \
 --vision-model models/vlm/smolvlm_vision_scatterfix_rk3576.rknn
```

Inside CLI, wait a moment for Camera frames, run `stats`, then enter `当前画面有什么` or `current image: What do you see?` (currently router supports `current image` and `what do you see`). Quit with `exit`.

## MVP limitations

- Packed one-plane NV12 3840x2160; stride checked. No DMA-BUF nor RGA.
- CPU bilinear Y/nearest UV BT.709 limited-range conversion; approximates, does not exactly match Pillow Lanczos; colorspace/range must be verified on actual ISP output.
- SmolVLM2 single crop 512x512 and 64 image tokens, so image details and accuracy are limited.
- Both RKNN and RKLLM models are resident during CLI session. When adding Qwen LLM and TTS, profile memory first (no swap on board).
- Language quality previously showed hallucinations, even with PyTorch; pipeline PASS does not imply semantic accuracy.
- Audio ASR and TTS are not yet connected in this patch.
