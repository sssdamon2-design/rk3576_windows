# 第五阶段5.1实际修改源码全文

由 tools/stage5_review.py 从当前源码读取生成，不能作为编译或硬件通过证据。改动语句的语法、所有权和线程解释见 stage5_01_architecture_audit.md 操作5。

第三阶段信号修复、当前ARM64/硬件验收与剩余风险见 [stage5_01_board_acceptance.md](stage5_01_board_acceptance.md)。本附录展示本地当前代码；实际部署版本必须与板端源文件哈希和日志核对。

## 操作 1：`CMakeLists.txt`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\CMakeLists.txt`

SHA256：`39836964f7ac9f20aeff1b5017ce62fc58c27dcfa6a0c703b5cbab047ea5a6e8`

### 最终完整源码

```cmake
cmake_minimum_required(VERSION 3.16)
project(rk3576_multimodal LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(Threads REQUIRED)

option(BUILD_WITH_RKLLM "Build the real Rockchip RKLLM backend" OFF)
option(BUILD_WITH_VLM "Build SmolVLM2 RKNN + RKLLM real VLM backend" OFF)
option(ENABLE_SHERPA_ASR "Build ALSA + sherpa-onnx audio pipeline" OFF)
set(SHERPA_ONNX_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
    CACHE PATH "Root of sherpa-onnx aarch64 shared CPU runtime")

# 真实视觉 SDK 仅在 RK3576 aarch64 Linux 上启用。
set(RKNN_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../rknn_test/include"
    CACHE PATH "Directory containing rknn_api.h")
set(RKNN_RUNTIME_LIBRARY "/usr/lib/librknnrt.so"
    CACHE FILEPATH "RKNN runtime shared library")

set(RKLLM_SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../rkllm_sdk"
    CACHE PATH "Root directory of the RKLLM SDK")

if(BUILD_WITH_RKLLM OR BUILD_WITH_VLM)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
        message(FATAL_ERROR "The real RKLLM backend currently requires Linux.")
    endif()

    if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
        message(FATAL_ERROR "The current RKLLM library requires Linux AArch64.")
    endif()

    set(RKLLM_API_DIR "${RKLLM_SDK_ROOT}/rkllm-runtime/Linux/librkllm_api")
    set(RKLLM_INCLUDE_DIR "${RKLLM_API_DIR}/include")
    set(RKLLM_RUNTIME_LIBRARY "${RKLLM_API_DIR}/aarch64/librkllmrt.so")

    if(NOT EXISTS "${RKLLM_INCLUDE_DIR}/rkllm.h")
        message(FATAL_ERROR "RKLLM header not found: ${RKLLM_INCLUDE_DIR}/rkllm.h")
    endif()

    if(NOT EXISTS "${RKLLM_RUNTIME_LIBRARY}")
        message(FATAL_ERROR "RKLLM runtime library not found: ${RKLLM_RUNTIME_LIBRARY}")
    endif()

    message(STATUS "RKLLM SDK library available")
    message(STATUS "RKLLM include: ${RKLLM_INCLUDE_DIR}")
    message(STATUS "RKLLM library: ${RKLLM_RUNTIME_LIBRARY}")
endif()

function(project_warnings target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /utf-8)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endfunction()

add_library(multimodal_core
    src/video/latest_frame_buffer.cpp
    src/ai/llm_engine.cpp
    src/ai/llm_worker.cpp
    src/ai/vlm_engine.cpp
    src/ai/rk_backends_unavailable.cpp
    src/router/intent_router.cpp
    src/app/request_processor.cpp
)

target_include_directories(multimodal_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(multimodal_core PUBLIC Threads::Threads)

if(BUILD_WITH_RKLLM)
    target_sources(multimodal_core PRIVATE src/ai/rkllm_backend.cpp)
    target_include_directories(multimodal_core PRIVATE "${RKLLM_INCLUDE_DIR}")
    target_link_libraries(multimodal_core PUBLIC "${RKLLM_RUNTIME_LIBRARY}")
    target_compile_definitions(multimodal_core PRIVATE RK3576_WITH_RKLLM=1)
endif()

if(BUILD_WITH_VLM)
    if(NOT EXISTS "${RKNN_INCLUDE_DIR}/rknn_api.h")
        message(FATAL_ERROR "RKNN header missing: ${RKNN_INCLUDE_DIR}/rknn_api.h")
    endif()
    if(NOT EXISTS "${RKNN_RUNTIME_LIBRARY}")
        message(FATAL_ERROR "RKNN runtime missing: ${RKNN_RUNTIME_LIBRARY}")
    endif()
    target_sources(multimodal_core PRIVATE src/ai/rk3576_vlm_backend.cpp)
    target_include_directories(multimodal_core PRIVATE "${RKNN_INCLUDE_DIR}" "${RKLLM_INCLUDE_DIR}")
    target_link_libraries(multimodal_core PUBLIC "${RKNN_RUNTIME_LIBRARY}" "${RKLLM_RUNTIME_LIBRARY}")
    target_compile_definitions(multimodal_core PRIVATE RK3576_WITH_VLM=1)
    message(STATUS "Real SmolVLM2 RKNN + RKLLM backend enabled")
endif()

project_warnings(multimodal_core)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CAMERA_CAPTURE_SOURCE src/video/video_capture.cpp)
else()
    set(CAMERA_CAPTURE_SOURCE src/video/video_capture_unavailable.cpp)
    message(STATUS "V4L2 unavailable: building portable core/CLI with explicit camera error")
endif()

add_library(multimodal_camera
    src/video/camera_service.cpp
    ${CAMERA_CAPTURE_SOURCE}
)

target_link_libraries(multimodal_camera PUBLIC multimodal_core)
project_warnings(multimodal_camera)

add_executable(rk3576_multimodal
    src/main.cpp
    src/app/cli.cpp
)

target_link_libraries(rk3576_multimodal PRIVATE multimodal_camera)
project_warnings(rk3576_multimodal)

# 操作 2.8：真实 RKLLMWorker 实机验证。
if(BUILD_WITH_RKLLM)
    add_executable(
        rkllm_worker_smoke
        src/ai/llm_worker_smoke.cpp
    )

    target_link_libraries(
        rkllm_worker_smoke
        PRIVATE multimodal_core
    )

    project_warnings(rkllm_worker_smoke)
endif()


# Optional audio pipeline. Disabled in the original portable/RKLLM-only builds.
if(ENABLE_SHERPA_ASR)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
        message(FATAL_ERROR "ALSA audio pipeline currently requires Linux")
    endif()

    find_package(ALSA REQUIRED)
    set(SHERPA_INCLUDE_DIR "${SHERPA_ONNX_ROOT}/include")
    set(SHERPA_LIBRARY "${SHERPA_ONNX_ROOT}/lib/libsherpa-onnx-c-api.so")
    if(NOT EXISTS "${SHERPA_INCLUDE_DIR}/sherpa-onnx/c-api/c-api.h")
        message(FATAL_ERROR "sherpa-onnx C API header missing: ${SHERPA_INCLUDE_DIR}")
    endif()
    if(NOT EXISTS "${SHERPA_LIBRARY}")
        message(FATAL_ERROR "sherpa-onnx C API library missing: ${SHERPA_LIBRARY}")
    endif()

    add_library(multimodal_audio
        src/audio/audio_capture.cpp
        src/audio/audio_preprocessor.cpp
        src/audio/asr_service.cpp
        src/audio/asr_pipeline.cpp
        src/audio/audio_worker.cpp
        src/audio/vad_audio_worker.cpp
    )
    target_include_directories(multimodal_audio PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        "${SHERPA_INCLUDE_DIR}")
    target_link_libraries(multimodal_audio PUBLIC
        Threads::Threads ALSA::ALSA "${SHERPA_LIBRARY}")
    project_warnings(multimodal_audio)

    # Restore previously used ASR verification targets.
    foreach(smoke IN ITEMS audio_capture_smoke asr_live_smoke
                           asr_pipeline_smoke asr_vad_smoke)
        add_executable(${smoke} "src/audio/${smoke}.cpp")
        target_link_libraries(${smoke} PRIVATE multimodal_audio)
        project_warnings(${smoke})
    endforeach()

    add_executable(asr_route_smoke src/audio/asr_route_smoke.cpp)
    target_link_libraries(asr_route_smoke PRIVATE multimodal_audio multimodal_camera)
    project_warnings(asr_route_smoke)

    # Operation 2.9: actual mic -> VAD -> ASR -> asynchronous RKLLM.
    if(BUILD_WITH_RKLLM)
        add_executable(asr_llm_smoke src/audio/asr_llm_smoke.cpp)
        target_link_libraries(asr_llm_smoke PRIVATE multimodal_audio multimodal_core)
        project_warnings(asr_llm_smoke)
    endif()
endif()


include(CTest)

if(BUILD_TESTING)

    # Portable production pipeline with a test-only ASRService implementation.
    # No ALSA, sherpa-onnx, model or NPU is used by this target.
    add_executable(asr_pipeline_tests
        tests/asr_pipeline_tests.cpp
        src/audio/asr_pipeline.cpp
        src/audio/audio_preprocessor.cpp)
    target_include_directories(asr_pipeline_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    target_link_libraries(asr_pipeline_tests PRIVATE Threads::Threads)
    project_warnings(asr_pipeline_tests)
    add_test(NAME asr_pipeline_tests COMMAND asr_pipeline_tests)
    set_tests_properties(asr_pipeline_tests PROPERTIES TIMEOUT 15)

    add_executable(audio_preprocessor_tests
        tests/audio_preprocessor_tests.cpp
        src/audio/audio_preprocessor.cpp)
    target_include_directories(audio_preprocessor_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    project_warnings(audio_preprocessor_tests)
    add_test(NAME audio_preprocessor_tests COMMAND audio_preprocessor_tests)
    set_tests_properties(audio_preprocessor_tests PROPERTIES TIMEOUT 10)

    # Mock Backend 测试，不加载模型、不使用 NPU。
    add_executable(llm_worker_tests tests/llm_worker_tests.cpp)
    target_link_libraries(llm_worker_tests PRIVATE multimodal_core)
    project_warnings(llm_worker_tests)
    add_test(NAME llm_worker_tests COMMAND llm_worker_tests)
    set_tests_properties(llm_worker_tests PROPERTIES TIMEOUT 15)

    if(NOT BUILD_WITH_RKLLM AND NOT BUILD_WITH_VLM)
        add_executable(core_tests tests/core_tests.cpp)
        target_link_libraries(core_tests PRIVATE multimodal_core)
        project_warnings(core_tests)
        add_test(NAME core_tests COMMAND core_tests)

        add_test(NAME cli_smoke COMMAND ${CMAKE_COMMAND}
            -DAPP=$<TARGET_FILE:rk3576_multimodal>
            -DTEST_DATA=${CMAKE_CURRENT_SOURCE_DIR}/tests
            -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/cli_smoke.cmake)

        set_tests_properties(core_tests cli_smoke PROPERTIES TIMEOUT 20)
    endif()

    add_executable(camera_service_tests
        tests/camera_service_tests.cpp
        tests/camera_test_capture.cpp
        src/video/camera_service.cpp)

    target_include_directories(camera_service_tests PRIVATE tests)
    target_link_libraries(camera_service_tests PRIVATE multimodal_core)
    project_warnings(camera_service_tests)
    add_test(NAME camera_service_tests COMMAND camera_service_tests)
    set_tests_properties(camera_service_tests PROPERTIES TIMEOUT 20)

endif()
# ==========================================================
# Stage 3.2: Offline TTSService + WAV smoke test
# ==========================================================

if(ENABLE_SHERPA_ASR)
    add_executable(tts_smoke
        src/audio/tts_smoke.cpp
    )

    target_link_libraries(tts_smoke
        PRIVATE multimodal_tts
    )

    project_warnings(tts_smoke)
endif()



# ==========================================================
# Stage 3.3: TTS -> ALSA Playback smoke test
# ==========================================================

if(ENABLE_SHERPA_ASR)
    add_executable(tts_playback_smoke
        src/audio/tts_playback_smoke.cpp
    )

    target_link_libraries(tts_playback_smoke
        PRIVATE multimodal_tts
    )

    project_warnings(tts_playback_smoke)
endif()




# ==========================================================
# Stage 3.4: Reusable TTS library + asynchronous worker
# ==========================================================

if(ENABLE_SHERPA_ASR)

    add_library(multimodal_tts STATIC
        src/audio/tts_service.cpp
        src/audio/alsa_playback_service.cpp
        src/audio/tts_worker.cpp
    )

    target_include_directories(multimodal_tts PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
    )

    target_link_libraries(multimodal_tts PUBLIC
        multimodal_audio
    )

    project_warnings(multimodal_tts)

    add_executable(tts_worker_smoke
        src/audio/tts_worker_smoke.cpp
    )

    target_link_libraries(tts_worker_smoke PRIVATE
        multimodal_tts
    )

    project_warnings(tts_worker_smoke)

endif()
# Stage 3.4: TTSWorker queue and shutdown verification
if(ENABLE_SHERPA_ASR)
    add_executable(tts_worker_queue_smoke
        src/audio/tts_worker_queue_smoke.cpp
    )

    target_link_libraries(tts_worker_queue_smoke
        PRIVATE multimodal_tts
    )

    project_warnings(tts_worker_queue_smoke)
endif()
# ==========================================================
# Stage 3.5: ASR -> LLM -> TTS -> ALSA
# ==========================================================

if(ENABLE_SHERPA_ASR AND BUILD_WITH_RKLLM)

    add_executable(asr_llm_tts_smoke
        src/audio/asr_llm_tts_smoke.cpp
    )

    target_link_libraries(asr_llm_tts_smoke PRIVATE
        multimodal_audio
        multimodal_core
        multimodal_camera
        multimodal_tts
    )

    project_warnings(asr_llm_tts_smoke)

endif()
```

## 操作 2：`include/ai/llm_worker.h`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\include\ai\llm_worker.h`

SHA256：`f1041f46336a752a7a4cd1104a75776d38b95eac057f0834b187dc7eee8e3401`

### 最终完整源码

```cpp
#pragma once

#include "ai/llm_engine.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

enum class LLMSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

using LLMWorkerChunk =
    std::function<void(std::uint64_t, const std::string&)>;

using LLMWorkerDone =
    std::function<void(std::uint64_t, const InferenceResult&, double)>;

// 单消费者、有界排队；不拥有 LLMEngine。
// Engine 必须比 Worker 活得更久。
// 回调中不得销毁 Worker，也不能 join Worker 自己的线程。
// start/join/destruction must be serialized by the owner thread.
// Callback captures (including mutexes/counters) must outlive the joined Worker.
class LLMWorker final
{
public:
    explicit LLMWorker(LLMEngine& engine, std::size_t capacity = 2);
    ~LLMWorker();

    LLMWorker(const LLMWorker&) = delete;
    LLMWorker& operator=(const LLMWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 正在执行的任务不占用等待队列容量。
    LLMSubmitStatus submit(std::uint64_t id,
                           std::string question,
                           LLMWorkerChunk on_chunk = {},
                           LLMWorkerDone on_done = {});

    // 停止接收新请求，排队任务取消。
    void requestStop() noexcept;

    // 需要先 requestStop，且不能从 Worker 线程内部调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;

private:
    struct Task
    {
        std::uint64_t id = 0;
        std::string question;
        LLMWorkerChunk on_chunk;
        LLMWorkerDone on_done;
        std::chrono::steady_clock::time_point enqueued_at{};
    };

    void run();

    LLMEngine& engine_;
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;
    std::size_t rejected_ = 0;
};
```

## 操作 3：`include/audio/asr_pipeline.h`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\include\audio\asr_pipeline.h`

SHA256：`0706f3f7289ea169a320ed06af983f33d9904c5b3898e504e8956ef5783ddb63`

### 最终完整源码

```cpp

#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

class ASRService;

// 一个完整的待识别音频段。
struct AudioSegment {
    std::uint64_t sequence = 0;

    // 操作 7 使用：S16_LE PCM。
    std::vector<std::int16_t> pcm;

    // 操作 8 使用：VAD 输出的 Float32。
    std::vector<float> samples;

    // 操作 10：阶段时间戳。
    // audio_end_estimated_at 为主机读取时钟推算的
    // VAD 音频段末尾时间，而非精确发声结束时间。
    bool timing_valid = false;

    std::chrono::steady_clock::time_point
        audio_end_estimated_at{};

    std::chrono::steady_clock::time_point
        vad_ready_at{};

    std::chrono::steady_clock::time_point
        enqueued_at{};
};

// 有界音频段队列。
class AudioBufferQueue {
public:
    explicit AudioBufferQueue(std::size_t capacity);

    bool push(AudioSegment segment);
    bool pop(AudioSegment& segment);

    void close();

    std::size_t droppedCount() const;

private:
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<AudioSegment> items_;

    bool closed_ = false;
    std::size_t dropped_ = 0;
};

// 操作 7 的音频生产者。
class AudioWorker {
public:
    AudioWorker(
        std::string device,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t segment_count
    );

    ~AudioWorker();

    AudioWorker(const AudioWorker&) = delete;
    AudioWorker& operator=(const AudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();

    // Read result state only after join().
    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();
    void runImpl();

    std::string device_;
    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t segment_count_;

    std::atomic<bool> stop_requested_{false};
    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};

// ASR 消费者。
// 支持操作 9 的可选识别文本回调。
class ASRWorker {
public:
    using TextCallback =
        std::function<void(const std::string&)>;

    ASRWorker(
        AudioBufferQueue& queue,
        ASRService& asr,
        std::mutex& print_mutex,
        TextCallback on_text = {}
    );

    ~ASRWorker();

    ASRWorker(const ASRWorker&) = delete;
    ASRWorker& operator=(const ASRWorker&) = delete;

    // Start once; start/join/destruction must be serialized by the owner.
    void start();
    // Close input and drain queued segments. Does not cancel active inference.
    void requestStop();
    void join();

    // Read result state only after join().
    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t processedCount() const {
        return processed_;
    }

private:
    void run();
    void runImpl();

    AudioBufferQueue& queue_;
    ASRService& asr_;
    std::mutex& print_mutex_;

    TextCallback on_text_;

    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t processed_ = 0;
};
```

## 操作 4：`include/audio/tts_worker.h`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\include\audio\tts_worker.h`

SHA256：`bfd8813c9e22f131137ba6f2f441156d2b4a6efdb07467cc6931effeae70000a`

### 最终完整源码

```cpp

#pragma once

#include "audio/alsa_playback_service.h"
#include "audio/tts_service.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

// 任务提交状态。
// 与现有 LLMSubmitStatus 保持一致。
enum class TTSSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

// 一次 TTS 合成和播放的执行结果。
struct TTSWorkerResult
{
    bool success = false;

    std::string error_message;

    // TTS 模型合成耗时。
    double synthesis_ms = 0.0;

    // ALSA 播放调用耗时，包含 drain。
    double playback_ms = 0.0;

    // 生成的音频时长。
    double audio_seconds = 0.0;

    std::int32_t sample_rate = 0;

    // 本次播放检测到的 XRUN 数量。
    std::uint64_t xrun_count = 0;
};

// 完成回调参数：
// request_id、结果、等待队列耗时（ms）。
// 取消的任务使用 queue_wait_ms=-1。
using TTSWorkerDone = std::function<void(
    std::uint64_t,
    const TTSWorkerResult&,
    double
)>;

// 单消费者 + 有界 FIFO。
// 不拥有 TTSService / AlsaPlaybackService。
//
// 必须先初始化两个 Service，再启动 Worker。
// 回调在 Worker 线程执行；回调中不得销毁
// 或 join 当前 Worker。
// start/join/destruction must be serialized by the owner thread.
// Callback captures must outlive the joined Worker, as must both Services.
class TTSWorker final
{
public:
    explicit TTSWorker(
        TTSService& tts,
        AlsaPlaybackService& playback,
        std::size_t capacity = 2
    );

    ~TTSWorker();

    TTSWorker(const TTSWorker&) = delete;
    TTSWorker& operator=(const TTSWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 非阻塞提交任务。
    TTSSubmitStatus submit(
        std::uint64_t id,
        std::string text,
        TTSWorkerDone on_done = {}
    );

    // 不再接收新任务。
    // 等待队列中的任务报告取消；
    // 正在执行的任务允许自然完成。
    void requestStop() noexcept;

    // 必须从非 Worker 线程调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;

private:
    struct Task
    {
        std::uint64_t id = 0;

        std::string text;

        TTSWorkerDone on_done;

        std::chrono::steady_clock::time_point
            enqueued_at{};
    };

    void run();

    // 外部对象引用，不负责销毁。
    TTSService& tts_;
    AlsaPlaybackService& playback_;

    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;

    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;

    std::size_t rejected_ = 0;
};
```

## 操作 5：`include/audio/vad_audio_worker.h`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\include\audio\vad_audio_worker.h`

SHA256：`897344fd93d5c9b0552c009b627c68826a14cc1722066df21d1363064ff1b517`

### 最终完整源码

```cpp

#pragma once

#include "audio/asr_pipeline.h"

#include <atomic>
#include <cstddef>
#include <mutex>
#include <string>
#include <thread>

class VadAudioWorker {
public:
    VadAudioWorker(
        std::string device,
        std::string vad_model,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t record_seconds
    );

    ~VadAudioWorker();

    VadAudioWorker(const VadAudioWorker&) = delete;
    VadAudioWorker& operator=(const VadAudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();
    // Completion publication lets the owner observe stop signals without blocking in join.
    bool isFinished() const noexcept { return finished_.load(std::memory_order_acquire); }

    // 仅在 join() 之后读取以下状态。
    bool ok() const { return ok_; }
    const std::string& error() const { return error_; }
    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();
    void runImpl();

    std::string device_;
    std::string vad_model_;

    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t record_seconds_;

    std::atomic<bool> stop_requested_{false};
    std::atomic<bool> finished_{false};
    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};
```

## 操作 6：`src/ai/llm_worker_smoke.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\ai\llm_worker_smoke.cpp`

SHA256：`8c45f582a366643ac0a309c28c31148a3a17b4524ff6fc262136494d6235a5ba`

### 最终完整源码

