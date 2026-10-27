# 5.2 当前修改源码全文

由 `tools/stage5_02_export.py` 从真实文件生成。逐句语义解释见 [stage5_02_statement_notes.md](stage5_02_statement_notes.md)，架构与实测见 [stage5_02_async_pipeline.md](stage5_02_async_pipeline.md)。本附录不省略入口及测试，不代替板端版本哈希或执行证据。

## 操作 1：CMakeLists.txt

SHA256：`765ea5e08c49037e12b69d4a6730f6e6b6195300e215251240ab2ed69ad5dd99`；357 行。

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

    add_executable(async_pipeline_tests tests/async_pipeline_tests.cpp
        src/audio/asr_pipeline.cpp src/audio/audio_preprocessor.cpp src/audio/tts_worker.cpp)
    target_link_libraries(async_pipeline_tests PRIVATE multimodal_core)
    project_warnings(async_pipeline_tests)
    add_test(NAME async_pipeline_tests COMMAND async_pipeline_tests)
    set_tests_properties(async_pipeline_tests PROPERTIES TIMEOUT 20)
    if(BUILD_WITH_RKLLM AND BUILD_WITH_VLM)
        add_executable(stage5_02_npu_probe tests/stage5_02_npu_probe.cpp)
        target_link_libraries(stage5_02_npu_probe PRIVATE multimodal_camera)
        project_warnings(stage5_02_npu_probe)
        # Manual hardware diagnostic only; never auto-register it in CTest.
    endif()

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

## 操作 2：include/ai/llm_worker.h

SHA256：`cbc723789394737b28b5711cf0acdf4ddfca7777754abd3ffd37dd087cb37f45`；101 行。

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
    // Reuse the same FIFO for custom inference, including VLM; owns no Engine.
    explicit LLMWorker(std::size_t capacity = 2);
    ~LLMWorker();

    LLMWorker(const LLMWorker&) = delete;
    LLMWorker& operator=(const LLMWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);
    // Explicit restart only after requestStop + join; start itself retains its one-shot contract.
    bool restart(std::string& error);

    // 正在执行的任务不占用等待队列容量。
    LLMSubmitStatus submit(std::uint64_t id,
                           std::string question,
                           LLMWorkerChunk on_chunk = {},
                           LLMWorkerDone on_done = {},
                           TaskOptions options = {});
    using Inference = std::function<InferenceResult(const LLMStreamCallback&)>;
    LLMSubmitStatus submitTask(std::uint64_t id, Inference inference,
                              LLMWorkerChunk on_chunk = {}, LLMWorkerDone on_done = {},
                              TaskOptions options = {});

    // 停止接收新请求，排队任务取消。
    void requestStop(StopMode mode = StopMode::CancelPending) noexcept;

    // 需要先 requestStop，且不能从 Worker 线程内部调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;
    WorkerStats stats() const;
    bool waitIdleFor(std::chrono::milliseconds timeout);

private:
    struct Task
    {
        std::uint64_t id = 0;
        Inference inference;
        LLMWorkerChunk on_chunk;
        LLMWorkerDone on_done;
        std::chrono::steady_clock::time_point enqueued_at{};
        TaskOptions options;
    };

    void run();

    LLMEngine* engine_ = nullptr;
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;
    StopMode stop_mode_ = StopMode::CancelPending;
    std::size_t rejected_ = 0;
    WorkerStats stats_;
};

// Descriptive alias; no second queue implementation or second AI framework.
using InferenceWorker = LLMWorker;
```

## 操作 3：include/app/pipeline_admission.h

SHA256：`b7aef862b129b9cf72c028137a03bfac47cbf1e712ca7b23c6744117ddf31437`；70 行。

```cpp
#pragma once
#include "common/work_control.h"
#include <algorithm>
#include <map>
#include <mutex>
#include <stdexcept>

// One credit covers inference, TTS waiting, synthesis and playback, not just one queue.
// Captured shared tickets release credit on all callback/exception/cancellation paths.
class PipelineAdmission {
    struct State;
public:
    struct Stats {std::size_t accepted=0,rejected=0,inflight=0,peak=0;bool closed=false;};
    class Ticket {
    public:
        ~Ticket();
        TaskOptions options(std::chrono::milliseconds max_wait) const {
            TaskOptions result;result.deadline=deadline_;result.max_queue_wait=max_wait;result.cancelled=cancelled_;return result;
        }
        bool cancelled() const noexcept {return cancelled_->load();}
    private:
        friend class PipelineAdmission;
        Ticket(std::shared_ptr<State> state,std::uint64_t id,TaskOptions::Clock::time_point deadline)
            :state_(std::move(state)),id_(id),deadline_(deadline),cancelled_(std::make_shared<std::atomic<bool>>(false)){}
        std::shared_ptr<State> state_;
        std::uint64_t id_;
        TaskOptions::Clock::time_point deadline_;
        std::shared_ptr<std::atomic<bool>> cancelled_;
        bool admitted_=false;
    };
    explicit PipelineAdmission(std::size_t capacity):state_(std::make_shared<State>(capacity)) {
        if(!capacity)throw std::invalid_argument("Pipeline admission capacity must be positive");
    }
    std::shared_ptr<Ticket> tryAcquire(std::uint64_t id,std::chrono::milliseconds lifetime) {
        std::lock_guard<std::mutex> lock(state_->mutex);
        if(state_->stats.closed || state_->stats.inflight>=state_->capacity || state_->tickets.count(id)) {
            ++state_->stats.rejected;return {};
        }
        auto ticket=std::shared_ptr<Ticket>(new Ticket(state_,id,TaskOptions::Clock::now()+lifetime));
        state_->tickets.emplace(id,ticket->cancelled_);
        ticket->admitted_=true;++state_->stats.accepted;++state_->stats.inflight;
        state_->stats.peak=std::max(state_->stats.peak,state_->stats.inflight);
        return ticket;
    }
    bool cancel(std::uint64_t id) {
        std::lock_guard<std::mutex> lock(state_->mutex);
        const auto found=state_->tickets.find(id);
        if(found==state_->tickets.end())return false;
        if(auto flag=found->second.lock()){flag->store(true);return true;}
        return false;
    }
    void close(bool cancel_waiting) {
        std::lock_guard<std::mutex> lock(state_->mutex);state_->stats.closed=true;
        if(cancel_waiting)for(auto& row:state_->tickets)if(auto flag=row.second.lock())flag->store(true);
    }
    Stats stats() const {std::lock_guard<std::mutex> lock(state_->mutex);return state_->stats;}
private:
    struct State {
        explicit State(std::size_t size):capacity(size){}
        std::mutex mutex;
        const std::size_t capacity;
        Stats stats;
        // Weak cancellation flags avoid destroying a Ticket recursively while this mutex is held.
        std::map<std::uint64_t,std::weak_ptr<std::atomic<bool>>> tickets;
    };
    std::shared_ptr<State> state_;
};
inline PipelineAdmission::Ticket::~Ticket() {
    if(admitted_){std::lock_guard<std::mutex> lock(state_->mutex);--state_->stats.inflight;state_->tickets.erase(id_);}
}
```

## 操作 4：include/app/pipeline_metrics.h

SHA256：`9fece6741f2a5f1e529b71057b1907824c404e49b744f01796dfd92b02a4ac30`；33 行。

```cpp
#pragma once
#include "common/work_control.h"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>

inline int pipelineEnv(const char* name,int fallback,int low,int high) {
    const char* value=std::getenv(name);if(!value)return fallback;
    std::size_t used=0;const std::string text(value);const int result=std::stoi(text,&used);
    if(used!=text.size() || result<low || result>high)throw std::invalid_argument(std::string("Invalid ")+name);
    return result;
}
struct DispatchTimer {
    std::mutex& mutex;
    std::uint64_t id;
    std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
    ~DispatchTimer(){
        const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        std::lock_guard<std::mutex> lock(mutex);std::cout<<"[Dispatch] id="<<id<<" callback_ms="<<ms<<'\n'<<std::flush;
    }
};
inline void printWorkerStats(const char* stage,const WorkerStats& s) {
    std::cout<<"[QueueStats] stage="<<stage<<" generation="<<s.generation
             <<" accepted="<<s.accepted<<" completed="<<s.completed<<" started="<<s.started
             <<" failed="<<s.failed<<" cancelled="<<s.cancelled<<" expired="<<s.expired
             <<" rejected_full="<<s.rejected_full<<" rejected_stopped="<<s.rejected_stopped
             <<" peak="<<s.peak_depth<<" pending="<<s.pending<<" active="<<s.active
             <<" callback_errors="<<s.callback_errors<<" queue_sum_ms="<<s.queue_wait_sum_ms
             <<" queue_max_ms="<<s.queue_wait_max_ms<<" service_sum_ms="<<s.service_sum_ms<<'\n';
}
```

## 操作 5：include/audio/alsa_playback_service.h

SHA256：`17f35d33cbd81ddd69eb605cce429d42a69416014824ef8891d7b0bb0760ff3a`；61 行。

```cpp

#pragma once

struct _snd_pcm;
typedef struct _snd_pcm snd_pcm_t;

#include <cstddef>
#include <cstdint>
#include <string>

// 阻塞式 ALSA 音频播放服务。
// 输入 float PCM，内部转换成 S16_LE。
// 3.3 阶段仅在一个线程中使用，不支持并发调用。
class AlsaPlaybackService
{
public:
    AlsaPlaybackService() = default;
    ~AlsaPlaybackService();

    // ALSA PCM 句柄不可复制。
    AlsaPlaybackService(const AlsaPlaybackService&) = delete;
    AlsaPlaybackService& operator=(const AlsaPlaybackService&) = delete;

    // 初始化声卡和 PCM 播放参数。
    bool open(
        const std::string& device,
        std::int32_t sample_rate,
        std::string& error
    );

    // 播放单声道 float PCM。
    // 本函数阻塞，直到音频播放完成或出错。
    bool play(
        const float* samples,
        std::size_t sample_count,
        std::string& error
    );

    // 关闭设备并释放资源。
    void close() noexcept;

    bool ready() const noexcept
    {
        return pcm_ != nullptr;
    }

    std::uint64_t xrunCount() const noexcept
    {
        return xrun_count_;
    }

private:
    // ALSA PCM 设备句柄。
    snd_pcm_t* pcm_ = nullptr;

    // 当前配置的采样率。
    std::int32_t sample_rate_ = 0;

    // Playback 发生缓冲区欠载的次数。
    std::uint64_t xrun_count_ = 0;
};
```

## 操作 6：include/audio/asr_pipeline.h

SHA256：`e13830024ef120d9a6411017cead5dddcb2d461754fb07d22453267e9b32c552`；177 行。

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
struct AudioQueueStats {
    std::size_t pushed=0,popped=0,dropped=0,rejected_closed=0,pending=0,peak=0;
};
class AudioBufferQueue {
public:
    explicit AudioBufferQueue(std::size_t capacity);

    bool push(AudioSegment segment);
    bool pop(AudioSegment& segment);

    void close();

    std::size_t droppedCount() const;
    AudioQueueStats stats() const;

private:
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<AudioSegment> items_;

    bool closed_ = false;
    std::size_t dropped_ = 0;
    AudioQueueStats stats_;
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

## 操作 7：include/audio/tts_service.h

SHA256：`ca3e0abd2ea33208a356f9e51a4615667096eb86b840c928002883e1a277e6ef`；63 行。

```cpp

#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct SherpaOnnxOfflineTts;

struct TTSAudio
{
    std::vector<float> samples;
    std::int32_t sample_rate = 0;
    double synthesis_ms = 0.0;
};

class TTSService
{
public:
    TTSService() = default;
    ~TTSService();

    TTSService(const TTSService&) = delete;
    TTSService& operator=(const TTSService&) = delete;
    TTSService(TTSService&&) = delete;
    TTSService& operator=(TTSService&&) = delete;

    // 新增 speaker_id，默认 0，保持旧调用兼容。
    bool initialize(
        const std::string& model_dir,
        std::string& error,
        std::int32_t num_threads = 2,
        std::int32_t speaker_id = 0
    );

    bool synthesize(
        const std::string& text,
        TTSAudio& output,
        std::string& error
    );

    void shutdown() noexcept;

    bool ready() const noexcept
    {
        return tts_ != nullptr;
    }

    std::int32_t sampleRate() const noexcept;
    std::int32_t numSpeakers() const noexcept;

    std::int32_t speakerId() const noexcept
    {
        return speaker_id_;
    }

private:
    // 当前实例所使用的 sherpa-onnx TTS 对象。
    const SherpaOnnxOfflineTts* tts_ = nullptr;

    // 本次初始化选中的音色编号。
    std::int32_t speaker_id_ = 0;
};
```

## 操作 8：include/audio/tts_worker.h

SHA256：`09c3117c0a23f980ec015a9799611f7239e792dd35aefbc0a36c0735c86937be`；141 行。

```cpp

#pragma once

#include "audio/alsa_playback_service.h"
#include "audio/tts_service.h"
#include "common/work_control.h"

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
    TaskDisposition disposition = TaskDisposition::Completed;
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
    bool restart(std::string& error);

    // 非阻塞提交任务。
    TTSSubmitStatus submit(
        std::uint64_t id,
        std::string text,
        TTSWorkerDone on_done = {},
        TaskOptions options = {}
    );

    // 不再接收新任务。
    // 等待队列中的任务报告取消；
    // 正在执行的任务允许自然完成。
    void requestStop(StopMode mode = StopMode::CancelPending) noexcept;

    // 必须从非 Worker 线程调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;
    WorkerStats stats() const;
    bool waitIdleFor(std::chrono::milliseconds timeout);

private:
    struct Task
    {
        std::uint64_t id = 0;

        std::string text;

        TTSWorkerDone on_done;

        std::chrono::steady_clock::time_point
            enqueued_at{};
        TaskOptions options;
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
    StopMode stop_mode_ = StopMode::CancelPending;

    std::size_t rejected_ = 0;
    WorkerStats stats_;
};
```

## 操作 9：include/common/inference_result.h

SHA256：`7fdec0feb5f34af678a46911ea034f10e393d821ad2f8332e817f413a30a2d0a`；20 行。

```cpp
#pragma once
#include <cstdint>
#include <string>
#include "common/work_control.h"

