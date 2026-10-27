#include <rknn_api.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " model.rknn\n";
        return 1;
    }

    rknn_context ctx = 0;
    auto t0 = std::chrono::steady_clock::now();

    int ret = rknn_init(&ctx, argv[1], 0, 0, nullptr);
    std::cout << "rknn_init ret=" << ret << std::endl;
    if (ret != RKNN_SUCC) return 1;

    auto cleanup = [&]() { rknn_destroy(ctx); };

    auto t1 = std::chrono::steady_clock::now();
    std::cout << "model_load_ms="
              << std::chrono::duration<double, std::milli>(t1-t0).count()
              << std::endl;

    rknn_sdk_version version{};
    ret = rknn_query(ctx, RKNN_QUERY_SDK_VERSION,
                     &version, sizeof(version));
    if (ret == RKNN_SUCC) {
        std::cout << "SDK API: " << version.api_version << "\n";
        std::cout << "NPU Driver: " << version.drv_version << "\n";
    }

    rknn_input_output_num io{};
    ret = rknn_query(ctx, RKNN_QUERY_IN_OUT_NUM, &io, sizeof(io));
    if (ret != RKNN_SUCC) {
        std::cerr << "query IO failed: " << ret << "\n";
        cleanup();
        return 1;
    }

    std::cout << "inputs=" << io.n_input
              << " outputs=" << io.n_output << "\n";

    if (io.n_input != 1 || io.n_output != 1) {
        std::cerr << "Unexpected IO count\n";
        cleanup();
        return 1;
    }

    auto print_attr = [&](rknn_query_cmd cmd, const char* name) {
        rknn_tensor_attr attr{};
        attr.index = 0;
        int r = rknn_query(ctx, cmd, &attr, sizeof(attr));
        if (r != RKNN_SUCC) return r;

        std::cout << name << " dims=[";
        for (uint32_t i = 0; i < attr.n_dims; ++i) {
            if (i) std::cout << ",";
            std::cout << attr.dims[i];
        }
        std::cout << "] elements=" << attr.n_elems
                  << " type=" << attr.type
                  << " fmt=" << attr.fmt << "\n";
        return r;
    };

    if (print_attr(RKNN_QUERY_INPUT_ATTR, "input") != RKNN_SUCC ||
        print_attr(RKNN_QUERY_OUTPUT_ATTR, "output") != RKNN_SUCC) {
        cleanup();
        return 1;
    }

    // 合成 512x512 RGB 图像，供第一轮 NPU 冒烟测试使用。
    // 使用 UINT8 NHWC，RKNN Runtime 负责转换到模型要求的格式。
    std::vector<uint8_t> pixels(512 * 512 * 3, 128);

    rknn_input input{};
    input.index = 0;
    input.buf = pixels.data();
    input.size = pixels.size();
    input.type = RKNN_TENSOR_UINT8;
    input.fmt = RKNN_TENSOR_NHWC;

    ret = rknn_inputs_set(ctx, 1, &input);
    std::cout << "rknn_inputs_set ret=" << ret << "\n";
    if (ret != RKNN_SUCC) {
        cleanup();
        return 1;
    }

    auto start = std::chrono::steady_clock::now();
    ret = rknn_run(ctx, nullptr);
    auto end = std::chrono::steady_clock::now();

    std::cout << "rknn_run ret=" << ret << "\n";
    std::cout << "inference_ms="
              << std::chrono::duration<double, std::milli>(end-start).count()
              << "\n";

    if (ret != RKNN_SUCC) {
        cleanup();
        return 1;
    }

    rknn_output output{};
    output.index = 0;
    output.want_float = 1;

    ret = rknn_outputs_get(ctx, 1, &output, nullptr);
    std::cout << "rknn_outputs_get ret=" << ret << "\n";

    if (ret != RKNN_SUCC) {
        cleanup();
        return 1;
    }

    size_t count = output.size / sizeof(float);
    const float* data = static_cast<const float*>(output.buf);

    bool finite = data != nullptr;
    float min_value = INFINITY;
    float max_value = -INFINITY;

    for (size_t i = 0; i < count && finite; ++i) {
        if (!std::isfinite(data[i])) {
            finite = false;
            break;
        }
        min_value = std::min(min_value, data[i]);
        max_value = std::max(max_value, data[i]);
    }

    std::cout << "output_elements=" << count << "\n"
              << "all_finite=" << (finite ? "YES" : "NO") << "\n";

    if (finite && count > 0) {
        std::cout << "output_range=[" << min_value
                  << "," << max_value << "]\n";
    }


    if (data != nullptr && count == 64 * 576 && finite) {
        std::ofstream file("/tmp/smolvlm_rknn_output.bin",
                           std::ios::binary);
        file.write(reinterpret_cast<const char*>(data),
                   output.size);
        file.close();
        std::cout << "OUTPUT SAVED: /tmp/smolvlm_rknn_output.bin"
                  << std::endl;
    }

    rknn_outputs_release(ctx, 1, &output);
    cleanup();

    bool pass = finite && count == 64 * 576;
    std::cout << "VISION NPU SMOKE: "
              << (pass ? "PASS" : "FAIL") << std::endl;

    return pass ? 0 : 1;
}