```cpp

#include "ai/llm_worker.h"
#include "ai/rk_backends.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iomanip>
#include <exception>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>

// 独立的 RKLLM + LLMWorker 实机验收入口。
int main(int argc, char** argv) try
{
    if (argc != 2)
    {
        std::cerr
            << "Usage: rkllm_worker_smoke "
            << "/absolute/path/to/model.rkllm\n";
        return 2;
    }

    BackendConfig config;
    config.model_path = argv[1];

    std::string error;

    LLMEngine llm(std::make_unique<RKLLMBackend>());

    if (!llm.initialize(config, error))
    {
        std::cerr
            << "LLM initialization failed: "
            << error << '\n';
        return 1;
    }

    // Worker 不拥有 LLMEngine。
    // 必须先等待 Worker 结束，再关闭 LLMEngine。
    std::mutex state_mutex;
    std::condition_variable done_cv;
    std::mutex print_mutex;

    bool done = false;
    bool printed_prefix = false;

    std::size_t chunk_count = 0;

    InferenceResult final_result;
    double queue_wait_ms = -1.0;

    const std::uint64_t request_id = 1;

    const std::string question =
        "请用两句话解释Linux中互斥锁的作用。";

    // Callback state must outlive the joined worker.
    LLMWorker worker(llm, 2);

    if (!worker.start(error))
    {
        std::cerr
            << "LLMWorker start failed: "
            << error << '\n';
        llm.shutdown();
        return 1;
    }

    const auto before_submit =
        std::chrono::steady_clock::now();

    // 提交异步请求。
    const auto status = worker.submit(
        request_id,
        question,

        // 流式文本回调：由 Worker 推理过程触发。
        [&](std::uint64_t id, const std::string& chunk)
        {
            if (id != request_id || chunk.empty())
                return;

            {
                std::lock_guard<std::mutex> lock(print_mutex);

                if (!printed_prefix)
                {
                    std::cout << "\n[Worker stream] ";
                    printed_prefix = true;
                }

                std::cout << chunk << std::flush;
            }

            {
                std::lock_guard<std::mutex> lock(state_mutex);
                ++chunk_count;
            }
        },

        // 推理完成回调。
        [&](std::uint64_t id,
            const InferenceResult& result,
            double wait_ms)
        {
            if (id != request_id)
                return;

            {
                std::lock_guard<std::mutex> lock(state_mutex);

                final_result = result;
                queue_wait_ms = wait_ms;
                done = true;
            }

            done_cv.notify_one();
        }
    );

    // 测量 submit() 调用本身的耗时。
    const double submit_ms =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - before_submit
        ).count();

    if (status != LLMSubmitStatus::Accepted)
    {
        std::cerr << "LLMWorker rejected the request\n";

        worker.requestStop();
        worker.join();
        llm.shutdown();

        return 1;
    }

    {
        std::lock_guard<std::mutex> lock(print_mutex);

        std::cout
            << std::fixed
            << std::setprecision(2)
            << "[Main] submit returned in "
            << submit_ms
            << " ms (NPU inference is running in worker thread)\n";
    }

    // 主线程每隔两秒继续执行自己的任务。
    std::size_t heartbeats = 0;

    for (;;)
    {
        std::unique_lock<std::mutex> lock(state_mutex);

        if (done_cv.wait_for(
                lock,
                std::chrono::seconds(2),
                [&] { return done; }))
        {
            break;
        }

        lock.unlock();

        ++heartbeats;

        std::lock_guard<std::mutex> print_lock(print_mutex);

        std::cout
            << "\n[Main] heartbeat #"
            << heartbeats
            << ": main thread is responsive\n"
            << std::flush;
    }

    // 正确的停止和资源释放顺序。
    worker.requestStop();
    worker.join();

    llm.shutdown();

    std::lock_guard<std::mutex> lock(print_mutex);

    std::cout
        << "\n[Main] completed: success="
        << std::boolalpha
        << final_result.success
        << ", stream_chunks="
        << chunk_count
        << ", queue_wait_ms="
        << queue_wait_ms
        << ", first_text_ms="
        << final_result.first_text_ms
        << ", request_latency_ms="
        << final_result.latency_ms
        << '\n';

    if (!final_result.success)
    {
        std::cerr
            << "[Main] inference error: "
            << final_result.error_message
            << '\n';
    }

    return final_result.success && chunk_count > 0 ? 0 : 1;
}

catch (const std::exception& e)
{
    std::cerr << "[Fatal] Worker smoke exception: " << e.what() << '\n';
    return 1;
}
catch (...)
{
    std::cerr << "[Fatal] Worker smoke: unknown exception\n";
    return 1;
}
```

## 操作 7：`src/ai/rk3576_vlm_backend.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\ai\rk3576_vlm_backend.cpp`

SHA256：`268f8f2c139b374371b77a3085f72f2a0a4b5d7ba5d639b42a64e927219bee55`

### 最终完整源码

```cpp
#include <stddef.h>  // rkllm.h uses size_t but does not include it itself.
#include "ai/rk_backends.h"
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

inline uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::max(0.0f, std::min(255.0f, std::round(v))));
}

// MVP CPU preprocessing: packed NV12, BT.709 limited range -> RGB, resize 512x512.
// Unlike PIL/Lanczos this uses bilinear Y and nearest chroma; quality validation is pending.
// Only read LatestFrameBuffer's owned ImageFrame (do not access mmap after QBUF).
bool frameToRgb512(const ImageFrame& f, std::vector<uint8_t>& rgb, std::string& error) {
    if (f.pixel_format != kNV12 || f.width == 0 || f.height == 0 ||
        (f.width % 2) || (f.height % 2)) {
        error = "Expected packed NV12 frame with even width/height";
        return false;
    }
    // VideoCapture concatenates mmap plane payloads. Current IMX415 returns one plane.
    if (f.plane_sizes.size() != 1 || f.plane_strides.size() != 1) {
        error = "This first VLM adapter expects one packed NV12 plane";
        return false;
    }
    const size_t stride = f.plane_strides[0];
    const size_t width = f.width;
    const size_t height = f.height;
    if (stride < width || stride > 16384 || width > 8192 || height > 8192 ||
        stride * (height + height / 2) > f.data.size()) {
        error = "Invalid NV12 stride/data size";
        return false;
    }
    const uint8_t* yPlane = f.data.data();
    const uint8_t* uvPlane = f.data.data() + stride * height;
    rgb.resize(kImageBytes);
    for (size_t dy = 0; dy < kHeight; ++dy) {
        const float sy = (static_cast<float>(dy) + 0.5f) * height / kHeight - 0.5f;
        const float fy = std::max(0.0f, sy);
        const size_t y0 = std::min(height - 1, static_cast<size_t>(fy));
        const size_t y1 = std::min(height - 1, y0 + 1);
        const float wy = std::min(1.0f, fy - y0);
        for (size_t dx = 0; dx < kWidth; ++dx) {
            const float sx = (static_cast<float>(dx) + 0.5f) * width / kWidth - 0.5f;
            const float fx = std::max(0.0f, sx);
            const size_t x0 = std::min(width - 1, static_cast<size_t>(fx));
            const size_t x1 = std::min(width - 1, x0 + 1);
            const float wx = std::min(1.0f, fx - x0);
            const float yy = (1-wy) * ((1-wx) * yPlane[y0*stride+x0] + wx * yPlane[y0*stride+x1]) +
                                   wy  * ((1-wx) * yPlane[y1*stride+x0] + wx * yPlane[y1*stride+x1]);
            const size_t ux = (std::min(width - 1, static_cast<size_t>(fx)) / 2) * 2;
            const size_t uy = std::min(height - 1, static_cast<size_t>(fy)) / 2;
            const float u = float(uvPlane[uy*stride+ux]) - 128.0f;
            const float v = float(uvPlane[uy*stride+ux+1]) - 128.0f;
            const float Y = 1.164383f * (yy - 16.0f);
            const size_t out = (dy*kWidth+dx)*3;
            rgb[out+0] = toByte(Y + 1.792741f*v);
            rgb[out+1] = toByte(Y - 0.213249f*u - 0.532909f*v);
            rgb[out+2] = toByte(Y + 2.112402f*u);
        }
    }
    return true;
}

// Own only a successfully acquired output; never copy SDK ownership.
struct RknnOutputOwner {
    rknn_context context;
    rknn_output output{};
    bool acquired = false;

    explicit RknnOutputOwner(rknn_context ctx) : context(ctx) {}
    RknnOutputOwner(const RknnOutputOwner&) = delete;
    RknnOutputOwner& operator=(const RknnOutputOwner&) = delete;
    ~RknnOutputOwner() noexcept {
        if (acquired) (void)rknn_outputs_release(context, 1, &output);
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
    if (!frameToRgb512(*frame, rgb, out.error_message)) return out;

    rknn_input img{};
    img.index = 0;
    img.type = RKNN_TENSOR_UINT8;
    img.fmt = RKNN_TENSOR_NHWC;
    img.size = kImageBytes;
    img.buf = rgb.data();
    int ret = rknn_inputs_set(impl_->rknn, 1, &img);
    if (ret != 0) {
        out.error_message = "rknn_inputs_set failed: " + std::to_string(ret);
        return out;
    }
    ret = rknn_run(impl_->rknn, nullptr);
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
        ret = rknn_outputs_get(impl_->rknn, 1, &result, nullptr);
        if (ret != 0) {
            out.error_message = "rknn_outputs_get failed: " + std::to_string(ret);
            return out;
        }
        owner.acquired = true;
        okay = result.buf && result.size == kEmbeddingFloats * sizeof(float);
        if (okay) {
            const float* ptr = static_cast<const float*>(result.buf);
            embeddings.assign(ptr, ptr + kEmbeddingFloats);
            okay = std::all_of(embeddings.begin(), embeddings.end(), [](float x) { return std::isfinite(x); });
        }
    } // Release RKNN output before RKLLM, also when embeddings.assign throws.
    if (!okay) { out.error_message = "Invalid vision embeddings"; return out; }

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
```

## 操作 8：`src/audio/asr_llm_smoke.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\asr_llm_smoke.cpp`

SHA256：`b5166c6ace67faba9c4d1c60bc8854217eba5a248402ab7c9a1096a1aff926bb`

### 最终完整源码

```cpp

#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <unistd.h>

// Operation 2.9: ALSA -> Silero VAD -> SenseVoice -> LLMWorker -> RKLLM.
// This smoke test intentionally handles only TEXT questions.
int main(int argc, char** argv) try
{
    if (argc != 5 && argc != 6)
    {
        std::cerr << "Usage: asr_llm_smoke <ALSA device> <ASR model dir> "
                  << "<VAD model> <RKLLM model> [record seconds: 20]\n";
        return 2;
    }

    const std::string audio_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    std::size_t record_seconds = 20;

    if (argc == 6)
    {
        try
        {
            const std::string value = argv[5];
            std::size_t parsed = 0;
            const unsigned long seconds = std::stoul(value, &parsed);

            if (parsed != value.size() || seconds < 1 || seconds > 120)
                throw std::invalid_argument("out of range");

            record_seconds = static_cast<std::size_t>(seconds);
        }
        catch (const std::exception&)
        {
            std::cerr << "Record seconds must be an integer from 1 to 120\n";
            return 2;
        }
    }

    const std::string asr_model = asr_dir + "/model.int8.onnx";
    const std::string asr_tokens = asr_dir + "/tokens.txt";

    for (const auto& path : {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr << "Cannot read model file: " << path << '\n';
            return 1;
        }
    }

    std::string error;

    LLMEngine llm(std::make_unique<RKLLMBackend>());

    std::cout << "[Init] RKLLM loading...\n" << std::flush;

    if (!llm.initialize(BackendConfig{llm_model, {}}, error))
    {
        std::cerr << "[Init] RKLLM failed: " << error << '\n';
        return 1;
    }

    ASRService asr;

    std::cout << "[Init] SenseVoice loading...\n" << std::flush;

    if (!asr.initialize(asr_model, asr_tokens, error))
    {
        std::cerr << "[Init] ASR failed: " << error << '\n';
        return 1;
    }

    // LLMWorker 内部使用独立线程执行 RKLLM 推理。
    // 队列容量为 2，用于限制等待推理的任务数量。
    AudioBufferQueue audio_queue(4);

    // 保护多线程终端输出，避免日志严重交错。
    std::mutex print_mutex;

    // 保护 LLM 请求完成情况。
    std::mutex state_mutex;
    std::condition_variable completed_cv;

    IntentRouter router;

    std::uint64_t next_id = 1;

    std::size_t accepted = 0;
    std::size_t completed = 0;
    std::size_t successful = 0;
    std::size_t failed = 0;
    std::size_t rejected = 0;
    std::size_t skipped_vision = 0;

    // ASRWorker 识别出文字后执行此回调。
    // 注意：本回调运行在 ASRWorker 的工作线程中。
    // Keep callback state alive until worker destruction has joined.
    LLMWorker llm_worker(llm, 2);

    if (!llm_worker.start(error))
    {
        std::cerr << "[Init] LLMWorker failed: " << error << '\n';
        return 1;
    }

    // 音频队列用于连接 VAD 与 ASRWorker。
    const auto on_text = [&](const std::string& recognized)
    {
        // 先通过 IntentRouter 判断请求类型。
        const RouteDecision route = router.route(recognized);

        // 当前操作 2.9 仅支持 TEXT。
        if (route.type != RequestType::Text)
        {
            ++skipped_vision;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[Route] VISION not supported in operation 2.9: "
                << recognized << '\n';

            return;
        }

        // 为每个请求分配唯一 ID。
        const std::uint64_t id = next_id++;

        // 用于控制流式输出前缀只打印一次。
        auto prefix_printed = std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[ASR->LLM] request #" << id
                << ": " << recognized
                << '\n'
                << std::flush;
        }

        // =====================================================
        // 操作 2.9 优化：构造简短回答 Prompt
        //
        // recognized：SenseVoice 输出的原始识别文字。
        // prompt：提交给 Qwen 的完整问题。
        //
        // 只约束 LLM 回答，不修改 ASR 原始识别内容。
        // =====================================================

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过50个汉字。";

        // =====================================================
        // 非阻塞提交 LLMWorker
        //
        // submit() 仅负责提交任务。
        // 真正耗时的 rkllm_run() 在 Worker 线程执行。
        // =====================================================

        const auto status = llm_worker.submit(
            id,
            prompt,

            // 流式输出回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const std::string& chunk)
            {
                if (chunk.empty())
                    return;

                std::lock_guard<std::mutex> lock(print_mutex);

                if (!*prefix_printed)
                {
                    std::cout
                        << "\n[LLM #" << request_id << "] ";

                    *prefix_printed = true;
                }

                std::cout << chunk << std::flush;
            },

            // LLM 推理完成回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const InferenceResult& result,
                double wait_ms)
            {
                {
                    std::lock_guard<std::mutex> lock(print_mutex);

                    if (*prefix_printed)
                        std::cout << '\n';

                    std::cout
                        << "[LLM done #" << request_id << "] success="
                        << (result.success ? "true" : "false")
                        << " queue_wait_ms=" << wait_ms
                        << " first_text_ms=" << result.first_text_ms
                        << " request_latency_ms=" << result.latency_ms
                        << '\n';

                    if (!result.success)
                    {
                        std::cout
                            << "[LLM error] "
                            << result.error_message
                            << '\n';
                    }
                }

                {
                    std::lock_guard<std::mutex> lock(state_mutex);

                    ++completed;

                    if (result.success)
                        ++successful;
                    else
                        ++failed;
                }

                // 通知主线程：某个 LLM 请求已完成。
                completed_cv.notify_one();
            }
        );

        // 判断任务是否成功加入队列。
        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            ++accepted;
        }
        else
        {
            ++rejected;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "[LLM rejected #" << id << "] "
                << (status == LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "worker not running")
                << '\n';
        }
    };

    // ASRWorker 从音频队列取出语音片段，执行 SenseVoice。
    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        on_text
    );

    // VadAudioWorker 负责 ALSA 录音和 Silero VAD 分段。
    VadAudioWorker producer(
        audio_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    std::cout
        << "[Listen] "
        << record_seconds
        << " seconds. Speak one short TEXT question, then pause.\n"
        << std::flush;

    try
    {
        // 启动 ASR 消费线程。
        consumer.start();

        // 启动 ALSA + VAD 生产线程。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Thread creation failed: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        return 1;
    }

    // 等待录音/VAD 线程结束。
    producer.join();

    // 等待 ASR 处理完剩余语音片段。
    consumer.join();

    // ASRWorker 退出后，不会再产生新的 LLM 请求。
    // 先等待所有已接受请求完成，再停止 LLMWorker。
    {
        std::unique_lock<std::mutex> lock(state_mutex);

        while (completed < accepted)
        {
            if (!completed_cv.wait_for(
                    lock,
                    std::chrono::seconds(2),
                    [&] { return completed == accepted; }))
            {
                const auto remaining = accepted - completed;

                lock.unlock();

                {
                    std::lock_guard<std::mutex> out(print_mutex);

                    std::cout
                        << "\n[Main] waiting for "
                        << remaining
                        << " LLM request(s)...\n"
                        << std::flush;
                }

                lock.lock();
            }
        }
    }

    // 正确的资源释放顺序：
    // 1. 停止 Worker。
    // 2. 等待 Worker 线程退出。
    // 3. 关闭 RKLLM Runtime。
    llm_worker.requestStop();
    llm_worker.join();
    llm.shutdown();

    // 输出整个语音问答链路的统计信息。
    {
        std::lock_guard<std::mutex> out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM summary ===\n"
            << "VAD segments: " << producer.producedCount() << '\n'
            << "ASR recognized: " << consumer.processedCount() << '\n'
            << "Audio queue dropped: " << audio_queue.droppedCount() << '\n'
            << "LLM accepted: " << accepted << '\n'
            << "LLM completed: " << completed << '\n'
            << "LLM successful: " << successful << '\n'
            << "LLM failed: " << failed << '\n'
            << "LLM rejected: " << rejected << '\n'
            << "Skipped VISION: " << skipped_vision << '\n';

        if (!producer.ok())
            std::cerr << "[VAD] " << producer.error() << '\n';

        if (!consumer.ok())
            std::cerr << "[ASR] " << consumer.error() << '\n';
    }

    // 最终验收条件。
    const bool passed =
        producer.ok() &&
        consumer.ok() &&
        accepted > 0 &&
        accepted == completed &&
        successful > 0 &&
        failed == 0 &&
        rejected == 0 &&
        audio_queue.droppedCount() == 0;

    std::cout << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
catch (const std::exception& e)
{
    std::cerr << "[Fatal] ASR/LLM exception: " << e.what() << '\n';
    return 1;
}
catch (...)
{
    std::cerr << "[Fatal] ASR/LLM: unknown exception\n";
    return 1;
}
```

## 操作 9：`src/audio/asr_llm_tts_smoke.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\asr_llm_tts_smoke.cpp`

SHA256：`28d84bce32042ce8136b27dd1c845b86f85d1168488cd51f25df0e77fa7a85e7`

### 最终完整源码