// 不可用的指标使用 -1，不伪造 TTFT 或 tokens/s。
struct InferenceResult
{
    bool success = false;
    std::string text;
    std::string error_message;
    double latency_ms = 0.0;
    uint64_t frame_id = 0;
    uint64_t frame_timestamp_ns = 0;
    double frame_age_ms = -1.0;

    // 从 rkllm_run 提交前至首个非空文本回调的耗时；无法获得时为 -1。
    double first_text_ms = -1.0;
    TaskDisposition disposition = TaskDisposition::Completed;
};
```

## 操作 10：include/common/work_control.h

SHA256：`ea1c2b63ec0e9a8e21b1dc16ce8b0a7274c644d5ca55ddb5feea753d18ae3529`；30 行。

```cpp
#pragma once
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>

enum class StopMode { Drain, CancelPending };
enum class TaskDisposition { Completed, Cancelled, Expired };
inline const char* dispositionName(TaskDisposition value) noexcept {
    return value==TaskDisposition::Cancelled?"cancelled":value==TaskDisposition::Expired?"expired":"completed";
}
struct TaskOptions {
    using Clock=std::chrono::steady_clock;
    Clock::time_point deadline=Clock::time_point::max();
    std::chrono::milliseconds max_queue_wait=std::chrono::milliseconds::max();
    std::shared_ptr<std::atomic<bool>> cancelled;
    TaskDisposition disposition(Clock::time_point enqueued, Clock::time_point now, bool stopping) const noexcept {
        if (stopping || (cancelled && cancelled->load())) return TaskDisposition::Cancelled;
        if (now>=deadline || (max_queue_wait!=std::chrono::milliseconds::max() && now-enqueued>=max_queue_wait))
            return TaskDisposition::Expired;
        return TaskDisposition::Completed;
    }
};
struct WorkerStats {
    std::uint64_t generation=0;
    std::size_t accepted=0,rejected_full=0,rejected_stopped=0,started=0,completed=0;
    std::size_t failed=0,cancelled=0,expired=0,callback_errors=0,peak_depth=0,pending=0,active=0;
    double queue_wait_sum_ms=0,queue_wait_max_ms=0,service_sum_ms=0;
};
```

## 操作 11：src/ai/llm_worker.cpp

SHA256：`78d1967345cea3fc61051c92b4a832128a1491868de284b60b67733a6bc7b367`；99 行。

```cpp
#include "ai/llm_worker.h"
#include <algorithm>
#include <atomic>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

LLMWorker::LLMWorker(LLMEngine& engine,std::size_t capacity):LLMWorker(capacity){engine_=&engine;}
LLMWorker::LLMWorker(std::size_t capacity):capacity_(capacity) {
    if (!capacity_) throw std::invalid_argument("LLMWorker capacity must be greater than zero");
}
LLMWorker::~LLMWorker(){requestStop();join();}
bool LLMWorker::start(std::string& error) {
    std::lock_guard<std::mutex> lock(mutex_);error.clear();
    if (started_ || stop_requested_) {error="LLMWorker can only be started once; use restart after stop/join";return false;}
    try {thread_=std::thread(&LLMWorker::run,this);started_=true;++stats_.generation;}
    catch(const std::exception& e){error=std::string("LLMWorker thread creation failed: ")+e.what();return false;}
    return true;
}
bool LLMWorker::restart(std::string& error) {
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!started_ || !stop_requested_ || thread_.joinable() || !pending_.empty()) {error="restart requires stopped and joined worker";return false;}
     started_=false;stop_requested_=false;rejected_=0;
     const auto generation=stats_.generation;stats_={};stats_.generation=generation;}
    return start(error);
}
LLMSubmitStatus LLMWorker::submit(std::uint64_t id,std::string question,LLMWorkerChunk chunk,LLMWorkerDone done,TaskOptions options) {
    if (!engine_) throw std::logic_error("submit(text) requires an LLMEngine");
    return submitTask(id,[this,question=std::move(question)](const LLMStreamCallback& callback){
        return engine_->inferStreaming(question,callback);
    },std::move(chunk),std::move(done),std::move(options));
}
LLMSubmitStatus LLMWorker::submitTask(std::uint64_t id,Inference inference,LLMWorkerChunk chunk,LLMWorkerDone done,TaskOptions options) {
    if (!inference) throw std::invalid_argument("Empty inference task");
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!started_ || stop_requested_) {++stats_.rejected_stopped;return LLMSubmitStatus::NotRunning;}
     if (pending_.size()>=capacity_) {++rejected_;++stats_.rejected_full;return LLMSubmitStatus::QueueFull;}
     Task task;task.id=id;task.inference=std::move(inference);task.on_chunk=std::move(chunk);task.on_done=std::move(done);
     task.enqueued_at=std::chrono::steady_clock::now();task.options=std::move(options);
     pending_.push_back(std::move(task));++stats_.accepted;stats_.peak_depth=std::max(stats_.peak_depth,pending_.size());}
    cv_.notify_one();return LLMSubmitStatus::Accepted;
}
void LLMWorker::requestStop(StopMode mode) noexcept {
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!stop_requested_ || mode==StopMode::CancelPending) stop_mode_=mode;
     stop_requested_=true;}
    cv_.notify_all();
}
void LLMWorker::join(){if(thread_.joinable())thread_.join();}
std::size_t LLMWorker::pendingCount() const {std::lock_guard<std::mutex> lock(mutex_);return pending_.size();}
std::size_t LLMWorker::rejectedCount() const {std::lock_guard<std::mutex> lock(mutex_);return rejected_;}
WorkerStats LLMWorker::stats() const {std::lock_guard<std::mutex> lock(mutex_);auto copy=stats_;copy.pending=pending_.size();return copy;}
bool LLMWorker::waitIdleFor(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    return cv_.wait_for(lock,timeout,[&]{return pending_.empty() && stats_.active==0;});
}
void LLMWorker::run() {
    using Clock=std::chrono::steady_clock;
    for (;;) {
        Task task;bool cancel=false;
        {std::unique_lock<std::mutex> lock(mutex_);
         cv_.wait(lock,[&]{return stop_requested_ || !pending_.empty();});
         if (pending_.empty() && stop_requested_) return;
         task=std::move(pending_.front());pending_.pop_front();stats_.active=1;
         cancel=stop_requested_ && stop_mode_==StopMode::CancelPending;}
        const auto begin=Clock::now();
        const double waited=std::chrono::duration<double,std::milli>(begin-task.enqueued_at).count();
        InferenceResult result;
        result.disposition=task.options.disposition(task.enqueued_at,begin,cancel);
        const auto disposition=result.disposition;
        if (disposition!=TaskDisposition::Completed) {
            result.error_message=std::string("Inference task ")+dispositionName(disposition);
            std::cerr<<"[Inference "<<dispositionName(disposition)<<" #"<<task.id<<"] queue_ms="<<waited<<'\n';
        } else {
            {std::lock_guard<std::mutex> lock(mutex_);++stats_.started;}
            std::atomic<bool> chunk_failed{false};
            try {
                result=task.inference([&](const std::string& chunk){
                    if (task.on_chunk) try {task.on_chunk(task.id,chunk);} catch(...) {chunk_failed.store(true);}
                });
            } catch(const std::exception& e) {result.success=false;result.text.clear();result.error_message=std::string("LLMWorker inference exception: ")+e.what();}
              catch(...) {result.success=false;result.text.clear();result.error_message="LLMWorker inference: unknown exception";}
            if (chunk_failed.load()) {result.success=false;result.text.clear();result.error_message="LLMWorker chunk callback threw an exception";}
        }
        const double service=std::chrono::duration<double,std::milli>(Clock::now()-begin).count();
        bool callback_failed=false;
        if (task.on_done) try {task.on_done(task.id,result,disposition==TaskDisposition::Cancelled?-1.0:waited);}
        catch(...) {callback_failed=true;std::cerr<<"[Inference callback error #"<<task.id<<"]\n";}
        const bool failed=disposition==TaskDisposition::Completed && !result.success;
        task=Task{};
        {std::lock_guard<std::mutex> lock(mutex_);
         ++stats_.completed;stats_.active=0;stats_.failed+=failed;
         stats_.cancelled+=disposition==TaskDisposition::Cancelled;stats_.expired+=disposition==TaskDisposition::Expired;
         stats_.callback_errors+=callback_failed;stats_.queue_wait_sum_ms+=waited;
         stats_.queue_wait_max_ms=std::max(stats_.queue_wait_max_ms,waited);stats_.service_sum_ms+=service;}
        cv_.notify_all();
    }
}
```

## 操作 12：src/audio/alsa_playback_service.cpp

SHA256：`5ed616ee7251c67b605f0c6d1ae24a088068b3d2858654ffdf9d8c5798626756`；400 行。

```cpp

#include "audio/alsa_playback_service.h"
#include <alsa/asoundlib.h>

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <new>
#include <string>
#include <vector>

AlsaPlaybackService::~AlsaPlaybackService()
{
    close();
}

