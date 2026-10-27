#include <stddef.h>  // rkllm.h uses size_t but does not include it itself.
#include "ai/rk_backends.h"
#include "video/image_preprocessor.h"
#include "common/image_profile.h"
#include <fstream>
#include <cstdlib>
#include "rknn_api.h"
#include "rkllm.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {
constexpr size_t kWidth = 512;
constexpr size_t kHeight = 512;
constexpr size_t kImageBytes = kWidth * kHeight * 3;
constexpr size_t kEmbeddingFloats = 64 * 576;
constexpr uint32_t kNV12 = uint32_t('N') | (uint32_t('V') << 8) |
                          (uint32_t('1') << 16) | (uint32_t('2') << 24);

// Own only a successfully acquired output; never copy SDK ownership.
struct RknnOutputOwner {
    rknn_context context;
    rknn_output output{};
    bool acquired = false;

    explicit RknnOutputOwner(rknn_context ctx) : context(ctx) {}
    RknnOutputOwner(const RknnOutputOwner&) = delete;
    RknnOutputOwner& operator=(const RknnOutputOwner&) = delete;
    ~RknnOutputOwner() noexcept {
        if (acquired) {
            auto begin=ImageProfile::Clock::now();
            const int code=rknn_outputs_release(context,1,&output);
            imageSample("rknn_outputs_release",ImageProfile::ms(begin));
            if(code)std::cerr<<"[RKNN release ERROR] ret="<<code<<'\n';
        }
    }
};

struct GenerationState {
    std::string text;
    bool finished = false;
    bool failed = false;
};

int onLlmResult(RKLLMResult* result, void* userdata, LLMCallState state) {
    auto* out = static_cast<GenerationState*>(userdata);
    if (!out) return 0;
    try {
        if (state == RKLLM_RUN_FINISH) out->finished = true;
        if (state == RKLLM_RUN_ERROR) out->failed = true;
        if (state == RKLLM_RUN_NORMAL && result && result->text)
            out->text += result->text;
    } catch (...) { out->failed = true; }
    return 0;
}
}  // namespace

struct RK3576VLMBackend::Impl {
    std::string rkllmPath;
    std::string rknnPath;
    rknn_context rknn = 0;
    LLMHandle llm = nullptr;
    RKLLMParam params{};
    RKLLMCallback callbacks{};
    std::size_t dump_counter=0;

    ~Impl() { close(); }
    void close() noexcept {
        if (llm) { rkllm_destroy(llm); llm = nullptr; }
        if (rknn) { rknn_destroy(rknn); rknn = 0; }
    }
};

RK3576VLMBackend::RK3576VLMBackend() = default;
RK3576VLMBackend::~RK3576VLMBackend() { shutdown(); }

bool RK3576VLMBackend::initialize(const BackendConfig& config, std::string& error) {
    shutdown();
    error.clear();
    if (config.model_path.empty() || config.vision_model_path.empty()) {
        error = "Both --vlm-model and --vision-model are required";
        return false;
    }
    auto next = std::make_unique<Impl>();
    next->rkllmPath = config.model_path;
    next->rknnPath = config.vision_model_path;
    int ret = rknn_init(&next->rknn,
                        const_cast<char*>(next->rknnPath.c_str()), 0, 0, nullptr);
    if (ret != 0) { error = "rknn_init failed: " + std::to_string(ret); return false; }
    rknn_input_output_num io{};
    ret = rknn_query(next->rknn, RKNN_QUERY_IN_OUT_NUM, &io, sizeof(io));
    if (ret != 0 || io.n_input != 1 || io.n_output != 1) {
        error = "Vision model must have one input and one output";
        return false;
    }
    rknn_tensor_attr input_attr{};
    input_attr.index = 0;
    rknn_tensor_attr output_attr{};
    output_attr.index = 0;
    if (rknn_query(next->rknn, RKNN_QUERY_INPUT_ATTR, &input_attr, sizeof(input_attr)) != 0 ||
        rknn_query(next->rknn, RKNN_QUERY_OUTPUT_ATTR, &output_attr, sizeof(output_attr)) != 0 ||
        input_attr.n_elems != kImageBytes || output_attr.n_elems != kEmbeddingFloats) {
        error = "Vision RKNN is not 512x512x3 -> 64x576";
        return false;
    }

    std::cout<<"[VisionTensor] input_type="<<input_attr.type<<" input_fmt="<<input_attr.fmt
             <<" input_elems="<<input_attr.n_elems<<" input_w_stride="<<input_attr.w_stride
             <<" input_size="<<input_attr.size<<" input_size_with_stride="<<input_attr.size_with_stride
             <<" output_elems="<<output_attr.n_elems<<" output_type="<<output_attr.type<<" input_dims=";
    for(uint32_t i=0;i<input_attr.n_dims;++i)std::cout<<input_attr.dims[i]<<',';
    std::cout<<" output_dims=";for(uint32_t i=0;i<output_attr.n_dims;++i)std::cout<<output_attr.dims[i]<<',';
    std::cout<<"\n";
    next->params = rkllm_createDefaultParam();
    next->params.model_path = next->rkllmPath.c_str();
    next->params.max_context_len = 2048;
    next->params.max_new_tokens = 96;
    next->params.top_k = 1;
    next->params.skip_special_token = true;
    next->params.is_async = false;
    next->params.extend_param.base_domain_id = 1;
    next->callbacks.result_callback = onLlmResult;
    ret = rkllm_init(&next->llm, &next->params, &next->callbacks);
    if (ret != 0 || !next->llm) {
        error = "VLM rkllm_init failed: " + std::to_string(ret);
        return false;
    }
    ret = rkllm_set_chat_template(next->llm, "", "<|im_start|>User:",
                                  "<end_of_utterance>\nAssistant:");
    if (ret != 0) {
        error = "VLM rkllm_set_chat_template failed: " + std::to_string(ret);
        return false;
    }
    impl_ = std::move(next);
    return true;
}