```cpp

#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"
#include "audio/tts_worker.h"

#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"
#include "ai/vlm_engine.h"
#include "video/camera_service.h"
#include "video/latest_frame_buffer.h"

#include <chrono>
#include <atomic>
#include <cerrno>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <thread>

#include <pthread.h>
#include <signal.h>

#include <unistd.h>

namespace {
// Construct before SDKs/workers: all descendant threads inherit the blocked set.
// sigtimedwait runs in an ordinary thread; there is no asynchronous signal handler.
class StopSignals {
public:
    StopSignals()
    {
        sigemptyset(&signals_);
        sigaddset(&signals_, SIGINT);
        sigaddset(&signals_, SIGTERM);
        if (pthread_sigmask(SIG_BLOCK, &signals_, &previous_) != 0)
            throw std::runtime_error("Cannot block stop signals");
        try
        {
            thread_ = std::thread([this] {
                const timespec interval{0, 100000000};
                while (!finished_.load())
                {
                    const int received = sigtimedwait(&signals_, nullptr, &interval);
                    if (received == SIGINT || received == SIGTERM)
                    {
                        int empty = 0;
                        signal_.compare_exchange_strong(empty, received);
                    }
                    else if (received < 0 && errno != EAGAIN && errno != EINTR)
                    {
                        wait_failed_.store(true);
                        break;
                    }
                }
            });
        }
        catch (...)
        {
            pthread_sigmask(SIG_SETMASK, &previous_, nullptr);
            throw;
        }
    }
    ~StopSignals()
    {
        finished_.store(true);
        if (thread_.joinable()) thread_.join();
        pthread_sigmask(SIG_SETMASK, &previous_, nullptr);
    }
    StopSignals(const StopSignals&) = delete;
    StopSignals& operator=(const StopSignals&) = delete;
    int received() const noexcept { return signal_.load(); }
    bool failed() const noexcept { return wait_failed_.load(); }
private:
    sigset_t signals_{};
    sigset_t previous_{};
    std::atomic<int> signal_{0};
    std::atomic<bool> finished_{false};
    std::atomic<bool> wait_failed_{false};
    std::thread thread_;
};
} // namespace

// ==========================================================
// Stage 3.5
//
// ALSA Capture
//     ↓
// Silero VAD
//     ↓
// SenseVoice ASR
//     ↓
// IntentRouter
//     ↓
// LLMWorker -> RKLLM / Qwen2.5
//     ↓
// TTSWorker -> Kokoro
//     ↓
// AlsaPlaybackService
//     ↓
// USB Headset
//
// TEXT is asynchronous; optional VISION runs synchronously on the ASR thread.
// ==========================================================

int main(int argc, char** argv) try
{
    // ------------------------------------------------------
    // 1. 命令行参数检查
    // ------------------------------------------------------

    if (argc < 7 || (argc > 10 && argc != 13))
    {
        std::cerr
            << "Usage: asr_llm_tts_smoke "
            << "<capture_device> "
            << "<asr_model_dir> "
            << "<vad_model> "
            << "<rkllm_model> "
            << "<kokoro_dir> "
            << "<playback_device> "
            << "[record_seconds=12] "
            << "[tts_threads=2] "
            << "[sid=17] "
            << "[vlm_rkllm vision_rknn camera_device]\n";

        return 2;
    }

    const std::string capture_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    const std::string kokoro_dir = argv[5];
    const std::string playback_device = argv[6];

    unsigned int record_seconds = 12;

    int tts_threads = 2;
    int sid = 17;

    // 兼容旧命令。新增三项参数时启用完整视觉语音链路。
    // 语音模式须传三个原有可选参数，再传 VLM 模型与 Camera 设备。
    const bool enable_vision = (argc == 13);
    const std::string vlm_model = enable_vision ? argv[10] : "";
    const std::string vision_model = enable_vision ? argv[11] : "";
    const std::string camera_device = enable_vision ? argv[12] : "";

    // ------------------------------------------------------
    // 2. 解析可选参数
    // ------------------------------------------------------

    try
    {
        const auto parse = [](
            const char* arg,
            int lo,
            int hi
        ) -> int
        {
            const std::string value(arg);

            std::size_t used = 0;

            const int result =
                std::stoi(value, &used);

            if (used != value.size() ||
                result < lo ||
                result > hi)
            {
                throw std::invalid_argument(
                    "out of range"
                );
            }

            return result;
        };

        if (argc >= 8)
        {
            record_seconds =
                static_cast<unsigned int>(
                    parse(argv[7], 1, 120)
                );
        }

        if (argc >= 9)
        {
            tts_threads =
                parse(argv[8], 1, 8);
        }

        if (argc >= 10)
        {
            sid =
                parse(argv[9], 0, 10000);
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "[Args] Invalid record_seconds / "
            << "threads / sid\n";

        return 2;
    }

    // ------------------------------------------------------
    // 3. 检查 ASR / VAD / LLM 模型文件
    // ------------------------------------------------------

    const std::string asr_model =
        asr_dir + "/model.int8.onnx";

    const std::string asr_tokens =
        asr_dir + "/tokens.txt";

    for (const auto& path :
         {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr
                << "[Init] Cannot read model file: "
                << path
                << '\n';

            return 1;
        }
    }

    if (enable_vision)
    {
        for (const auto& path : {vlm_model, vision_model})
        {
            if (::access(path.c_str(), R_OK) != 0)
            {
                std::cerr << "[Init] Cannot read VLM file: " << path << '\n';
                return 1;
            }
        }
    }

    std::string error;

    StopSignals stop_signals;

    // ------------------------------------------------------
    // 4. 初始化 RKLLM
    // ------------------------------------------------------

    LLMEngine llm(
        std::make_unique<RKLLMBackend>()
    );

    std::cout
        << "[Init] Loading RKLLM...\n"
        << std::flush;

    if (!llm.initialize(
            BackendConfig{llm_model, {}},
            error))
    {
        std::cerr
            << "[Init] RKLLM failed: "
            << error
            << '\n';

        return 1;
    }

    // ------------------------------------------------------
    // 5. 初始化 SenseVoice
    // ------------------------------------------------------

    ASRService asr;

    std::cout
        << "[Init] Loading SenseVoice...\n"
        << std::flush;

    if (!asr.initialize(
            asr_model,
            asr_tokens,
            error))
    {
        std::cerr
            << "[Init] ASR failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 6. 初始化 Kokoro TTS
    // ------------------------------------------------------

    TTSService tts;

    std::cout
        << "[Init] Loading Kokoro...\n"
        << std::flush;

    if (!tts.initialize(
            kokoro_dir,
            error,
            tts_threads,
            sid))
    {
        std::cerr
            << "[Init] Kokoro failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 7. 初始化 ALSA Playback
    // ------------------------------------------------------

    AlsaPlaybackService playback;

    if (!playback.open(
            playback_device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[Init] ALSA playback failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // Callback state precedes workers: reverse destruction joins workers first.
    // ------------------------------------------------------
    // 10. 创建 ASR 音频队列和线程同步对象
    // ------------------------------------------------------

    AudioBufferQueue audio_queue(4);

    // 保护不同线程的日志输出。
    std::mutex print_mutex;

    // 保护 LLM/TTS 任务完成计数。
    std::mutex state_mutex;

    // 通知主线程有任务完成。
    std::condition_variable completed_cv;

    IntentRouter router;

    // 由单个 ASRWorker 回调生成请求 ID。
    std::uint64_t next_id = 1;

    // ------------------------------------------------------
    // 11. LLM 和 TTS 统计
    // ------------------------------------------------------

    std::size_t llm_accepted = 0;
    std::size_t llm_completed = 0;
    std::size_t llm_successful = 0;
    std::size_t llm_failed = 0;
    std::size_t llm_rejected = 0;

    std::size_t skipped_vision = 0;
    std::size_t vision_completed = 0;
    std::size_t vision_successful = 0;
    std::size_t vision_failed = 0;

    std::size_t tts_accepted = 0;
    std::size_t tts_completed = 0;
    std::size_t tts_successful = 0;
    std::size_t tts_failed = 0;
    std::size_t tts_rejected = 0;
    std::size_t tts_empty = 0;

    // ------------------------------------------------------
    // 8. 创建并启动 TTSWorker
    // ------------------------------------------------------
    //
    // TTSWorker 不拥有 TTSService 和 PlaybackService。
    // 两个 Service 必须比 Worker 活得更久。
    //
    // capacity=2 表示最多允许两个等待任务。
    // ------------------------------------------------------

    TTSWorker tts_worker(
        tts,
        playback,
        2
    );

    if (!tts_worker.start(error))
    {
        std::cerr
            << "[Init] TTSWorker failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 9. 创建并启动 LLMWorker
    // ------------------------------------------------------

    LLMWorker llm_worker(
        llm,
        2
    );

    if (!llm_worker.start(error))
    {
        std::cerr
            << "[Init] LLMWorker failed: "
            << error
            << '\n';

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // Stage 4: 正式 Camera + VLM Backend。保持旧的 TEXT 链路不变。
    LatestFrameBuffer frames;
    std::unique_ptr<CameraService> camera;
    std::unique_ptr<VLMEngine> vlm;
    if (enable_vision)
    {
        constexpr std::uint32_t nv12 = std::uint32_t('N') |
            (std::uint32_t('V') << 8) |
            (std::uint32_t('1') << 16) |
            (std::uint32_t('2') << 24);

        camera = std::make_unique<CameraService>(
            camera_device, 3840, 2160, nv12, frames);
        if (!camera->start())
        {
            std::cerr << "[Init] Camera failed: "
                      << camera->stats().last_error << '\n';
            llm_worker.requestStop();
            llm_worker.join();
            tts_worker.requestStop();
            tts_worker.join();
            llm.shutdown();
            return 1;
        }

        vlm = std::make_unique<VLMEngine>(
            std::make_unique<RK3576VLMBackend>());
        std::cout << "[Init] Loading SmolVLM2 RKNN + RKLLM...\n"
                  << std::flush;
        if (!vlm->initialize(
            BackendConfig{vlm_model, vision_model}, error))
        {
            std::cerr << "[Init] VLM failed: " << error << '\n';
            camera->stop();
            llm_worker.requestStop();
            llm_worker.join();
            tts_worker.requestStop();
            tts_worker.join();
            llm.shutdown();
            return 1;
        }
        std::cout << "[Init] VLM and Camera ready\n";
    }

    // ------------------------------------------------------
    // 12. ASR 识别完成回调
    // ------------------------------------------------------
    //
    // 此回调在 ASRWorker 线程执行。
    //
    // recognized 是 SenseVoice 的识别结果。
    // ------------------------------------------------------

    const auto on_text =
        [&](const std::string& recognized)
    {
        // --------------------------------------------------
        // 12.1 意图判断
        // --------------------------------------------------

        const RouteDecision route =
            router.route(recognized);

        if (route.type == RequestType::Vision)
        {
            if (!enable_vision || !vlm)
            {
                ++skipped_vision;
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "\n[Route] VISION disabled: "
                          << recognized << '\n';
                return;
            }

            const auto request_id = next_id++;
            const auto question_at = std::chrono::steady_clock::now();
            // 先复用已在实机验证的英语单图问答；中文语音负责触发路由。
            // 避免 256M 模型不稳定的中文指令影响最终闭环验收。
            const std::string vlm_question =
                "What do you see? Answer briefly.";

            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "\n[ASR->VISION #" << request_id << "] "
                          << recognized << '\n';
            }

            const auto frame = frames.getLatest();
            const InferenceResult result = vlm->infer(frame, vlm_question);
            ++vision_completed;
            if (result.success && !result.text.empty())
                ++vision_successful;
            else
                ++vision_failed;

            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "[VLM done #" << request_id << "] success="
                          << (result.success ? "true" : "false")
                          << " frame_id=" << result.frame_id
                          << " frame_age_ms=" << result.frame_age_ms
                          << " latency_ms=" << result.latency_ms
                          << '\n';
                if (result.success)
                    std::cout << "[VLM Answer #" << request_id << "] "
                              << result.text << '\n';
                else
                    std::cout << "[VLM Error] " << result.error_message << '\n';
            }

            if (result.success && !result.text.empty())
            {
                const auto status = tts_worker.submit(
                    request_id, result.text,
                    [&, question_at](
                        std::uint64_t done_id,
                        const TTSWorkerResult& outcome,
                        double queue_ms)
                    {
                        const double e2e_ms = std::chrono::duration<
                            double, std::milli>(
                            std::chrono::steady_clock::now() - question_at
                        ).count();
                        {
                            std::lock_guard<std::mutex> out(print_mutex);
                            std::cout << "[VISION TTS done #" << done_id
                                      << "] success="
                                      << (outcome.success ? "true" : "false")
                                      << " queue_ms=" << queue_ms
                                      << " synth_ms=" << outcome.synthesis_ms
                                      << " playback_ms=" << outcome.playback_ms
                                      << " asr_text_to_end_ms=" << e2e_ms
                                      << '\n';
                            if (!outcome.success)
                                std::cout << "[TTS error] "
                                          << outcome.error_message << '\n';
                        }
                        {
                            std::lock_guard<std::mutex> lock(state_mutex);
                            ++tts_completed;
                            if (outcome.success) ++tts_successful;
                            else ++tts_failed;
                        }
                        completed_cv.notify_all();
                    });

                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    if (status == TTSSubmitStatus::Accepted)
                        ++tts_accepted;
                    else
                        ++tts_rejected;
                }
                if (status != TTSSubmitStatus::Accepted)
                {
                    std::lock_guard<std::mutex> out(print_mutex);
                    std::cout << "[VISION TTS rejected #" << request_id
                              << "] status=" << static_cast<int>(status)
                              << '\n';
                }
            }
            else if (result.success)
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                ++tts_empty;
            }
            // 此分支同步完成 VLM 推理，ASR 线程随后继续处理新语音。
            return;
        }

        // --------------------------------------------------
        // 12.2 分配请求 ID
        // --------------------------------------------------

        const std::uint64_t id =
            next_id++;

        // 记录 ASR 输出文本的时刻。
        const auto question_at =
            std::chrono::steady_clock::now();

        // 记录 LLM 是否已经输出前缀。
        auto prefix_printed =
            std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "\n[ASR->LLM #" << id << "] "
                << recognized
                << '\n';
        }

        // --------------------------------------------------
        // 12.3 构造 LLM Prompt
        // --------------------------------------------------
        //
        // 限制回答长度，降低当前 Kokoro 的合成等待。
        // 不改变 ASR 原始文本。
        // --------------------------------------------------

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过25个汉字。";

        // --------------------------------------------------
        // 12.4 非阻塞提交 LLMWorker
        // --------------------------------------------------

        const auto status =
            llm_worker.submit(
                id,
                prompt,

                // ------------------------------------------
                // LLM 流式文本回调
                // ------------------------------------------

                [&, prefix_printed](
                    std::uint64_t request_id,
                    const std::string& chunk)
                {
                    if (chunk.empty())
                    {
                        return;
                    }

                    std::lock_guard<std::mutex>
                        out(print_mutex);

                    if (!*prefix_printed)
                    {
                        std::cout
                            << "\n[LLM #"
                            << request_id
                            << "] ";

                        *prefix_printed = true;
                    }

                    std::cout
                        << chunk
                        << std::flush;
                },

                // ------------------------------------------
                // LLM 推理完成回调
                // ------------------------------------------
                //
                // 关键：这里把 LLM 答案交给 TTSWorker。
                // ------------------------------------------

                [&, prefix_printed, question_at](
                    std::uint64_t request_id,
                    const InferenceResult& result,
                    double llm_queue_ms)
                {
                    {
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        if (*prefix_printed)
                        {
                            std::cout << '\n';
                        }

                        std::cout
                            << "[LLM done #"
                            << request_id
                            << "] success="
                            << (result.success
                                ? "true"
                                : "false")
                            << " queue_ms="
                            << llm_queue_ms
                            << " first_text_ms="
                            << result.first_text_ms
                            << " latency_ms="
                            << result.latency_ms
                            << '\n';

                        if (!result.success)
                        {
                            std::cout
                                << "[LLM error] "
                                << result.error_message
                                << '\n';
                        }
                    }

                    // --------------------------------------
                    // 12.5 判断 LLM 是否产生有效文本
                    // --------------------------------------

                    TTSSubmitStatus tts_status =
                        TTSSubmitStatus::NotRunning;

                    std::string tts_submit_error;

                    const bool has_answer =
                        result.success &&
                        !result.text.empty();

                    if (has_answer)
                    {
                        try
                        {
                            // ------------------------------
                            // 12.6 向 TTSWorker 提交答案
                            // ------------------------------

                            tts_status =
                                tts_worker.submit(
                                    request_id,
                                    result.text,

                                    // ----------------------
                                    // TTS 完成回调
                                    // ----------------------

                                    [&, question_at](
                                        std::uint64_t tts_id,
                                        const TTSWorkerResult& tts_result,
                                        double tts_queue_ms)
                                    {
                                        // 从 ASR 输出文本到
                                        // 播放任务结束的耗时。
                                        const double e2e_ms =
                                            std::chrono::duration<
                                                double,
                                                std::milli
                                            >(
                                                std::chrono::
                                                    steady_clock::now()
                                                - question_at
                                            ).count();

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > out(print_mutex);

                                            std::cout
                                                << "[TTS done #"
                                                << tts_id
                                                << "] success="
                                                << (tts_result.success
                                                    ? "true"
                                                    : "false")
                                                << " queue_ms="
                                                << tts_queue_ms
                                                << " synth_ms="
                                                << tts_result.synthesis_ms
                                                << " audio_sec="
                                                << tts_result.audio_seconds
                                                << " playback_ms="
                                                << tts_result.playback_ms
                                                << " xruns="
                                                << tts_result.xrun_count
                                                << " asr_text_to_end_ms="
                                                << e2e_ms
                                                << '\n';

                                            if (!tts_result.success)
                                            {
                                                std::cout
                                                    << "[TTS error] "
                                                    << tts_result.error_message
                                                    << '\n';
                                            }
                                        }

                                        // ------------------
                                        // 更新 TTS 任务统计
                                        // ------------------

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > lock(state_mutex);

                                            ++tts_completed;

                                            if (tts_result.success)
                                            {
                                                ++tts_successful;
                                            }
                                            else
                                            {
                                                ++tts_failed;
                                            }
                                        }

                                        // 唤醒等待中的主线程。
                                        completed_cv.notify_all();
                                    }
                                );
                        }
                        catch (const std::exception& e)
                        {
                            tts_submit_error = e.what();
                        }
                        catch (...)
                        {
                            tts_submit_error =
                                "unknown exception";
                        }

                        // ----------------------------------
                        // 12.7 处理 TTS 提交失败
                        // ----------------------------------

                        if (tts_status !=
                            TTSSubmitStatus::Accepted)
                        {
                            std::lock_guard<std::mutex>
                                out(print_mutex);

                            std::cout
                                << "[TTS rejected #"
                                << request_id
                                << "] ";

                            if (!tts_submit_error.empty())
                            {
                                std::cout
                                    << tts_submit_error;
                            }
                            else if (
                                tts_status ==
                                TTSSubmitStatus::QueueFull)
                            {
                                std::cout
                                    << "queue full";
                            }
                            else
                            {
                                std::cout
                                    << "not running";
                            }

                            std::cout << '\n';
                        }
                    }
                    else if (result.success)
                    {
                        // LLM 成功但回答为空，
                        // 不能向 TTS 提交空文本。
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        std::cout
                            << "[TTS skipped #"
                            << request_id
                            << "] LLM returned empty answer\n";
                    }

                    // --------------------------------------
                    // 12.8 更新任务计数
                    // --------------------------------------
                    //
                    // 重要：
                    // 先提交 TTS，再标记 LLM completed。
                    //
                    // 这样主线程等完所有 LLM 后，
                    // 就能确认不再产生新的 TTS 请求。
                    // --------------------------------------

                    {
                        std::lock_guard<std::mutex>
                            lock(state_mutex);

                        ++llm_completed;

                        if (result.success)
                        {
                            ++llm_successful;
                        }
                        else
                        {
                            ++llm_failed;
                        }

                        if (result.success &&
                            result.text.empty())
                        {
                            ++tts_empty;
                        }

                        if (has_answer)
                        {
                            if (tts_status ==
                                TTSSubmitStatus::Accepted)
                            {
                                ++tts_accepted;
                            }
                            else
                            {
                                ++tts_rejected;
                            }
                        }
                    }

                    completed_cv.notify_all();
                }
            );

        // --------------------------------------------------
        // 12.9 处理 LLM 任务提交结果
        // --------------------------------------------------

        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex>
                lock(state_mutex);

            ++llm_accepted;
        }
        else
        {
            // 只有 ASRWorker 修改该计数。
            ++llm_rejected;

            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "[LLM rejected #"
                << id
                << "] "
                << (status ==
                    LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "not running")
                << '\n';
        }
    };

    // ------------------------------------------------------
    // 13. 创建 ASRWorker 和 VadAudioWorker
    // ------------------------------------------------------

    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        on_text
    );

    VadAudioWorker producer(
        capture_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    std::cout
        << "[Listen] "
        << record_seconds
        << " seconds. "
        << (enable_vision ? "Ask ONE short voice question (text or camera).\n"
                           : "Ask ONE short text question and pause.\n")
        << std::flush;

    // ------------------------------------------------------
    // 14. 启动录音/VAD 和 ASR 工作线程
    // ------------------------------------------------------

    try
    {
        // ASR 消费者先启动。
        consumer.start();

        // VAD 录音生产者后启动。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Cannot start capture/ASR thread: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 15. 等待录音/VAD 和 ASR 完成
    // ------------------------------------------------------

    bool stop_reported = false;
    while (!producer.isFinished())
    {
        if (stop_signals.received() != 0 || stop_signals.failed())
        {
            producer.requestStop();
            if (!stop_reported)
            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "[Shutdown] signal=" << stop_signals.received()
                          << " stopping capture; draining accepted work\n" << std::flush;
                stop_reported = true;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    producer.join();

    consumer.join();
    asr.shutdown();
    std::cout << "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\n" << std::flush;

    // 此时 ASRWorker 已经退出，
    // 不会继续向 LLMWorker 提交新请求。

    // ------------------------------------------------------
    // 16. 通用 Worker 完成等待函数
    // ------------------------------------------------------
    //
    // 在等待期间，主线程每 2 秒输出一次进度。
    //
    // accepted / completed 都必须由 state_mutex 保护。
    // ------------------------------------------------------

    const auto wait_for_jobs =
        [&](const char* stage,
            const std::size_t& accepted,
            const std::size_t& completed,
            int deadline_seconds) -> bool
    {
        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::seconds(deadline_seconds);

        std::unique_lock<std::mutex>
            lock(state_mutex);

        while (completed < accepted)
        {
            const bool all_done =
                completed_cv.wait_for(
                    lock,
                    std::chrono::seconds(2),
                    [&]()
                    {
                        return completed >= accepted;
                    }
                );

            if (all_done)
            {
                break;
            }

            const std::size_t remaining =
                accepted - completed;

            // 输出日志前释放状态锁。
            lock.unlock();

            {
                std::lock_guard<std::mutex>
                    out(print_mutex);

                std::cout
                    << "[Main] waiting for "
                    << remaining
                    << " "
                    << stage
                    << " task(s)...\n"
                    << std::flush;
            }

            lock.lock();

            if (std::chrono::steady_clock::now() >=
                deadline)
            {
                return false;
            }
        }

        return true;
    };

    // ------------------------------------------------------
    // 17. 等待全部 LLM 任务完成
    // ------------------------------------------------------

    const bool llm_drained =
        wait_for_jobs(
            "LLM",
            llm_accepted,
            llm_completed,
            180
        );

    if (!llm_drained)
    {
        std::cerr
            << "[Timeout] LLM tasks "
            << "did not finish in 180s\n";
    }

    // ------------------------------------------------------
    // 18. 停止 LLMWorker
    // ------------------------------------------------------
    //
    // 必须等 LLMWorker 完全停止，
    // 才能确认不会再向 TTSWorker 提交任务。
    // ------------------------------------------------------

    llm_worker.requestStop();
    llm_worker.join();

    // LLM 不再被工作线程访问后，
    // 才允许释放 RKLLM Runtime。
    llm.shutdown();

    std::cout << "[Shutdown] LLM joined; Qwen runtime destroyed\n" << std::flush;

    // ------------------------------------------------------
    // 19. 等待全部 TTS 任务完成
    // ------------------------------------------------------
    //
    // 必须先等待 accepted == completed，
    // 然后再 requestStop。
    //
    // 否则会把队列中等待的 TTS 任务取消。
    // ------------------------------------------------------

    const bool tts_drained =
        wait_for_jobs(
            "TTS",
            tts_accepted,
            tts_completed,
            600
        );

    if (!tts_drained)
    {
        std::cerr
            << "[Timeout] TTS tasks "
            << "did not finish in 600s\n";
    }

    // ------------------------------------------------------
    // 20. 停止 TTSWorker
    // ------------------------------------------------------

    tts_worker.requestStop();
    tts_worker.join();

    std::cout << "[Shutdown] TTS joined; playback_xruns=" << playback.xrunCount()
              << '\n' << std::flush;

    // 只有 Worker 退出以后，
    // 才能安全关闭 ALSA 和 TTSService。
    playback.close();
    tts.shutdown();
    if (camera) camera->stop();
    if (vlm) vlm->shutdown();
    std::cout << "[Shutdown] playback/TTS closed; Camera stopped; VLM destroyed\n"
              << "[Shutdown] complete signal=" << stop_signals.received() << '\n'
              << std::flush;

    // ------------------------------------------------------
    // 21. 输出整个语音交互链路的统计
    // ------------------------------------------------------

    {
        std::lock_guard<std::mutex>
            out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM -> TTS summary ===\n"

            << "VAD segments: "
            << producer.producedCount()
            << '\n'

            << "ASR recognized: "
            << consumer.processedCount()
            << '\n'

            << "Audio queue dropped: "
            << audio_queue.droppedCount()
            << '\n'

            << "LLM accepted/completed/"
            << "success/failed/rejected: "
            << llm_accepted
            << '/'
            << llm_completed
            << '/'
            << llm_successful
            << '/'
            << llm_failed
            << '/'
            << llm_rejected
            << '\n'

            << "TTS accepted/completed/"
            << "success/failed/rejected/empty: "
            << tts_accepted
            << '/'
            << tts_completed
            << '/'
            << tts_successful
            << '/'
            << tts_failed
            << '/'
            << tts_rejected
            << '/'
            << tts_empty
            << '\n'

            << "Skipped VISION: "
            << skipped_vision
            << '\n'
            << "VISION completed/success/failed: "
            << vision_completed << '/'
            << vision_successful << '/'
            << vision_failed << '\n';

        if (!producer.ok())
        {
            std::cerr
                << "[VAD] "
                << producer.error()
                << '\n';
        }

        if (!consumer.ok())
        {
            std::cerr
                << "[ASR] "
                << consumer.error()
                << '\n';
        }
    }

    // ------------------------------------------------------
    // 22. 最终验收条件
    // ------------------------------------------------------

    const bool passed =
        producer.ok() &&
        consumer.ok() &&

        audio_queue.droppedCount() == 0 &&

        llm_drained &&
        tts_drained &&

        !stop_signals.failed() &&
        (stop_signals.received() != 0 || llm_accepted > 0 ||
         (enable_vision && vision_successful > 0)) &&
        llm_accepted == llm_completed &&
        llm_successful == llm_accepted &&
        llm_failed == 0 &&
        llm_rejected == 0 &&

        (!enable_vision || vision_failed == 0) &&
        tts_accepted == llm_successful + vision_successful &&
        tts_completed == tts_accepted &&
        tts_successful == tts_accepted &&
        tts_failed == 0 &&
        tts_rejected == 0 &&
        tts_empty == 0;

    std::cout
        << (passed ? (stop_signals.received() != 0 ? "STOPPED\n" : "PASS\n") : "FAIL\n");

    return passed ? 0 : 1;
}
catch (const std::exception& e)
{
    std::cerr << "[Fatal] Voice pipeline exception: " << e.what() << '\n';
    return 1;
}
catch (...)
{
    std::cerr << "[Fatal] Voice pipeline: unknown exception\n";
    return 1;
}
```

## 操作 10：`src/audio/asr_pipeline.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\asr_pipeline.cpp`

SHA256：`bec2d62b58d33faf02b04a415ca6c8f2deca335db17c904d69a66f6ff7bb8efd`

### 最终完整源码