bool AlsaPlaybackService::open(
    const std::string& device,
    std::int32_t sample_rate,
    std::string& error)
{
    close();
    error.clear();

    if (device.empty() || sample_rate <= 0)
    {
        error = "Invalid ALSA device or sample rate";
        return false;
    }

    // 1. 打开阻塞式 ALSA Playback PCM。
    int rc = snd_pcm_open(
        &pcm_,
        device.c_str(),
        SND_PCM_STREAM_PLAYBACK,
        0
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_open: ") +
                snd_strerror(rc);
        pcm_ = nullptr;
        return false;
    }

    // 2. 统一配置硬件和软件参数。
    // soft_resample=1 允许 ALSA 插件进行采样率转换。
    // latency=500000 us，即 500 ms 的目标缓冲延迟。
    rc = snd_pcm_set_params(
        pcm_,
        SND_PCM_FORMAT_S16_LE,
        SND_PCM_ACCESS_RW_INTERLEAVED,
        1,
        static_cast<unsigned int>(sample_rate),
        1,
        500000
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_set_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 3. 查询真正协商出来的 buffer 和 period。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 ||
        buffer_frames < 2 ||
        period_frames == 0)
    {
        error = "Cannot obtain valid ALSA buffer parameters";
        close();
        return false;
    }

    // 4. 设置软件参数。
    snd_pcm_sw_params_t* sw = nullptr;
    snd_pcm_sw_params_alloca(&sw);

    rc = snd_pcm_sw_params_current(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("sw_params_current: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 至少积累一部分音频再启动播放。
    // 阈值不超过缓冲区大小减 1。
    const snd_pcm_uframes_t start_threshold =
        std::min(
            buffer_frames - 1,
            period_frames * 2
        );

    rc = snd_pcm_sw_params_set_start_threshold(
        pcm_,
        sw,
        start_threshold
    );

    if (rc < 0)
    {
        error = std::string("set_start_threshold: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params_set_avail_min(
        pcm_,
        sw,
        period_frames
    );

    if (rc < 0)
    {
        error = std::string("set_avail_min: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("snd_pcm_sw_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    sample_rate_ = sample_rate;
    xrun_count_ = 0;

    std::cout
        << "[ALSA config]"
        << " buffer_frames=" << buffer_frames
        << " period_frames=" << period_frames
        << " start_threshold=" << start_threshold
        << " buffer_ms="
        << (1000.0 * buffer_frames / sample_rate)
        << '\n';

    return true;
}

bool AlsaPlaybackService::play(
    const float* samples,
    std::size_t sample_count,
    std::string& error)
{
    error.clear();

    if (pcm_ == nullptr)
    {
        error = "ALSA device is not initialized";
        return false;
    }

    if (samples == nullptr || sample_count == 0)
    {
        error = "Invalid audio samples";
        return false;
    }

    // 1. 先在内存中完成全部格式转换，
    // 避免播放期间进行耗时的逐样本转换。
    std::vector<std::int16_t> pcm_data;

    try
    {
        pcm_data.resize(sample_count);
    }
    catch (const std::bad_alloc&)
    {
        error = "Cannot allocate playback PCM buffer";
        return false;
    }

    for (std::size_t i = 0; i < sample_count; ++i)
    {
        float value = samples[i];

        if (!std::isfinite(value))
        {
            value = 0.0f;
        }

        value = std::max(
            -1.0f,
            std::min(1.0f, value)
        );

        const float scale =
            value < 0.0f ? 32768.0f : 32767.0f;

        pcm_data[i] = static_cast<std::int16_t>(
            std::lround(value * scale)
        );
    }

    // 2. 准备播放设备。
    int rc = snd_pcm_prepare(pcm_);

    if (rc < 0)
    {
        error = std::string("snd_pcm_prepare: ") +
                snd_strerror(rc);
        return false;
    }

    // 查询 period，以便按照设备缓冲节奏提交数据。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 || period_frames == 0)
    {
        error = "Cannot query playback period size";
        return false;
    }

    std::size_t offset = 0;
    int consecutive_recoveries = 0;
    int wait_timeouts = 0;

    // 3. 持续将音频送入 ALSA。
    while (offset < pcm_data.size())
    {
        const std::size_t remaining =
            pcm_data.size() - offset;

        const snd_pcm_uframes_t frames =
            static_cast<snd_pcm_uframes_t>(
                std::min(
                    remaining,
                    static_cast<std::size_t>(
                        period_frames
                    )
                )
            );

        const snd_pcm_sframes_t written =
            snd_pcm_writei(
                pcm_,
                pcm_data.data() + offset,
                frames
            );

        if (written > 0)
        {
            offset += static_cast<std::size_t>(written);

            consecutive_recoveries = 0;
            wait_timeouts = 0;
            continue;
        }

        if (written == -EAGAIN || written == 0)
        {
            const int wait_rc =
                snd_pcm_wait(pcm_, 1000);

            if (wait_rc < 0)
            {
                error = std::string("snd_pcm_wait: ") +
                        snd_strerror(wait_rc);
                return false;
            }

            if (wait_rc == 0)
            {
                if (++wait_timeouts > 5)
                {
                    error = "ALSA wait timeout";
                    return false;
                }
            }

            continue;
        }

        // EPIPE 表示播放缓冲区欠载。
        if (written == -EPIPE)
        {
            ++xrun_count_;

            std::cerr
                << "[ALSA XRUN] write offset="
                << offset
                << " total=" << pcm_data.size()
                << '\n';
        }

        const int recover_rc = snd_pcm_recover(
            pcm_,
            static_cast<int>(written),
            1
        );

        if (recover_rc < 0)
        {
            error = std::string("snd_pcm_recover: ") +
                    snd_strerror(recover_rc);
            return false;
        }

        if (++consecutive_recoveries > 5)
        {
            error = "Too many ALSA recoveries";
            return false;
        }
    }

    // 4. 记录全部数据写入后的 PCM 状态。
    snd_pcm_state_t state = snd_pcm_state(pcm_);

    std::cout
        << "[ALSA write]"
        << " submitted_frames=" << offset
        << " state=" << snd_pcm_state_name(state)
        << '\n';

    // 对短音频：如果还未达到自动启动阈值，
    // 显式启动播放，再进行 drain。
    if (state == SND_PCM_STATE_PREPARED)
    {
        rc = snd_pcm_start(pcm_);

        if (rc < 0)
        {
            error = std::string("snd_pcm_start: ") +
                    snd_strerror(rc);
            return false;
        }
    }

    // 5. 等待 ALSA 将缓冲区中的音频播放完。
    rc = snd_pcm_drain(pcm_);

    if (rc < 0)
    {
        if (rc == -EPIPE)
        {
            ++xrun_count_;
        }

        state = snd_pcm_state(pcm_);

        error = std::string("snd_pcm_drain: ") +
                snd_strerror(rc) +
                " state=" +
                snd_pcm_state_name(state);

        return false;
    }

    // XRUN 即使恢复成功，也说明本次播放可能存在断续。
    if (xrun_count_ != 0)
    {
        error = "Playback completed with detected XRUN";
        return false;
    }

    return true;
}

void AlsaPlaybackService::close() noexcept
{
    if (pcm_ != nullptr)
    {
        snd_pcm_close(pcm_);
        pcm_ = nullptr;
    }

    sample_rate_ = 0;
    xrun_count_ = 0;
}
```

## 操作 13：src/audio/asr_llm_tts_smoke.cpp

SHA256：`b746bbb89fff7ba559a101117eecf69074aec561bc9d3515b99646a6d59e5550`；1417 行。

```cpp

#include "audio/asr_pipeline.h"
#include "app/pipeline_admission.h"
#include "app/pipeline_metrics.h"
#include <fstream>
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
#include <fstream>
#include <sstream>
#include <cstdlib>
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
// TEXT and VISION share one asynchronous bounded inference FIFO.
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

    const int max_inflight = pipelineEnv("STAGE5_MAX_INFLIGHT", 2, 1, 8);
    const int request_lifetime_ms = pipelineEnv("STAGE5_REQUEST_LIFETIME_MS", 45000, 1, 300000);
    const int inference_queue_ms = pipelineEnv("STAGE5_INFERENCE_QUEUE_MS", 10000, 1, 60000);
    const int tts_queue_ms = pipelineEnv("STAGE5_TTS_QUEUE_MS", 12000, 1, 60000);
    const char* stop_value = std::getenv("STAGE5_STOP_MODE");
    const std::string stop_mode = stop_value ? stop_value : "drain";
    if (stop_mode != "drain" && stop_mode != "cancel_pending") throw std::invalid_argument("Invalid STAGE5_STOP_MODE");
    PipelineAdmission admission(static_cast<std::size_t>(max_inflight));
    std::size_t dispatch_calls=0, pipeline_rejected=0, cancelled_before_submit=0;
    std::size_t vision_accepted=0, vision_rejected=0;
    std::size_t llm_cancelled=0, llm_expired=0, vision_cancelled=0, vision_expired=0;
    std::size_t tts_cancelled=0, tts_expired=0, downstream_cancelled=0;
    // Must outlive the asynchronous inference worker, including exception unwinding.
    LatestFrameBuffer frames;
    std::unique_ptr<CameraService> camera;
    std::unique_ptr<VLMEngine> vlm;

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
        DispatchTimer dispatch_timer{print_mutex, ++dispatch_calls};
        // --------------------------------------------------
        // 12.1 意图判断
        // --------------------------------------------------

        const RouteDecision route =
            router.route(recognized);

        const auto request_id = next_id++;
        auto ticket = admission.tryAcquire(request_id, std::chrono::milliseconds(request_lifetime_ms));
        if (!ticket)
        {
            ++pipeline_rejected;
            std::lock_guard<std::mutex> out(print_mutex);
            std::cout << "[Pipeline rejected #" << request_id << "] route=" << requestTypeName(route.type)
                      << " reason=busy_or_closed limit=" << max_inflight << '\n';
            return;
        }

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

            const auto status = llm_worker.submitTask(request_id,
                [&, vlm_question](const LLMStreamCallback&) {
                    // Fetch a fresh owned frame when the task executes, never pin queued full frames.
                    return vlm->infer(frames.getLatest(), vlm_question);
                }, {},
                [&, question_at, ticket](std::uint64_t request_id, const InferenceResult& result, double inference_wait_ms)
                {
                    {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        ++vision_completed;
                        if (result.disposition==TaskDisposition::Cancelled) ++vision_cancelled;
                        else if (result.disposition==TaskDisposition::Expired) ++vision_expired;
                        else if (result.success && !result.text.empty()) ++vision_successful;
                        else ++vision_failed;
                    }

                    {
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[VLM done #" << request_id << "] success="
                                  << (result.success ? "true" : "false")
                                  << " queue_ms=" << inference_wait_ms
                                  << " disposition=" << dispositionName(result.disposition)
                                  << " frame_id=" << result.frame_id
                                  << " frame_age_ms=" << result.frame_age_ms
                                  << " latency_ms=" << result.latency_ms
                                  << '\n';
                        if (result.success)
                            std::cout << "[VLM Answer #" << request_id << "] "
                                      << result.text << '\n';
                        else
                            std::cout << (result.disposition==TaskDisposition::Completed ? "[VLM Error] " : "[VLM terminal] ") << result.error_message << '\n';
                    }

                    if (result.success && !result.text.empty() && ticket->cancelled())
                    {
                        { std::lock_guard<std::mutex> lock(state_mutex); ++downstream_cancelled; }
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[Pipeline downstream cancelled #" << request_id << "] stage=tts\n";
                    }
                    if (result.success && !result.text.empty() && !ticket->cancelled())
                    {
                        const auto status = tts_worker.submit(
                            request_id, result.text,
                            [&, question_at, ticket](
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
                                        std::cout << (outcome.disposition==TaskDisposition::Completed ? "[TTS error] " : "[TTS terminal] ")
                                                  << outcome.error_message << '\n';
                                }
                                {
                                    std::lock_guard<std::mutex> lock(state_mutex);
                                    ++tts_completed;
                                    if (outcome.success) ++tts_successful;
                                    else if (outcome.disposition==TaskDisposition::Cancelled) ++tts_cancelled;
                                    else if (outcome.disposition==TaskDisposition::Expired) ++tts_expired;
                                    else ++tts_failed;
                                }
                                completed_cv.notify_all();
                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms)));

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
            else if (result.success && result.text.empty())
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                ++tts_empty;
            }
            // Inference/done run on the shared worker; ASR only submits.
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms)));
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                if (status==LLMSubmitStatus::Accepted) ++vision_accepted;
                else if (status==LLMSubmitStatus::NotRunning && ticket->cancelled()) ++cancelled_before_submit;
                else ++vision_rejected;
            }
            if (status!=LLMSubmitStatus::Accepted)
            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << (ticket->cancelled() ? "[VISION submission cancelled #" : "[VISION rejected #") << request_id << "] status=" << static_cast<int>(status) << '\n';
            }
            return;
        }

        // --------------------------------------------------
        // 12.2 分配请求 ID
        // --------------------------------------------------

        const std::uint64_t id =
            request_id;

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

                [&, prefix_printed, question_at, ticket](
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
                                << (result.disposition==TaskDisposition::Completed ? "[LLM error] " : "[LLM terminal] ")
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

                    if (result.success && !result.text.empty() && ticket->cancelled())
                    {
                        { std::lock_guard<std::mutex> lock(state_mutex); ++downstream_cancelled; }
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[Pipeline downstream cancelled #" << request_id << "] stage=tts\n";
                    }
                    const bool has_answer =
                        result.success &&
                        !result.text.empty() && !ticket->cancelled();

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

                                    [&, question_at, ticket](
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
                                                    << (tts_result.disposition==TaskDisposition::Completed ? "[TTS error] " : "[TTS terminal] ")
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
                                            else if (tts_result.disposition==TaskDisposition::Cancelled) ++tts_cancelled;
                                            else if (tts_result.disposition==TaskDisposition::Expired) ++tts_expired;
                                            else ++tts_failed;
                                        }

                                        // 唤醒等待中的主线程。
                                        completed_cv.notify_all();
                                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms))
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
                        else if (result.disposition==TaskDisposition::Cancelled) ++llm_cancelled;
                        else if (result.disposition==TaskDisposition::Expired) ++llm_expired;
                        else ++llm_failed;

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
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms))
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
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                if (status==LLMSubmitStatus::NotRunning && ticket->cancelled()) ++cancelled_before_submit;
                else ++llm_rejected;
            }

            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << (ticket->cancelled() ? "[LLM submission cancelled #" : "[LLM rejected #")
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

    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");
    const bool replay_mode=replay_path!=nullptr;
    if (!replay_mode)
    {
        std::cout
            << "[Listen] "
            << record_seconds
            << " seconds. "
            << (enable_vision ? "Ask ONE short voice question (text or camera).\n"
                               : "Ask ONE short text question and pause.\n")
            << std::flush;
    }
    else std::cout << "[Replay ready] controlled text; microphone/VAD/ASR not run\n" << std::flush;

    // ------------------------------------------------------
    // 14. 启动录音/VAD 和 ASR 工作线程
    // ------------------------------------------------------

    if (replay_mode)
    {
        std::ifstream input(replay_path);
        if (!input) throw std::runtime_error("Cannot open replay input");
        std::cout << "[InputMode] replay_only NO_MICROPHONE_ASR_OR_VAD_INFERENCE\n" << std::flush;
        const auto replay_start=std::chrono::steady_clock::now();
        std::string line;
        while (std::getline(input,line))
        {
            if (line.empty()) continue;
            const auto tab=line.find('\t');
            if (tab==std::string::npos) throw std::runtime_error("Invalid replay line");
            std::size_t used=0;
            const long delay=std::stol(line.substr(0,tab),&used);
            if (used!=tab || delay<0 || delay>120000) throw std::runtime_error("Invalid replay offset");
            std::this_thread::sleep_until(replay_start+std::chrono::milliseconds(delay));
            if (stop_signals.received()!=0) break;
            std::cout << "[Replay] scheduled_ms=" << delay << " source=controlled_text\n" << std::flush;
            on_text(line.substr(tab+1));
        }
        audio_queue.close();
    }
    else
    {
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
            if (stop_mode == "cancel_pending")
            {
                admission.close(true);
                llm_worker.requestStop(StopMode::CancelPending);
            }
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
    }
    asr.shutdown();
    admission.close(false);
    std::cout << (replay_mode ? "[Shutdown] replay input closed; recognizer destroyed\n" : "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\n") << std::flush;

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

    const auto wait_for_jobs = [&](const char* stage, auto& worker, int deadline_seconds) -> bool
    {
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(deadline_seconds);
        while (!worker.waitIdleFor(std::chrono::milliseconds(100)))
        {
            if ((stop_signals.received()!=0 || stop_signals.failed()) && stop_mode=="cancel_pending")
            {
                admission.close(true);
                llm_worker.requestStop(StopMode::CancelPending);
            }
            if (std::chrono::steady_clock::now()>=deadline)
            {
                std::cerr << "[Timeout] " << stage << " did not become idle\n";
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
            llm_worker,
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
            tts_worker,
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

        if (!replay_mode && !producer.ok())
        {
            std::cerr
                << "[VAD] "
                << producer.error()
                << '\n';
        }

        if (!replay_mode && !consumer.ok())
        {
            std::cerr
                << "[ASR] "
                << consumer.error()
                << '\n';
        }
    }

    const auto audio_stats=audio_queue.stats();
    std::cout << "[AudioQueueStats] pushed=" << audio_stats.pushed << " popped=" << audio_stats.popped
              << " dropped=" << audio_stats.dropped << " rejected_closed=" << audio_stats.rejected_closed
              << " peak=" << audio_stats.peak << " pending=" << audio_stats.pending << '\n';
    const auto inference_stats=llm_worker.stats();
    const auto tts_stats=tts_worker.stats();
    const auto admission_stats=admission.stats();
    printWorkerStats("inference", inference_stats);
    printWorkerStats("tts", tts_stats);
    std::cout << "[PipelineStats] dispatched=" << dispatch_calls << " accepted=" << admission_stats.accepted
              << " rejected=" << pipeline_rejected << " inflight=" << admission_stats.inflight
              << " peak=" << admission_stats.peak << " limit=" << max_inflight
              << " vision_accepted=" << vision_accepted << " vision_rejected=" << vision_rejected
              << " llm_cancelled=" << llm_cancelled << " llm_expired=" << llm_expired
              << " vision_cancelled=" << vision_cancelled << " vision_expired=" << vision_expired
              << " cancelled_before_submit=" << cancelled_before_submit
              << " downstream_cancelled=" << downstream_cancelled
              << " tts_cancelled=" << tts_cancelled << " tts_expired=" << tts_expired << '\n';

    // ------------------------------------------------------
    // 22. 最终验收条件
    // ------------------------------------------------------

    const bool passed =
        (replay_mode || (producer.ok() && consumer.ok())) && audio_queue.droppedCount()==0 &&
        llm_drained && tts_drained && !stop_signals.failed() &&
        (stop_signals.received()!=0 || llm_successful+vision_successful>0) &&
        inference_stats.accepted==inference_stats.completed && tts_stats.accepted==tts_stats.completed &&
        inference_stats.failed==0 && tts_stats.failed==0 &&
        inference_stats.callback_errors==0 && tts_stats.callback_errors==0 &&
        admission_stats.inflight==0 && llm_rejected==0 && vision_rejected==0 && tts_rejected==0;

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

## 操作 14：src/audio/asr_pipeline.cpp

SHA256：`8324a7211312ede7367f2c90e5fa1116334a8e4c8c43155f8362a03f9a009475`；336 行。

```cpp

#include "audio/asr_pipeline.h"

#include "audio/asr_service.h"
#include "audio/audio_preprocessor.h"

#include <chrono>
#include <algorithm>
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
    std::uint64_t dropped_sequence=0;
    bool dropped=false;
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (closed_)
        {
            ++stats_.rejected_closed;
            std::cerr << "[Audio queue rejected #" << segment.sequence << "] closed\n";
            return false;
        }

        // 队列满时丢弃最旧的完整音频段。
        if (items_.size() >= capacity_)
        {
            dropped_sequence=items_.front().sequence;
            dropped=true;
            items_.pop_front();
            ++dropped_;
        }

        items_.push_back(std::move(segment));
        ++stats_.pushed;
        stats_.peak=std::max(stats_.peak,items_.size());
    }
    if(dropped) std::cerr << "[Audio queue dropped #" << dropped_sequence << "] replaced_oldest\n";

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
    ++stats_.popped;

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

AudioQueueStats AudioBufferQueue::stats() const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto copy=stats_;copy.dropped=dropped_;copy.pending=items_.size();return copy;
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

## 操作 15：src/audio/tts_service.cpp

SHA256：`26bb0f1213224b72c9cf869d396d7b1d2e7c2dbef9d533a432d991b28dd08abb`；314 行。

```cpp

#include "audio/tts_service.h"
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <exception>
#include <memory>
#include <string>
#include <vector>

#include <unistd.h>

TTSService::~TTSService()
{
    shutdown();
}

bool TTSService::initialize(
    const std::string& model_dir,
    std::string& error,
    std::int32_t num_threads,
    std::int32_t speaker_id)
{
    shutdown();
    error.clear();

    if (num_threads < 1 || num_threads > 8)
    {
        error = "num_threads must be in [1, 8]";
        return false;
    }

    if (speaker_id < 0)
    {
        error = "speaker_id must be non-negative";
        return false;
    }

    // 根据模型目录名称区分当前两类模型。
    // 后续系统集成时可替换为显式配置枚举。
    const bool is_kokoro =
        model_dir.find("kokoro") != std::string::npos;

    const std::string model =
        model_dir + "/model.onnx";

    const std::string tokens =
        model_dir + "/tokens.txt";

    std::vector<std::string> required{
        model, tokens
    };

    // 这些字符串必须活到 CreateOfflineTts 返回。
    std::string voices;
    std::string data_dir;
    std::string lexicons;

    std::string vits_lexicon;
    std::string rule_fsts;

    SherpaOnnxOfflineTtsConfig cfg{};

    cfg.model.num_threads = num_threads;
    cfg.model.provider = "cpu";
    cfg.model.debug = 0;
    cfg.max_num_sentences = 1;
    cfg.silence_scale = 0.2f;

    if (is_kokoro)
    {
        // Kokoro v1.1 模型文件。
        voices = model_dir + "/voices.bin";

        data_dir =
            model_dir + "/espeak-ng-data";

        const std::string lexicon_en =
            model_dir + "/lexicon-us-en.txt";

        const std::string lexicon_zh =
            model_dir + "/lexicon-zh.txt";

        required.push_back(voices);
        required.push_back(lexicon_en);
        required.push_back(lexicon_zh);

        // 词典之间使用英文逗号分隔。
        lexicons = lexicon_en + "," + lexicon_zh;

        cfg.model.kokoro.model = model.c_str();
        cfg.model.kokoro.voices = voices.c_str();
        cfg.model.kokoro.tokens = tokens.c_str();

        cfg.model.kokoro.data_dir =
            data_dir.c_str();

        cfg.model.kokoro.lexicon =
            lexicons.c_str();
    }
    else
    {
        // 保留先前已经测试成功的 MeloTTS 配置。
        vits_lexicon =
            model_dir + "/lexicon.txt";

        const std::string phone =
            model_dir + "/phone.fst";

        const std::string date =
            model_dir + "/date.fst";

        const std::string number =
            model_dir + "/number.fst";

        const std::string heteronym =
            model_dir + "/new_heteronym.fst";

        required.push_back(vits_lexicon);
        required.push_back(phone);
        required.push_back(date);
        required.push_back(number);
        required.push_back(heteronym);

        rule_fsts =
            phone + "," +
            date + "," +
            number + "," +
            heteronym;

        cfg.model.vits.model = model.c_str();

        cfg.model.vits.lexicon =
            vits_lexicon.c_str();

        cfg.model.vits.tokens = tokens.c_str();

        cfg.model.vits.noise_scale = 0.667f;
        cfg.model.vits.noise_scale_w = 0.8f;
        cfg.model.vits.length_scale = 1.0f;

        cfg.rule_fsts = rule_fsts.c_str();
    }

    // 检查所有需要的文件。
    for (const auto& path : required)
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            error = "Cannot read TTS file: " + path;
            return false;
        }
    }

    // Kokoro 英文前端数据目录必须存在。
    if (is_kokoro &&
        ::access(data_dir.c_str(), F_OK) != 0)
    {
        error =
            "Cannot find espeak data directory: " +
            data_dir;

        return false;
    }

    const SherpaOnnxOfflineTts* new_tts =
        SherpaOnnxCreateOfflineTts(&cfg);

    if (new_tts == nullptr)
    {
        error =
            "SherpaOnnxCreateOfflineTts returned null";
        return false;
    }

    // 加载成功后，检查说话人编号是否合法。
    const std::int32_t speakers =
        SherpaOnnxOfflineTtsNumSpeakers(new_tts);

    if (speaker_id >= speakers)
    {
        error =
            "Invalid speaker_id=" +
            std::to_string(speaker_id) +
            ", speakers=" +
            std::to_string(speakers);

        SherpaOnnxDestroyOfflineTts(new_tts);
        return false;
    }

    tts_ = new_tts;
    speaker_id_ = speaker_id;

    return true;
}

