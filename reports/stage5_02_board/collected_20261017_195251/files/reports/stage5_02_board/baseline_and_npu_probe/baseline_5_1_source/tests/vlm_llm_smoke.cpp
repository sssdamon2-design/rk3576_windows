#include <stddef.h>
#include "rkllm.h"

#include <chrono>
#include <iostream>
#include <string>

struct TestState {
    bool finished = false;
    bool error = false;
    std::string generated;
};

static int on_result(
    RKLLMResult* result,
    void* userdata,
    LLMCallState state
) {
    auto* test = static_cast<TestState*>(userdata);

    if (state == RKLLM_RUN_NORMAL) {
        if (result && result->text) {
            std::cout << result->text << std::flush;
            test->generated += result->text;
        }
    } else if (state == RKLLM_RUN_FINISH) {
        test->finished = true;
        std::cout << "\n[Generation finished]\n";
    } else if (state == RKLLM_RUN_ERROR) {
        test->error = true;
        std::cerr << "\n[RKLLM generation error]\n";
    }

    return 0;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0]
                  << " model.rkllm\n";
        return 1;
    }

    RKLLMParam param = rkllm_createDefaultParam();

    param.model_path = argv[1];
    param.max_context_len = 2048;
    param.max_new_tokens = 48;
    param.top_k = 1;
    param.skip_special_token = true;
    param.is_async = false;
    param.extend_param.base_domain_id = 1;

    TestState test;

    RKLLMCallback callback{};
    callback.result_callback = on_result;
    callback.result_userdata = &test;

    LLMHandle handle = nullptr;

    std::cout << "=== SmolVLM2 RKLLM Smoke Test ===\n";

    auto t0 = std::chrono::steady_clock::now();

    int ret = rkllm_init(&handle, &param, &callback);

    auto t1 = std::chrono::steady_clock::now();

    std::cout << "rkllm_init ret=" << ret << "\n";
    std::cout << "load_ms="
              << std::chrono::duration<double, std::milli>(
                     t1 - t0
                 ).count()
              << "\n";

    if (ret != 0 || handle == nullptr) {
        std::cerr << "RKLLM INIT: FAIL\n";
        if (handle) rkllm_destroy(handle);
        return 1;
    }

    // SmolVLM2 原生 Chat Template
    const char* system_prompt = "";
    const char* prompt_prefix = "<|im_start|>User: ";
    const char* prompt_postfix = "<end_of_utterance>\nAssistant:";

    int tmpl_ret = rkllm_set_chat_template(
        handle,
        system_prompt,
        prompt_prefix,
        prompt_postfix
    );

    std::cout << "rkllm_set_chat_template ret="
              << tmpl_ret << "\n";

    if (tmpl_ret != 0) {
        std::cerr << "Chat template setup failed\n";
        rkllm_destroy(handle);
        return 1;
    }

    RKLLMInput input{};
    input.input_type = RKLLM_INPUT_PROMPT;
    input.role = "user";
    input.prompt_input =
        "What is two plus three? Answer with one digit.";

    RKLLMInferParam infer{};
    infer.mode = RKLLM_INFER_GENERATE;
    infer.keep_history = 0;

    std::cout << "Prompt: " << input.prompt_input << "\n";
    std::cout << "Response: " << std::flush;

    auto t2 = std::chrono::steady_clock::now();

    ret = rkllm_run(handle, &input, &infer, nullptr);

    auto t3 = std::chrono::steady_clock::now();

    std::cout << "rkllm_run ret=" << ret << "\n";
    std::cout << "generation_ms="
              << std::chrono::duration<double, std::milli>(
                     t3 - t2
                 ).count()
              << "\n";

    std::cout << "generated_chars="
              << test.generated.size() << "\n";

    int destroy_ret = rkllm_destroy(handle);
    std::cout << "rkllm_destroy ret=" << destroy_ret << "\n";

    bool pass =
        ret == 0 &&
        destroy_ret == 0 &&
        test.finished &&
        !test.error &&
        !test.generated.empty();

    std::cout << "RKLLM SMOKE: "
              << (pass ? "PASS" : "FAIL")
              << std::endl;

    return pass ? 0 : 1;
}