```cpp

#include "audio/asr_pipeline.h"

#include "audio/asr_service.h"
#include "audio/audio_preprocessor.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

// ====================================================
// 1. AudioBufferQueue
// ====================================================

AudioBufferQueue::AudioBufferQueue(std::size_t capacity)
    : capacity_(capacity == 0 ? 1 : capacity)
{
}

bool AudioBufferQueue::push(AudioSegment segment)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (closed_)
            return false;

        // 队列满时丢弃最旧的完整音频段。
        if (items_.size() >= capacity_)
        {
            items_.pop_front();
            ++dropped_;
        }

        items_.push_back(std::move(segment));
    }

    cv_.notify_one();
    return true;
}

bool AudioBufferQueue::pop(AudioSegment& segment)
{
    std::unique_lock<std::mutex> lock(mutex_);

    cv_.wait(lock, [this] {
        return closed_ || !items_.empty();
    });

    if (items_.empty())
        return false;

    segment = std::move(items_.front());
    items_.pop_front();

    return true;
}

void AudioBufferQueue::close()
{
    {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
    }

    cv_.notify_all();
}

std::size_t AudioBufferQueue::droppedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return dropped_;
}

// ====================================================
// 3. ASRWorker
// ====================================================

ASRWorker::ASRWorker(
    AudioBufferQueue& queue,
    ASRService& asr,
    std::mutex& print_mutex,
    TextCallback on_text)
    : queue_(queue),
      asr_(asr),
      print_mutex_(print_mutex),
      on_text_(std::move(on_text))
{
}

ASRWorker::~ASRWorker()
{
    // Wake an idle consumer even if producer construction/start failed.
    if (thread_.joinable())
        requestStop();
    join();
}

void ASRWorker::start()
{
    if (started_)
        throw std::logic_error("ASRWorker can only be started once");
    thread_ = std::thread(
        &ASRWorker::run, this
    );
    started_ = true;
}

void ASRWorker::requestStop()
{
    queue_.close();
}

void ASRWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void ASRWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("ASRWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "ASRWorker: unknown exception";
        queue_.close();
    }
}

void ASRWorker::runImpl()
{
    AudioSegment segment;

    while (queue_.pop(segment))
    {
        using Clock = std::chrono::steady_clock;

        // 消费者真正从队列取出音频的时间。
        const auto popped_at = Clock::now();

        std::vector<float> samples;
        std::string error;

        if (!segment.samples.empty())
        {
            // VAD 已输出 Float32，直接移动。
            samples = std::move(segment.samples);
        }
        else
        {
            // 兼容原始 S16_LE 录音流水线。
            if (!AudioPreprocessor::convertS16ToFloat32(
                    segment.pcm,
                    16000,
                    1,
                    samples,
                    error))
            {
                error_ = "Preprocessing: " + error;
                queue_.close();
                return;
            }
        }

        if (samples.empty())
        {
            error_ = "Empty ASR audio segment";
            queue_.close();
            return;
        }

        std::string text;
        double latency_ms = 0.0;

        // 推理开始时间。
        const auto infer_start = Clock::now();

        if (!asr_.recognize(
                samples,
                text,
                latency_ms,
                error))
        {
            error_ = "ASR: " + error;
            queue_.close();
            return;
        }

        // 获取文字结果的时间。
        const auto result_ready = Clock::now();

        ++processed_;

        const double audio_duration_ms =
            1000.0 *
            static_cast<double>(samples.size()) /
            16000.0;

        const double rtf =
            latency_ms / audio_duration_ms;

        // 统一使用 steady_clock 时间差。
        auto elapsed_ms = [](
            Clock::time_point first,
            Clock::time_point second)
        {
            return std::chrono::duration<
                double, std::milli
            >(second - first).count();
        };

        {
            std::lock_guard<std::mutex> lock(
                print_mutex_
            );

            // 原始 ASR 输出格式保持不变。
            std::cout
                << "[ASR] Segment #"
                << segment.sequence
                << ": "
                << (text.empty() ? "<empty>" : text)
                << " | latency="
                << latency_ms
                << " ms"
                << " | RTF="
                << rtf
                << '\n';

            // 仅对来自 VAD 的有效时间戳计算。
            if (segment.timing_valid)
            {
                std::cout
                    << "[Timing] Segment #"
                    << segment.sequence

                    << " endpoint_est_ms="
                    << elapsed_ms(
                        segment.audio_end_estimated_at,
                        segment.vad_ready_at
                    )

                    << " vad_to_queue_ms="
                    << elapsed_ms(
                        segment.vad_ready_at,
                        segment.enqueued_at
                    )

                    << " queue_wait_ms="
                    << elapsed_ms(
                        segment.enqueued_at,
                        popped_at
                    )

                    << " preprocess_ms="
                    << elapsed_ms(
                        popped_at,
                        infer_start
                    )

                    << " asr_wall_ms="
                    << elapsed_ms(
                        infer_start,
                        result_ready
                    )

                    << " total_est_ms="
                    << elapsed_ms(
                        segment.audio_end_estimated_at,
                        result_ready
                    )

                    << '\n';
            }
        }

        // ASR 完成后回调 RequestProcessor。
        // 必须在释放 print_mutex_ 后执行。
        if (on_text_ && !text.empty())
        {
            try
            {
                on_text_(text);
            }
            catch (const std::exception& e)
            {
                error_ =
                    std::string("ASR text callback: ") +
                    e.what();

                queue_.close();
                return;
            }
            catch (...)
            {
                error_ =
                    "ASR text callback: unknown exception";

                queue_.close();
                return;
            }
        }
    }

    ok_ = true;
}
```

## 操作 11：`src/audio/audio_worker.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\audio_worker.cpp`

SHA256：`5b9a342d64215a4e703eda6848e2866b0b9ed4b38290e5263dfe68f3dd63049c`

### 最终完整源码

```cpp
#include "audio/asr_pipeline.h"
#include "audio/audio_capture.h"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

// ====================================================
// 2. AudioWorker
// ====================================================

AudioWorker::AudioWorker(
    std::string device,
    AudioBufferQueue& queue,
    std::mutex& print_mutex,
    std::size_t segment_count)
    : device_(std::move(device)),
      queue_(queue),
      print_mutex_(print_mutex),
      segment_count_(segment_count)
{
}

AudioWorker::~AudioWorker()
{
    requestStop();
    join();
}

void AudioWorker::start()
{
    if (started_)
        throw std::logic_error("AudioWorker can only be started once");
    thread_ = std::thread(
        &AudioWorker::run, this
    );
    started_ = true;
}

void AudioWorker::requestStop() noexcept
{
    stop_requested_.store(true);
}

void AudioWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void AudioWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("AudioWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "AudioWorker: unknown exception";
        queue_.close();
    }
}

void AudioWorker::runImpl()
{
    struct QueueCloser {
        AudioBufferQueue& queue;

        ~QueueCloser() {
            queue.close();
        }
    } closer{queue_};

    AudioCapture capture(device_);

    if (!capture.open(error_))
        return;

    constexpr std::size_t kFramesPerRead = 320;
    constexpr std::size_t kReadsPerSegment = 250;

    constexpr std::size_t kFramesPerSegment =
        kFramesPerRead * kReadsPerSegment;

    std::vector<std::int16_t> chunk;

    for (std::size_t id = 1;
         id <= segment_count_ &&
         !stop_requested_.load();
         ++id)
    {
        {
            std::lock_guard<std::mutex> lock(
                print_mutex_
            );

            std::cout
                << "[Capture] Recording #"
                << id
                << " (5 seconds)...\n"
                << std::flush;
        }

        AudioSegment segment;
        segment.sequence = id;

        segment.pcm.reserve(kFramesPerSegment);

        for (std::size_t i = 0;
             i < kReadsPerSegment;
             ++i)
        {
            if (stop_requested_.load())
                break;

            chunk.clear();

            if (!capture.readFrames(
                    chunk,
                    kFramesPerRead,
                    error_))
            {
                return;
            }

            if (chunk.size() != kFramesPerRead)
            {
                error_ = "Unexpected short ALSA chunk";
                return;
            }

            segment.pcm.insert(
                segment.pcm.end(),
                chunk.begin(),
                chunk.end()
            );
        }

        if (stop_requested_.load())
            break;

        if (!queue_.push(std::move(segment)))
        {
            error_ = "Audio queue was closed";
            return;
        }

        ++produced_;
    }

    ok_ = true;
}
```

## 操作 12：`src/audio/tts_worker_smoke.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\tts_worker_smoke.cpp`

SHA256：`dd42eda5efabe5f9224251b8f3be8f8272c03ed01cfec1c7889945154a16b0de`

### 最终完整源码

```cpp

#include "audio/tts_worker.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) try
{
    if (argc != 6)
    {
        std::cerr
            << "Usage: tts_worker_smoke "
            << "<model_dir> <device> <text> "
            << "<threads> <speaker_id>\n";

        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];
    const std::string text = argv[3];

    int threads = 2;
    int sid = 17;

    try
    {
        const std::string threads_arg = argv[4];
        const std::string sid_arg = argv[5];

        std::size_t n1 = 0;
        std::size_t n2 = 0;

        threads = std::stoi(threads_arg, &n1);
        sid = std::stoi(sid_arg, &n2);

        if (n1 != threads_arg.size() ||
            n2 != sid_arg.size() ||
            threads < 1 ||
            threads > 8 ||
            sid < 0)
        {
            throw std::invalid_argument(
                "Invalid threads or sid"
            );
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "Invalid threads or speaker_id\n";

        return 2;
    }

    std::string error;

    // 先创建并初始化两个 Service。
    TTSService tts;
    AlsaPlaybackService playback;

    std::cout
        << "[Init] Loading TTS model...\n"
        << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            sid))
    {
        std::cerr
            << "[Init] FAIL: "
            << error << '\n';

        return 1;
    }

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() -
            init_start
        ).count();

    std::cout
        << "[Init] OK init_ms="
        << init_ms << '\n';

    // ALSA 使用 TTS 模型的实际采样率。
    if (!playback.open(
            device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[ALSA] Open FAIL: "
            << error << '\n';

        return 1;
    }

    // Worker 最后构造，确保它最先析构。
    std::mutex done_mutex;
    std::condition_variable done_cv;

    bool finished = false;

    TTSWorkerResult final_result;
    double queue_wait_ms = -1.0;

    // 提交一个真实 TTS 播放任务。
    // Callback state must outlive the joined worker.
    TTSWorker worker(tts, playback, 2);

    if (!worker.start(error))
    {
        std::cerr
            << "[Worker] Start FAIL: "
            << error << '\n';

        return 1;
    }

    // 主线程用于接收完成回调的同步变量。
    const auto status = worker.submit(
        1,
        text,
        [&](std::uint64_t id,
            const TTSWorkerResult& result,
            double queue_ms)
        {
            if (id != 1)
            {
                return;
            }

            {
                std::lock_guard<std::mutex>
                    lock(done_mutex);

                final_result = result;
                queue_wait_ms = queue_ms;
                finished = true;
            }

            done_cv.notify_one();
        }
    );

    if (status != TTSSubmitStatus::Accepted)
    {
        std::cerr
            << "[Main] submit rejected\n";

        worker.requestStop();
        worker.join();

        return 1;
    }

    // 这条日志应在 TTS 合成完成前出现。
    std::cout
        << "[Main] submit accepted; "
        << "main thread remains responsive\n"
        << std::flush;

    // 主线程阻塞等待“完成通知”，
    // 但不负责执行 TTS 推理或音频播放。
    bool completed = false;

    {
        std::unique_lock<std::mutex>
            lock(done_mutex);

        completed = done_cv.wait_for(
            lock,
            std::chrono::seconds(180),
            [&] {
                return finished;
            }
        );
    }

    // 退出前执行安全停止。
    worker.requestStop();
    worker.join();

    if (!completed)
    {
        std::cerr
            << "[Worker] FAIL: completion timeout\n";

        return 1;
    }

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Done] success="
        << std::boolalpha
        << final_result.success
        << " queue_ms=" << queue_wait_ms
        << " synth_ms=" << final_result.synthesis_ms
        << " audio_sec=" << final_result.audio_seconds
        << " playback_ms=" << final_result.playback_ms
        << " xrun_count=" << final_result.xrun_count
        << '\n';

    if (!final_result.success)
    {
        std::cerr
            << "[Done] error="
            << final_result.error_message
            << '\n';

        return 1;
    }

    std::cout << "PASS\n";

    return 0;
}

catch (const std::exception& e)
{
    std::cerr << "[Fatal] Worker smoke exception: " << e.what() << '\n';
    return 1;
}
catch (...)
{
    std::cerr << "[Fatal] Worker smoke: unknown exception\n";
    return 1;
}
```

## 操作 13：`src/audio/vad_audio_worker.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\src\audio\vad_audio_worker.cpp`

SHA256：`4252accf02fcce9af5fc2822c640628c63331cd59b15399ad953ed498055c91b`

### 最终完整源码

```cpp

#include "audio/vad_audio_worker.h"

#include "audio/audio_capture.h"
#include "audio/audio_preprocessor.h"

#include <sherpa-onnx/c-api/c-api.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <deque>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <memory>
#include <utility>
#include <vector>

VadAudioWorker::VadAudioWorker(
    std::string device,
    std::string vad_model,
    AudioBufferQueue& queue,
    std::mutex& print_mutex,
    std::size_t record_seconds)
    : device_(std::move(device)),
      vad_model_(std::move(vad_model)),
      queue_(queue),
      print_mutex_(print_mutex),
      record_seconds_(record_seconds)
{
}

VadAudioWorker::~VadAudioWorker()
{
    requestStop();
    join();
}

void VadAudioWorker::start()
{
    if (started_)
        throw std::logic_error("VadAudioWorker can only be started once");
    thread_ = std::thread(
        &VadAudioWorker::run, this
    );
    started_ = true;
}

void VadAudioWorker::requestStop() noexcept
{
    stop_requested_.store(true);
}

void VadAudioWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void VadAudioWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("VadAudioWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "VadAudioWorker: unknown exception";
        queue_.close();
    }
    finished_.store(true, std::memory_order_release);
}

void VadAudioWorker::runImpl()
{
    // 生产者结束时关闭队列，唤醒消费者。
    struct QueueCloser {
        AudioBufferQueue& queue;

        ~QueueCloser() {
            queue.close();
        }
    } closer{queue_};

    if (stop_requested_.load())
    {
        ok_ = true;
        return;
    }

    // ==================================================
    // 1. 初始化 Silero VAD
    // ==================================================

    SherpaOnnxVadModelConfig config{};

    config.silero_vad.model =
        vad_model_.c_str();

    config.silero_vad.threshold = 0.50f;
    config.silero_vad.min_silence_duration = 0.60f;
    config.silero_vad.min_speech_duration = 0.25f;
    config.silero_vad.max_speech_duration = 8.0f;
    config.silero_vad.window_size = 512;

    config.sample_rate = 16000;
    config.num_threads = 1;
    config.provider = "cpu";

    using VadPtr = std::unique_ptr<
        const SherpaOnnxVoiceActivityDetector,
        decltype(
            &SherpaOnnxDestroyVoiceActivityDetector
        )
    >;

    VadPtr vad(
        SherpaOnnxCreateVoiceActivityDetector(
            &config,
            30.0f
        ),
        &SherpaOnnxDestroyVoiceActivityDetector
    );

    if (!vad)
    {
        error_ = "Failed to initialize Silero VAD";
        return;
    }

    // ==================================================
    // 2. ALSA 初始化和异常计数
    // ==================================================

    AudioCapture capture(device_);

    // 退出采集线程时，自动打印异常统计。
    // capture 对象在这个 RAII 结构析构期间仍有效。
    struct CaptureStatsPrinter {
        AudioCapture& capture;
        std::mutex& print_mutex;

        ~CaptureStatsPrinter()
        {
            const auto s = capture.stats();

            std::lock_guard<std::mutex> lock(
                print_mutex
            );

            std::cout
                << "[ALSA] XRUN="
                << s.xrun_count

                << " Suspends="
                << s.suspend_count

                << " Recoveries="
                << s.recovered_errors

                << " RecoveryFailures="
                << s.recovery_failures

                << '\n'
                << std::flush;
        }
    } stats_printer{capture, print_mutex_};

    if (!capture.open(error_))
        return;

    constexpr std::size_t kSampleRate = 16000;
    constexpr std::size_t kChunkFrames = 320;
    constexpr std::size_t kWindowFrames = 512;

    constexpr std::size_t kHistoryCapacity =
        kSampleRate * 15;

    constexpr std::int64_t kPreRollSamples = 3200;

    std::deque<float> history;

    std::int64_t captured_samples = 0;

    // 用采集块读取完成时的主机时钟，
    // 估算某个样本对应的时间。
    //
    // 这不是 ALSA 硬件时间戳。
    using Clock = std::chrono::steady_clock;

    Clock::time_point latest_read_completed_at{};

    std::int64_t latest_read_end_sample = 0;

    // VAD 接受 512 Samples 的窗口。
    std::array<float, kWindowFrames> window{};

    std::size_t filled = 0;

    std::vector<std::int16_t> chunk;
    std::vector<float> float_chunk;

    // ==================================================
    // 3. 从 VAD 中提取完整语音段
    // ==================================================

    auto drain_segments = [&]() -> bool
    {
        while (!SherpaOnnxVoiceActivityDetectorEmpty(
                   vad.get()))
        {
            using SpeechPtr = std::unique_ptr<
                const SherpaOnnxSpeechSegment,
                decltype(
                    &SherpaOnnxDestroySpeechSegment
                )
            >;

            SpeechPtr speech(
                SherpaOnnxVoiceActivityDetectorFront(
                    vad.get()
                ),
                &SherpaOnnxDestroySpeechSegment
            );

            if (!speech ||
                speech->n <= 0 ||
                speech->samples == nullptr)
            {
                error_ = "Invalid VAD speech segment";
                return false;
            }

            AudioSegment segment;
            segment.sequence = produced_ + 1;

            // VAD 语音段在整条音频流中的起始采样索引。
            const std::int64_t speech_start =
                std::max<std::int64_t>(
                    0,
                    speech->start
                );

            // 历史缓存的起始样本位置。
            const std::int64_t history_start =
                captured_samples -
                static_cast<std::int64_t>(
                    history.size()
                );

            // 最多增加 200 ms 前导音频。
            const std::int64_t prefix_start =
                std::max(
                    history_start,
                    std::max<std::int64_t>(
                        0,
                        speech_start - kPreRollSamples
                    )
                );

            const std::int64_t prefix_end =
                std::min(
                    speech_start,
                    captured_samples
                );

            for (std::int64_t pos = prefix_start;
                 pos < prefix_end;
                 ++pos)
            {
                segment.samples.push_back(
                    history[
                        static_cast<std::size_t>(
                            pos - history_start
                        )
                    ]
                );
            }

            // 拼接完整的 VAD 语音段。
            segment.samples.insert(
                segment.samples.end(),
                speech->samples,
                speech->samples + speech->n
            );

            const double duration =
                static_cast<double>(
                    segment.samples.size()
                ) / kSampleRate;

            // ==================================================
            // 4. 计算音频段末尾的估算时间戳
            // ==================================================

            // VAD 返回音频段的末尾采样点。
            // 不包含额外附加的 pre-roll。
            const std::int64_t audio_end_index =
                speech->start +
                static_cast<std::int64_t>(
                    speech->n
                );

            const auto captured_stats =
                capture.stats();

            // 出现可观察的 XRUN / 挂起时，
            // 采样索引与时间之间可能出现不连续，
            // 此时不输出可能误导的时间估算。
            if (
                latest_read_completed_at !=
                    Clock::time_point{} &&

                audio_end_index >= 0 &&

                audio_end_index <=
                    latest_read_end_sample &&

                captured_stats.xrun_count == 0 &&

                captured_stats.suspend_count == 0
            )
            {
                const double seconds_ago =
                    static_cast<double>(
                        latest_read_end_sample -
                        audio_end_index
                    ) /
                    static_cast<double>(
                        kSampleRate
                    );

                segment.audio_end_estimated_at =
                    latest_read_completed_at -
                    std::chrono::duration_cast<
                        Clock::duration
                    >(
                        std::chrono::duration<double>(
                            seconds_ago
                        )
                    );

                segment.timing_valid = true;
            }

            // 完整语音已复制，可以从 VAD 内部删除。
            SherpaOnnxVoiceActivityDetectorPop(
                vad.get()
            );

            const auto sequence = segment.sequence;

            // VAD 完成语音段处理的时刻。
            segment.vad_ready_at = Clock::now();

            // 准备送入队列的时刻。
            segment.enqueued_at = Clock::now();

            if (!queue_.push(std::move(segment)))
            {
                error_ = "Audio queue was closed";
                return false;
            }

            ++produced_;

            {
                std::lock_guard<std::mutex> lock(
                    print_mutex_
                );

                std::cout
                    << "[VAD] Speech #"
                    << sequence
                    << " duration="
                    << duration
                    << " s\n"
                    << std::flush;
            }
        }

        return true;
    };

    // ==================================================
    // 5. 连续读取 ALSA 数据
    // ==================================================

    const std::size_t total_chunks =
        record_seconds_ *
        kSampleRate /
        kChunkFrames;

    for (
        std::size_t i = 0;

        i < total_chunks &&
        !stop_requested_.load();

        ++i
    )
    {
        chunk.clear();

        if (!capture.readFrames(
                chunk,
                kChunkFrames,
                error_))
        {
            return;
        }

        if (chunk.size() != kChunkFrames)
        {
            error_ = "Unexpected short ALSA chunk";
            return;
        }

        // ALSA 当前块读取完成，记录主机时间。
        // 每块为 320 / 16000 = 20 ms。
        latest_read_completed_at =
            Clock::now();

        latest_read_end_sample =
            captured_samples +
            static_cast<std::int64_t>(
                chunk.size()
            );

        // S16_LE PCM 转 Float32。
        if (!AudioPreprocessor::convertS16ToFloat32(
                chunk,
                16000,
                1,
                float_chunk,
                error_))
        {
            return;
        }

        for (float sample : float_chunk)
        {
            // 保留历史音频用于前导补偿。
            history.push_back(sample);
            ++captured_samples;

            if (history.size() > kHistoryCapacity)
                history.pop_front();

            // 重组成 512 Samples 的 VAD 窗口。
            window[filled++] = sample;

            if (filled == kWindowFrames)
            {
                SherpaOnnxVoiceActivityDetectorAcceptWaveform(
                    vad.get(),
                    window.data(),
                    static_cast<std::int32_t>(
                        kWindowFrames
                    )
                );

                filled = 0;

                if (!drain_segments())
                    return;
            }
        }
    }

    // ==================================================
    // 6. 结束采集并 Flush VAD
    // ==================================================

    if (filled != 0)
    {
        // 不足 512 Samples 的窗口补零。
        std::fill(
            window.begin() + filled,
            window.end(),
            0.0f
        );

        SherpaOnnxVoiceActivityDetectorAcceptWaveform(
            vad.get(),
            window.data(),
            static_cast<std::int32_t>(
                kWindowFrames
            )
        );
    }

    SherpaOnnxVoiceActivityDetectorFlush(
        vad.get()
    );

    if (!drain_segments())
        return;

    // A requested stop is successful if capture/VAD cleanup and final flush succeeded.
    ok_ = true;
}
```

## 操作 14：`tests/asr_pipeline_tests.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tests\asr_pipeline_tests.cpp`

SHA256：`c13703450a49482c369471a0ff53c53e996a81311eaa34d23c643a76d05bbd23`

### 最终完整源码

```cpp
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"

#include <atomic>
#include <chrono>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

// Test-only service definitions. Never linked into multimodal_audio.
// This verifies production queue/worker control flow, not ASR inference.
namespace
{
enum class Fault { None, Standard, Unknown };
std::atomic<Fault> fault{Fault::None};
std::atomic<int> calls{0};

void check(bool okay, const char* message)
{
    if (!okay) throw std::runtime_error(message);
}

AudioSegment segment(std::uint64_t id)
{
    AudioSegment result;
    result.sequence = id;
    result.samples.assign(160, 0.0f);
    return result;
}

void testQueue()
{
    AudioBufferQueue queue(2);
    check(queue.push(segment(1)) && queue.push(segment(2)) &&
          queue.push(segment(3)), "queue push");
    check(queue.droppedCount() == 1, "drop-oldest count");
    queue.close();
    queue.close();
    check(!queue.push(segment(4)), "closed queue accepted input");
    AudioSegment output;
    check(queue.pop(output) && output.sequence == 2, "drop-oldest order");
    check(queue.pop(output) && output.sequence == 3, "queue drain order");
    check(!queue.pop(output), "closed queue did not reach EOF");

    AudioBufferQueue idle(1);
    auto waiter = std::async(std::launch::async, [&] {
        AudioSegment value;
        return idle.pop(value);
    });
    idle.close();
    check(waiter.wait_for(std::chrono::seconds(2)) == std::future_status::ready,
          "close did not wake consumer");
    check(!waiter.get(), "empty close returned a segment");
}

void testIdleDestructionAndUnwind()
{
    ASRService asr;
    std::mutex print_mutex;
    AudioBufferQueue queue(1);
    {
        ASRWorker worker(queue, asr, print_mutex);
        worker.start();
        // No producer ever starts or closes input. Destructor must wake pop().
    }
    check(!queue.push(segment(1)), "destructor did not close input");

    AudioBufferQueue unwind_queue(1);
    bool caught = false;
    try
    {
        ASRWorker worker(unwind_queue, asr, print_mutex);
        worker.start();
        throw std::runtime_error("test owner startup failure");
    }
    catch (const std::runtime_error&) { caught = true; }
    check(caught && !unwind_queue.push(segment(1)), "exception unwind cleanup");
}

void testDrainAndStartContract()
{
    ASRService asr;
    std::mutex print_mutex;
    AudioBufferQueue queue(3);
    std::vector<std::string> texts; // Outlives worker and its callback.
    calls = 0;
    fault = Fault::None;
    ASRWorker worker(queue, asr, print_mutex,
                     [&](const std::string& text) { texts.push_back(text); });
    check(queue.push(segment(1)), "float input");
    AudioSegment pcm;
    pcm.sequence = 2;
    pcm.pcm.assign(160, 0);
    check(queue.push(std::move(pcm)), "PCM input");
    worker.start();
    bool rejected = false;
    try { worker.start(); }
    catch (const std::logic_error&) { rejected = true; }
    check(rejected, "second start was not rejected");
    worker.requestStop(); // Close and drain; no silent cancellation.
    worker.join();
    worker.join();
    check(worker.ok() && worker.processedCount() == 2 && calls == 2 &&
          texts.size() == 2, "stop did not drain both input formats");
    rejected = false;
    try { worker.start(); }
    catch (const std::logic_error&) { rejected = true; }
    check(rejected, "restart after join was not rejected");
}

void testFailures()
{
    ASRService asr;
    std::mutex print_mutex;
    for (const auto value : {Fault::Standard, Fault::Unknown})
    {
        fault = value;
        AudioBufferQueue queue(1);
        ASRWorker worker(queue, asr, print_mutex);
        check(queue.push(segment(1)), "fault input");
        worker.start();
        worker.join(); // Failure itself must close input.
        check(!worker.ok() && !worker.error().empty() &&
              !queue.push(segment(2)), "inference exception escaped worker");
    }
    fault = Fault::None;
    for (const bool unknown : {false, true})
    {
        AudioBufferQueue queue(1);
        ASRWorker worker(queue, asr, print_mutex, [unknown](const std::string&) {
            if (unknown) throw 7;
            throw std::runtime_error("test callback failure");
        });
        check(queue.push(segment(1)), "callback input");
        worker.start();
        worker.join();
        check(!worker.ok() && worker.error().find("callback") != std::string::npos,
              "callback error lost");
    }
    AudioBufferQueue queue(1);
    ASRWorker worker(queue, asr, print_mutex);
    check(queue.push(AudioSegment{}), "empty input enqueue");
    worker.start();
    worker.join();
    check(!worker.ok() && !worker.error().empty(), "empty input accepted");
}
} // namespace

ASRService::~ASRService() = default;
bool ASRService::recognize(const std::vector<float>& samples, std::string& text,
                           double& latency_ms, std::string& error)
{
    ++calls;
    if (fault == Fault::Standard) throw std::runtime_error("test service failure");
    if (fault == Fault::Unknown) throw 42;
    check(samples.size() == 160, "worker changed sample count");
    text = "test-only transcript";
    latency_ms = 0.0; // Test data only; never reported as model performance.
    error.clear();
    return true;
}

int main()
{
    try
    {
        testQueue();
        testIdleDestructionAndUnwind();
        testDrainAndStartContract();
        testFailures();
        std::cout << "ASR pipeline tests passed: queue, idle destruction, unwind, "
                     "drain, one-shot start, service/callback faults. No SDK or hardware used.\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
```