bool TTSService::synthesize(
    const std::string& text,
    TTSAudio& output,
    std::string& error)
{
    output = TTSAudio{};
    error.clear();

    if (tts_ == nullptr)
    {
        error = "TTSService is not initialized";
        return false;
    }

    if (text.empty())
    {
        error = "Input text is empty";
        return false;
    }

    SherpaOnnxGenerationConfig gen{};

    // 关键：使用初始化时选定的说话人。
    gen.sid = speaker_id_;

    gen.speed = 1.0f;
    gen.silence_scale = 0.2f;

    using AudioDeleter = decltype(
        &SherpaOnnxDestroyOfflineTtsGeneratedAudio
    );

    using AudioOwner = std::unique_ptr<
        const SherpaOnnxGeneratedAudio,
        AudioDeleter
    >;

    const auto start =
        std::chrono::steady_clock::now();

    // 真正执行 ONNX TTS 推理。
    AudioOwner audio(
        SherpaOnnxOfflineTtsGenerateWithConfig(
            tts_,
            text.c_str(),
            &gen,
            nullptr,
            nullptr
        ),
        &SherpaOnnxDestroyOfflineTtsGeneratedAudio
    );

    const auto finish =
        std::chrono::steady_clock::now();

    if (!audio ||
        !audio->samples ||
        audio->n <= 0 ||
        audio->sample_rate <= 0)
    {
        error =
            "TTS generation returned invalid audio";
        return false;
    }

    try
    {
        // 复制 SDK PCM 到 C++ 自有缓冲区。
        output.samples.assign(
            audio->samples,
            audio->samples + audio->n
        );
    }
    catch (const std::exception& e)
    {
        error =
            std::string("PCM copy failed: ") +
            e.what();

        return false;
    }

    output.sample_rate = audio->sample_rate;

    output.synthesis_ms =
        std::chrono::duration<double, std::milli>(
            finish - start
        ).count();

    // audio 离开作用域时自动调用 SDK 删除器。
    return true;
}

void TTSService::shutdown() noexcept
{
    if (tts_ != nullptr)
    {
        SherpaOnnxDestroyOfflineTts(tts_);
        tts_ = nullptr;
    }

    speaker_id_ = 0;
}

std::int32_t TTSService::sampleRate() const noexcept
{
    return tts_
        ? SherpaOnnxOfflineTtsSampleRate(tts_)
        : 0;
}

std::int32_t TTSService::numSpeakers() const noexcept
{
    return tts_
        ? SherpaOnnxOfflineTtsNumSpeakers(tts_)
        : 0;
}
```

## 操作 16：src/audio/tts_smoke.cpp

SHA256：`40589cab7c13bd0208ff0f2b7d00ab24eaf1edbfed0ee34c47f05ed947dab650`；183 行。

```cpp

#include "audio/tts_service.h"
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

static bool parseInteger(
    const char* raw,
    std::int32_t minimum,
    std::int32_t maximum,
    std::int32_t& result)
{
    try
    {
        const std::string value(raw);
        std::size_t used = 0;

        const long parsed = std::stol(value, &used);

        if (used != value.size() ||
            parsed < minimum ||
            parsed > maximum)
        {
            return false;
        }

        result = static_cast<std::int32_t>(parsed);
        return true;
    }
    catch (const std::exception&)
    {
        return false;
    }
}

int main(int argc, char** argv)
{
    if (argc < 4 || argc > 6)
    {
        std::cerr
            << "Usage: tts_smoke "
            << "<model_dir> <output.wav> <text> "
            << "[threads=2] [speaker_id=0]\n";

        return 2;
    }

    const std::string model_dir(argv[1]);
    const std::string wav_path(argv[2]);
    const std::string text(argv[3]);

    std::int32_t threads = 2;
    std::int32_t speaker_id = 0;

    if (argc >= 5 &&
        !parseInteger(argv[4], 1, 8, threads))
    {
        std::cerr << "Invalid threads\n";
        return 2;
    }

    if (argc >= 6 &&
        !parseInteger(argv[5], 0, 10000, speaker_id))
    {
        std::cerr << "Invalid speaker_id\n";
        return 2;
    }

    TTSService tts;
    std::string error;

    std::cout
        << "[Init] Loading TTS model...\n"
        << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            speaker_id))
    {
        std::cerr
            << "[Init] FAIL: " << error << '\n';

        return 1;
    }

    const auto init_end =
        std::chrono::steady_clock::now();

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            init_end - init_start
        ).count();

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Init] OK"
        << " time_ms=" << init_ms
        << " sample_rate=" << tts.sampleRate()
        << " speakers=" << tts.numSpeakers()
        << " sid=" << tts.speakerId()
        << '\n';

    TTSAudio audio;

    std::cout
        << "[TTS] text=" << text << '\n'
        << std::flush;

    if (!tts.synthesize(text, audio, error))
    {
        std::cerr
            << "[TTS] FAIL: " << error << '\n';

        return 1;
    }

    if (audio.sample_rate <= 0 ||
        audio.samples.empty())
    {
        std::cerr << "[TTS] Invalid PCM data\n";
        return 1;
    }

    const double audio_seconds =
        static_cast<double>(audio.samples.size()) /
        audio.sample_rate;

    const double rtf =
        (audio.synthesis_ms / 1000.0) /
        audio_seconds;

    std::cout
        << "[TTS] sample_count="
        << audio.samples.size()
        << " sample_rate=" << audio.sample_rate
        << " audio_sec=" << audio_seconds
        << " synth_ms=" << audio.synthesis_ms
        << " RTF=" << rtf
        << '\n';

    if (audio.samples.size() >
        static_cast<std::size_t>(
            std::numeric_limits<std::int32_t>::max()))
    {
        std::cerr << "[WAV] Too many samples\n";
        return 1;
    }

    const int ok = SherpaOnnxWriteWave(
        audio.samples.data(),
        static_cast<std::int32_t>(
            audio.samples.size()
        ),
        audio.sample_rate,
        wav_path.c_str()
    );

    if (ok != 1)
    {
        std::cerr
            << "[WAV] FAIL: " << wav_path << '\n';

        return 1;
    }

    std::cout
        << "[WAV] " << wav_path << '\n'
        << "PASS\n";

    return 0;
}
```

## 操作 17：src/audio/tts_worker.cpp

SHA256：`d954d44cd619fdfc6c7c05086cb5304aec87f246688b2cd6530cf8efa493c254`；325 行。

```cpp

#include "audio/tts_worker.h"

#include <exception>
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <utility>

TTSWorker::TTSWorker(
    TTSService& tts,
    AlsaPlaybackService& playback,
    std::size_t capacity)
    : tts_(tts),
      playback_(playback),
      capacity_(capacity)
{
    if (capacity_ == 0)
    {
        throw std::invalid_argument(
            "TTSWorker capacity must be > 0"
        );
    }
}

TTSWorker::~TTSWorker()
{
    requestStop();
    join();
}