InferenceResult RK3576VLMBackend::infer(LatestFrameBuffer::FramePtr frame,
                                        const std::string& question) {
    InferenceResult out;
    if (!impl_ || !impl_->llm || !impl_->rknn) {
        out.error_message = "VLM backend not initialized";
        return out;
    }
    if (!frame) { out.error_message = "No camera frame"; return out; }
    if (question.empty()) { out.error_message = "Empty VLM question"; return out; }
    std::vector<uint8_t> rgb;
    const auto preprocess_begin=ImageProfile::Clock::now();
    if (!frameToRgb512Reference(*frame, rgb, out.error_message)) return out;
    imageSample("preprocess_fused",ImageProfile::ms(preprocess_begin),frame->frame_id,kImageBytes,1);
    auto input_prepare_begin=ImageProfile::Clock::now();

    rknn_input img{};
    img.index = 0;
    img.type = RKNN_TENSOR_UINT8;
    img.fmt = RKNN_TENSOR_NHWC;
    img.size = kImageBytes;
    img.buf = rgb.data();
    imageSample("rknn_input_descriptor",ImageProfile::ms(input_prepare_begin),frame->frame_id);
    auto inputs_set_begin=ImageProfile::Clock::now();
    int ret = rknn_inputs_set(impl_->rknn, 1, &img);
    imageSample("rknn_inputs_set",ImageProfile::ms(inputs_set_begin),frame->frame_id,kImageBytes);
    if (ret != 0) {
        out.error_message = "rknn_inputs_set failed: " + std::to_string(ret);
        return out;
    }
    auto vision_begin=ImageProfile::Clock::now();
    ret = rknn_run(impl_->rknn, nullptr);
    imageSample("rknn_run",ImageProfile::ms(vision_begin),frame->frame_id);
    if (ret != 0) {
        out.error_message = "rknn_run failed: " + std::to_string(ret);
        return out;
    }
    std::vector<float> embeddings;
    bool okay = false;
    {
        RknnOutputOwner owner(impl_->rknn);
        auto& result = owner.output;
        result.index = 0;
        result.want_float = 1;
        auto output_begin=ImageProfile::Clock::now();
        ret = rknn_outputs_get(impl_->rknn, 1, &result, nullptr);
        imageSample("rknn_outputs_get",ImageProfile::ms(output_begin),frame->frame_id);
        if (ret != 0) {
            out.error_message = "rknn_outputs_get failed: " + std::to_string(ret);
            return out;
        }
        owner.acquired = true;
        okay = result.buf && result.size == kEmbeddingFloats * sizeof(float);
        if (okay) {
            const float* ptr = static_cast<const float*>(result.buf);
            auto embedding_begin=ImageProfile::Clock::now();
            embeddings.assign(ptr, ptr + kEmbeddingFloats);
            imageSample("embedding_alloc_copy",ImageProfile::ms(embedding_begin),frame->frame_id,kEmbeddingFloats*sizeof(float),1);
            okay = std::all_of(embeddings.begin(), embeddings.end(), [](float x) { return std::isfinite(x); });
        }
    } // Release RKNN output before RKLLM, also when embeddings.assign throws.
    if (!okay) { out.error_message = "Invalid vision embeddings"; return out; }

    if(const char* directory=std::getenv("STAGE5_VISION_DUMP_DIR")) {
        const std::string prefix=std::string(directory)+"/sample_"+std::to_string(impl_->dump_counter++);
        std::ofstream rgb_file(prefix+".rgb",std::ios::binary),emb_file(prefix+".f32",std::ios::binary);
        rgb_file.write(reinterpret_cast<const char*>(rgb.data()),rgb.size());
        emb_file.write(reinterpret_cast<const char*>(embeddings.data()),embeddings.size()*sizeof(float));
        if(!rgb_file||!emb_file){out.error_message="Diagnostic image/embedding dump failed";return out;}
    }
    std::string prompt = "<image>" + question;
    RKLLMInput input{};
    input.role = "user";
    input.input_type = RKLLM_INPUT_MULTIMODAL;
    input.multimodal_input.prompt = const_cast<char*>(prompt.c_str());
    input.multimodal_input.image.image_embed = embeddings.data();
    input.multimodal_input.image.n_image_tokens = 64;
    input.multimodal_input.image.n_image = 1;
    input.multimodal_input.image.image_height = 512;
    input.multimodal_input.image.image_width = 512;
    input.multimodal_input.image.image_start = "<fake_token_around_image><global-img>";
    input.multimodal_input.image.image_content = "<image>";
    input.multimodal_input.image.image_end = "<fake_token_around_image>";
    RKLLMInferParam infer{};
    infer.mode = RKLLM_INFER_GENERATE;
    infer.keep_history = 0;
    GenerationState state;
    ret = rkllm_run(impl_->llm, &input, &infer, &state);
    if (ret != 0 || state.failed || !state.finished || state.text.empty()) {
        out.error_message = "VLM rkllm_run failed or empty answer, ret=" + std::to_string(ret);
        return out;
    }
    out.success = true;
    out.text = std::move(state.text);
    return out;
}

void RK3576VLMBackend::shutdown() noexcept { impl_.reset(); }