## 操作 15：`tests/llm_worker_tests.cpp`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tests\llm_worker_tests.cpp`

SHA256：`3e65faf61186d475ad58dcf2031e6d3f76f7127cd8d7ed8a143ad099064eff3f`

### 最终完整源码

```cpp
#include "ai/llm_worker.h"

#include <chrono>
#include <condition_variable>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std::chrono_literals;

namespace
{

void check(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

class GatedLLM final : public ILLMBackend
{
public:
    std::promise<void> entered;
    std::promise<void> release;
    std::shared_future<void> gate =
        release.get_future().share();

    int calls = 0;

    bool initialize(
        const BackendConfig&,
        std::string& error) override
    {
        error.clear();
        return true;
    }

    InferenceResult infer(
        const std::string& question) override
    {
        return inferStreaming(question, {});
    }

    InferenceResult inferStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk) override
    {
        ++calls;

        if (calls == 1)
        {
            entered.set_value();
            gate.wait();
        }

        if (on_chunk)
        {
            on_chunk("part:");
            on_chunk(question);
        }

        InferenceResult result;
        result.success = true;
        result.text = "part:" + question;
        return result;
    }

    void shutdown() noexcept override {}
};

void testQueueFullAndFifo()
{
    auto backend = std::make_unique<GatedLLM>();
    auto* gate = backend.get();
    auto first_entered = gate->entered.get_future();

    LLMEngine engine(std::move(backend));
    std::string error;
    check(engine.initialize({}, error), "mock LLM init");

    std::mutex done_mutex;
    std::condition_variable done_cv;
    std::vector<std::uint64_t> completed;
    std::vector<std::string> chunks;
    bool all_success = true;

    const auto on_chunk =
        [&](std::uint64_t id, const std::string& text)
    {
        std::lock_guard<std::mutex> lock(done_mutex);
        chunks.push_back(std::to_string(id) + ":" + text);
    };

    const auto on_done =
        [&](std::uint64_t id,
            const InferenceResult& result,
            double wait_ms)
    {
        {
            std::lock_guard<std::mutex> lock(done_mutex);
            completed.push_back(id);

            if (!result.success || wait_ms < 0.0)
                all_success = false;
        }

        done_cv.notify_all();
    };

    LLMWorker worker(engine, 2);

    check(
        worker.submit(0, "not started")
            == LLMSubmitStatus::NotRunning,
        "submit before start");

    check(worker.start(error), "worker start");

    check(
        worker.submit(1, "A", on_chunk, on_done)
            == LLMSubmitStatus::Accepted,
        "submit first");

    const bool entered =
        first_entered.wait_for(2s)
        == std::future_status::ready;

    const bool accept2 =
        worker.submit(2, "B", on_chunk, on_done)
        == LLMSubmitStatus::Accepted;

    const bool accept3 =
        worker.submit(3, "C", on_chunk, on_done)
        == LLMSubmitStatus::Accepted;

    const bool full =
        worker.submit(4, "D", on_chunk, on_done)
        == LLMSubmitStatus::QueueFull;

    const bool pending2 = worker.pendingCount() == 2;
    const bool rejected1 = worker.rejectedCount() == 1;

    // 即使检查失败，也先释放阻塞的 mock，避免 join 卡死。
    gate->release.set_value();

    bool finished = false;

    {
        std::unique_lock<std::mutex> lock(done_mutex);

        finished = done_cv.wait_for(
            lock,
            3s,
            [&] { return completed.size() == 3; });
    }

    worker.requestStop();
    worker.join();

    check(entered, "worker did not start first inference");

    check(
        accept2 && accept3 && full && pending2 && rejected1,
        "bounded queue behaviour");

    check(finished && all_success, "worker completion");

    check(
        completed == std::vector<std::uint64_t>({1, 2, 3}),
        "FIFO order");

    check(chunks.size() == 6, "stream chunks not propagated");

    check(
        worker.submit(5, "E")
            == LLMSubmitStatus::NotRunning,
        "submit after stop");
}

void testStopCancelsPending()
{
    auto backend = std::make_unique<GatedLLM>();
    auto* gate = backend.get();
    auto first_entered = gate->entered.get_future();

    LLMEngine engine(std::move(backend));
    std::string error;
    check(engine.initialize({}, error), "mock LLM init");

    std::mutex mutex;
    std::vector<std::uint64_t> ids;
    std::vector<bool> success;
    std::vector<std::string> errors;

    const auto on_done =
        [&](std::uint64_t id,
            const InferenceResult& result,
            double)
    {
        std::lock_guard<std::mutex> lock(mutex);
        ids.push_back(id);
        success.push_back(result.success);
        errors.push_back(result.error_message);
    };

    LLMWorker worker(engine, 2);
    check(worker.start(error), "worker start");

    check(
        worker.submit(11, "active", {}, on_done)
            == LLMSubmitStatus::Accepted,
        "active submit");

    const bool entered =
        first_entered.wait_for(2s)
        == std::future_status::ready;

    const bool second_accepted =
        worker.submit(12, "queued", {}, on_done)
        == LLMSubmitStatus::Accepted;

    worker.requestStop();

    const bool rejected =
        worker.submit(13, "after stop")
        == LLMSubmitStatus::NotRunning;

    gate->release.set_value();
    worker.join();

    check(
        entered && second_accepted && rejected,
        "stop setup");

    check(
        ids == std::vector<std::uint64_t>({11, 12}),
        "stop completion order");

    check(
        success.size() == 2 && success[0] && !success[1],
        "active vs queued cancellation");

    check(
        errors[1].find("cancelled") != std::string::npos,
        "cancel diagnostic");
}

void testCallbackExceptionsAndUnwind()
{
    auto backend = std::make_unique<GatedLLM>();
    auto* gate = backend.get();
    gate->release.set_value(); // No blocking inference in this test.
    LLMEngine engine(std::move(backend));
    std::string error;
    check(engine.initialize({}, error), "callback test init");

    // Shared callback state is declared before the Worker.
    std::promise<InferenceResult> first;
    auto first_result = first.get_future();
    std::promise<void> second;
    auto second_done = second.get_future();
    bool caught = false;
    try
    {
        LLMWorker worker(engine, 2);
        check(worker.start(error), "callback worker start");
        check(worker.submit(21, "chunk fault",
            [](std::uint64_t, const std::string&) {
                throw std::runtime_error("test chunk fault");
            },
            [&](std::uint64_t, const InferenceResult& result, double) {
                first.set_value(result);
                throw std::runtime_error("test done fault");
            }) == LLMSubmitStatus::Accepted, "callback fault submit");
        check(first_result.wait_for(2s) == std::future_status::ready,
              "chunk fault completion missing");
        const auto result = first_result.get();
        check(!result.success && result.text.empty() &&
              result.error_message.find("callback") != std::string::npos,
              "chunk exception was not reported");
        check(worker.submit(22, "following request", {},
            [&](std::uint64_t, const InferenceResult& value, double) {
                if (value.success) second.set_value();
            }) == LLMSubmitStatus::Accepted, "follow-up submit");
        check(second_done.wait_for(2s) == std::future_status::ready,
              "done exception killed worker");
        // Owner unwinds with the Worker still running, waiting for input.
        throw std::runtime_error("test owner failure");
    }
    catch (const std::runtime_error& e)
    {
        if (std::string(e.what()) != "test owner failure") throw;
        caught = true;
    }
    check(caught && gate->calls == 2, "unwind failed to join worker");
}

}  // namespace

int main()
{
    try
    {
        testQueueFullAndFifo();
        testStopCancelsPending();
        testCallbackExceptionsAndUnwind();

        std::cout
            << "LLMWorker tests passed: "
            << "FIFO, bounded queue, streaming, stop.\n";

        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "LLMWorker tests FAILED: "
            << e.what() << '\n';

        return 1;
    }
}
```

## 操作 16：`tests/stage5_board_tools_tests.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tests\stage5_board_tools_tests.py`

SHA256：`a772f6e12d022584d2468a46e1565f9ffe15487872c34d2db68e89098f3131a0`

### 最终完整源码

```python
"""Local synthetic fixtures for review tooling. These are NOT board logs/results."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


capture = module("capture", "tools/stage5_board_capture.py")
bundle = module("bundle", "tools/stage5_prepare_board_bundle.py")

# Fabricated unit-test input only; never written to reports/stage5_01_board.
FIXTURE = """VAD segments: 2
ASR recognized: 2
Audio queue dropped: 0
LLM accepted/completed/success/failed/rejected: 1/1/1/0/0
TTS accepted/completed/success/failed/rejected/empty: 2/2/2/0/0/0
VISION completed/success/failed: 1/1/0
PASS
"""


class ToolTests(unittest.TestCase):
    def test_accepts_consistent_fixture_only(self):
        self.assertTrue(capture.accepted(capture.parse_summary(FIXTURE), 0, "both", False, False, False))

    def test_rejects_sigint_even_if_last_output_says_pass(self):
        for code in (0, 130, -2):
            self.assertFalse(capture.accepted(capture.parse_summary(FIXTURE), code, "both", True, False, False))

    def test_rejects_timeout_or_forced_kill(self):
        summary = capture.parse_summary(FIXTURE)
        self.assertFalse(capture.accepted(summary, 0, "both", False, True, False))
        self.assertFalse(capture.accepted(summary, 0, "both", False, False, True))

    def test_rejects_pass_without_counts(self):
        self.assertFalse(capture.accepted(capture.parse_summary("PASS\n"), 0, "both", False, False, False))

    def test_rejects_missing_branch_or_dropped_audio(self):
        for text in (FIXTURE.replace("Audio queue dropped: 0", "Audio queue dropped: 1"),
                     FIXTURE.replace("VISION completed/success/failed: 1/1/0", "VISION completed/success/failed: 0/0/0")):
            self.assertFalse(capture.accepted(capture.parse_summary(text), 0, "both", False, False, False))

    def test_rejects_corrupted_counts_and_errors(self):
        for text in (FIXTURE.replace("1/1/1/0/0", "1"), FIXTURE + "[Fatal] fixture\n"):
            self.assertFalse(capture.accepted(capture.parse_summary(text), 0, "both", False, False, False))

    def test_source_bundle_excludes_models_and_binaries(self):
        selected = bundle.package_files(ROOT)
        self.assertIn(Path("src/audio/audio_worker.cpp"), selected)
        self.assertIn(Path("CMakeLists.txt"), selected)
        self.assertIn(Path("tools/stage5_board_build.sh"), selected)
        self.assertTrue(all(not p.is_absolute() and ".." not in p.parts for p in selected))
        self.assertFalse(any(p.parts[0] in {"models", "build", "backups"} or
                             p.suffix in {".onnx", ".rkllm", ".rknn", ".so", ".exe"} for p in selected))


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
```

## 操作 17：`tools/stage5_board_build.sh`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_build.sh`

SHA256：`68732afc2050ad76794ecc59f4d1d975555e1280ce2a1413819513f567ac4e33`

### 最终完整源码

```bash
#!/usr/bin/env bash
# Board execution is separately authorized by the user; not run by packaging.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $(uname -m) == aarch64 || $(uname -m) == arm64 ]] || { echo 'ARM64 required'; exit 2; }
[[ -x "$STAGE5_ORIGINAL/build/stage5_full/asr_llm_tts_smoke" ]] || { echo 'Stable executable missing'; exit 2; }
cd -- "$ROOT"
sha256sum --check SOURCE_SHA256SUMS
stamp=$(date -u +%Y%m%dT%H%M%SZ)
logdir="$ROOT/reports/stage5_01_board/build_$stamp"
mkdir -p -- "$ROOT/reports/stage5_01_board"
mkdir -- "$logdir"
exec > >(tee "$logdir/session.log") 2>&1
printf '=== target environment ===\n'
date -Is
uname -a
cmake --version
c++ --version
stage5_stable_fingerprint > "$logdir/stable_before.sha256"
finish() {
    code=$?
    trap - EXIT
    set +e
    stage5_stable_fingerprint > "$logdir/stable_after.sha256"
    fingerprint_code=$?
    cmp "$logdir/stable_before.sha256" "$logdir/stable_after.sha256"
    compare_code=$?
    if [[ "$fingerprint_code" != 0 || "$compare_code" != 0 ]]; then code=1; fi
    printf '%s\n' "$code" > "$logdir/exit_code.txt"
    exit "$code"
}
trap finish EXIT
stage5_check_dependencies
cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" \
    -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" 2>&1 | tee "$logdir/configure.log"
cmake --build "$ROOT/build/stage5_01_board" --parallel 3 2>&1 | tee "$logdir/build.log"
ctest --test-dir "$ROOT/build/stage5_01_board" --output-on-failure -V 2>&1 | tee "$logdir/ctest.log"
ldd "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" | tee "$logdir/ldd.log"
if grep -q 'not found' "$logdir/ldd.log"; then exit 1; fi
printf 'BUILD_AND_PORTABLE_CTEST_COMPLETE: real voice tests still required.\n'
```

## 操作 18：`tools/stage5_board_capture.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_capture.py`