bool TTSWorker::start(std::string& error)
{
    std::lock_guard<std::mutex> lock(mutex_);
    error.clear();

    if (started_ || stop_requested_)
    {
        error =
            "TTSWorker can only be started once";
        return false;
    }

    // 两个 Service 必须事先初始化。
    if (!tts_.ready() || !playback_.ready())
    {
        error =
            "Initialize TTSService and ALSA Playback "
            "before starting TTSWorker";
        return false;
    }

    try
    {
        // 启动 TTSWorker::run() 工作线程。
        thread_ = std::thread(
            &TTSWorker::run,
            this
        );

        started_ = true;
        ++stats_.generation;
    }
    catch (const std::exception& e)
    {
        error =
            std::string(
                "TTSWorker thread creation failed: "
            ) + e.what();

        return false;
    }

    return true;
}

TTSSubmitStatus TTSWorker::submit(
    std::uint64_t id,
    std::string text,
    TTSWorkerDone on_done,
    TaskOptions options)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
        {
            ++stats_.rejected_stopped;
            return TTSSubmitStatus::NotRunning;
        }

        if (pending_.size() >= capacity_)
        {
            ++rejected_;
            ++stats_.rejected_full;
            return TTSSubmitStatus::QueueFull;
        }

        Task task;
        task.id = id;
        task.text = std::move(text);
        task.on_done = std::move(on_done);
        task.options = std::move(options);

        task.enqueued_at =
            std::chrono::steady_clock::now();

        pending_.push_back(std::move(task));
        ++stats_.accepted;
        stats_.peak_depth = std::max(stats_.peak_depth, pending_.size());
    }

    // 通知一个等待中的消费者线程。
    cv_.notify_one();

    return TTSSubmitStatus::Accepted;
}

void TTSWorker::requestStop(StopMode mode) noexcept
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!stop_requested_ || mode == StopMode::CancelPending) stop_mode_ = mode;
        stop_requested_ = true;
    }

    // 唤醒线程，让它处理停止请求。
    cv_.notify_all();
}

void TTSWorker::join()
{
    if (thread_.joinable())
    {
        thread_.join();
    }
}

std::size_t TTSWorker::pendingCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return pending_.size();
}

std::size_t TTSWorker::rejectedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return rejected_;
}

void TTSWorker::run()
{
    for (;;)
    {
        Task task;
        bool cancelled = false;

        {
            std::unique_lock<std::mutex> lock(mutex_);

            // 没有任务时休眠，不进行忙轮询。
            cv_.wait(lock, [this] {
                return stop_requested_ ||
                       !pending_.empty();
            });

            // 队列清空且要求停止时，退出线程。
            if (pending_.empty() && stop_requested_)
            {
                return;
            }

            // FIFO：取出队首任务。
            task = std::move(pending_.front());
            pending_.pop_front();

            // 停止请求到来后，
            // 尚未开始的排队任务转为取消结果。
            cancelled = stop_requested_ && stop_mode_ == StopMode::CancelPending;
            stats_.active = 1;
        }

        const auto begin = std::chrono::steady_clock::now();
        const double waited = std::chrono::duration<double,std::milli>(begin-task.enqueued_at).count();
        TTSWorkerResult result;
        result.disposition = task.options.disposition(task.enqueued_at, begin, cancelled);
        const auto disposition = result.disposition;
        const double queue_wait_ms = disposition == TaskDisposition::Cancelled ? -1.0 : waited;
        if (disposition != TaskDisposition::Completed)
        {
            result.error_message = std::string("TTS task ") + dispositionName(disposition);
            std::cerr << "[TTS " << dispositionName(disposition) << " #" << task.id << "] queue_ms=" << waited << '\n';
        }
        else
        {
            { std::lock_guard<std::mutex> lock(mutex_); ++stats_.started; }
            try
            {
                TTSAudio audio;
                std::string error;

                // 1. 在工作线程中执行 TTS。
                if (!tts_.synthesize(
                        task.text, audio, error))
                {
                    result.error_message =
                        "TTS synthesize: " + error;
                }
                else if (
                    audio.sample_rate <= 0 ||
                    audio.samples.empty())
                {
                    result.error_message =
                        "TTS returned invalid PCM";
                }
                else
                {
                    result.synthesis_ms =
                        audio.synthesis_ms;

                    result.sample_rate =
                        audio.sample_rate;

                    result.audio_seconds =
                        static_cast<double>(
                            audio.samples.size()
                        ) / audio.sample_rate;

                    // 记录本次播放前的 XRUN 总数。
                    const std::uint64_t xruns_before =
                        playback_.xrunCount();

                    const auto play_start =
                        std::chrono::steady_clock::now();

                    // 2. 在同一工作线程中播放 PCM。
                    const bool played = playback_.play(
                        audio.samples.data(),
                        audio.samples.size(),
                        error
                    );

                    const auto play_end =
                        std::chrono::steady_clock::now();

                    result.playback_ms =
                        std::chrono::duration<
                            double, std::milli
                        >(
                            play_end - play_start
                        ).count();

                    result.xrun_count =
                        playback_.xrunCount() -
                        xruns_before;

                    if (!played)
                    {
                        result.error_message =
                            "ALSA playback: " + error;
                    }
                    else if (result.xrun_count != 0)
                    {
                        result.error_message =
                            "ALSA detected XRUN";
                    }
                    else
                    {
                        result.success = true;
                    }
                }
            }
            catch (const std::exception& e)
            {
                result.error_message =
                    std::string(
                        "TTSWorker exception: "
                    ) + e.what();
            }
            catch (...)
            {
                result.error_message =
                    "TTSWorker: unknown exception";
            }
        }

        const double service = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
        bool callback_failed = false;
        if (task.on_done)
        {
            try { task.on_done(task.id, result, queue_wait_ms); }
            catch (...) { callback_failed=true; std::cerr << "[TTS callback error #" << task.id << "]\n"; }
        }
        const bool failed = disposition == TaskDisposition::Completed && !result.success;
        task = Task{}; // release captured admission tickets outside the queue lock
        {
            std::lock_guard<std::mutex> lock(mutex_);
            ++stats_.completed; stats_.active=0; stats_.failed+=failed;
            stats_.cancelled+=disposition==TaskDisposition::Cancelled;
            stats_.expired+=disposition==TaskDisposition::Expired;
            stats_.callback_errors+=callback_failed;
            stats_.queue_wait_sum_ms+=waited; stats_.queue_wait_max_ms=std::max(stats_.queue_wait_max_ms,waited);
            stats_.service_sum_ms+=service;
        }
        cv_.notify_all();
    }
}

bool TTSWorker::restart(std::string& error) {
    { std::lock_guard<std::mutex> lock(mutex_);
      if (!started_ || !stop_requested_ || thread_.joinable() || !pending_.empty()) { error="restart requires stopped and joined TTSWorker"; return false; }
      started_=false; stop_requested_=false; rejected_=0;
      const auto generation=stats_.generation; stats_={}; stats_.generation=generation; }
    return start(error);
}
WorkerStats TTSWorker::stats() const {
    std::lock_guard<std::mutex> lock(mutex_); auto copy=stats_; copy.pending=pending_.size(); return copy;
}
bool TTSWorker::waitIdleFor(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    return cv_.wait_for(lock,timeout,[&]{return pending_.empty() && stats_.active==0;});
}
```

## 操作 18：tests/async_pipeline_tests.cpp

SHA256：`7b183ed3b10fe382f83d0622774acdcb37ff49a89832b0be16206c4e58760de2`；128 行。

```cpp
#include "ai/llm_worker.h"
#include "app/pipeline_admission.h"
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/tts_worker.h"
#include <atomic>
#include <future>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace std::chrono_literals;
namespace {
void check(bool value,const char* message){if(!value)throw std::runtime_error(message);}
struct Gate {
    std::promise<void> entered,release;
    std::shared_future<void> ready=entered.get_future().share(),go=release.get_future().share();
    bool opened=false;
    void open(){if(!opened){opened=true;release.set_value();}}
};
struct OpenOnExit {Gate& gate;~OpenOnExit(){gate.open();}};
InferenceResult answer(){InferenceResult r;r.success=true;r.text="fake answer";return r;}
std::atomic<int> recognizes{0};
std::function<void()> synth_hook;
void testASRContinues() {
    recognizes=0;Gate gate;std::mutex output,done_mutex;std::vector<std::uint64_t> done;
    ASRService asr;AudioBufferQueue queue(4);InferenceWorker worker(4);std::string error;
    check(worker.start(error),"ASR test worker start");OpenOnExit unblock{gate};
    std::atomic<int> submitted{0};std::atomic<int> executed{0};
    ASRWorker consumer(queue,asr,output,[&](const std::string& text){
        const auto id=static_cast<std::uint64_t>(std::stoi(text));
        const auto caller=std::this_thread::get_id();
        auto status=worker.submitTask(id,[&,id,caller](const LLMStreamCallback&){
            check(std::this_thread::get_id()!=caller,"inference ran on ASR thread");
            if(id==1){gate.entered.set_value();gate.go.wait();}
            ++executed;return answer();
        },{},[&](std::uint64_t id,const InferenceResult& r,double){
            check(r.success,"alternating task failed");std::lock_guard<std::mutex> lock(done_mutex);done.push_back(id);
        });
        check(status==LLMSubmitStatus::Accepted,"alternating submit");++submitted;
    });
    for(int id=1;id<=3;++id){AudioSegment s;s.sequence=id;s.samples.assign(160,static_cast<float>(id));queue.push(std::move(s));}
    queue.close();consumer.start();
    check(gate.ready.wait_for(2s)==std::future_status::ready,"first fake VLM not executing");
    const auto deadline=std::chrono::steady_clock::now()+2s;
    while(submitted.load()!=3 && std::chrono::steady_clock::now()<deadline)std::this_thread::yield();
    const bool continued=submitted==3 && recognizes==3 && executed==0;
    consumer.join();gate.open();worker.requestStop(StopMode::Drain);worker.join();
    check(continued,"ASR did not advance while first VLM blocked");
    check(consumer.ok() && done==std::vector<std::uint64_t>({1,2,3}),"TEXT/VISION FIFO/ASR completion");
}
void testBoundCancelExpireRestart() {
    Gate gate;std::vector<TaskDisposition> results;std::mutex mutex;InferenceWorker worker(1);std::string error;
    check(worker.start(error),"start bounded");OpenOnExit unblock{gate};
    auto done=[&](std::uint64_t,const InferenceResult& r,double){std::lock_guard<std::mutex> lock(mutex);results.push_back(r.disposition);};
    worker.submitTask(1,[&](const LLMStreamCallback&){gate.entered.set_value();gate.go.wait();return answer();},{},done);
    check(gate.ready.wait_for(2s)==std::future_status::ready,"active gate");
    TaskOptions options;options.cancelled=std::make_shared<std::atomic<bool>>(false);
    check(worker.submitTask(2,[](const LLMStreamCallback&){throw std::runtime_error("cancelled body executed");return answer();},{},done,options)==LLMSubmitStatus::Accepted,"pending submit");
    check(worker.submitTask(3,[](const LLMStreamCallback&){return answer();})==LLMSubmitStatus::QueueFull,"full not rejected");
    options.cancelled->store(true);gate.open();check(worker.waitIdleFor(2s),"cancel idle");
    TaskOptions expired;expired.deadline=TaskOptions::Clock::now()-1ms;
    worker.submitTask(4,[](const LLMStreamCallback&){throw std::runtime_error("expired body executed");return answer();},{},done,expired);
    check(worker.waitIdleFor(2s),"expiry idle");worker.requestStop(StopMode::Drain);worker.join();
    auto stats=worker.stats();check(stats.started==1 && stats.cancelled==1 && stats.expired==1 && stats.rejected_full==1 && stats.completed==3,"terminal stats");
    check(results==std::vector<TaskDisposition>({TaskDisposition::Completed,TaskDisposition::Cancelled,TaskDisposition::Expired}),"terminal callbacks");
    check(!worker.start(error),"implicit restart contract changed");check(worker.restart(error),"explicit restart failed");
    worker.submitTask(5,[](const LLMStreamCallback&){return answer();},{},[](std::uint64_t,const InferenceResult&,double){throw 1;});
    check(worker.waitIdleFor(2s),"throwing done stranded owner");worker.requestStop();worker.join();
    check(worker.stats().generation==2 && worker.stats().callback_errors==1,"restart/error publication");
}
void testStopModes() {
    for(auto mode:{StopMode::Drain,StopMode::CancelPending}) {
        Gate gate;InferenceWorker worker(1);std::string error;std::atomic<int> executed{0};
        check(worker.start(error),"stop worker start");OpenOnExit unblock{gate};
        worker.submitTask(1,[&](const LLMStreamCallback&){gate.entered.set_value();gate.go.wait();++executed;return answer();});
        check(gate.ready.wait_for(2s)==std::future_status::ready,"stop active gate");
        worker.submitTask(2,[&](const LLMStreamCallback&){++executed;return answer();});
        worker.requestStop(mode);check(worker.submitTask(3,[](const LLMStreamCallback&){return answer();})==LLMSubmitStatus::NotRunning,"accept after close");
        gate.open();worker.join();check(executed==(mode==StopMode::Drain?2:1),"drain/cancel semantics");
        check(worker.stats().completed==2,"lost terminal count");
    }
}
void testAdmission() {
    PipelineAdmission admission(2);
    auto first=admission.tryAcquire(1,1s),second=admission.tryAcquire(2,1s);
    check(first && second && !admission.tryAcquire(3,1s),"pipeline capacity");
    check(admission.cancel(2) && second->cancelled(),"cancel by id");first.reset();
    auto next=admission.tryAcquire(3,1s);check(bool(next),"credit not recovered");
    admission.close(true);check(next->cancelled() && !admission.tryAcquire(4,1s),"close/cancel flags");
    second.reset();next.reset();check(admission.stats().inflight==0 && admission.stats().peak==2,"ticket lifetime");
    // Race final ticket release against cancellation; cancellation map holds flags, not tickets.
    for(int i=0;i<200;++i){PipelineAdmission a(1);auto ticket=a.tryAcquire(1,1s);std::thread close([&]{a.close(true);});ticket.reset();close.join();check(a.stats().inflight==0,"release/cancel deadlock");}
}
void testTTS() {
    TTSService tts;AlsaPlaybackService playback;std::string error;
    check(tts.initialize("fake",error) && playback.open("fake",16000,error),"fake services init");
    Gate gate;synth_hook=[&]{gate.entered.set_value();gate.go.wait();};
    TTSWorker worker(tts,playback,1);check(worker.start(error),"tts start");OpenOnExit unblock{gate};
    worker.submit(1,"first");check(gate.ready.wait_for(2s)==std::future_status::ready,"tts synth active");
    TaskOptions expired;expired.deadline=TaskOptions::Clock::now()-1ms;
    check(worker.submit(2,"stale",{},expired)==TTSSubmitStatus::Accepted,"tts pending");
    check(worker.submit(3,"full")==TTSSubmitStatus::QueueFull,"tts bound");
    gate.open();check(worker.waitIdleFor(2s),"tts drain");worker.requestStop(StopMode::Drain);worker.join();
    check(worker.stats().started==1 && worker.stats().expired==1 && worker.stats().completed==2,"tts expiry accounting");
    synth_hook={};check(worker.restart(error),"tts restart");
    worker.submit(4,"again",[](std::uint64_t,const TTSWorkerResult&,double){throw 1;});
    check(worker.waitIdleFor(2s),"tts callback failure idle");worker.requestStop();worker.join();
    check(worker.stats().generation==2 && worker.stats().callback_errors==1,"tts callback errors");
}
} // namespace

// Test-only service implementations: no SDK, ALSA, model or device is called.
ASRService::~ASRService()=default;
bool ASRService::recognize(const std::vector<float>& samples,std::string& text,double& latency,std::string& error){++recognizes;text=std::to_string(static_cast<int>(samples.at(0)));latency=0;error.clear();return true;}
struct SherpaOnnxOfflineTts {};
struct _snd_pcm {};
TTSService::~TTSService(){shutdown();}
bool TTSService::initialize(const std::string&,std::string&,std::int32_t,std::int32_t){static SherpaOnnxOfflineTts fake;tts_=&fake;return true;}
bool TTSService::synthesize(const std::string&,TTSAudio& output,std::string&){if(synth_hook)synth_hook();output.sample_rate=16000;output.samples.assign(160,0);return true;}
void TTSService::shutdown() noexcept {tts_=nullptr;}
AlsaPlaybackService::~AlsaPlaybackService(){close();}
bool AlsaPlaybackService::open(const std::string&,std::int32_t,std::string&){static _snd_pcm fake;pcm_=&fake;return true;}
bool AlsaPlaybackService::play(const float*,std::size_t,std::string&){return true;}
void AlsaPlaybackService::close() noexcept {pcm_=nullptr;}
int main() try {
    testASRContinues();testBoundCancelExpireRestart();testStopModes();testAdmission();testTTS();
    std::cout<<"PASS deterministic async pipeline: ASR progression, alternating FIFO, overload, cancel/expiry, restart, callback failures, ticket races, TTS. Fake services only.\n";return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
```

## 操作 19：tests/stage5_02_npu_probe.cpp

SHA256：`e4e18c2454d0dc006a0886777a6152e776b75e43a008145167068d69d89b22ca`；84 行。

```cpp
#include "ai/rk_backends.h"
#include "ai/llm_engine.h"
#include "ai/vlm_engine.h"
#include "video/camera_service.h"
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>

// Real SDK diagnostic, never a mock benchmark or an NPU utilization measurement.
int main(int argc, char** argv) try
{
    if (argc != 5) return 2;
    using Clock=std::chrono::steady_clock;
    const auto origin=Clock::now();
    auto ms=[&](Clock::time_point t) { return std::chrono::duration<double,std::milli>(t-origin).count(); };
    LLMEngine llm(std::make_unique<RKLLMBackend>());
    VLMEngine vlm(std::make_unique<RK3576VLMBackend>());
    std::string error;
    if (!llm.initialize(BackendConfig{argv[1],{}},error)) { std::cerr<<error<<'\n';return 1; }
    LatestFrameBuffer frames;
    constexpr std::uint32_t nv12=std::uint32_t('N')|(std::uint32_t('V')<<8)|(std::uint32_t('1')<<16)|(std::uint32_t('2')<<24);
    CameraService camera(argv[4],3840,2160,nv12,frames);
    if (!camera.start()) { std::cerr<<camera.stats().last_error<<'\n';return 1; }
    if (!vlm.initialize(BackendConfig{argv[2],argv[3]},error)) { std::cerr<<error<<'\n';return 1; }
    const auto deadline=Clock::now()+std::chrono::seconds(3);
    while (!frames.getLatest() && Clock::now()<deadline) std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if (!frames.getLatest()) return 1;
    unsigned int successful=0;
    for (bool parallel : {false,true})
    {
        for (int round=0;round<3;++round)
        {
            InferenceResult text,vision;
            double tb=0,te=0,vb=0,ve=0;
            auto run_text=[&] {
                tb=ms(Clock::now());
                text=llm.infer("What is one plus one? Answer in one short sentence.");
                te=ms(Clock::now());
            };
            std::cout<<"PROBE_BEGIN parallel="<<parallel<<" round="<<round<<'\n'<<std::flush;
            if (parallel)
            {
                std::mutex mutex;
                std::condition_variable cv;
                bool go=false;
                struct Joined { std::thread thread; ~Joined(){if(thread.joinable())thread.join();} } joined;
                joined.thread=std::thread([&] {
                    {std::unique_lock<std::mutex> lock(mutex);cv.wait(lock,[&]{return go;});}
                    run_text();
                });
                {std::lock_guard<std::mutex> lock(mutex);go=true;}
                cv.notify_one();
                vb=ms(Clock::now());
                vision=vlm.infer(frames.getLatest(),"What do you see? Answer briefly.");
                ve=ms(Clock::now());
                joined.thread.join();
            }
            else
            {
                run_text();
                vb=ms(Clock::now());
                vision=vlm.infer(frames.getLatest(),"What do you see? Answer briefly.");
                ve=ms(Clock::now());
            }
            const double overlap=std::max(0.0,std::min(te,ve)-std::max(tb,vb));
            std::cout<<"PROBE_RESULT parallel="<<parallel<<" round="<<round
                     <<" text_ok="<<text.success<<" vision_ok="<<vision.success
                     <<" text_ms="<<te-tb<<" vision_ms="<<ve-vb
                     <<" sdk_call_overlap_ms="<<overlap
                     <<" pair_ms="<<std::max(te,ve)-std::min(tb,vb)<<'\n'<<std::flush;
            if (!text.success) std::cerr<<"TEXT_ERROR "<<text.error_message<<'\n';
            if (!vision.success) std::cerr<<"VISION_ERROR "<<vision.error_message<<'\n';
            successful+=text.success && vision.success;
        }
    }
    camera.stop();vlm.shutdown();llm.shutdown();
    std::cout<<"PROBE_SUMMARY pairs="<<successful<<"/6\n";
    return successful==6?0:1;
}
catch(const std::exception& e){std::cerr<<"PROBE_FATAL "<<e.what()<<'\n';return 1;}
```

## 操作 20：tests/stage5_02_replay.tsv

SHA256：`5f072a66a072912f2765712c46b980929dafbf12f6149263c5e59b81e710c799`；4 行。

```text
0	前面有什么
1000	一加一等于几
2000	前面有什么
3000	一加一等于几
```

## 操作 21：tests/stage5_02_replay_pair.tsv

SHA256：`7079fcead7fc22ef0d5ee034be25974caa047ceb25187265e739f1901126f54c`；2 行。

```text
0	前面有什么
1000	一加一等于几
```

## 操作 22：tools/stage5_02_board_run.py

SHA256：`01da83e6b4eaca3b6ce3b0204ce7cbcb6ca354cff0de0077bc324e323410adc0`；195 行。

```python
#!/usr/bin/env python3
"""Stage 5.2 hardware/replay comparisons; explicit input mode and PID-safe timeout guards."""
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
    parser.add_argument('--variant',choices=('baseline','candidate'),default='candidate')
    parser.add_argument('--replay',action='store_true')
    parser.add_argument('--replay-source',choices=('four','pair'),default='four')
    parser.add_argument('--stop-mode',choices=('drain','cancel_pending'),default='drain')
    parser.add_argument('--tts-queue-ms',type=int,default=12000)
    parser.add_argument('--request-lifetime-ms',type=int,default=45000)
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
    report=ROOT/'reports/stage5_02_board'/args.name
    report.mkdir()
    before=fingerprint(); save(report/'stable_before.json',before)
    audio=discover_audio(); save(report/'audio_detection.json',audio)
    pre=devices(audio);save(report/'devices_before.json',pre)
    assert pre['clear'],'target device occupied'
    assert os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize>=500*1024**2
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)])})
    envout=subprocess.check_output(['bash','-c','source "$1/tools/stage5_board_paths.sh"; env -0','phase3',str(ROOT)],timeout=15)
    env=dict(part.decode().split('=',1) for part in envout.split(b'\0') if b'=' in part)
    assert 1<=args.tts_queue_ms<=60000 and 1<=args.request_lifetime_ms<=300000
    env['STAGE5_STOP_MODE']=args.stop_mode
    env['STAGE5_TTS_QUEUE_MS']=str(args.tts_queue_ms)
    env['STAGE5_REQUEST_LIFETIME_MS']=str(args.request_lifetime_ms)
    if args.replay:
        replay=ROOT/('tests/stage5_02_replay.tsv' if args.replay_source=='four' else 'tests/stage5_02_replay_pair.tsv')
        env['STAGE5_REPLAY_FILE']=str(replay)
        save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'text':replay.read_text()})
    else: env.pop('STAGE5_REPLAY_FILE',None)
    base='/home/cat/projects/RK3576'
    exe=ROOT/('build/stage5_02_baseline/asr_llm_tts_smoke' if args.variant=='baseline' else 'build/stage5_02_board/asr_llm_tts_smoke')
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
    input_closed_at=None
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
                    milestone=('[Shutdown] replay input closed' in s or '[Shutdown] capture/VAD and ASR joined' in s)
                    if milestone and input_closed_at is None:
                        input_closed_at=time.monotonic()
                        eventlog.write(json.dumps({'event':'input_closed','elapsed':input_closed_at-start})+'\n');eventlog.flush()

                    text_done |= bool(re.search(r'(?<!VISION )\[TTS done .*success=true',s))
                    vision_done |= '[VISION TTS done ' in s and 'success=true' in s
                    found=(args.trigger=='init' and '[Init] Loading RKLLM' in s or args.trigger=='ready' and ('[Listen]' in s or '[Replay ready]' in s) or args.trigger=='llm' and '[ASR->LLM #' in s or args.trigger=='vision' and '[ASR->VISION #' in s or args.trigger=='tts' and '[ALSA write]' in s or args.trigger=='both_done' and text_done and vision_done)
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
             'duration_seconds':ended-start,'input_closed_to_exit_seconds':None if input_closed_at is None else ended-input_closed_at,'signal_to_exit_seconds':None if sent_at is None else ended-sent_at,
             'timing_scope':'child exit/output EOF, excludes subsequent device/fingerprint queries',
             'process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':before==after,
             'shutdown_complete_marker':'[Shutdown] complete' in terminal,'program_PASS':bool(re.search(r'^PASS\s*$',terminal,re.M)),
             'text_tts_completed':text_done,'vision_tts_completed':vision_done,'user_audible_confirmation':None,'variant':args.variant,'input_mode':'controlled_replay_no_microphone_ASR' if args.replay else 'real_microphone_ASR','stop_mode':args.stop_mode}
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'dmesg':query(['dmesg','--ctime'])})
    save(report/'result.json',summary)
    print('PHASE3_RUN_RESULT',json.dumps(summary),flush=True)
    print('REMOTE_REPORT',report,flush=True)
    return 0 # transport succeeded; child return code remains explicitly recorded above


if __name__=='__main__':
    raise SystemExit(main())
```

## 操作 23：tools/stage5_02_collect.py

SHA256：`f907d6359526f609f0f37112c63a99346286cfe89e7b7e884ad3b86f36e5e09b`；38 行。

```python
#!/usr/bin/env python3
"""Read only the isolated Stage 5.2 reports, preserving raw logs locally."""
from datetime import datetime
import hashlib,json,tarfile
from pathlib import Path,PurePosixPath
import stage5_phase2_deploy as transport