SHA256：`4cef97d1394b364a5ce76e1ae660370d15744547dc18be255e8f2d0fcaece3b2`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Capture one authorized isolated board run; never treats SIGINT death as clean shutdown."""

import argparse
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

REVIEW = Path("/home/cat/projects/RK3576/rk3576_multimodal_stage5_review")


def resource_sample(pid):
    result = {"elapsed_monotonic": time.monotonic(), "pid": pid}
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        for line in status.splitlines():
            key = line.split(":", 1)[0]
            if key in {"VmRSS", "VmHWM", "VmSize", "Threads", "State"}:
                result[key] = line.split(":", 1)[1].strip()
        result["fd_count"] = len(list(Path(f"/proc/{pid}/fd").iterdir()))
        result["task_ids"] = sorted(p.name for p in Path(f"/proc/{pid}/task").iterdir())
    except (OSError, ValueError) as error:
        result["sample_error"] = str(error)
    return result


def parse_summary(text):
    import re
    parsed = {}
    for label in ("VAD segments", "ASR recognized", "Audio queue dropped",
                  "LLM accepted/completed/success/failed/rejected",
                  "TTS accepted/completed/success/failed/rejected/empty",
                  "VISION completed/success/failed"):
        found = re.search(r"^" + re.escape(label) + r": ([0-9/]+)\s*$", text, re.M)
        parsed[label] = [int(x) for x in found.group(1).split("/")] if found else None
    parsed["program_PASS"] = bool(re.search(r"^PASS\s*$", text, re.M))
    parsed["error_lines"] = [line for line in text.splitlines() if re.search(
        r"\[Fatal\]|\[Timeout\]|\[.*(?:error|Error|rejected)\]|segmentation fault|bad_alloc", line)]
    return parsed


def accepted(summary, exitcode, expect, interrupted, timed_out, forced):
    # The first submitted patch has no cooperative voice SIGINT implementation.
    # Signal cases are observations, never acceptance passes merely for exiting.
    if interrupted or timed_out or forced or exitcode != 0 or not summary["program_PASS"]:
        return False
    llm = summary["LLM accepted/completed/success/failed/rejected"]
    tts = summary["TTS accepted/completed/success/failed/rejected/empty"]
    vision = summary["VISION completed/success/failed"]
    vad = summary["VAD segments"]
    asr = summary["ASR recognized"]
    dropped = summary["Audio queue dropped"]
    if not all(x is not None for x in (llm, tts, vision, vad, asr, dropped)):
        return False
    if [len(x) for x in (llm, tts, vision, vad, asr, dropped)] != [5, 6, 3, 1, 1, 1]:
        return False
    if summary["error_lines"]:
        return False
    if dropped != [0] or not (vad[0] == asr[0] and asr[0] > 0):
        return False
    if not (llm[0] == llm[1] == llm[2] and llm[3:] == [0, 0]):
        return False
    if not (vision[0] == vision[1] and vision[2] == 0):
        return False
    if not (tts[0] == tts[1] == tts[2] == llm[2] + vision[1] and tts[3:] == [0, 0, 0]):
        return False
    return (expect == "text" and llm[2] > 0 or
            expect == "vision" and vision[1] > 0 or
            expect == "both" and llm[2] > 0 and vision[1] > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Explicitly run only after user authorization")
    parser.add_argument("--name", required=True)
    parser.add_argument("--expect", choices=("text", "vision", "both"), default="both")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--sigint-after-ready", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not args.name.replace("_", "").replace("-", "").isalnum():
        parser.error("Provide a simple run name and -- executable arguments")
    if args.timeout <= 0 or (args.sigint_after_ready is not None and args.sigint_after_ready < 0):
        parser.error("Invalid time limit")
    if not args.execute:
        print(json.dumps({"status": "NOT_EXECUTED", "command": command,
                          "expect": args.expect, "name": args.name}, indent=2))
        return 0
    root = Path(__file__).resolve().parents[1]
    exe = Path(command[0]).resolve()
    if sys.platform != "linux" or root != REVIEW or exe != REVIEW / "build/stage5_01_board/asr_llm_tts_smoke":
        parser.error("Only the isolated Linux review executable may be run")
    report_parent = root / "reports/stage5_01_board"
    if report_parent.resolve() != report_parent:
        parser.error("Report directory must not redirect outside the review tree")
    report_parent.mkdir(parents=True, exist_ok=True)
    report = report_parent / args.name
    report.mkdir() # Refuse overwriting a previous run.
    (report / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    events = queue.Queue()
    def reader():
        try:
            for line in iter(child.stdout.readline, b""):
                events.put(line)
        finally:
            events.put(None)
    reading = threading.Thread(target=reader, daemon=True)
    reading.start()
    requested = threading.Event()
    previous = {}
    for value in (signal.SIGINT, signal.SIGTERM):
        previous[value] = signal.signal(value, lambda *_: requested.set())
    start = time.monotonic()
    ready_at = None
    interrupted = False
    timed_out = False
    forced = False
    stop_at = None
    eof = False
    next_sample = start
    try:
        with (report / "terminal.log").open("wb") as log, (report / "resources.jsonl").open("w") as resources:
            while child.poll() is None or not eof:
                try:
                    line = events.get(timeout=0.1)
                    if line is None:
                        eof = True
                    else:
                        log.write(line)
                        log.flush()
                        sys.stdout.buffer.write(line)
                        sys.stdout.buffer.flush()
                        if b"[Listen]" in line and ready_at is None:
                            ready_at = time.monotonic()
                except queue.Empty:
                    pass
                now = time.monotonic()
                if now >= next_sample and child.poll() is None:
                    sample = resource_sample(child.pid)
                    sample["elapsed_s"] = now - start
                    resources.write(json.dumps(sample) + "\n")
                    resources.flush()
                    next_sample = now + 1
                automated = (args.sigint_after_ready is not None and ready_at is not None and
                             now - ready_at >= args.sigint_after_ready)
                if child.poll() is None and stop_at is None and (requested.is_set() or automated or now-start > args.timeout):
                    timed_out = now - start > args.timeout and not requested.is_set() and not automated
                    interrupted = not timed_out
                    try:
                        os.killpg(child.pid, signal.SIGTERM if timed_out else signal.SIGINT)
                    except ProcessLookupError:
                        pass
                    stop_at = now
                if child.poll() is None and stop_at is not None and now-stop_at > 15:
                    forced = True
                    try:
                        os.killpg(child.pid, signal.SIGKILL) # Only this launched test process group.
                    except ProcessLookupError:
                        pass
            exitcode = child.wait()
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)
        if child.poll() is None:
            child.kill()
            child.wait()
    text = (report / "terminal.log").read_text(encoding="utf-8", errors="replace")
    summary = parse_summary(text)
    passed = accepted(summary, exitcode, args.expect, interrupted, timed_out, forced)
    outcome = {"child_exit_code": exitcode, "elapsed_s": time.monotonic()-start,
               "interrupted": interrupted, "timed_out": timed_out, "forced_kill": forced,
               "process_gone": not Path(f"/proc/{child.pid}").exists(),
               "automatic_functional_acceptance": passed, "summary": summary,
               "graceful_sigint_acceptance": "NOT_PASSED: current voice entry has no cooperative handler" if interrupted else "NOT_TESTED",
               "audible_output_confirmed_by_user": None,
               "leak_freedom_proven": False}
    (report / "result.json").write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(outcome, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## 操作 19：`tools/stage5_board_compile_only.sh`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_compile_only.sh`

SHA256：`cdc90f324f68f73bff023811232e0ab462285235a4d3368c2af55c2a4cbcfd66`

### 最终完整源码

```bash
#!/usr/bin/env bash
# Phase 2 only: isolated source compilation. Never run CTest or AI programs.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $(uname -m) == aarch64 || $(uname -m) == arm64 ]] || { echo 'ARM64 required'; exit 2; }
cd -- "$ROOT"
sha256sum --check SOURCE_SHA256SUMS
[[ ! -L "$ROOT/build" && ! -L "$ROOT/reports" ]] || { echo 'Refusing symlinked output'; exit 2; }
[[ ! -e "$ROOT/build/stage5_01_board" ]] || { echo 'Build directory already exists; stop'; exit 2; }
free_bytes=$(df -B1 --output=avail "$ROOT" | tail -n 1 | tr -d ' ')
(( free_bytes >= 2147483648 )) || { echo 'Less than planned 2 GiB disk reserve; stop'; exit 2; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
logdir="$ROOT/reports/stage5_01_board/compile_only_$stamp"
mkdir -p -- "$ROOT/reports/stage5_01_board"
mkdir -- "$logdir"
exec > >(tee "$logdir/session.log") 2>&1
stage5_stable_fingerprint > "$logdir/stable_before.sha256"
finish() {
    code=$?
    trap - EXIT
    set +e
    stage5_stable_fingerprint > "$logdir/stable_after.sha256"
    fingerprint_code=$?
    cmp "$logdir/stable_before.sha256" "$logdir/stable_after.sha256"
    compare_code=$?
    if [[ "$fingerprint_code" != 0 || "$compare_code" != 0 ]]; then code=1; fi
    printf '%s\n' "$code" > "$logdir/exit_code.txt"
    printf 'CTest=NOT_EXECUTED\nAI_PROGRAMS=NOT_STARTED\n' > "$logdir/phase_scope.txt"
    exit "$code"
}
trap finish EXIT
date -Is
uname -a
df -h "$ROOT"
free -h
stage5_check_dependencies
timeout --signal=TERM --kill-after=15s 180s \
    cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" 2>&1 | tee "$logdir/configure.log"
timeout --signal=TERM --kill-after=15s 600s \
    cmake --build "$ROOT/build/stage5_01_board" --parallel 3 2>&1 | tee "$logdir/build.log"
timeout 15s ldd "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" | tee "$logdir/ldd.log"
if grep -q 'not found' "$logdir/ldd.log"; then exit 1; fi
df -h "$ROOT"
printf 'PHASE2_COMPILE_ONLY_COMPLETE; CTest and hardware tests await phase 3 authorization.\n'
```

## 操作 20：`tools/stage5_board_paths.sh`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_paths.sh`

SHA256：`f12b18a3b7fe057d3a724e99a696581fc5767e0343d547ad9c1c667042f07f7b`

### 最终完整源码

```bash
#!/usr/bin/env bash
# Source this file. Historical paths from 4.md, verified on board before use.
STAGE5_BASE=/home/cat/projects/RK3576
STAGE5_ORIGINAL="$STAGE5_BASE/rk3576_multimodal"
STAGE5_REVIEW="$STAGE5_BASE/rk3576_multimodal_stage5_review"
STAGE5_ASR="$STAGE5_BASE/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
STAGE5_VAD="$STAGE5_BASE/asr_runtime/vad/silero_vad.onnx"
STAGE5_QWEN="$STAGE5_BASE/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm"
STAGE5_KOKORO="$STAGE5_BASE/tts_runtime/models/kokoro-multi-lang-v1_1"
STAGE5_VLM="$STAGE5_ORIGINAL/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm"
STAGE5_VISION="$STAGE5_ORIGINAL/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn"
STAGE5_SHERPA="$STAGE5_BASE/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
STAGE5_RKLLM="$STAGE5_BASE/rkllm_sdk"
STAGE5_RKNN_INCLUDE="$STAGE5_BASE/rknn_test/include"
STAGE5_RKNN_LIBRARY=/usr/lib/librknnrt.so
# Prefer the stable build's explicit SDK cache paths, never eval its contents.
stage5_cache_value() {
    local key="$1" cache="$STAGE5_ORIGINAL/build/stage5_full/CMakeCache.txt"
    if [[ -r "$cache" ]]; then
        sed -n "s/^${key}:[^=]*=//p" "$cache" | head -n 1
    fi
}
stage5_value=$(stage5_cache_value SHERPA_ONNX_ROOT)
[[ -z "$stage5_value" ]] || STAGE5_SHERPA="$stage5_value"
stage5_value=$(stage5_cache_value RKLLM_SDK_ROOT)
[[ -z "$stage5_value" ]] || STAGE5_RKLLM="$stage5_value"
stage5_value=$(stage5_cache_value RKNN_INCLUDE_DIR)
[[ -z "$stage5_value" ]] || STAGE5_RKNN_INCLUDE="$stage5_value"
stage5_value=$(stage5_cache_value RKNN_RUNTIME_LIBRARY)
[[ -z "$stage5_value" ]] || STAGE5_RKNN_LIBRARY="$stage5_value"
unset stage5_value
STAGE5_RKLLM_LIB="$STAGE5_RKLLM/rkllm-runtime/Linux/librkllm_api/aarch64"
export LD_LIBRARY_PATH="$STAGE5_SHERPA/lib:$STAGE5_RKLLM_LIB:$(dirname -- "$STAGE5_RKNN_LIBRARY")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

stage5_check_dependencies() {
    local path failed=0
    for path in "$STAGE5_ASR/model.int8.onnx" "$STAGE5_ASR/tokens.txt" \
        "$STAGE5_VAD" "$STAGE5_QWEN" "$STAGE5_KOKORO/model.onnx" \
        "$STAGE5_KOKORO/tokens.txt" "$STAGE5_KOKORO/voices.bin" \
        "$STAGE5_KOKORO/lexicon-us-en.txt" "$STAGE5_KOKORO/lexicon-zh.txt" \
        "$STAGE5_VLM" "$STAGE5_VISION" \
        "$STAGE5_SHERPA/include/sherpa-onnx/c-api/c-api.h" \
        "$STAGE5_SHERPA/lib/libsherpa-onnx-c-api.so" \
        "$STAGE5_RKLLM/rkllm-runtime/Linux/librkllm_api/include/rkllm.h" \
        "$STAGE5_RKLLM_LIB/librkllmrt.so" \
        "$STAGE5_RKNN_INCLUDE/rknn_api.h" "$STAGE5_RKNN_LIBRARY"; do
        if [[ -r "$path" && -f "$path" ]]; then
            stat -Lc 'READABLE %s bytes %n' -- "$path"
        else
            printf 'MISSING_OR_UNREADABLE %s\n' "$path"
            failed=1
        fi
    done
    [[ -d "$STAGE5_KOKORO/espeak-ng-data" ]] || failed=1
    return "$failed"
}

stage5_stable_fingerprint() {
    # Reads only: source files and the preserved known-good executable.
    (
        cd -- "$STAGE5_ORIGINAL"
        { printf '%s\0' CMakeLists.txt build/stage5_full/asr_llm_tts_smoke;
          find src include tests -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.cmake' \) -print0;
        } | sort -z | xargs -0 sha256sum --
    )
}
```

## 操作 21：`tools/stage5_board_phase3_run.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_phase3_run.py`

SHA256：`7e65dd346a97dfd79d91a373e6ee9e0913fededd791d0dea66f19afea2320622`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Bounded, PID-checked hardware runs, only inside the authorized review tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import resource
import signal
import subprocess
import sys
import threading
import time

ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_board_readonly_inventory import fingerprint


def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def query(command):
    r=subprocess.run(command,capture_output=True,timeout=15)
    return {'command':command,'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}


def discover_audio():
    cards=Path('/proc/asound/cards').read_text()
    matches=re.findall(r'^\s*(\d+)\s+\[([^\]]+)\]\s*:\s*USB-Audio - HyperX Cloud III\s*$',cards,re.M)
    assert len(matches)==1,'expected exactly one HyperX Cloud III'
    card,card_id=matches[0]; card_id=card_id.strip()
    capture={re.search(r'pcm(\d+)c$',p.name).group(1) for p in Path('/proc/asound',f'card{card}').glob('pcm*c')}
    playback={re.search(r'pcm(\d+)p$',p.name).group(1) for p in Path('/proc/asound',f'card{card}').glob('pcm*p')}
    common=capture & playback
    assert len(common)==1, 'expected unique duplex PCM device'
    device=common.pop()
    return {'cards':cards,'capture_listing':query(['arecord','-l']),'playback_listing':query(['aplay','-l']),
            'card_number':int(card),'card_id':card_id,'pcm_device':int(device),
            'alsa_device':f'plughw:CARD={card_id},DEV={device}',
            'nodes':[f'/dev/snd/pcmC{card}D{device}c',f'/dev/snd/pcmC{card}D{device}p']}


def devices(audio):
    nodes=['/dev/video11',*audio['nodes']]
    for p in Path('/sys/class/drm').glob('renderD*'):
        driver=p/'device/driver'
        if driver.exists() and 'rknpu' in str(driver.resolve()).lower():
            nodes.append('/dev/dri/'+p.name)
    assert len(nodes)==4, 'one RKNPU target required'
    r=query(['sudo','-n','--','/usr/bin/fuser','-v',*nodes]) # query only, never -k
    return {'nodes':nodes,'query':r,'clear':r['exit_code']==1 and not r['stdout'].strip() and not r['stderr'].strip(),
            'alsa_status':{str(p):p.read_text() for p in Path('/proc/asound',f"card{audio['card_number']}").glob('pcm*/sub*/status')}}


def sample(pid):
    result={'time':time.time(),'pid':pid}
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            k=line.split(':',1)[0]
            if k in {'State','Threads','VmRSS','VmHWM','VmSize'}:
                result[k]=line.split(':',1)[1].strip()
        result['fds']={p.name:os.readlink(p) for p in Path(f'/proc/{pid}/fd').iterdir()}
        result['tasks']=sorted(p.name for p in Path(f'/proc/{pid}/task').iterdir())
    except OSError as e:
        result['sample_error']=str(e)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--signal',choices=('SIGINT','SIGTERM'))
    parser.add_argument('--trigger',choices=('init','ready','llm','vision','tts','both_done'),default='ready')
    parser.add_argument('--delay',type=float,default=2)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--timeout',type=int,default=240)
    parser.add_argument('--grace',type=int,default=40)
    args=parser.parse_args()
    assert Path(__file__).resolve().parents[1]==ROOT and not ROOT.is_symlink()
    assert re.fullmatch(r'[A-Za-z0-9_-]+',args.name)
    assert 1<=args.seconds<=120 and 1<=args.timeout<=400 and 1<=args.grace<=90 and args.delay>=0
    report=ROOT/'reports/stage5_01_board'/args.name
    report.mkdir()
    before=fingerprint(); save(report/'stable_before.json',before)
    audio=discover_audio(); save(report/'audio_detection.json',audio)
    pre=devices(audio);save(report/'devices_before.json',pre)
    assert pre['clear'],'target device occupied'
    assert os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize>=500*1024**2
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)])})
    envout=subprocess.check_output(['bash','-c','source "$1/tools/stage5_board_paths.sh"; env -0','phase3',str(ROOT)],timeout=15)
    env=dict(part.decode().split('=',1) for part in envout.split(b'\0') if b'=' in part)
    base='/home/cat/projects/RK3576'
    exe=ROOT/'build/stage5_01_board/asr_llm_tts_smoke'
    command=['stdbuf','-oL','-eL',str(exe),audio['alsa_device'],
             base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',
             base+'/asr_runtime/vad/silero_vad.onnx',base+'/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm',
             base+'/tts_runtime/models/kokoro-multi-lang-v1_1',audio['alsa_device'],str(args.seconds),'2','17',
             base+'/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm',
             base+'/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn','/dev/video11']
    save(report/'command.json',command)
    save(report/'test_parameters.json',vars(args))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    events=queue.Queue()
    def reader():
        for line in iter(child.stdout.readline,b''):
            events.put(line)
        events.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    start=time.monotonic(); trigger_at=None; sent_at=None; eof=False; forced=False; timed_out=False; signaled=None
    pid_token=None; text_done=False; vision_done=False; lines=[]; next_sample=start
    save(report/'pid.json',{'pid':child.pid,'exe':str(exe),'started':time.time()})
    def checked_signal(value):
        nonlocal pid_token
        assert child.poll() is None
        assert Path(f'/proc/{child.pid}/exe').resolve()==exe.resolve(),'PID/executable mismatch; refuse signal'
        current=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
        if pid_token is None: pid_token=current
        assert current==pid_token,'PID start token mismatch'
        os.kill(child.pid,value) # exactly the child PID, no shared process group
    with (report/'terminal.log').open('wb') as terminal,(report/'resources.jsonl').open('w') as samples,(report/'events.jsonl').open('w') as eventlog:
        while child.poll() is None or not eof:
            try:
                line=events.get(timeout=0.1)
                if line is None: eof=True
                else:
                    terminal.write(line);terminal.flush();sys.stdout.buffer.write(line);sys.stdout.buffer.flush()
                    s=line.decode(errors='replace');lines.append(s)
                    text_done |= bool(re.search(r'(?<!VISION )\[TTS done .*success=true',s))
                    vision_done |= '[VISION TTS done ' in s and 'success=true' in s
                    found=(args.trigger=='init' and '[Init] Loading RKLLM' in s or args.trigger=='ready' and '[Listen]' in s or args.trigger=='llm' and '[ASR->LLM #' in s or args.trigger=='vision' and '[ASR->VISION #' in s or args.trigger=='tts' and '[ALSA write]' in s or args.trigger=='both_done' and text_done and vision_done)
                    if trigger_at is None and found:
                        trigger_at=time.monotonic()
                        eventlog.write(json.dumps({'event':'trigger','elapsed':trigger_at-start,'trigger':args.trigger})+'\n');eventlog.flush()
            except queue.Empty: pass
            now=time.monotonic()
            if child.poll() is None and now>=next_sample:
                samples.write(json.dumps(sample(child.pid))+'\n');samples.flush();next_sample=now+1
            if child.poll() is None and sent_at is None:
                requested=args.signal and trigger_at is not None and now-trigger_at>=args.delay
                timed_out=now-start>args.timeout
                if requested or timed_out:
                    signaled='SIGTERM' if timed_out else args.signal
                    checked_signal(getattr(signal,signaled));sent_at=now
                    eventlog.write(json.dumps({'event':'signal','signal':signaled,'elapsed':now-start,'pid':child.pid,'pid_start_token':pid_token,'timeout':timed_out})+'\n');eventlog.flush()
            if child.poll() is None and sent_at is not None and now-sent_at>args.grace:
                checked_signal(signal.SIGKILL);forced=True
                eventlog.write(json.dumps({'event':'FORCED_KILL_EXIT_FAILURE','pid':child.pid,'elapsed':now-start})+'\n');eventlog.flush()
                child.wait(timeout=10)
            if child.poll() is not None and not eof and now-start>args.timeout+args.grace+10:
                raise RuntimeError('child ended but output did not close')
    code=child.wait(); ended=time.monotonic(); thread.join(timeout=5)
    terminal=''.join(lines)
    post=devices(audio);save(report/'devices_after.json',post)
    after=fingerprint();save(report/'stable_after.json',after)
    summary={'pid':child.pid,'returncode':code,'sent_signal':signaled,'trigger_observed':trigger_at is not None,'forced_kill':forced,'timeout':timed_out,
             'duration_seconds':ended-start,'signal_to_exit_seconds':None if sent_at is None else ended-sent_at,
             'timing_scope':'child exit/output EOF, excludes subsequent device/fingerprint queries',
             'process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':before==after,
             'shutdown_complete_marker':'[Shutdown] complete' in terminal,'program_PASS':bool(re.search(r'^PASS\s*$',terminal,re.M)),
             'text_tts_completed':text_done,'vision_tts_completed':vision_done,'user_audible_confirmation':None}
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'dmesg':query(['dmesg','--ctime'])})
    save(report/'result.json',summary)
    print('PHASE3_RUN_RESULT',json.dumps(summary),flush=True)
    print('REMOTE_REPORT',report,flush=True)
    return 0 # transport succeeded; child return code remains explicitly recorded above


if __name__=='__main__':
    raise SystemExit(main())
```

## 操作 22：`tools/stage5_board_preflight.sh`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_preflight.sh`

SHA256：`d57e0c2cf12a1aa01ed05a3e40c8da50a77690fedf484fb41298fc7b08c23b82`

### 最终完整源码

```bash
#!/usr/bin/env bash
# Read-only inspection. No mkdir, copying, compilation, device open, sudo or deletion.
set -euo pipefail
STAGE5_BASE=/home/cat/projects/RK3576
STAGE5_ORIGINAL="$STAGE5_BASE/rk3576_multimodal"
printf '=== identity ===\n'
date -Is
uname -a
id
printf '=== tools ===\n'
for tool in cmake ctest c++ python3 tar sha256sum arecord aplay; do
    command -v "$tool" || true
done
printf '=== resources ===\n'
free -h
df -h "$STAGE5_BASE"
ps -eo pid,ppid,comm,rss,args --sort=-rss | head -n 16 || true
printf '=== devices (listing only) ===\n'
if command -v arecord >/dev/null; then arecord -l; fi
if command -v aplay >/dev/null; then aplay -l; fi
ls -l /dev/video11 || true
printf '=== stable executable and source fingerprints ===\n'
cd -- "$STAGE5_ORIGINAL"
sha256sum CMakeLists.txt src/audio/asr_llm_tts_smoke.cpp \
    src/ai/rkllm_backend.cpp src/ai/rk3576_vlm_backend.cpp \
    build/stage5_full/asr_llm_tts_smoke
printf '=== stable SDK cache (if present) ===\n'
if [[ -r build/stage5_full/CMakeCache.txt ]]; then
    sed -n -e '/^SHERPA_ONNX_ROOT:/p' -e '/^RKLLM_SDK_ROOT:/p' \
        -e '/^RKNN_INCLUDE_DIR:/p' -e '/^RKNN_RUNTIME_LIBRARY:/p' \
        -e '/^CMAKE_CXX_COMPILER:/p' build/stage5_full/CMakeCache.txt
fi
printf '=== historical model locations (existence, not inference) ===\n'
stat -L -- "$STAGE5_BASE/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx" \
    "$STAGE5_BASE/asr_runtime/vad/silero_vad.onnx" \
    "$STAGE5_BASE/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm" \
    "$STAGE5_BASE/tts_runtime/models/kokoro-multi-lang-v1_1/model.onnx" \
    models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm \
    models/vlm/smolvlm_vision_scatterfix_rk3576.rknn
printf '=== review destination ===\n'
if [[ -e "$STAGE5_BASE/rk3576_multimodal_stage5_review" ]]; then
    printf 'EXISTS: do not overwrite; choose a new directory and revise scripts first.\n'
else
    printf 'ABSENT: available after explicit deployment approval.\n'
fi
```

## 操作 23：`tools/stage5_board_readonly_inventory.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_readonly_inventory.py`

SHA256：`f2b44c2300bdd0c87af87e16f7ca086e42a10b0ec194fae1d6ab1edeff8c09ec`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Read-only inventory sent through SSH stdin; never install or build anything."""
import glob
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

BASE = Path("/home/cat/projects/RK3576")
ORIGINAL = BASE / "rk3576_multimodal"
REVIEW = BASE / "rk3576_multimodal_stage5_review"
STABLE_BUILD = ORIGINAL / "build/stage5_full"
STABLE_EXE = STABLE_BUILD / "asr_llm_tts_smoke"
DISK_RESERVE_BYTES = 2 * 1024 ** 3  # Planning allowance, not measured build size.


def run(command, env=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout=20, env=env)
        return {"command": command, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "exit_code": None, "error": str(error)}


def fingerprint():
    selected = {ORIGINAL / "CMakeLists.txt", ORIGINAL / "README_STAGE5.txt"}
    for directory in ("src", "include", "tests", "config", "build/stage5_full"):
        start = ORIGINAL / directory
        if not start.is_dir():
            continue
        for current, dirs, files in os.walk(start, followlinks=False):
            for name in dirs + files:
                path = Path(current) / name
                if path.is_symlink():
                    selected.add(path)
            selected.update(Path(current) / name for name in files)
    result = {}
    for path in sorted(selected):
        relative = str(path.relative_to(ORIGINAL))
        try:
            if path.is_symlink():
                result[relative] = {"symlink": os.readlink(path)}
                continue
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.stat()
            result[relative] = {"sha256": digest.hexdigest(), "bytes": after.st_size,
                                "mtime_ns": after.st_mtime_ns,
                                "changed_while_reading": (before.st_size, before.st_mtime_ns) !=
                                (after.st_size, after.st_mtime_ns)}
        except OSError as error:
            result[relative] = {"error": str(error)}
    return result


def devices_and_owners(target_only=False):
    nodes = sorted(set(glob.glob("/dev/video*") + glob.glob("/dev/snd/pcm*") +
                       glob.glob("/dev/rknpu*") + glob.glob("/dev/dri/renderD*")))
    node_info = []
    by_device = {}
    for name in nodes:
        path = Path(name)
        try:
            value = path.stat()
            if not stat.S_ISCHR(value.st_mode):
                continue
            driver = None
            if name.startswith("/dev/dri/"):
                driver_path = Path("/sys/class/drm") / path.name / "device/driver"
                if driver_path.exists():
                    driver = str(driver_path.resolve())
            kind = ("alsa_pcm" if name.startswith("/dev/snd/pcm") else
                    "camera_target" if name == "/dev/video11" else
                    "camera_other" if name.startswith("/dev/video") else
                    "npu" if "rknpu" in (name + (driver or "")).lower() else "render_unclassified")
            row = {"path": name, "kind": kind, "driver": driver,
                   "major": os.major(value.st_rdev), "minor": os.minor(value.st_rdev)}
            node_info.append(row)
            by_device.setdefault(value.st_rdev, []).append(row)
        except OSError:
            pass
    if target_only:
        node_info = [row for row in node_info if row["path"] in {
            "/dev/video11", "/dev/snd/pcmC1D0c", "/dev/snd/pcmC1D0p"} or row["kind"] == "npu"]
        nodes = [row["path"] for row in node_info]
        selected_device_numbers = {os.makedev(row["major"], row["minor"]) for row in node_info}
        by_device = {key: value for key, value in by_device.items() if key in selected_device_numbers}
    owners = []
    denied = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            descriptors = list((process / "fd").iterdir())
        except PermissionError:
            denied.append(int(process.name))
            continue
        except FileNotFoundError:
            continue
        for descriptor in descriptors:
            try:
                value = descriptor.stat()
                if stat.S_ISCHR(value.st_mode) and value.st_rdev in by_device:
                    owners.append({"pid": int(process.name), "fd": descriptor.name,
                                   "comm": (process / "comm").read_text().strip(),
                                   "devices": by_device[value.st_rdev]})
            except PermissionError:
                denied.append(int(process.name))
            except FileNotFoundError:
                pass
    # Ordinary users may not see other users' FDs. Only a noninteractive,
    # read-only fuser listing is attempted with sudo; no kill option is used.
    privileged = None
    if denied and nodes and Path("/usr/bin/fuser").is_file() and shutil.which("sudo"):
        # This board's fuser rejected a standalone -- after -v. Paths are all
        # fixed absolute /dev paths, so there is no option-like operand here.
        privileged = run(["sudo", "-n", "--", "/usr/bin/fuser", "-v"] +
                         [row["path"] for row in node_info])
    privileged_clear = bool(privileged and privileged.get("exit_code") == 1 and
                            not privileged.get("stdout", "").strip() and
                            not privileged.get("stderr", "").strip())
    normal_clear = not denied and not owners
    pcm = {}
    for filename in glob.glob("/proc/asound/card*/pcm*/sub*/status"):
        try:
            pcm[filename] = Path(filename).read_text()
        except OSError as error:
            pcm[filename] = "UNREADABLE: " + str(error)
    return {"nodes": node_info, "visible_owners": owners,
            "permission_denied_pids": sorted(set(denied)),
            "sudo_readonly_fuser": privileged, "alsa_status": pcm,
            "all_listed_nodes_clear_confirmed": normal_clear or privileged_clear,
            "npu_node_identified": any(row["kind"] == "npu" for row in node_info),
            "camera_sysfs_names": {str(path): path.read_text().strip() for path in
                                    Path("/sys/class/video4linux").glob("video*/name")},
            "camera_service_process": run(["ps", "-C", "rkaiq_3A_server", "-o", "pid,ppid,user,comm,args"])}


def main():
    # First check, including dangling symlinks. Stop before any further query.
    if os.path.lexists(REVIEW):
        print("DESTINATION_EXISTS_STOP")
        return 20
    print("DESTINATION_ABSENT\nSSH_READONLY_CONNECTED", flush=True)
    result = {"started_unix_time": time.time(), "read_only": True,
              "review_directory_absent_before": True}
    before = fingerprint()
    result["identity"] = {name: run(command) for name, command in {
        "uname": ["uname", "-a"], "user": ["id"], "time": ["date", "-Is"],
        "memory": ["free", "-h"], "disk": ["df", "-h", str(BASE)],
        "processes": ["ps", "-eo", "pid,ppid,user,comm,rss,args", "--sort=-rss"],
        "capture_devices": ["arecord", "-l"], "playback_devices": ["aplay", "-l"],
        "cmake": ["cmake", "--version"], "compiler": ["c++", "--version"]}.items()}
    disk = shutil.disk_usage(BASE)
    fs = os.statvfs(BASE)
    result["disk_budget"] = {"free_bytes": disk.free, "free_inodes": fs.f_favail,
                             "required_reserve_bytes": DISK_RESERVE_BYTES,
                             "reserve_is_planning_allowance_not_measurement": True,
                             "enough": disk.free >= DISK_RESERVE_BYTES and fs.f_favail >= 2000}
    cache = {}
    cache_path = STABLE_BUILD / "CMakeCache.txt"
    if cache_path.is_file():
        for line in cache_path.read_text(errors="replace").splitlines():
            if "=" in line and ":" in line.split("=", 1)[0]:
                key, value = line.split("=", 1)
                cache[key.split(":", 1)[0]] = value
    sdk = {
        "SHERPA_ONNX_ROOT": cache.get("SHERPA_ONNX_ROOT") or str(BASE / "asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"),
        "RKLLM_SDK_ROOT": cache.get("RKLLM_SDK_ROOT") or str(BASE / "rkllm_sdk"),
        "RKNN_INCLUDE_DIR": cache.get("RKNN_INCLUDE_DIR") or str(BASE / "rknn_test/include"),
        "RKNN_RUNTIME_LIBRARY": cache.get("RKNN_RUNTIME_LIBRARY") or "/usr/lib/librknnrt.so"}
    result["sdk_paths"] = {key: {"path": value, "source": "stable_CMakeCache" if cache.get(key) else "historical_default"}
                           for key, value in sdk.items()}
    asr = BASE / "asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
    kokoro = BASE / "tts_runtime/models/kokoro-multi-lang-v1_1"
    rklib = Path(sdk["RKLLM_SDK_ROOT"]) / "rkllm-runtime/Linux/librkllm_api"
    paths = {
        "asr_model": asr / "model.int8.onnx", "asr_tokens": asr / "tokens.txt",
        "vad": BASE / "asr_runtime/vad/silero_vad.onnx",
        "qwen": BASE / "rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm",
        "vlm": ORIGINAL / "models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm",
        "vision": ORIGINAL / "models/vlm/smolvlm_vision_scatterfix_rk3576.rknn",
        "sherpa_header": Path(sdk["SHERPA_ONNX_ROOT"]) / "include/sherpa-onnx/c-api/c-api.h",
        "sherpa_library": Path(sdk["SHERPA_ONNX_ROOT"]) / "lib/libsherpa-onnx-c-api.so",
        "rkllm_header": rklib / "include/rkllm.h", "rkllm_library": rklib / "aarch64/librkllmrt.so",
        "rknn_header": Path(sdk["RKNN_INCLUDE_DIR"]) / "rknn_api.h",
        "rknn_library": Path(sdk["RKNN_RUNTIME_LIBRARY"]),
        "alsa_header": Path("/usr/include/alsa/asoundlib.h"),
        "stable_executable": STABLE_EXE}
    for name in ("model.onnx", "tokens.txt", "voices.bin", "lexicon-us-en.txt", "lexicon-zh.txt", "espeak-ng-data"):
        paths["kokoro_" + name] = kokoro / name
    result["dependencies"] = {}
    for name, path in paths.items():
        row = {"path": str(path), "exists": path.exists(), "readable": os.access(path, os.R_OK)}
        if path.exists():
            row.update({"resolved_path": str(path.resolve()), "bytes": path.stat().st_size,
                        "is_directory": path.is_dir()})
        result["dependencies"][name] = row
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = ":".join((str(Path(sdk["SHERPA_ONNX_ROOT"]) / "lib"),
                                                 str(rklib / "aarch64"),
                                                 str(Path(sdk["RKNN_RUNTIME_LIBRARY"]).parent)))
    result["stable_binary_file_type"] = run(["file", "-L", str(STABLE_EXE)])
    result["dynamic_link_inspection"] = run(["ldd", str(STABLE_EXE)], environment)
    result["resource_occupancy"] = devices_and_owners(target_only=True)
    result["resource_occupancy_scope"] = "/dev/video11, HyperX card1 PCM capture/playback, identified RKNPU node(s); ISP 3A service retained"
    after = fingerprint()
    result["original_fingerprints_before"] = before
    result["original_fingerprints_after"] = after
    result["original_scope"] = "CMakeLists/README/src/include/tests/config and all regular files/symlinks in build/stage5_full; model weights not hashed/copied"
    result["original_unchanged"] = before == after and not any(
        row.get("error") or row.get("changed_while_reading") for row in before.values())
    result["review_directory_absent_after"] = not os.path.lexists(REVIEW)
    result["checks"] = {
        "review_directory_absent": result["review_directory_absent_after"],
        "disk_budget_sufficient": result["disk_budget"]["enough"],
        "original_and_stable_build_present": ORIGINAL.is_dir() and STABLE_BUILD.is_dir() and STABLE_EXE.is_file(),
        "original_fingerprints_unchanged": result["original_unchanged"],
        "all_required_paths_readable": all(row["exists"] and row["readable"] for row in result["dependencies"].values()),
        "dynamic_libraries_resolved": result["dynamic_link_inspection"].get("exit_code") == 0 and
                                      "not found" not in result["dynamic_link_inspection"].get("stdout", ""),
        "device_owners_clear": result["resource_occupancy"]["all_listed_nodes_clear_confirmed"],
        "npu_device_identified": result["resource_occupancy"]["npu_node_identified"]}
    result["stage1_all_checks_passed"] = all(result["checks"].values())
    print("STAGE5_READONLY_JSON_BEGIN")
    print(json.dumps(result, indent=2, ensure_ascii=True))
    print("STAGE5_READONLY_JSON_END")
    if not result["review_directory_absent_after"]:
        print("DESTINATION_EXISTS_STOP")
        return 20
    return 0 if result["stage1_all_checks_passed"] else 22


if __name__ == "__main__":
    raise SystemExit(main())
```

## 操作 24：`tools/stage5_board_voice.sh`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_board_voice.sh`

SHA256：`9a25f02bab964e4f7fde766aaf74d9f48fb0f8f6348b86ce0584e9303a71325a`

### 最终完整源码

```bash
#!/usr/bin/env bash
# Usage: bash tools/stage5_board_voice.sh text|vision|both|sigint RUN_NAME
# Requires explicit prior user authorization. Run names must be new.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $# == 2 ]] || { echo 'Expected mode and unique run name'; exit 2; }
mode="$1"
name="$2"
case "$mode" in text|vision|both|sigint) ;; *) echo 'Invalid mode'; exit 2;; esac
[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Invalid run name'; exit 2; }
[[ ! -e "$ROOT/reports/stage5_01_board/$name" ]] || { echo 'Run exists'; exit 2; }
stage5_check_dependencies
cd -- "$ROOT"
fingerprints=$(stage5_stable_fingerprint)
postcheck() {
    code=$?
    trap - EXIT
    set +e
    after=$(stage5_stable_fingerprint)
    if [[ "$fingerprints" != "$after" ]]; then
        echo 'ERROR: stable source/binary fingerprint changed'
        code=1
    fi
    if [[ -d "$ROOT/reports/stage5_01_board/$name" ]]; then
        printf '%s\n' "$fingerprints" > "$ROOT/reports/stage5_01_board/$name/stable_before.sha256"
        printf '%s\n' "$after" > "$ROOT/reports/stage5_01_board/$name/stable_after.sha256"
        printf '%s\n' "$code" > "$ROOT/reports/stage5_01_board/$name/runner_exit_code.txt"
        dmesg --ctime > "$ROOT/reports/stage5_01_board/$name/dmesg_after.log" 2>&1
    fi
    exit "$code"
}
trap postcheck EXIT
expect="$mode"
extras=()
seconds=15
if [[ "$mode" == sigint ]]; then
    expect=both
    seconds=120
    extras=(--sigint-after-ready 2)
fi
args=(plughw:1,0 "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" \
      "$STAGE5_KOKORO" plughw:1,0 "$seconds" 2 17)
if [[ "$mode" != text ]]; then
    args+=("$STAGE5_VLM" "$STAGE5_VISION" /dev/video11)
fi
python3 "$ROOT/tools/stage5_board_capture.py" --execute --name "$name" \
    --expect "$expect" --timeout 300 "${extras[@]}" -- \
    "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" "${args[@]}"
```

## 操作 25：`tools/stage5_phase2_deploy.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_phase2_deploy.py`

SHA256：`ec94120f75817664e2f790da669ae3b98b4886179ecc9b5fb19bd158f01d2d34`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Authorized phase 2 only: immutable bundle deployment and monitored ARM64 build.