def main():
 report=transport.ROOT/'reports/stage5_02_board'/('collected_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
 report.mkdir()
 payload=b'''from pathlib import Path
import sys,tarfile
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
selected=root/'reports/stage5_02_board'
assert selected.is_dir() and not root.is_symlink()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as package:
 for p in sorted(selected.rglob('*')):
  if p.is_file() and not p.is_symlink():
   assert p.resolve().is_relative_to(selected) and p.stat().st_size<20*1024**2
   package.add(p,arcname=str(p.relative_to(root)),recursive=False)
'''
 code=transport.run_step(report,'collection',transport.remote_command(),payload,120,binary=True)
 if code:return code
 destination=report/'files';destination.mkdir();manifest=[];total=0
 with tarfile.open(report/'collection.tgz','r:gz') as package:
  for item in package:
   relative=PurePosixPath(item.name)
   assert item.isfile() and not relative.is_absolute() and '..' not in relative.parts
   assert relative.parts[:2]==('reports','stage5_02_board') and item.size<20*1024**2
   total+=item.size;assert total<200*1024**2
   target=destination/Path(*relative.parts);assert target.resolve().is_relative_to(destination.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);content=package.extractfile(item).read()
   with target.open('xb') as output:output.write(content)
   manifest.append(dict(file=item.name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
 (report/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('COLLECTED',report,'files',len(manifest),'bytes',total)
 return 0
if __name__=='__main__':raise SystemExit(main())
```

## 操作 24：tools/stage5_02_export.py

SHA256：`b26d622fe28a98eee1b2d4a807f2912705fa0841bd6c370e1ecff109c27a848d`；60 行。

```python
#!/usr/bin/env python3
"""Export Stage 5.2 full current source, hashes and Git-format patch; no remote writes."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def main():
 before=ROOT/'backups/stage5_02_before';report=ROOT/'reports/stage5_02_local'
 baseline=json.loads((report/'baseline_manifest.json').read_text())
 assert all(sha(before/r['file'])==r['sha256'] for r in baseline),'baseline snapshot drift'
 paths={Path('CMakeLists.txt')}
 for directory in ['include','src','tests','tools','docs','config']:
  paths.update(p.relative_to(ROOT) for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.h','.cpp','.hpp','.cmake','.md','.py','.sh','.txt','.tsv','.ps1'})
 changed=sorted(p for p in paths if sha(before/p)!=sha(ROOT/p))
 source=[p for p in changed if p.parts[0]!='docs']
 appendix=['# 5.2 当前修改源码全文\n\n','由 `tools/stage5_02_export.py` 从真实文件生成。逐句语义解释见 [stage5_02_statement_notes.md](stage5_02_statement_notes.md)，架构与实测见 [stage5_02_async_pipeline.md](stage5_02_async_pipeline.md)。本附录不省略入口及测试，不代替板端版本哈希或执行证据。\n\n']
 for i,p in enumerate(source,1):
  lang='cmake' if p.name=='CMakeLists.txt' else {'.py':'python','.sh':'bash','.tsv':'text','.ps1':'powershell'}.get(p.suffix,'cpp')
  content=(ROOT/p).read_text(encoding='utf-8-sig')
  appendix.append(f'## 操作 {i}：{p.as_posix()}\n\nSHA256：`{sha(ROOT/p)}`；{len(content.splitlines())} 行。\n\n```{lang}\n{content.rstrip()}\n```\n\n')
 (ROOT/'docs/stage5_02_source_appendix.md').write_text(''.join(appendix),encoding='utf-8',newline='\n')
 changed=sorted(set(changed+[Path('docs/stage5_02_source_appendix.md')]))
 manifest=[dict(file=p.as_posix(),before_sha256=sha(before/p),after_sha256=sha(ROOT/p),status='modified' if (before/p).exists() else 'added') for p in changed]
 # Use real git diff --no-index, including byte-level line-ending changes.
 scratch=Path(tempfile.mkdtemp(prefix='stage5_02_diff_'));patch=[]
 for p in changed:
  a=scratch/'a'/p;b=scratch/'b'/p;b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,b)
  if (before/p).is_file():a.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before/p,a);old=(Path('a')/p).as_posix()
  else:old='/dev/null'
  command=['git','-c','core.quotepath=false','-c','core.autocrlf=false','diff','--no-index','--binary','--src-prefix=','--dst-prefix=',old,(Path('b')/p).as_posix()]
  result=subprocess.run(command,cwd=scratch,capture_output=True,timeout=30)
  assert result.returncode in (0,1),result.stderr
  content=result.stdout
  lines=content.splitlines(keepends=True)
  lines[0]=('diff --git a/'+p.as_posix()+' b/'+p.as_posix()+'\n').encode()
  content=b''.join(lines)
  patch.append(content)
 (report/'changes.patch').write_bytes(b''.join(patch))
 (report/'change_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Apply to exact baseline bytes in a new temporary tree, never to the real workspace.
 check=scratch/'apply';shutil.copytree(before,check)
 command=['git','-c','core.autocrlf=false','apply','--check',str(report/'changes.patch')]
 result=subprocess.run(command,cwd=check,capture_output=True,timeout=60)
 (report/'patch_check.json').write_text(json.dumps(dict(command=command,exit_code=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace')),indent=2))
 assert result.returncode==0,result.stderr.decode(errors='replace')
 applied=subprocess.run(['git','-c','core.autocrlf=false','apply',str(report/'changes.patch')],cwd=check,capture_output=True,timeout=60)
 verification={p.as_posix():sha(check/p)==sha(ROOT/p) for p in changed}
 (report/'patch_roundtrip.json').write_text(json.dumps(dict(exit_code=applied.returncode,all_bytes_match=all(verification.values()),files=verification,stderr=applied.stderr.decode(errors='replace')),indent=2))
 assert applied.returncode==0 and all(verification.values()),verification
 invariants=[]
 for name in ['src/ai/rkllm_backend.cpp','src/ai/rk3576_vlm_backend.cpp','src/video/video_capture.cpp','src/video/camera_service.cpp','src/audio/asr_service.cpp','src/audio/vad_audio_worker.cpp']:
  invariants.append(dict(file=name,before=sha(before/name),after=sha(ROOT/name),unchanged=sha(before/name)==sha(ROOT/name)))
 def signal_helper(path):
  text=path.read_text(encoding='utf-8');start=text.index('class StopSignals');return text[start:text.index('\n};',start)+3]
 signal_same=signal_helper(before/'src/audio/asr_llm_tts_smoke.cpp')==signal_helper(ROOT/'src/audio/asr_llm_tts_smoke.cpp')
 (report/'source_invariants.json').write_text(json.dumps(dict(checks=invariants,signal_helper_unchanged=signal_same,scope='Source equality only; not runtime evidence'),indent=2))
 assert signal_same and all(item['unchanged'] for item in invariants)
 print('EXPORTED',len(source),'source files;',len(manifest),'changes; patch check',result.returncode)
if __name__=='__main__':main()
```

## 操作 25：tools/stage5_02_performance.py

SHA256：`d1a4d99508efdc71b853d3e23dd8de3b21a1a3ae21d13d07b750174679aeedfd`；66 行。

```python
#!/usr/bin/env python3
"""Generate finite-sample performance tables from immutable Stage 5.2 evidence."""
from pathlib import Path
import json,re
from stage5_02_summarize import distribution,fields
ROOT=Path(__file__).resolve().parents[1]
def f(value):return '—' if value is None else f'{value:.3f}'
def main():
 data=json.loads((ROOT/'reports/stage5_02_board/metrics.json').read_text(encoding='utf-8'))
 evidence=ROOT/data['collection']/'files/reports/stage5_02_board';cases=data['cases']
 text=(evidence/'baseline_and_npu_probe/probe.stdout.log').read_text()
 npu=[fields(line) for line in text.splitlines() if line.startswith('PROBE_RESULT')]
 stats={}
 for mode in [0,1]:
  rows=[r for r in npu if r['parallel']==mode]
  stats[str(mode)]={key:distribution([r[key] for r in rows]) for key in ['text_ms','vision_ms','pair_ms','sdk_call_overlap_ms']}
 (ROOT/'reports/stage5_02_board/npu_metrics.json').write_text(json.dumps(dict(rounds=npu,stats=stats),indent=2)+'\n')
 out=['# 5.2 实测性能数据\n\n',
      '本表由 `tools/stage5_02_performance.py` 从采集的原始终端/JSON 生成。设备、模型、构建和限制见 [验收报告](stage5_02_board_acceptance.md)。日期 2026-10-17，RK3576 真机；Fake 测试不纳入这些性能数字。\n\n',
      '统计均为毫秒（吞吐表除外），P50/P95 使用 nearest-rank，n=2 的 P50 为较小值，n≤4 的 P95 常等于最大值。每个 case 仅运行一次、请求数很小，没有置信区间或生产尾延迟结论；频率、温度、图像和生成长度未严格固定。\n\n',
      '## 操作 1：NPU 实际 SDK 调用对照\n\n',
      '| 调用方式（每类 n=3） | 指标 | 平均 ms | P50 ms | P95 ms |\n|---|---|---:|---:|---:|\n']
 for mode,name in [('0','顺序'),('1','重叠')]:
  for key,label in [('text_ms','Qwen 调用'),('vision_ms','RKNN+SmolVLM2 调用'),('pair_ms','一对任务完成'),('sdk_call_overlap_ms','SDK 调用区间交集')]:
   d=stats[mode][key];out.append(f'| {name} | {label} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\n6/6 对成功。重叠未观察到崩溃，但 Qwen 调用变慢；区间交集不是 NPU 硬件利用率。统一消费者是响应可预测性的选择，不是“并行已经被证明不安全”的结论。\n\n',
       '## 操作 2：ASR 业务回调/受控提交阻塞\n\n',
       '| case | n | 平均 ms | P50 ms | P95 ms |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  d=c['dispatch_ms'];out.append(f'| {c["case"]} | {d["n"]} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\nbaseline 的 VISION 耗时落在调用者线程；candidate 的 VISION 工作落在推理 Worker。表中混合 TEXT/VISION；过载 case 的 n 包括被拒绝请求，应同时读接受率。受控文本模式测同一个生产回调，不测 ASR 模型；真实 microphone case 才包含 USB/VAD/SenseVoice。\n\n',
       '## 操作 3：各队列等待\n\n',
       '| case | 推理排队 n / 平均 / P50 / P95 ms | TTS 终态 n / 平均 / P50 / P95 ms |\n|---|---|---|\n']
 for c in cases:
  def ds(d):return f'{d["n"]} / {f(d["mean"])} / {f(d["p50"])} / {f(d["p95"])}'
  out.append(f'| {c["case"]} | {ds(c["inference_queue_ms"])} | {ds(c["tts_queue_ms_all_terminals"])} |\n')
 out+=['\nbaseline 推理队列 n 只包含异步 TEXT，VISION 直接同步执行，没有相应 queue_ms；不能把缺失数据当零后混平均。TTS 统计包括过期/取消的真实驻留；取消回调兼容值 -1 已用 `[TTS cancelled]` 的实际驻留代替。过期出队时检查，实际驻留可超过配置期限。\n\n',
       '## 操作 4：深度、接受/拒绝、成功率和完整交付\n\n',
       '| case | 推理峰值 / TTS 峰值 | 跨阶段峰值 | 推理成功/实际执行 | 播放/输入请求 | Admission 拒绝 | TTS 过期/取消 | 子进程码 |\n|---|---|---|---|---|---:|---|---:|\n']
 for c in cases:
  q=c['queues'];p=c['pipeline'];old=c['baseline_peaks']
  peaks=f'{q["inference"]["peak"]}/{q["tts"]["peak"]}' if q else f'{old["inference_peak"]}/{old["tts_peak"]}'
  credit=str(p['peak']) if p else '无跨阶段限制'
  reject=p['rejected'] if p else '不适用'
  terminal=f'{p["tts_expired"]}/{p["tts_cancelled"]}' if p else '无该策略'
  out.append(f'| {c["case"]} | {peaks} | {credit} | {c["ai_successful"]}/{c["ai_started"]} | {c["delivered"]}/{c["dispatch_count"]} | {reject} | {terminal} | {c["process"]["returncode"]} |\n')
 out+=['\nbaseline_replay_overload 另有 1 次 TTS 队列满拒绝，退出 1；其余子程序返回 0。candidate_cancel_active_vision 下游取消 1，不启动 TTS。不能把推理成功率当请求最终交付率；没有执行的请求不计进模型成功分母。音频队列两轮真实 microphone 均峰值 1、dropped 0。\n\n',
       '## 操作 5：有限批次吞吐和自然排空退出\n\n',
       '| case | ready 至退出 s | 成功推理 / s | 完成播放 / s | 输入关闭至退出 s |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  if c['post_ready_to_exit_seconds'] is None:continue
  out.append(f'| {c["case"]} | {f(c["post_ready_to_exit_seconds"])} | {f(c["inference_per_second_including_shutdown"])} | {f(c["delivered_per_second_including_shutdown"])} | {f(c["process"].get("input_closed_to_exit_seconds"))} |\n')
 out+=['\n吞吐分母包含 drain/退出；真实 microphone case 还包含等待用户和静音窗口，不能称持续最大吞吐。两请求 equal_work_pair 都接受并播放 2/2，TTL 放宽到 60 s 排队/120 s 生命周期以避免策略丢弃。源输入相同，但 VLM 分别生成12 与 17 个英文词，PCM 帧数 80696 与 107578，未保持计算工作量完全相同；candidate 的批次排空实际更慢，不能宣称端到端加速。其主要收益是 VISION 回调不再占用 ASR。\n\n',
       '## 操作 6：停止模式和资源采样\n\n',
       '| case | 信号 | 模式 | 信号至退出 s | 采样峰值 RSS KiB | 采样线程峰值 |\n|---|---|---|---:|---:|---:|\n']
 for c in cases:
  p=c['process'];out.append(f'| {c["case"]} | {p["sent_signal"] or "自然结束"} | {p["stop_mode"]} | {f(p["signal_to_exit_seconds"])} | {c["rss_peak_kib"]} | {c["thread_peak"]} |\n')
 out+=['\n信号延迟从 harness 发送时刻至子进程退出/输出 EOF，排除后续 fuser/指纹查询。Drain 与 CancelPending 完成工作量不同，不是同等计算加速。采样周期约 1 s，可能漏过短峰值；RSS 包含 SDK、模型映射和工作缓冲，不能当 C++ heap 泄漏大小。全部 case 无超时/强制终止且设备释放。长期稳定性留后续独立验收。\n\n',
       '## 操作 7：模型计算时间与局限\n\n',
       '| case | 成功 TTS n | 合成平均 ms | P50 ms | P95 ms |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  d=c['tts_synthesis_ms'];out.append(f'| {c["case"]} | {d["n"]} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\n回答文本长度、CPU 竞争和 Camera 场景不同，合成数值波动不能归因为异步化提升模型速度。本节未改变 Kokoro 模型或合成算法。5.4 再按固定语料、更多样本和统一时间链路分析计算性能。\n']
 (ROOT/'docs/stage5_02_performance.md').write_text(''.join(out),encoding='utf-8',newline='\n')
 print('Generated performance tables for',len(cases),'cases and',len(npu),'NPU pairs')
if __name__=='__main__':main()
```

## 操作 26：tools/stage5_02_prepare_replay.py

SHA256：`9dfb1ccce7904bf28e974141f6d2e144fdba72536aa3da9993d8f1c7e631db84`；106 行。

```python
#!/usr/bin/env python3
"""Add the same explicit replay/timer instrumentation to candidate and copied 5.1 entry.

Runs locally only. Baseline model algorithms, capacities and stop semantics are retained.
"""
from pathlib import Path
import difflib

ROOT=Path(__file__).resolve().parents[1]


def replay(s, candidate):
    s=s.replace('#include <chrono>','#include <chrono>\n#include <fstream>\n#include <sstream>\n#include <cstdlib>')
    begin=s.index('    try\n    {\n        // ASR',s.index('    const auto on_text ='))
    end=s.index('    asr.shutdown();',begin)
    normal=s[begin:end]
    s=s[:begin]+'''    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");
    const bool replay_mode=replay_path!=nullptr;
    if (replay_mode)
    {
        std::ifstream input(replay_path);
        if (!input) throw std::runtime_error("Cannot open replay input");
        std::cout << "[InputMode] replay_only NO_MICROPHONE_ASR_OR_VAD_INFERENCE\\n" << std::flush;
        const auto replay_start=std::chrono::steady_clock::now();
        std::string line;
        while (std::getline(input,line))
        {
            if (line.empty()) continue;
            const auto tab=line.find('\\t');
            if (tab==std::string::npos) throw std::runtime_error("Invalid replay line");
            std::size_t used=0;
            const long delay=std::stol(line.substr(0,tab),&used);
            if (used!=tab || delay<0 || delay>120000) throw std::runtime_error("Invalid replay offset");
            std::this_thread::sleep_until(replay_start+std::chrono::milliseconds(delay));
            if (stop_signals.received()!=0) break;
            std::cout << "[Replay] scheduled_ms=" << delay << " source=controlled_text\\n" << std::flush;
            on_text(line.substr(tab+1));
        }
        audio_queue.close();
    }
    else
    {
'''+normal+'''    }
'''+s[end:]
    # Unlike real microphone runs, replay must not claim the non-started VAD/ASR workers succeeded.
    s=s.replace('if (!producer.ok())','if (!replay_mode && !producer.ok())')
    s=s.replace('if (!consumer.ok())','if (!replay_mode && !consumer.ok())')
    if candidate:
        s=s.replace('producer.ok() && consumer.ok() && audio_queue.droppedCount()==0 &&','(replay_mode || (producer.ok() && consumer.ok())) && audio_queue.droppedCount()==0 &&')
    else:
        s=s.replace('''        producer.ok() &&
        consumer.ok() &&''','''        (replay_mode || (producer.ok() && consumer.ok())) &&''')
    # Honest mode labels: replay does not start/join capture/VAD/ASR workers.
    declarations='    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");\n    const bool replay_mode=replay_path!=nullptr;\n'
    s=s.replace(declarations,'',1)
    listen=s.index('    std::cout\n        << "[Listen] "')
    listen_end=s.index('        << std::flush;',listen)+len('        << std::flush;')
    s=s[:listen]+declarations+'    if (!replay_mode)\n    {\n'+s[listen:listen_end]+'\n    }\n    else std::cout << "[Replay ready] controlled text; microphone/VAD/ASR not run\\n" << std::flush;'+s[listen_end:]
    s=s.replace('std::cout << "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\\n" << std::flush;', 'std::cout << (replay_mode ? "[Shutdown] replay input closed; recognizer destroyed\\n" : "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\\n") << std::flush;')
    return s


def main():
    entry=ROOT/'src/audio/asr_llm_tts_smoke.cpp'
    s=entry.read_text(encoding='utf-8')
    if '[InputMode] replay_only' in s:raise SystemExit('Replay already prepared; refuse duplicate instrumentation')
    entry.write_text(replay(s,True),encoding='utf-8')
    baseline=ROOT/'backups/stage5_02_before'
    out=ROOT/'reports/stage5_02_local/instrumented_baseline'
    out.mkdir()
    changes=[]
    def save(name,modified):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(modified,encoding='utf-8')
        old=(baseline/name).read_text(encoding='utf-8') if (baseline/name).exists() else ''
        changes.extend(difflib.unified_diff(old.splitlines(keepends=True),modified.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
    s=(baseline/'src/audio/asr_llm_tts_smoke.cpp').read_text(encoding='utf-8')
    s=s.replace('#include <chrono>','#include <chrono>\n#include "app/pipeline_metrics.h"')
    s=s.replace('    IntentRouter router;','    IntentRouter router;\n    std::size_t dispatch_calls=0;')
    anchor='    {\n        // --------------------------------------------------\n        // 12.1'
    start=s.index(anchor,s.index('    const auto on_text ='))
    s=s[:start]+s[start:].replace('    {\n','    {\n        DispatchTimer dispatch_timer{print_mutex, ++dispatch_calls};\n',1)
    s=replay(s,False)
    start=s.index('    const bool passed =')
    s=s[:start]+'''    std::cout << "[BaselineQueues] inference_peak=" << llm_worker.peakCount()
              << " tts_peak=" << tts_worker.peakCount() << " audio_peak=" << audio_queue.peakCount() << '\\n';
'''+s[start:]
    save('src/audio/asr_llm_tts_smoke.cpp',s)
    for name,container,field in [('ai/llm_worker','pending_','rejected_'),('audio/tts_worker','pending_','rejected_'),('audio/asr_pipeline','items_','dropped_')]:
        hname='include/'+name+'.h';cname='src/'+name+'.cpp'
        h=(baseline/hname).read_text(encoding='utf-8')
        h=h.replace('    std::size_t '+field+' = 0;','    std::size_t '+field+' = 0;\n    std::size_t measured_peak_ = 0;',1)
        h=h.replace('    std::size_t '+('rejectedCount' if field=='rejected_' else 'droppedCount')+'() const;',
                    '    std::size_t '+('rejectedCount' if field=='rejected_' else 'droppedCount')+'() const;\n    std::size_t peakCount() const {std::lock_guard<std::mutex> lock(mutex_);return measured_peak_;}',1)
        c=(baseline/cname).read_text(encoding='utf-8')
        c='#include <algorithm>\n'+c
        push='        '+container+'.push_back(std::move('+('task' if container=='pending_' else 'segment')+'));'
        assert push in c
        c=c.replace(push,push+'\n        measured_peak_=std::max(measured_peak_,'+container+'.size());',1)
        save(hname,h);save(cname,c)
    for name in ('include/app/pipeline_metrics.h','include/common/work_control.h'):
        save(name,(ROOT/name).read_text(encoding='utf-8'))
    (ROOT/'reports/stage5_02_local/baseline_instrumentation.patch').write_text(''.join(changes),encoding='utf-8')
    print('Prepared matching explicit replay/timer instrumentation; baseline queue algorithms and limits unchanged.')


if __name__=='__main__':main()
```

## 操作 27：tools/stage5_02_ssh.py

SHA256：`398082a1f9dd001c21574ad582caea39271944cc27586f2f610092243a049f4d`；25 行。

```python
#!/usr/bin/env python3
"""Stage 5.2 authorized isolated payload transport; records raw output and status."""
import argparse
from datetime import datetime
import sys
from pathlib import Path
import stage5_phase2_deploy as transport

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=300)
    args=parser.parse_args()
    path=args.payload.resolve();assert path.is_relative_to(transport.ROOT)
    source=path.read_bytes();compile(source,'<remote>','exec')
    report=transport.ROOT/'reports/stage5_02_board'/('ssh_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    code=transport.run_step(report,'remote',transport.remote_command(),source,args.timeout)
    print('REPORT_DIRECTORY',report.relative_to(transport.ROOT),flush=True)
    for name in ('remote.stdout.log','remote.stderr.log'):
        print((report/name).read_text(encoding='utf-8',errors='replace')[-14000:],flush=True)
    return code

if __name__=='__main__':raise SystemExit(main())
```

## 操作 28：tools/stage5_02_summarize.py

SHA256：`f87abe093ace430e90db503f71cbb7b4421e217dc02744377e26bd4f6916631c`；76 行。

```python
#!/usr/bin/env python3
"""Derive Stage 5.2 finite-sample metrics from preserved terminal/result evidence."""
import argparse,csv,json,math,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def distribution(values):
 if not values:return dict(n=0,mean=None,p50=None,p95=None,max=None)
 ordered=sorted(values)
 return dict(n=len(values),mean=statistics.mean(values),p50=ordered[max(0,math.ceil(.50*len(values))-1)],p95=ordered[max(0,math.ceil(.95*len(values))-1)],max=max(values),method='nearest-rank; finite sample only')
def fields(text):
 return {k:float(v) if '.' in v or 'e' in v.lower() else int(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+(?:e[+-]?\d+)?)',text,re.I)}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collection',type=Path);args=parser.parse_args()
 folder=args.collection or sorted((ROOT/'reports/stage5_02_board').glob('collected_*'))[-1]
 evidence=folder/'files/reports/stage5_02_board';cases=[]
 confirmations=load(ROOT/'reports/stage5_02_board/user_confirmations.json')
 for result in sorted(evidence.glob('*/result.json')):
  case=result.parent;log=case/'terminal.log'
  if not log.is_file():continue
  text=log.read_text(encoding='utf-8',errors='replace');summary=load(result)
  def values(pattern):return [float(x) for x in re.findall(pattern,text)]
  # completed lines only; cancelled/expired callback rows stay included in wait distribution.
  infer_lines=re.findall(r'\[(?:LLM|VLM) done #\d+\][^\n]*',text)
  tts_lines=re.findall(r'\[(?:VISION )?TTS done #\d+\][^\n]*',text)
  ready=None
  events=case/'events.jsonl'
  if events.is_file():
   for line in events.read_text().splitlines():
    event=json.loads(line)
    if event.get('event')=='trigger' and event.get('trigger')=='ready':ready=event['elapsed']
  cancelled_waits={int(i):float(v) for i,v in re.findall(r'\[TTS cancelled #(\d+)\] queue_ms=([\d.e+-]+)',text)}
  measured_tts_waits=[]
  for line in tts_lines:
   if 'queue_ms=' not in line:continue
   wait=fields(line)['queue_ms']
   if wait<0:
    request=int(re.search(r'done #(\d+)',line).group(1))
    wait=cancelled_waits.get(request)
   if wait is not None:measured_tts_waits.append(wait)
  delivered=sum('success=true' in line for line in tts_lines)
  successful=sum('success=true' in line for line in infer_lines)
  started=len(infer_lines)
  rows={}
  for line in re.findall(r'\[QueueStats\][^\n]*',text):
   stage=re.search(r'stage=(\w+)',line).group(1);rows[stage]=fields(line)
  if 'inference' in rows:started=rows['inference']['started']
  pipe=re.search(r'\[PipelineStats\]([^\n]*)',text)
  if pipe:pipe=fields(pipe.group(1))
  scope=summary['duration_seconds']-ready if ready is not None else None
  samples=[json.loads(x) for x in (case/'resources.jsonl').read_text().splitlines()]
  rss=[int(x['VmRSS'].split()[0]) for x in samples if 'VmRSS' in x]
  entry=dict(case=case.name,evidence=str(case.relative_to(ROOT)),process=summary,
             dispatch_ms=distribution(values(r'\[Dispatch\] id=\d+ callback_ms=([\d.e+-]+)')),
             inference_queue_ms=distribution([fields(x)['queue_ms'] for x in infer_lines if 'queue_ms=' in x]),
             tts_queue_ms_all_terminals=distribution(measured_tts_waits),
             tts_cancel_callback_sentinel='Cancelled callback retains legacy -1; actual wait read from [TTS cancelled] marker or QueueStats',
             tts_synthesis_ms=distribution([fields(x)['synth_ms'] for x in tts_lines if 'success=true' in x]),
             ai_started=started,ai_successful=successful,inference_success_fraction=None if not started else successful/started,
             delivered=delivered,dispatch_count=len(re.findall(r'\[Dispatch\]',text)),pipeline=pipe,queues=rows,
             baseline_peaks=fields(re.search(r'\[BaselineQueues\]([^\n]*)',text).group(1)) if '[BaselineQueues]' in text else None,
             post_ready_to_exit_seconds=scope,inference_per_second_including_shutdown=None if not scope else successful/scope,
             delivered_per_second_including_shutdown=None if not scope else delivered/scope,
             throughput_warning='Includes shutdown/drain, and quiet microphone window. Not steady-state NPU throughput.',
             rss_peak_kib=max(rss) if rss else None,thread_peak=max(int(x.get('Threads',0)) for x in samples),
             playback_xruns=values(r'playback_xruns=(\d+)'),audio_capture_xruns=values(r'\[ALSA\] XRUN=(\d+)'),
             runtime_error_markers=re.findall(r'^.*\[(?:Fatal|LLM error|VLM Error|TTS error|Inference callback error|TTS callback error)\].*$',text,re.M),
             user_confirmation=[r for r in confirmations if r['case']==case.name])
  cases.append(entry)
 report=ROOT/'reports/stage5_02_board'
 (report/'metrics.json').write_text(json.dumps(dict(collection=str(folder.relative_to(ROOT)),percentile_method='nearest-rank',cases=cases),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 with (report/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as out:
  writer=csv.writer(out);writer.writerow(['case','returncode','dispatch_n','dispatch_mean_ms','dispatch_p50_ms','dispatch_p95_ms','ai_started','ai_successful','delivered','tts_wait_mean_ms','tts_wait_max_ms','rss_peak_kib','signal_to_exit_seconds'])
  for c in cases:writer.writerow([c['case'],c['process']['returncode'],c['dispatch_ms']['n'],c['dispatch_ms']['mean'],c['dispatch_ms']['p50'],c['dispatch_ms']['p95'],c['ai_started'],c['ai_successful'],c['delivered'],c['tts_queue_ms_all_terminals']['mean'],c['tts_queue_ms_all_terminals']['max'],c['rss_peak_kib'],c['process']['signal_to_exit_seconds']])
 print(json.dumps([dict(case=c['case'],code=c['process']['returncode'],dispatch=c['dispatch_ms'],ai=c['ai_successful'],delivered=c['delivered'],pipe=c['pipeline']) for c in cases],indent=2))
if __name__=='__main__':main()
```