No CTest, AI executable, device test, installation, or deletion is performed.
Run --prepare to inspect exact payloads, then --execute with approved networking.
"""
import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/cat/projects/RK3576/rk3576_multimodal_stage5_review'
ARCHIVE = 'stage5_01_review_preflight_v2.tgz'
EXPECTED = 'a653dd57e1ed5138170dd6d6ff7eb77a1518aa0e97c909402b662cab45c13c6e'
SSH = 'C:/Windows/System32/OpenSSH/ssh.exe'
SCP = 'C:/Windows/System32/OpenSSH/scp.exe'
OPTIONS = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=5',
           '-o', 'ServerAliveCountMax=2', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'UpdateHostKeys=no', '-o', 'ClearAllForwardings=yes',
           '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
           '-o', 'PermitLocalCommand=no', '-o', 'RemoteCommand=none']


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fingerprint_code():
    source = (ROOT / 'tools/stage5_board_readonly_inventory.py').read_text(encoding='utf-8')
    return source.split('\ndef devices_and_owners(', 1)[0]


def payloads():
    baseline = json.loads((ROOT / 'reports/stage5_01_board/stable_original_baseline.json').read_text(encoding='utf-8'))['fingerprints']
    common = fingerprint_code() + '\nEXPECTED_BASELINE = ' + repr(baseline) + '\n'
    guard = common + '''
if os.path.lexists(REVIEW):
    print('DESTINATION_EXISTS_STOP', flush=True)
    raise SystemExit(20)
assert os.getuid() == 1000 and os.geteuid() != 0, 'ordinary cat required'
assert os.uname().machine == 'aarch64', 'ARM64 required'
assert fingerprint() == EXPECTED_BASELINE, 'original differs from approved baseline'
assert shutil.disk_usage(BASE).free >= 2147483648, 'less than 2 GiB planning reserve'
os.umask(0o077)
REVIEW.mkdir()  # exclusive: no parents=True or exist_ok=True
print('CREATED_EXCLUSIVE_ISOLATED_DIRECTORY', REVIEW, flush=True)
print('ORIGINAL_BASELINE_IDENTICAL', len(EXPECTED_BASELINE), flush=True)
'''
    extract = f'''
import hashlib, json, os, subprocess, tarfile
from pathlib import Path, PurePosixPath
root = Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink() and str(root.resolve()) == str(root)
archive = root / {ARCHIVE!r}
assert archive.is_file() and not archive.is_symlink()
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == {EXPECTED!r}, 'archive hash mismatch'
subprocess.run(['sha256sum', '-c', {ARCHIVE!r} + '.sha256'], cwd=root, check=True, timeout=10)
with tarfile.open(archive, 'r:gz') as package:
    members = package.getmembers()
    names = [m.name for m in members]
    assert len(names) == len(set(names)), 'duplicate members'
    assert len(names) == 87, 'unexpected member count'
    assert sum(m.size for m in members) < 5*1024*1024, 'unexpected expansion size'
    for m in members:
        p = PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts
        assert p.parts[0] in {{'CMakeLists.txt','README_STAGE5.txt','src','include','tests','tools','docs','SOURCE_SHA256SUMS'}}
        assert not os.path.lexists(root / m.name), 'refusing existing extraction destination'
    manifest = package.extractfile('SOURCE_SHA256SUMS').read().decode('utf-8')
    hashes = dict((name, sha) for sha, name in (line.split('  ', 1) for line in manifest.splitlines()))
    assert set(hashes) == set(names) - {{'SOURCE_SHA256SUMS'}}
    for name, sha in hashes.items():
        assert hashlib.sha256(package.extractfile(name).read()).hexdigest() == sha
subprocess.run(['tar','--keep-old-files','-xzf',archive.name], cwd=root, check=True, timeout=30)
subprocess.run(['sha256sum','-c','SOURCE_SHA256SUMS'], cwd=root, check=True, timeout=15)
report = root / 'reports/stage5_01_board'
report.mkdir(parents=True)
result = {{'archive':archive.name,'sha256':digest,'regular_members':len(names),'safe_paths':True,'all_member_hashes_match':True,'extraction_exit_code':0}}
(report / 'phase2_archive_validation.json').write_text(json.dumps(result,indent=2)+'\\n')
print('ARCHIVE_VALIDATED_AND_EXTRACTED', json.dumps(result), flush=True)
'''
    compile_payload = common + f'''
import signal
root = Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink()
assert fingerprint() == EXPECTED_BASELINE, 'original changed before compilation'
logdir = root / 'reports/stage5_01_board' / ('supervisor_' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
logdir.mkdir()
(logdir / 'stable_before.json').write_text(json.dumps(fingerprint(),indent=2)+'\\n')
command = ['timeout','--signal=TERM','--kill-after=15s','840s','bash',str(root/'tools/stage5_board_compile_only.sh')]
(logdir/'command.json').write_text(json.dumps(command,indent=2)+'\\n')
process = subprocess.Popen(command, start_new_session=True)
started = time.monotonic()
reason = None
minimum = shutil.disk_usage(root).free
with (logdir/'disk_samples.jsonl').open('x') as samples:
    while process.poll() is None:
        available = shutil.disk_usage(root).free
        minimum = min(minimum, available)
        samples.write(json.dumps({{'unix_time':time.time(),'free_bytes':available}})+'\\n')
        samples.flush()
        if available < 500*1024*1024:
            reason = 'DISK_BELOW_500_MiB'
        elif time.monotonic()-started > 840:
            reason = 'SUPERVISOR_TIMEOUT_840_SECONDS'
        if reason:
            print('STOP_BUILD',reason,flush=True)
            # Only this build's new process group, never unrelated processes.
            try:
                os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait(timeout=10)
            break
        time.sleep(1)
child_code = process.wait()
after = fingerprint()
unchanged = after == EXPECTED_BASELINE
(logdir/'stable_after.json').write_text(json.dumps(after,indent=2)+'\\n')
result = {{'build_process_exit_code':child_code,'stop_reason':reason,'original_321_entries_unchanged':unchanged,'minimum_disk_free_bytes':minimum,'final_disk_free_bytes':shutil.disk_usage(root).free,'duration_seconds':time.monotonic()-started,'ctest_executed':False,'ai_programs_started':False}}
code = 90 if reason == 'DISK_BELOW_500_MiB' else 124 if reason else child_code
if not unchanged:
    code = 91
result['supervisor_exit_code'] = code
(logdir/'result.json').write_text(json.dumps(result,indent=2)+'\\n')
print('PHASE2_SUPERVISOR_RESULT',json.dumps(result),flush=True)
raise SystemExit(code if 0 <= code <= 255 else 1)
'''
    collect = f'''
import io, json, os, subprocess, sys, tarfile
from pathlib import Path
root=Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink()
reports=root/'reports/stage5_01_board'
build=root/'build/stage5_01_board'
if build.is_dir():
    output=subprocess.run(['cmake','--build',str(build),'--target','help'],capture_output=True,timeout=20)
    (reports/'phase2_targets_help.log').write_bytes(output.stdout+output.stderr)
    files=sorted(p for p in build.iterdir() if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b'\\x7fELF')
    rows=[]
    for p in files:
        r=subprocess.run(['file',str(p)],capture_output=True,timeout=5)
        rows.append({{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'file':r.stdout.decode(errors='replace'),'exit_code':r.returncode}})
    (reports/'phase2_elf_files.json').write_text(json.dumps(rows,indent=2)+'\\n')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as output:
    for p in sorted(reports.rglob('*')):
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
    for name in ('CMakeCache.txt','CMakeFiles/CMakeOutput.log','CMakeFiles/CMakeError.log','CTestTestfile.cmake'):
        p=build/name
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
'''
    return {'01_create':guard,'03_validate_extract':extract,'04_compile':compile_payload,'05_collect':collect}


def remote_command():
    return [SSH, '-T', *OPTIONS, 'cat@192.168.10.27', 'python3 -I -B -']


def run_step(report, name, command, payload=None, timeout=60, binary=False):
    dump(report / (name+'.command.json'), command)
    if payload is not None:
        (report/(name+'.remote.py')).write_bytes(payload)
    out = report/(name+('.tgz' if binary else '.stdout.log'))
    err = report/(name+'.stderr.log')
    timed_out=False
    with out.open('xb') as stdout, err.open('xb') as stderr:
        process=subprocess.Popen(command, stdin=subprocess.PIPE if payload else subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        try:
            process.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            process.kill()  # local SSH only; remote build supervisor remains bounded
            process.communicate()
    result={'exit_code':process.returncode,'local_timeout':timed_out,'remote_exit_known':not timed_out and process.returncode!=255}
    dump(report/(name+'.execution.json'),result)
    print(name,json.dumps(result),flush=True)
    return process.returncode if not timed_out else 124


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    assert args.prepare != args.execute, 'choose exactly one action'
    package=ROOT/'reports/stage5_01_local/board_package'/ARCHIVE
    assert hashlib.sha256(package.read_bytes()).hexdigest()==EXPECTED
    scripts=payloads()
    for source in scripts.values():
        compile(source,'<remote>','exec')
    if args.prepare:
        destination=ROOT/'reports/stage5_01_local/phase2_execution_plan'
        destination.mkdir(exist_ok=True)
        for name,source in scripts.items():
            (destination/(name+'.py')).write_text(source,encoding='utf-8')
        print('Prepared four syntax-checked payloads; immutable 126256-byte archive verified. No remote action.')
        return 0
    report=ROOT/'reports/stage5_01_board'/('phase2_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    dump(report/'scope.json',{'authorization':'User approved phase 2 isolated deploy/compile only','remote_root':REMOTE,'archive':ARCHIVE,'sha256':EXPECTED,'ctest':False,'hardware_tests':False,'disk_stop_below_bytes':500*1024*1024})
    code=run_step(report,'01_create',remote_command(),scripts['01_create'].encode(),60)
    if code:
        return code
    code=run_step(report,'02_upload',[SCP,'-S',SSH,*OPTIONS,str(package),str(package)+'.sha256','cat@192.168.10.27:'+REMOTE+'/'],timeout=90)
    if code:
        return code
    code=run_step(report,'03_validate_extract',remote_command(),scripts['03_validate_extract'].encode(),90)
    if code:
        return code
    build_code=run_step(report,'04_compile',remote_command(),scripts['04_compile'].encode(),900)
    collect_code=run_step(report,'05_collect',remote_command(),scripts['05_collect'].encode(),90,binary=True)
    if collect_code==0:
        destination=report/'collected'
        destination.mkdir()
        with tarfile.open(report/'05_collect.tgz','r:gz') as archive:
            for member in archive.getmembers():
                p=PurePosixPath(member.name)
                assert member.isfile() and not p.is_absolute() and '..' not in p.parts
                target=destination/Path(*p.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as output:
                    output.write(archive.extractfile(member).read())
    dump(report/'result.json',{'compile_ssh_exit_code':build_code,'collection_ssh_exit_code':collect_code,'ctest_executed':False,'hardware_tests_executed':False})
    print('REPORT_DIRECTORY',str(report.relative_to(ROOT)),flush=True)
    return build_code or collect_code


if __name__=='__main__':
    raise SystemExit(main())
```

## 操作 26：`tools/stage5_phase3_ssh.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_phase3_ssh.py`

SHA256：`1af9109ff8de9ee783bbd1523ed15dba2a0d9120bc67c506232b155e90f8f9b0`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Capture an explicitly authorized phase-3 SSH payload without rewriting output."""
import argparse
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import stage5_phase2_deploy as transport


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    assert bool(args.payload) != args.collect
    root = transport.ROOT
    report = root/'reports/stage5_01_board'/('phase3_ssh_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    if args.collect:
        source = transport.payloads()['05_collect']
    else:
        path = args.payload.resolve()
        assert path.is_relative_to(root)
        source = path.read_text(encoding='utf-8')
    compile(source, '<remote>', 'exec')
    code = transport.run_step(report, 'remote', transport.remote_command(), source.encode('utf-8'), args.timeout, binary=args.collect)
    if args.collect and code == 0:
        destination=report/'collected'
        destination.mkdir()
        with tarfile.open(report/'remote.tgz','r:gz') as archive:
            for m in archive.getmembers():
                p=PurePosixPath(m.name)
                assert m.isfile() and not p.is_absolute() and '..' not in p.parts
                target=destination/Path(*p.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(archive.extractfile(m).read())
    print('REPORT_DIRECTORY',report.relative_to(root),flush=True)
    if not args.collect:
        print((report/'remote.stdout.log').read_text(encoding='utf-8',errors='replace')[-18000:],flush=True)
        print((report/'remote.stderr.log').read_text(encoding='utf-8',errors='replace')[-4000:],flush=True)
    return code


if __name__=='__main__':
    raise SystemExit(main())
```

## 操作 27：`tools/stage5_prepare_board_bundle.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_prepare_board_bundle.py`

SHA256：`004c69225dc02870ca1c72c5c773c30e7fb35e2606a334193b19e6c5a823a31f`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Create a source-only board-review archive locally. Does not invoke SSH/SCP."""

import hashlib
import argparse
import io
import json
from pathlib import Path
import tarfile


def package_files(root):
    selected = [Path("CMakeLists.txt"), Path("README_STAGE5.txt")]
    for folder in ("src", "include", "tests"):
        selected.extend(p.relative_to(root) for p in (root / folder).rglob("*")
                        if p.is_file() and p.suffix in {".cpp", ".h", ".hpp", ".cmake", ".txt"})
    selected.extend(p.relative_to(root) for p in (root / "tools").glob("stage5_board_*.*")
                    if p.suffix in {".sh", ".py"})
    selected.append(Path("docs/stage5_01_board_review.md"))
    if (root / "docs/stage5_01_readonly_preflight.md").is_file():
        selected.append(Path("docs/stage5_01_readonly_preflight.md"))
    return sorted(set(selected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-name", default="stage5_01_review.tgz")
    args = parser.parse_args()
    if Path(args.archive_name).name != args.archive_name or not args.archive_name.endswith(".tgz"):
        parser.error("Use a simple .tgz basename")
    root = Path(__file__).resolve().parents[1]
    destination = root / "reports/stage5_01_local/board_package"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / args.archive_name
    if archive.exists():
        raise SystemExit("Archive already exists; retain it and choose a fresh version before repackaging")
    manifest = []
    for relative in package_files(root):
        path = root / relative
        if path.is_symlink() or not path.is_file() or ".." in relative.parts or relative.is_absolute():
            raise SystemExit("Unsafe or missing package member: " + str(relative))
        data = path.read_bytes()
        manifest.append({"file": relative.as_posix(), "size": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    checksums = "".join(f"{row['sha256']}  {row['file']}\n" for row in manifest).encode("utf-8")
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as output:
        for row in manifest:
            data = (root / row["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise SystemExit("Source changed while packaging: " + row["file"])
            entry = tarfile.TarInfo(row["file"])
            entry.size = len(data)
            entry.mode = 0o644
            output.addfile(entry, io.BytesIO(data))
        entry = tarfile.TarInfo("SOURCE_SHA256SUMS")
        entry.size = len(checksums)
        entry.mode = 0o644
        output.addfile(entry, io.BytesIO(checksums))
    result = {"status": "PREPARED_LOCALLY_NOT_DEPLOYED", "archive": archive.name,
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "destination": "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review",
              "excluded": ["models", "SDK", "runtime libraries", "build products", "backups", ".git"],
              "files": manifest}
    current = destination / "bundle_manifest.json"
    if current.is_file():
        previous = json.loads(current.read_text(encoding="utf-8"))
        frozen = destination / (previous["archive"] + ".manifest.json")
        if not frozen.exists():
            frozen.write_bytes(current.read_bytes())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    current.write_text(rendered, encoding="utf-8")
    (destination / (archive.name + ".manifest.json")).write_text(rendered, encoding="utf-8")
    (destination / (archive.name + ".sha256")).write_text(
        result["archive_sha256"] + "  " + archive.name + "\n", encoding="ascii")
    print(f"Prepared {len(manifest)} source/document/script files. No remote action performed.")
    print("SHA256 " + result["archive_sha256"])


if __name__ == "__main__":
    main()
```

## 操作 28：`tools/stage5_readonly_ssh.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_readonly_ssh.py`

SHA256：`372953a1b813ecef160019733917d65e881dd0173142b633c4c687517042598a`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Run only the user-authorized read-only RK3576 guard/inspection over SSH."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("guard", "full"), required=True)
    parser.add_argument("--occupancy-only", action="store_true")
    parser.add_argument("--target-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    client = Path("C:/Windows/System32/OpenSSH/ssh.exe")
    destination = "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review"
    guard = (f"if [ -e '{destination}' ] || [ -L '{destination}' ]; then "
             "printf 'DESTINATION_EXISTS_STOP\\n'; exit 20; fi; "
             "printf 'DESTINATION_ABSENT\\n'; printf 'SSH_READONLY_CONNECTED\\n'; "
             "uname -m; uname -r; id; date -Is")
    payload = None
    remote_command = guard
    if args.phase == "full":
        inspection = (root / "tools/stage5_board_readonly_inventory.py").read_bytes()
        if args.occupancy_only:
            inspection = inspection.split(b'if __name__ == "__main__":', 1)[0]
            call = "devices_and_owners(target_only=True)" if args.target_only else "devices_and_owners()"
            inspection += ('print("STAGE5_READONLY_JSON_BEGIN")\n'
                           'print(json.dumps({"resource_occupancy": ' + call + ', '
                           '"review_directory_absent_after": not os.path.lexists(REVIEW)}, indent=2))\n'
                           'print("STAGE5_READONLY_JSON_END")\n').encode("ascii")
        payload = ("set -eu\n" + guard + "\npython3 -I -B - <<'STAGE5_READONLY_PY'\n").encode("ascii")
        payload += inspection + b"\nSTAGE5_READONLY_PY\n"
        remote_command = "timeout 120s bash -s"
    command = [str(client), "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
               "-o", "ConnectionAttempts=1", "-o", "ServerAliveInterval=5",
               "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=yes",
               "-o", "UpdateHostKeys=no", "-o", "ClearAllForwardings=yes",
               "-o", "ControlMaster=no", "-o", "ControlPath=none",
               "-o", "PermitLocalCommand=no", "-o", "RemoteCommand=none",
               "cat@192.168.10.27", remote_command]
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S_%f")
    report = root / "reports/stage5_01_board" / ("readonly_" + args.phase + "_" + stamp)
    report.mkdir(parents=True)
    (report / "command.json").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
    if payload is not None:
        (report / "inspection_script.sh").write_bytes(payload)
    timed_out = False
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(payload, timeout=30 if args.phase == "guard" else 150)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill() # Only the local SSH client; no remote process kill command.
        stdout, stderr = process.communicate()
    (report / "stdout.log").write_bytes(stdout)
    (report / "stderr.log").write_bytes(stderr)
    outcome = {
        "phase": args.phase, "ssh_process_exit_code": process.returncode,
        "occupancy_only": args.occupancy_only,
        "target_only": args.target_only,
        "local_client_timeout": timed_out,
        "remote_command_exit_known": not timed_out and process.returncode != 255,
        "destination_exists_stop": b"DESTINATION_EXISTS_STOP" in stdout,
        "destination_absent_observed": b"DESTINATION_ABSENT" in stdout,
        "ssh_connection_confirmed": b"SSH_READONLY_CONNECTED" in stdout,
        "scope": "Only authorized read-only inspection; no remote file writes/builds/program tests",
        "payload_sha256": hashlib.sha256(payload).hexdigest() if payload else None,
        "report_directory": str(report.relative_to(root)),
    }
    (report / "execution.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    decoded = stdout.decode("utf-8", errors="replace")
    if args.phase == "full" and "STAGE5_READONLY_JSON_BEGIN" in decoded:
        value = json.loads(decoded.split("STAGE5_READONLY_JSON_BEGIN", 1)[1].split("STAGE5_READONLY_JSON_END", 1)[0])
        (report / "inventory.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        occupancy = value.get("resource_occupancy", {})
        query = occupancy.get("sudo_readonly_fuser") or {}
        print(json.dumps({"checks": value.get("checks"),
                          "all_listed_nodes_clear_confirmed": occupancy.get("all_listed_nodes_clear_confirmed"),
                          "fuser_exit_code": query.get("exit_code"),
                          "fuser_stdout": query.get("stdout"), "fuser_stderr": query.get("stderr"),
                          "npu_node_identified": occupancy.get("npu_node_identified"),
                          "camera_sysfs_names": occupancy.get("camera_sysfs_names"),
                          "camera_service_process": occupancy.get("camera_service_process"),
                          "review_directory_absent_after": value.get("review_directory_absent_after")}, indent=2))
    else:
        print(decoded, end="")
    if stderr:
        print("--- SSH stderr ---\n" + stderr.decode("utf-8", errors="replace"), end="")
    print("\n" + json.dumps(outcome, indent=2))
    return process.returncode if process.returncode is not None and not timed_out else 124


if __name__ == "__main__":
    raise SystemExit(main())
```

## 操作 29：`tools/stage5_review.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_review.py`

SHA256：`ad87bcc628125423d4cf2b16a256387545e0a1035feaee065659a3ca652786a9`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Save a reviewable Stage 5.1 diff, hashes and full source appendix. No deployment."""

import difflib
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main():
    root = Path(__file__).resolve().parents[1]
    before = root / "backups/stage5_01_before"
    report = root / "reports/stage5_01_local"
    if not before.is_dir():
        raise SystemExit("Missing original snapshot; refusing to invent a baseline")
    report.mkdir(parents=True, exist_ok=True)
    paths = [Path("CMakeLists.txt"), Path("README_STAGE5.txt")]
    for folder in ("src", "include", "tests", "docs", "config", "tools"):
        paths.extend(p.relative_to(root) for p in (root / folder).rglob("*")
                     if p.is_file() and p.suffix in {".cpp", ".h", ".hpp", ".cmake",
                                                   ".md", ".txt", ".py", ".ps1", ".sh"})
    paths = sorted(set(paths))
    changed = [p for p in paths if sha256(before / p) != sha256(root / p)]
    source_paths = [p for p in changed if p.suffix in {".cpp", ".h", ".hpp", ".py", ".sh"}
                    or p.name == "CMakeLists.txt"]
    appendix = [
        "# 第五阶段5.1实际修改源码全文\n\n",
        "由 tools/stage5_review.py 从当前源码读取生成，不能作为编译或硬件通过证据。"
        "改动语句的语法、所有权和线程解释见 stage5_01_architecture_audit.md 操作5。\n\n",
        "第三阶段信号修复、当前ARM64/硬件验收与剩余风险见 "
        "[stage5_01_board_acceptance.md](stage5_01_board_acceptance.md)。"
        "本附录展示本地当前代码；实际部署版本必须与板端源文件哈希和日志核对。\n\n",
    ]
    for index, path in enumerate(source_paths, 1):
        content = (root / path).read_text(encoding="utf-8")
        appendix.append(f"## 操作 {index}：`{path.as_posix()}`\n\n")
        appendix.append(f"完整路径：`{root / path}`\n\n")
        appendix.append(f"SHA256：`{sha256(root / path)}`\n\n")
        language = "cmake" if path.name == "CMakeLists.txt" else (
            "python" if path.suffix == ".py" else "bash" if path.suffix == ".sh" else "cpp")
        appendix.append("### 最终完整源码\n\n```" + language + "\n" +
                        content.rstrip("\n") + "\n```\n\n")
    appendix_path = root / "docs/stage5_01_source_appendix.md"
    appendix_path.write_text("".join(appendix), encoding="utf-8", newline="\n")
    changed = sorted(set(changed + [appendix_path.relative_to(root)]))

    patch = []
    manifest = []
    for path in changed:
        old_path, new_path = before / path, root / path
        old = old_path.read_text(encoding="utf-8") if old_path.exists() else ""
        new = new_path.read_text(encoding="utf-8")
        patch.extend(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="a/" + path.as_posix() if old_path.exists() else "/dev/null",
            tofile="b/" + path.as_posix()))
        manifest.append({"file": path.as_posix(), "before_sha256": sha256(old_path),
                         "after_sha256": sha256(new_path),
                         "status": "modified" if old_path.exists() else "added"})
    (report / "changes.patch").write_text("".join(patch), encoding="utf-8", newline="\n")
    (report / "change_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {}
    vlm_path = Path("src/ai/rk3576_vlm_backend.cpp")
    old = (before / vlm_path).read_text(encoding="utf-8")
    new = (root / vlm_path).read_text(encoding="utf-8")
    checks["cpu_preprocessor_unchanged"] = (
        old[old.index("bool frameToRgb512"):old.index("struct GenerationState")] ==
        new[new.index("bool frameToRgb512"):new.index("// Own only a successfully")])
    checks["vlm_initialization_unchanged"] = (
        old[old.index("bool RK3576VLMBackend::initialize"):old.index("InferenceResult RK3576")] ==
        new[new.index("bool RK3576VLMBackend::initialize"):new.index("InferenceResult RK3576")])
    checks["vlm_tokens_and_generation_unchanged"] = (
        old[old.index('    std::string prompt = "<image>"'): ] ==
        new[new.index('    std::string prompt = "<image>"'): ])
    for filename, cls in (("asr_pipeline.cpp", "ASRWorker"),
                          ("vad_audio_worker.cpp", "VadAudioWorker")):
        old = (before / "src/audio" / filename).read_text(encoding="utf-8")
        new = (root / "src/audio" / filename).read_text(encoding="utf-8")
        old_body = old[old.index(f"void {cls}::run()") + len(f"void {cls}::run()") :]
        new_body = new[new.index(f"void {cls}::runImpl()") + len(f"void {cls}::runImpl()") :]
        if cls == "VadAudioWorker" and "    ok_ = true;" in new_body:
            # Explicitly account for the reviewed signal-stop guard and completion status.
            # The VAD/PCM/pre-roll/timing/queue algorithm must otherwise remain identical.
            guard = "\n    if (stop_requested_.load())\n    {\n        ok_ = true;\n        return;\n    }\n"
            final = "    // A requested stop is successful if capture/VAD cleanup and final flush succeeded.\n    ok_ = true;"
            limited = new_body.count(guard) == 1 and new_body.count(final) == 1
            normalized = new_body.replace(guard, "", 1).replace(final, "    ok_ = !stop_requested_.load();", 1)
            checks["VadAudioWorker_signal_stop_changes_limited"] = limited and old_body == normalized
        else:
            checks[cls + "_algorithm_unchanged"] = old_body == new_body
    old = (before / "src/audio/asr_pipeline.cpp").read_text(encoding="utf-8")
    new = (root / "src/audio/audio_worker.cpp").read_text(encoding="utf-8")
    checks["AudioWorker_algorithm_unchanged"] = (
        old[old.index("void AudioWorker::run()") + len("void AudioWorker::run()"):
            old.index("// ====================================================\n// 3. ASRWorker")].strip() ==
        new[new.index("void AudioWorker::runImpl()") + len("void AudioWorker::runImpl()"):].strip())
    checks["qwen_backend_unchanged"] = (
        sha256(before / "src/ai/rkllm_backend.cpp") == sha256(root / "src/ai/rkllm_backend.cpp"))
    checks["camera_capture_unchanged"] = (
        sha256(before / "src/video/video_capture.cpp") == sha256(root / "src/video/video_capture.cpp"))
    for filename in ("asr_llm_smoke.cpp", "asr_llm_tts_smoke.cpp"):
        old = (before / "src/audio" / filename).read_text(encoding="utf-8")
        new = (root / "src/audio" / filename).read_text(encoding="utf-8")
        checks[filename + "_routing_prompts_callbacks_unchanged"] = (
            old[old.index("    const auto on_text ="):old.index("    ASRWorker consumer(")] ==
            new[new.index("    const auto on_text ="):new.index("    ASRWorker consumer(")])
    (report / "source_invariants.json").write_text(
        json.dumps({"checks": checks, "note": "Source equality checks only; no SDK/hardware validation."},
                   indent=2) + "\n", encoding="utf-8")
    print(f"Saved patch and hashes for {len(manifest)} files; full appendix: {len(source_paths)} files")
    if not all(checks.values()):
        raise SystemExit("Source equality check failed: " + str(checks))
    print("Source invariants passed (not inference/quality/performance evidence)")


if __name__ == "__main__":
    main()
```

## 操作 30：`tools/stage5_summarize_phase3.py`

完整路径：`Z:\master_T\Linux\资料\code\rk3576_multimodal_stage5_source\rk3576_multimodal\tools\stage5_summarize_phase3.py`

SHA256：`8695f007dc1e12073f1df72a8849ed47c06c1ecbd4ec86fae4df7b3b0546d1a7`

### 最终完整源码

```python
#!/usr/bin/env python3
"""Derive the Stage 5.1 acceptance summary from preserved board/user evidence."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=Path('reports/stage5_01_board/phase3_ssh_20261017_190524_321782')
BASE=ROOT/EVIDENCE/'collected/reports/stage5_01_board'


def read(path):
    return path.read_text(encoding='utf-8')


def load(path):
    return json.loads(read(path))


def counters(text):
    labels=('VAD segments','ASR recognized','Audio queue dropped',
            'LLM accepted/completed/success/failed/rejected',
            'TTS accepted/completed/success/failed/rejected/empty',
            'VISION completed/success/failed')
    result={}
    for label in labels:
        match=re.search('^'+re.escape(label)+r': ([0-9/]+)\s*$',text,re.M)
        assert match, 'Missing counter: '+label
        result[label]=[int(n) for n in match.group(1).split('/')]
    return result


def main():
    cases={}
    for name in ('baseline_sigint','baseline_sigterm','fixed_idle_sigint','fixed_idle_sigterm',
                 'fixed_initializing_sigterm','voice_both_natural_01','voice_text_active_sigterm'):
        folder=BASE/name
        result=load(folder/'result.json')
        terminal=read(folder/'terminal.log')
        capture=re.search(r'\[ALSA\] XRUN=(\d+) Suspends=(\d+) Recoveries=(\d+) RecoveryFailures=(\d+)',terminal)
        result['capture_error_counters']=dict(zip(('xruns','suspends','recoveries','recovery_failures'),map(int,capture.groups()))) if capture else None
        playback=re.search(r'\[Shutdown\] TTS joined; playback_xruns=(\d+)',terminal)
        result['playback_xruns']=int(playback.group(1)) if playback else None
        result['nonfatal_diagnostics']={'kokoro_unknown_token':terminal.count('Unknown token:'),
                                        'rkllm_custom_template_warning':terminal.count('Calling rkllm_set_chat_template will disable')}
        samples=[json.loads(line) for line in read(folder/'resources.jsonl').splitlines()]
        result['sampled_max_rss_kib']=max((int(s['VmRSS'].split()[0]) for s in samples if 'VmRSS' in s),default=0)
        result['sampled_max_threads']=max((int(s['Threads']) for s in samples if 'Threads' in s),default=0)
        result['evidence_directory']=(EVIDENCE/'collected/reports/stage5_01_board'/name).as_posix()
        assert not result['forced_kill'] and not result['timeout']
        assert result['process_gone'] and result['devices_released'] and result['original_321_unchanged']
        if name.startswith('baseline_'):
            assert result['returncode']==(-2 if name.endswith('sigint') else -15)
            result['acceptance']='OBSERVED_DEFECT_BEFORE_FIX'
        else:
            assert result['returncode']==0 and result['shutdown_complete_marker']
            result['acceptance']='PASSED'
            result['counters']=counters(terminal)
            assert result['playback_xruns']==0
            if result['capture_error_counters'] is not None:
                assert all(v==0 for v in result['capture_error_counters'].values())
        if 'timing_scope' not in result:
            result['timing_interpretation']='Legacy interval includes post-exit device/fingerprint queries; conservative upper bound, not precise child exit latency'
        cases[name]=result
    core=cases['voice_both_natural_01']
    assert core['program_PASS'] and core['text_tts_completed'] and core['vision_tts_completed']
    assert core['counters']['LLM accepted/completed/success/failed/rejected']==[1,1,1,0,0]
    assert core['counters']['TTS accepted/completed/success/failed/rejected/empty']==[2,2,2,0,0,0]
    assert core['counters']['VISION completed/success/failed']==[1,1,0]
    assert core['counters']['VAD segments']==core['counters']['ASR recognized']==[2]
    assert core['counters']['Audio queue dropped']==[0]
    active=cases['voice_text_active_sigterm']
    assert active['text_tts_completed'] and active['counters']['TTS accepted/completed/success/failed/rejected/empty']==[1,1,1,0,0,0]
    user=load(ROOT/'reports/stage5_01_board/user_participation.json')
    assert user['audible_confirmation']['run']=='voice_both_natural_01'
    assert user['audible_confirmation']['text_answer_heard'] and user['audible_confirmation']['vision_answer_heard']
    assert user['active_signal_audible_confirmation']['text_answer_heard']
    assert load(BASE/'voice_text_active_sigterm/user_confirmation.json')==user
    suites=[]
    for folder in (BASE/'phase3_precheck_ctest_20261017T105346Z',BASE/'signal_fix_20261017T105740Z'):
        xml=ET.parse(folder/'ctest.xml').getroot()
        assert xml.attrib['tests']=='4' and xml.attrib['failures']=='0'
        tests=[{'name':e.attrib['name'],'time_seconds':float(e.attrib['time']),
                'kind':'pure_algorithm' if e.attrib['name']=='audio_preprocessor_tests' else 'Fake_or_Mock_unit_test'} for e in xml.findall('testcase')]
        output=read(folder/'ctest.stdout.log')
        total=float(re.search(r'Total Test time \(real\) =\s+([0-9.]+)',output).group(1))
        code=load(folder/'result.json')['ctest_exit_code'] if (folder/'result.json').exists() else int(read(folder/'ctest.exit_code.txt'))
        assert code==0
        suites.append({'folder':folder.name,'total':4,'passed':4,'failed':0,'exit_code':code,'ctest_total_seconds':total,'tests':tests})
    build_folder=BASE/'signal_fix_20261017T105740Z'
    rebuilt=set(re.findall(r'Built target (\S+)',read(build_folder/'build.stdout.log')))
    original_targets=set(load(ROOT/'reports/stage5_01_board/phase2_summary.json')['build_targets_passed'])
    assert rebuilt==original_targets and len(rebuilt)==21
    assert load(build_folder/'build.result.json')=={'returncode':0,'stop_reason':None}
    final=load(BASE/'phase3_final_20261017T110519Z/result.json')
    assert final['original_321_unchanged'] and final['devices']['clear'] and not final['live_isolated_voice_pids']
    assert final['local_remote_source_files_match']==77
    baseline=load(ROOT/'reports/stage5_01_board/stable_original_baseline.json')['fingerprints']
    assert load(BASE/'phase3_final_20261017T110519Z/original_fingerprint.json')==baseline
    for name,digest in load(BASE/'phase3_final_20261017T110519Z/source_sha256.json').items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    initial=load(BASE/'baseline_sigint/system_after.json')['dmesg']
    final_kernel=final['dmesg']
    added=[line for line in final_kernel['stdout'].splitlines() if line not in set(initial['stdout'].splitlines())]
    suspicious=[line for line in added if re.search(r'BUG:|Oops:|segfault|Out of memory|Killed process|rknpu.*(?:failed|error|timeout)',line,re.I)]
    assert final_kernel['exit_code']==0 and not suspicious
    summary={'status':'STAGE5_01_ACCEPTED','scope':'Bounded ARM64 unit tests and short real hardware regression; not proof of long-run leak freedom or exhaustive SDK failure behavior',
             'stage5_01_formally_accepted':True,'ready_for_stage5_02':True,'stage5_02_implementation_started':False,
             'host':'cat@192.168.10.27','remote_root':'/home/cat/projects/RK3576/rk3576_multimodal_stage5_review',
             'local_complete_evidence':EVIDENCE.as_posix(),'arm64_build':'21/21 targets built; post-fix rebuild exit 0',
             'post_fix_build_targets':sorted(rebuilt),'post_fix_build_exit_code':0,
             'ctest_runs':suites,'hardware_and_signal_runs':cases,'user_confirmation':user,
             'error_statistics':{'original_signal_defects_observed':2,'post_fix_case_failures':0,
                                 'ctest_failures_before_fix':0,'ctest_failures_after_fix':0,
                                 'timeouts':0,'forced_kills':0,'core_audio_queue_dropped':0,
                                 'core_llm_failures':0,'core_vision_failures':0,'core_tts_failures':0,
                                 'note':'Absent pre-fix/early-stop capture statistics remain null, not fabricated zeros; known nonfatal model diagnostics are counted per case'},
             'final_checks':{'time':final['time']['stdout'].strip(),'original_321_unchanged':True,'source_files_match':77,
                             'target_devices_clear':True,'live_isolated_voice_pids':[],
                             'disk_free_bytes':final['disk_free_bytes'],'memory_command':final['memory'],
                             'existing_3a_service':final['existing_3a_service'],
                             'new_kernel_lines_since_baseline':len(added),'matching_oom_crash_npu_error_lines':suspicious},
             'production_fix_files':['src/audio/asr_llm_tts_smoke.cpp','include/audio/vad_audio_worker.h','src/audio/vad_audio_worker.cpp'],
             'phase3_production_patch':'reports/stage5_01_local/phase3_signal_fix/signal_fix.patch',
             'phase3_raw_git_diff':'reports/stage5_01_local/phase3_signal_fix/signal_fix.git.diff',
             'remaining_risks':['Synchronous SDK initialization/inference and blocking ALSA calls are drained, not forcibly cancelled; hung SDK remains bounded by the external test guard only',
                                'Short separate-process regressions do not prove same-process long-duration leak freedom; no ASan/Valgrind or exhaustive SDK fault injection',
                                'RKNN failed outputs_get ownership and release/destroy error returns remain untested SDK failure cases',
                                'Runtime callback serialization/late-userdata behavior is not exhaustively proven; current real synchronous runs passed',
                                'Completion callback exception can still lose completion accounting; prior documented risk, not observed in these runs',
                                'NPU parallel arbitration/throughput not tested; Stage 5.2 architecture remains unchanged',
                                'Existing Kokoro unknown-token and RKLLM custom-template diagnostics retained; no model modifications',
                                'VLM image semantics and varied Chinese visual questioning not accepted; original fixed English prompt retained']}
    output=ROOT/'reports/stage5_01_board/phase3_summary.json'
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    artifacts=[]
    for p in sorted((ROOT/EVIDENCE).rglob('*')):
        if p.is_file():
            artifacts.append({'file':p.relative_to(ROOT/EVIDENCE).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (ROOT/'reports/stage5_01_board/phase3_evidence_manifest.json').write_text(json.dumps(artifacts,indent=2)+'\n',encoding='utf-8')
    print('Verified board/user evidence: CTest 4/4 twice, original signal defect twice, five successful fixed hardware/signal cases; original 321 entries unchanged.')
    print('Stage 5.1 accepted within documented scope; Stage 5.2 not started.')


if __name__=='__main__':
    main()
```

