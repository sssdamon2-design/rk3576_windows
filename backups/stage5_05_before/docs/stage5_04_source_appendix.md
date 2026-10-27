# 5.4 当前修改源码全文

由 `tools/stage5_04_export.py` 从真实文件生成。逐句语义解释见 [stage5_04_statement_notes.md](stage5_04_statement_notes.md)，架构与实测见 [stage5_04_performance_profiling.md](stage5_04_performance_profiling.md)。本附录不省略入口及测试，不代替板端版本哈希或执行证据。

## 修改前 1：CMakeLists.txt

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
    src/video/image_preprocessor.cpp
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
    add_executable(image_pipeline_tests tests/image_pipeline_tests.cpp
        tests/camera_test_capture.cpp src/video/camera_service.cpp)
    target_include_directories(image_pipeline_tests PRIVATE tests)
    target_link_libraries(image_pipeline_tests PRIVATE multimodal_core)
    project_warnings(image_pipeline_tests)
    add_test(NAME image_pipeline_tests COMMAND image_pipeline_tests)
    set_tests_properties(image_pipeline_tests PROPERTIES TIMEOUT 30)

    add_executable(async_pipeline_tests tests/async_pipeline_tests.cpp
        src/audio/asr_pipeline.cpp src/audio/audio_preprocessor.cpp src/audio/tts_worker.cpp)
    target_link_libraries(async_pipeline_tests PRIVATE multimodal_core)
    project_warnings(async_pipeline_tests)
    add_test(NAME async_pipeline_tests COMMAND async_pipeline_tests)
    set_tests_properties(async_pipeline_tests PROPERTIES TIMEOUT 20)
    if(BUILD_WITH_RKLLM AND BUILD_WITH_VLM)
        find_path(STAGE5_RGA_INCLUDE_DIR im2d.h PATH_SUFFIXES rga)
        find_library(STAGE5_RGA_LIBRARY rga)
        if(STAGE5_RGA_INCLUDE_DIR AND STAGE5_RGA_LIBRARY)
            add_executable(stage5_03_rga_probe tests/stage5_03_rga_probe.cpp)
            target_include_directories(stage5_03_rga_probe PRIVATE "${STAGE5_RGA_INCLUDE_DIR}" "${RKNN_INCLUDE_DIR}")
            target_link_libraries(stage5_03_rga_probe PRIVATE multimodal_core "${STAGE5_RGA_LIBRARY}")
            project_warnings(stage5_03_rga_probe)
        endif()
        add_executable(stage5_03_memory_probe tests/stage5_03_memory_probe.cpp)
        target_link_libraries(stage5_03_memory_probe PRIVATE multimodal_camera)
        project_warnings(stage5_03_memory_probe)
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

## 修改后 1：CMakeLists.txt

SHA256：`48b1a55f4d11e364cb629e680636f25e4cbfa764b389e5183240ff310e2750e8`；395 行。

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
    src/video/image_preprocessor.cpp
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
    if(BUILD_TESTING)
        add_executable(stage5_04_asr_bench tests/stage5_04_asr_bench.cpp)
        target_link_libraries(stage5_04_asr_bench PRIVATE multimodal_audio)
        project_warnings(stage5_04_asr_bench)
    endif()

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
    add_executable(request_profile_tests tests/request_profile_tests.cpp)
    target_link_libraries(request_profile_tests PRIVATE multimodal_core)
    project_warnings(request_profile_tests)
    add_test(NAME request_profile_tests COMMAND request_profile_tests "${CMAKE_CURRENT_BINARY_DIR}/request_profile_test.jsonl")
    set_tests_properties(request_profile_tests PROPERTIES TIMEOUT 10)
    add_executable(image_pipeline_tests tests/image_pipeline_tests.cpp
        tests/camera_test_capture.cpp src/video/camera_service.cpp)
    target_include_directories(image_pipeline_tests PRIVATE tests)
    target_link_libraries(image_pipeline_tests PRIVATE multimodal_core)
    project_warnings(image_pipeline_tests)
    add_test(NAME image_pipeline_tests COMMAND image_pipeline_tests)
    set_tests_properties(image_pipeline_tests PROPERTIES TIMEOUT 30)

    add_executable(async_pipeline_tests tests/async_pipeline_tests.cpp
        src/audio/asr_pipeline.cpp src/audio/audio_preprocessor.cpp src/audio/tts_worker.cpp)
    target_link_libraries(async_pipeline_tests PRIVATE multimodal_core)
    project_warnings(async_pipeline_tests)
    add_test(NAME async_pipeline_tests COMMAND async_pipeline_tests)
    set_tests_properties(async_pipeline_tests PROPERTIES TIMEOUT 20)
    if(BUILD_WITH_RKLLM AND BUILD_WITH_VLM)
        find_path(STAGE5_RGA_INCLUDE_DIR im2d.h PATH_SUFFIXES rga)
        find_library(STAGE5_RGA_LIBRARY rga)
        if(STAGE5_RGA_INCLUDE_DIR AND STAGE5_RGA_LIBRARY)
            add_executable(stage5_03_rga_probe tests/stage5_03_rga_probe.cpp)
            target_include_directories(stage5_03_rga_probe PRIVATE "${STAGE5_RGA_INCLUDE_DIR}" "${RKNN_INCLUDE_DIR}")
            target_link_libraries(stage5_03_rga_probe PRIVATE multimodal_core "${STAGE5_RGA_LIBRARY}")
            project_warnings(stage5_03_rga_probe)
        endif()
        add_executable(stage5_03_memory_probe tests/stage5_03_memory_probe.cpp)
        target_link_libraries(stage5_03_memory_probe PRIVATE multimodal_camera)
        project_warnings(stage5_03_memory_probe)
        add_executable(stage5_04_vision_bench tests/stage5_04_vision_bench.cpp)
        target_link_libraries(stage5_04_vision_bench PRIVATE multimodal_core)
        project_warnings(stage5_04_vision_bench)
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
    if(BUILD_TESTING)
        add_executable(stage5_04_tts_bench tests/stage5_04_tts_bench.cpp)
        target_link_libraries(stage5_04_tts_bench PRIVATE multimodal_tts)
        target_compile_definitions(stage5_04_tts_bench PRIVATE STAGE5_BENCH_TRACE=1)
        project_warnings(stage5_04_tts_bench)
    endif()

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

## 修改前 2：include/app/pipeline_admission.h

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

## 修改后 2：include/app/pipeline_admission.h

SHA256：`1bb1366ce1dc50767dc58fe101ebdb248292174d3381953b3cdcf0318687a9cb`；70 行。

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
        TaskOptions options(std::chrono::milliseconds max_wait,RequestTracePtr trace={}) const {
            TaskOptions result;result.deadline=deadline_;result.max_queue_wait=max_wait;result.cancelled=cancelled_;result.trace=std::move(trace);return result;
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

## 修改后 3：include/app/profiling_inputs.h

SHA256：`e8e40cbfa81d722321ee1c036c0c2dc67f99ae275f701195b804b4960d77bf06`；41 行。

```cpp
#pragma once
// Explicit offline benchmark inputs. None of these paths are active by default.
#include "common/types.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
inline std::shared_ptr<const ImageFrame> loadProfilingFrame(const std::filesystem::path& folder){
    std::ifstream meta(folder/"frame_0.json");std::stringstream content;content<<meta.rdbuf();const auto text=content.str();
    if(!meta||text.size()>4096)throw std::runtime_error("Invalid profiling frame metadata");
    auto field=[&](const char* key){std::smatch match;if(!std::regex_search(text,match,std::regex(std::string("\"")+key+"\":\\s*([0-9]+)")))throw std::runtime_error(std::string("Missing frame field: ")+key);return std::stoull(match[1]);};
    const auto width=field("width"),height=field("height"),stride=field("stride"),bytes=field("bytes");
    if(!width||!height||width%2||height%2||width>8192||height>8192||stride<width||stride>16384||bytes>100*1024*1024||bytes<stride*(height+height/2))throw std::runtime_error("Invalid packed NV12 profiling frame");
    const auto file=folder/"frame_0.nv12";if(std::filesystem::file_size(file)!=bytes)throw std::runtime_error("Profiling frame size mismatch");
    auto frame=std::make_shared<ImageFrame>();frame->width=static_cast<std::uint32_t>(width);frame->height=static_cast<std::uint32_t>(height);frame->pixel_format=0x3231564e;
    frame->plane_strides={static_cast<std::uint32_t>(stride)};frame->plane_sizes={static_cast<std::size_t>(bytes)};frame->frame_id=field("frame_id");frame->data.resize(bytes);
    std::ifstream raw(file,std::ios::binary);raw.read(reinterpret_cast<char*>(frame->data.data()),frame->data.size());if(!raw)throw std::runtime_error("Profiling frame read failed");
    return frame; // No live acquisition timestamp; Frame Age remains unavailable.
}
inline std::vector<float> loadProfilingAudio(const std::filesystem::path& file){
    static_assert(sizeof(float)==4,"Profiling fixture requires 32-bit float");
    const auto bytes=std::filesystem::file_size(file);
    if(!bytes||bytes%sizeof(float)||bytes>16000*16*sizeof(float))throw std::runtime_error("Invalid 16kHz mono float profiling audio size");
    std::vector<float> samples(bytes/sizeof(float));std::ifstream input(file,std::ios::binary);input.read(reinterpret_cast<char*>(samples.data()),bytes);
    if(!input||!std::all_of(samples.begin(),samples.end(),[](float x){return std::isfinite(x)&&std::abs(x)<=1.001f;}))throw std::runtime_error("Invalid profiling PCM");
    return samples;
}
inline void dumpProfilingAudio(const std::filesystem::path& folder,std::uint64_t id,const std::vector<float>& samples){
    if(!std::filesystem::is_directory(folder))throw std::runtime_error("Audio fixture directory must exist");
    const auto stem=folder/("segment_"+std::to_string(id));const auto audio=stem.string()+".f32",meta=stem.string()+".json";
    if(std::filesystem::exists(audio)||std::filesystem::exists(meta))throw std::runtime_error("Refusing to overwrite profiling audio");
    std::ofstream output(audio,std::ios::binary);output.write(reinterpret_cast<const char*>(samples.data()),samples.size()*sizeof(float));
    std::ofstream metadata(meta);metadata<<"{\"sample_rate\":16000,\"channels\":1,\"format\":\"f32le\",\"samples\":"<<samples.size()<<",\"request_id\":"<<id<<"}\n";
    if(!output||!metadata)throw std::runtime_error("Profiling audio write failed");
}
```

## 修改前 4：include/audio/asr_pipeline.h

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

## 修改后 4：include/audio/asr_pipeline.h

SHA256：`11f76809de0670bbc1d51487b2a81272d9526a015a9442a07c59e19d256a7db6`；182 行。

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
#include "common/request_trace.h"

class ASRService;

// 一个完整的待识别音频段。
struct AudioSegment {
    RequestTracePtr trace;
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
    using ContextCallback = std::function<void(const std::string&,const AudioSegment&)>;

    ASRWorker(
        AudioBufferQueue& queue,
        ASRService& asr,
        std::mutex& print_mutex,
        TextCallback on_text = {},
        ContextCallback on_context = {}
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
    ContextCallback on_context_;

    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t processed_ = 0;
};
```

## 修改前 5：include/audio/tts_service.h

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

## 修改后 5：include/audio/tts_service.h

SHA256：`32e38b1ed2460a8a1cdc91040c1a349a250520fa4d0dce31e6a92736f6605b91`；63 行。

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
        std::int32_t num_threads = 4,
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

## 修改前 6：include/common/image_profile.h

```cpp
#pragma once
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>

// Optional diagnostic JSONL. Each duration ends before file I/O; no frame data held.
class ImageProfile {
public:
    using Clock=std::chrono::steady_clock;
    static double ms(Clock::time_point start,Clock::time_point end=Clock::now()) {
        return std::chrono::duration<double,std::milli>(end-start).count();
    }
    static ImageProfile& instance(){static ImageProfile profile;return profile;}
    void sample(const char* stage,double duration,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) noexcept {
        if(!enabled_)return;
        try {
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"stage\":\""<<stage<<"\",\"ms\":"<<duration<<",\"id\":"<<id<<",\"bytes\":"<<bytes<<",\"allocations\":"<<allocations<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] write failed\n";}
        } catch(...) {std::cerr<<"[ImageProfile ERROR] exception\n";}
    }
private:
    ImageProfile(){
        if(const char* path=std::getenv("STAGE5_IMAGE_PROFILE")) {
            enabled_=true;output_.open(path,std::ios::out|std::ios::trunc);
            if(!output_){enabled_=false;failed_=true;std::cerr<<"[ImageProfile ERROR] cannot open log\n";}
        }
    }
    bool enabled_=false,failed_=false;
    std::mutex mutex_;
    std::ofstream output_;
};
inline void imageSample(const char* stage,double ms,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) {
    ImageProfile::instance().sample(stage,ms,id,bytes,allocations);
}
```

## 修改后 6：include/common/image_profile.h

SHA256：`4796e43ce77c9aba244636b711180799a86b5ab492f7098077d4bfa6a2e66af5`；60 行。

```cpp
#pragma once
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>

// Frame IDs and request IDs belong to different namespaces. SDK callbacks carry
// an explicit RequestTrace; ordinary synchronous stages inherit this scoped ID.
inline thread_local std::uint64_t image_profile_request_id=0;

// Optional diagnostic JSONL. Each duration ends before file I/O; no frame data held.
class ImageProfile {
public:
    using Clock=std::chrono::steady_clock;
    static double ms(Clock::time_point start,Clock::time_point end=Clock::now()) {
        return std::chrono::duration<double,std::milli>(end-start).count();
    }
    static ImageProfile& instance(){static ImageProfile profile;return profile;}
    bool enabled() const noexcept {return enabled_;}
    void sample(const char* stage,double duration,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) noexcept {
        if(!enabled_ || (!background_ && image_profile_request_id==0))return;
        try {
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"stage\":\""<<stage<<"\",\"ms\":"<<duration<<",\"id\":"<<id<<",\"request_id\":"<<image_profile_request_id<<",\"bytes\":"<<bytes<<",\"allocations\":"<<allocations<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] write failed\n";}
        } catch(...) {std::cerr<<"[ImageProfile ERROR] exception\n";}
    }
    void request(std::uint64_t id,const char* event,Clock::time_point at,double value=-1) noexcept {
        if(!enabled_)return;
        try {
            const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(at.time_since_epoch()).count();
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"kind\":\"request\",\"stage\":\"request_event\",\"ms\":0,\"id\":0,\"bytes\":0,\"allocations\":0,\"request_id\":"<<id<<",\"event\":\""<<event<<"\",\"at_ns\":"<<ns<<",\"value\":"<<value<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] request write failed\n";}
        }catch(...){std::cerr<<"[ImageProfile ERROR] request exception\n";}
    }
private:
    ImageProfile(){
        const char* path=std::getenv("STAGE5_PROFILE");
        background_=path==nullptr; // Legacy image profiling retains all Camera samples.
        if(!path)path=std::getenv("STAGE5_IMAGE_PROFILE");
        if(path) {
            enabled_=true;output_.open(path,std::ios::out|std::ios::trunc);
            if(!output_){enabled_=false;failed_=true;std::cerr<<"[ImageProfile ERROR] cannot open log\n";}
        }
    }
    bool enabled_=false,failed_=false,background_=true;
    std::mutex mutex_;
    std::ofstream output_;
};
inline void imageSample(const char* stage,double ms,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) {
    ImageProfile::instance().sample(stage,ms,id,bytes,allocations);
}
```

## 修改后 7：include/common/request_trace.h

SHA256：`9da18836555bc01869070cdbfde0d788a9f4466db954fdeb5100f335a05cc970`；38 行。

```cpp
#pragma once
#include "common/image_profile.h"
#include <memory>
#include <utility>

// One bounded-lifetime object travels through existing queue/task ownership.
// No central map retains completed requests. Raw timestamps use steady_clock.
class RequestTrace {
public:
    using Clock=std::chrono::steady_clock;
    explicit RequestTrace(std::uint64_t id):id_(id){}
    std::uint64_t id() const noexcept {return id_;}
    void mark(const char* event,Clock::time_point at=Clock::now(),double value=-1) const noexcept {
        ImageProfile::instance().request(id_,event,at,value);
    }
private:
    const std::uint64_t id_;
};
using RequestTracePtr=std::shared_ptr<RequestTrace>;
inline RequestTracePtr makeRequestTrace(std::uint64_t id) {
    return ImageProfile::instance().enabled()?std::make_shared<RequestTrace>(id):RequestTracePtr{};
}
inline RequestTracePtr& currentRequestTrace(){static thread_local RequestTracePtr trace;return trace;}
class RequestTraceScope {
public:
    explicit RequestTraceScope(RequestTracePtr trace):previous_(std::move(currentRequestTrace())),previous_id_(image_profile_request_id) {
        currentRequestTrace()=std::move(trace);image_profile_request_id=currentRequestTrace()?currentRequestTrace()->id():0;
    }
    ~RequestTraceScope(){currentRequestTrace()=std::move(previous_);image_profile_request_id=previous_id_;}
    RequestTraceScope(const RequestTraceScope&)=delete;
    RequestTraceScope& operator=(const RequestTraceScope&)=delete;
private:
    RequestTracePtr previous_;
    std::uint64_t previous_id_;
};
inline void traceMark(const char* event,RequestTrace::Clock::time_point at=RequestTrace::Clock::now(),double value=-1) noexcept {
    if(currentRequestTrace())currentRequestTrace()->mark(event,at,value);
}
```

## 修改前 8：include/common/work_control.h

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

## 修改后 8：include/common/work_control.h

SHA256：`077cda07787f8536cd063a32f9251a976868852e676d5e90d9fd5bd4d02084d2`；32 行。

```cpp
#pragma once
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>
#include "common/request_trace.h"

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
    RequestTracePtr trace;
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

## 修改前 9：src/ai/llm_worker.cpp

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

## 修改后 9：src/ai/llm_worker.cpp

SHA256：`5116f71770098e5d0031af0453fcfa5fe5b6b87b0a02cf250a62da6de817d8b0`；106 行。

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
    const auto trace=options.trace;std::chrono::steady_clock::time_point enqueued{};std::size_t depth=0;
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!started_ || stop_requested_) {++stats_.rejected_stopped;if(trace)trace->mark("inference_rejected_stopped");return LLMSubmitStatus::NotRunning;}
     if (pending_.size()>=capacity_) {++rejected_;++stats_.rejected_full;if(trace)trace->mark("inference_rejected_full");return LLMSubmitStatus::QueueFull;}
     Task task;task.id=id;task.inference=std::move(inference);task.on_chunk=std::move(chunk);task.on_done=std::move(done);
     task.enqueued_at=std::chrono::steady_clock::now();enqueued=task.enqueued_at;task.options=std::move(options);
     pending_.push_back(std::move(task));++stats_.accepted;depth=pending_.size();stats_.peak_depth=std::max(stats_.peak_depth,depth);}
    if(trace)trace->mark("inference_enqueued",enqueued,static_cast<double>(depth));
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
        RequestTraceScope trace_scope(task.options.trace);
        traceMark("inference_dequeued",begin);
        const double waited=std::chrono::duration<double,std::milli>(begin-task.enqueued_at).count();
        InferenceResult result;
        result.disposition=task.options.disposition(task.enqueued_at,begin,cancel);
        const auto disposition=result.disposition;
        if (disposition!=TaskDisposition::Completed) {
            traceMark(disposition==TaskDisposition::Cancelled?"inference_cancelled":"inference_expired");
            result.error_message=std::string("Inference task ")+dispositionName(disposition);
            std::cerr<<"[Inference "<<dispositionName(disposition)<<" #"<<task.id<<"] queue_ms="<<waited<<'\n';
        } else {
            {std::lock_guard<std::mutex> lock(mutex_);++stats_.started;}
            traceMark("inference_begin");
            std::atomic<bool> chunk_failed{false};
            try {
                result=task.inference([&](const std::string& chunk){
                    if (task.on_chunk) try {task.on_chunk(task.id,chunk);} catch(...) {chunk_failed.store(true);}
                });
            } catch(const std::exception& e) {result.success=false;result.text.clear();result.error_message=std::string("LLMWorker inference exception: ")+e.what();}
              catch(...) {result.success=false;result.text.clear();result.error_message="LLMWorker inference: unknown exception";}
            if (chunk_failed.load()) {result.success=false;result.text.clear();result.error_message="LLMWorker chunk callback threw an exception";}
            traceMark(result.success?"inference_end":"inference_failed");
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

## 修改前 10：src/ai/rk3576_vlm_backend.cpp

```cpp
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
    bool cached=true;
    Rgb512Preprocessor preprocessor;
    std::vector<uint8_t> rgb_buffer;
    std::vector<float> embedding_buffer;

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
    if(const char* value=std::getenv("STAGE5_VISION_PREPROCESS")) {
        const std::string mode(value);
        if(mode!="reference" && mode!="cached"){error="Invalid STAGE5_VISION_PREPROCESS";return false;}
        next->cached=mode=="cached";
    }
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
    std::vector<uint8_t> reference_rgb;
    auto& rgb=impl_->cached?impl_->rgb_buffer:reference_rgb;
    const std::size_t rgb_growth=rgb.capacity()<kImageBytes;
    const auto preprocess_begin=ImageProfile::Clock::now();
    const bool converted=impl_->cached?impl_->preprocessor.convert(*frame,rgb,out.error_message):frameToRgb512Reference(*frame,rgb,out.error_message);
    if(!converted)return out;
    imageSample("preprocess_fused",ImageProfile::ms(preprocess_begin),frame->frame_id,kImageBytes,rgb_growth);
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
    std::vector<float> reference_embeddings;
    auto& embeddings=impl_->cached?impl_->embedding_buffer:reference_embeddings;
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
            const std::size_t embedding_growth=embeddings.capacity()<kEmbeddingFloats;
            auto embedding_begin=ImageProfile::Clock::now();
            embeddings.assign(ptr, ptr + kEmbeddingFloats);
            imageSample("embedding_alloc_copy",ImageProfile::ms(embedding_begin),frame->frame_id,kEmbeddingFloats*sizeof(float),embedding_growth);
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
```

## 修改后 10：src/ai/rk3576_vlm_backend.cpp

SHA256：`1ec8b408405eb04defc358a028f149dd0cf70e68c63aa519b4d56e74db213b24`；275 行。

```cpp
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
#include <mutex>
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
    std::mutex mutex;
    std::string text;
    bool finished = false;
    bool failed = false;
    RequestTracePtr trace;
    std::chrono::steady_clock::time_point decoder_start{};
    double first_text_ms=-1;
};

int onLlmResult(RKLLMResult* result, void* userdata, LLMCallState state) {
    auto* out = static_cast<GenerationState*>(userdata);
    if (!out) return 0;
    try {
        std::lock_guard<std::mutex> lock(out->mutex);
        if (state == RKLLM_RUN_FINISH) out->finished = true;
        if (state == RKLLM_RUN_ERROR) out->failed = true;
        if (state == RKLLM_RUN_NORMAL && result && result->text && result->text[0]) {
            if(out->first_text_ms<0){
                const auto now=std::chrono::steady_clock::now();
                out->first_text_ms=std::chrono::duration<double,std::milli>(now-out->decoder_start).count();
                if(out->trace)out->trace->mark("first_text_chunk",now);
            }
            out->text += result->text;
        }
    } catch (...) { std::lock_guard<std::mutex> lock(out->mutex);out->failed = true; }
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
    bool cached=true;
    Rgb512Preprocessor preprocessor;
    std::vector<uint8_t> rgb_buffer;
    std::vector<float> embedding_buffer;

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
    if(const char* value=std::getenv("STAGE5_VISION_PREPROCESS")) {
        const std::string mode(value);
        if(mode!="reference" && mode!="cached"){error="Invalid STAGE5_VISION_PREPROCESS";return false;}
        next->cached=mode=="cached";
    }
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
    std::vector<uint8_t> reference_rgb;
    auto& rgb=impl_->cached?impl_->rgb_buffer:reference_rgb;
    const std::size_t rgb_growth=rgb.capacity()<kImageBytes;
    const auto preprocess_begin=ImageProfile::Clock::now();
    const bool converted=impl_->cached?impl_->preprocessor.convert(*frame,rgb,out.error_message):frameToRgb512Reference(*frame,rgb,out.error_message);
    if(!converted)return out;
    imageSample("preprocess_fused",ImageProfile::ms(preprocess_begin),frame->frame_id,kImageBytes,rgb_growth);
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
    std::vector<float> reference_embeddings;
    auto& embeddings=impl_->cached?impl_->embedding_buffer:reference_embeddings;
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
            const std::size_t embedding_growth=embeddings.capacity()<kEmbeddingFloats;
            auto embedding_begin=ImageProfile::Clock::now();
            embeddings.assign(ptr, ptr + kEmbeddingFloats);
            imageSample("embedding_alloc_copy",ImageProfile::ms(embedding_begin),frame->frame_id,kEmbeddingFloats*sizeof(float),embedding_growth);
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
    state.trace=currentRequestTrace();
    state.decoder_start=std::chrono::steady_clock::now();
    traceMark("decoder_begin",state.decoder_start);
    ret = rkllm_run(impl_->llm, &input, &infer, &state);
    traceMark("decoder_end");
    std::lock_guard<std::mutex> state_lock(state.mutex);
    if (ret != 0 || state.failed || !state.finished || state.text.empty()) {
        out.error_message = "VLM rkllm_run failed or empty answer, ret=" + std::to_string(ret);
        return out;
    }
    out.success = true;
    out.text = std::move(state.text);
    out.first_text_ms=state.first_text_ms;
    return out;
}

void RK3576VLMBackend::shutdown() noexcept { impl_.reset(); }
```

## 修改前 11：src/ai/rkllm_backend.cpp

```cpp
#include "ai/rk_backends.h"
#include "rkllm.h"

#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <utility>

namespace
{

struct RunContext
{
    std::mutex mutex;
    std::string text;
    const LLMStreamCallback* on_chunk = nullptr;
    std::chrono::steady_clock::time_point start;
    double first_text_ms = -1.0;
    bool failed = false;
};

// SDK C 回调中不允许 C++ 异常逃逸。
int onRKLLMResult(RKLLMResult* result, void* userdata, LLMCallState state)
{
    auto* context = static_cast<RunContext*>(userdata);
    if (context == nullptr) return 0;

    if (state == RKLLM_RUN_ERROR)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
        return 0;
    }

    if (state != RKLLM_RUN_NORMAL || result == nullptr ||
        result->text == nullptr || result->text[0] == '\0')
        return 0;

    try
    {
        // 必须在当前回调期间复制 Runtime 提供的字符数据。
        const std::string chunk(result->text);
        {
            std::lock_guard<std::mutex> lock(context->mutex);
            if (context->first_text_ms < 0.0)
            {
                const auto now = std::chrono::steady_clock::now();
                context->first_text_ms =
                    std::chrono::duration<double, std::milli>(now - context->start).count();
            }
            context->text.append(chunk);
        }

        // 不持有 RunContext 的 mutex 调用上层，避免锁重入。
        // 第一版要求回调只做短小的、非阻塞的处理。
        if (context->on_chunk != nullptr && *context->on_chunk)
            (*context->on_chunk)(chunk);
    }
    catch (...)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
    }
    return 0;
}

}  // namespace

struct RKLLMBackend::Impl
{
    std::string model_path;
    LLMHandle handle = nullptr;
    RKLLMParam params{};
    RKLLMCallback callbacks{};

    ~Impl() noexcept
    {
        if (handle != nullptr)
        {
            (void)rkllm_destroy(handle);
            handle = nullptr;
        }
    }
};

RKLLMBackend::RKLLMBackend() = default;

RKLLMBackend::~RKLLMBackend()
{
    shutdown();
}

bool RKLLMBackend::initialize(const BackendConfig& config, std::string& error)
{
    shutdown();
    error.clear();

    if (config.model_path.empty())
    {
        error = "RKLLM model_path is empty";
        return false;
    }

    auto next = std::make_unique<Impl>();
    next->model_path = config.model_path;
    next->params = rkllm_createDefaultParam();
    next->params.model_path = next->model_path.c_str();

    // 保持与已经验证成功的官方 Demo 参数一致。
    next->params.top_k = 1;
    next->params.top_p = 0.95f;
    next->params.temperature = 0.8f;
    next->params.repeat_penalty = 1.1f;
    next->params.frequency_penalty = 0.0f;
    next->params.presence_penalty = 0.0f;
    next->params.max_new_tokens = 128;
    next->params.max_context_len = 1024;
    next->params.skip_special_token = true;
    next->params.is_async = false;
    next->params.extend_param.base_domain_id = 0;
    next->params.extend_param.embed_flash = 1;

    next->callbacks.result_callback = onRKLLMResult;

    const int ret = rkllm_init(&next->handle, &next->params, &next->callbacks);
    if (ret != 0 || next->handle == nullptr)
    {
        error = "rkllm_init failed, ret=" + std::to_string(ret);
        return false;
    }

    impl_ = std::move(next);
    return true;
}

InferenceResult RKLLMBackend::infer(const std::string& question)
{
    return inferStreaming(question, {});
}

InferenceResult RKLLMBackend::inferStreaming(
    const std::string& question,
    const LLMStreamCallback& on_chunk)
{
    InferenceResult output;
    if (!impl_ || impl_->handle == nullptr)
    {
        output.error_message = "RKLLM backend is not initialized";
        return output;
    }
    if (question.empty())
    {
        output.error_message = "RKLLM question is empty";
        return output;
    }

    RKLLMInput input{};
    input.input_type = RKLLM_INPUT_PROMPT;
    input.role = "user";
    input.prompt_input = question.c_str();

    RKLLMInferParam infer_params{};
    infer_params.mode = RKLLM_INFER_GENERATE;
    infer_params.keep_history = 0;

    RunContext context;
    context.on_chunk = &on_chunk;
    context.start = std::chrono::steady_clock::now();

    const int ret = rkllm_run(impl_->handle, &input, &infer_params, &context);

    std::lock_guard<std::mutex> lock(context.mutex);
    if (ret != 0)
    {
        output.error_message = "rkllm_run failed, ret=" + std::to_string(ret);
        return output;
    }
    if (context.failed)
    {
        output.error_message = "RKLLM callback reported an error";
        return output;
    }
    if (context.text.empty())
    {
        output.error_message = "RKLLM inference produced no text";
        return output;
    }

    output.success = true;
    output.text = std::move(context.text);
    output.first_text_ms = context.first_text_ms;
    return output;
}

void RKLLMBackend::shutdown() noexcept
{
    impl_.reset();
}
```

## 修改后 11：src/ai/rkllm_backend.cpp

SHA256：`f8d2807b4814f18d92de8ebf45dfd761ae0da16244bbaab1c232e68907865860`；204 行。

```cpp
#include "ai/rk_backends.h"
#include "rkllm.h"

#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <utility>

namespace
{

struct RunContext
{
    std::mutex mutex;
    std::string text;
    const LLMStreamCallback* on_chunk = nullptr;
    std::chrono::steady_clock::time_point start;
    double first_text_ms = -1.0;
    bool failed = false;
    RequestTracePtr trace;
};

// SDK C 回调中不允许 C++ 异常逃逸。
int onRKLLMResult(RKLLMResult* result, void* userdata, LLMCallState state)
{
    auto* context = static_cast<RunContext*>(userdata);
    if (context == nullptr) return 0;

    if (state == RKLLM_RUN_ERROR)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
        return 0;
    }

    if (state != RKLLM_RUN_NORMAL || result == nullptr ||
        result->text == nullptr || result->text[0] == '\0')
        return 0;

    try
    {
        // 必须在当前回调期间复制 Runtime 提供的字符数据。
        const std::string chunk(result->text);
        {
            std::lock_guard<std::mutex> lock(context->mutex);
            if (context->first_text_ms < 0.0)
            {
                const auto now = std::chrono::steady_clock::now();
                context->first_text_ms =
                    std::chrono::duration<double, std::milli>(now - context->start).count();
                if(context->trace)context->trace->mark("first_text_chunk",now,static_cast<double>(chunk.size()));
            }
            context->text.append(chunk);
        }

        // 不持有 RunContext 的 mutex 调用上层，避免锁重入。
        // 第一版要求回调只做短小的、非阻塞的处理。
        if (context->on_chunk != nullptr && *context->on_chunk)
            (*context->on_chunk)(chunk);
    }
    catch (...)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
    }
    return 0;
}

}  // namespace

struct RKLLMBackend::Impl
{
    std::string model_path;
    LLMHandle handle = nullptr;
    RKLLMParam params{};
    RKLLMCallback callbacks{};

    ~Impl() noexcept
    {
        if (handle != nullptr)
        {
            (void)rkllm_destroy(handle);
            handle = nullptr;
        }
    }
};

RKLLMBackend::RKLLMBackend() = default;

RKLLMBackend::~RKLLMBackend()
{
    shutdown();
}

bool RKLLMBackend::initialize(const BackendConfig& config, std::string& error)
{
    shutdown();
    error.clear();

    if (config.model_path.empty())
    {
        error = "RKLLM model_path is empty";
        return false;
    }

    auto next = std::make_unique<Impl>();
    next->model_path = config.model_path;
    next->params = rkllm_createDefaultParam();
    next->params.model_path = next->model_path.c_str();

    // 保持与已经验证成功的官方 Demo 参数一致。
    next->params.top_k = 1;
    next->params.top_p = 0.95f;
    next->params.temperature = 0.8f;
    next->params.repeat_penalty = 1.1f;
    next->params.frequency_penalty = 0.0f;
    next->params.presence_penalty = 0.0f;
    next->params.max_new_tokens = 128;
    next->params.max_context_len = 1024;
    next->params.skip_special_token = true;
    next->params.is_async = false;
    next->params.extend_param.base_domain_id = 0;
    next->params.extend_param.embed_flash = 1;

    next->callbacks.result_callback = onRKLLMResult;

    const int ret = rkllm_init(&next->handle, &next->params, &next->callbacks);
    if (ret != 0 || next->handle == nullptr)
    {
        error = "rkllm_init failed, ret=" + std::to_string(ret);
        return false;
    }

    impl_ = std::move(next);
    return true;
}

InferenceResult RKLLMBackend::infer(const std::string& question)
{
    return inferStreaming(question, {});
}

InferenceResult RKLLMBackend::inferStreaming(
    const std::string& question,
    const LLMStreamCallback& on_chunk)
{
    InferenceResult output;
    if (!impl_ || impl_->handle == nullptr)
    {
        output.error_message = "RKLLM backend is not initialized";
        return output;
    }
    if (question.empty())
    {
        output.error_message = "RKLLM question is empty";
        return output;
    }

    RKLLMInput input{};
    input.input_type = RKLLM_INPUT_PROMPT;
    input.role = "user";
    input.prompt_input = question.c_str();

    RKLLMInferParam infer_params{};
    infer_params.mode = RKLLM_INFER_GENERATE;
    infer_params.keep_history = 0;

    RunContext context;
    context.on_chunk = &on_chunk;
    context.start = std::chrono::steady_clock::now();
    context.trace=currentRequestTrace();
    traceMark("decoder_begin",context.start);

    const int ret = rkllm_run(impl_->handle, &input, &infer_params, &context);
    traceMark("decoder_end");

    std::lock_guard<std::mutex> lock(context.mutex);
    if (ret != 0)
    {
        output.error_message = "rkllm_run failed, ret=" + std::to_string(ret);
        return output;
    }
    if (context.failed)
    {
        output.error_message = "RKLLM callback reported an error";
        return output;
    }
    if (context.text.empty())
    {
        output.error_message = "RKLLM inference produced no text";
        return output;
    }

    output.success = true;
    output.text = std::move(context.text);
    output.first_text_ms = context.first_text_ms;
    return output;
}

void RKLLMBackend::shutdown() noexcept
{
    impl_.reset();
}
```

## 修改前 12：src/audio/alsa_playback_service.cpp

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

## 修改后 12：src/audio/alsa_playback_service.cpp

SHA256：`df0dbd6e2f3b693afa97309dc83a400f5483fac59b231258bde68ee9915031d8`；412 行。

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
#include "common/request_trace.h"

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
    traceMark("playback_convert_begin");

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
    traceMark("playback_convert_end");
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
    bool first_submission=true;

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

        const auto submit_begin=std::chrono::steady_clock::now();
        const snd_pcm_sframes_t written =
            snd_pcm_writei(
                pcm_,
                pcm_data.data() + offset,
                frames
            );

        if (written > 0)
        {
            if(first_submission){
                traceMark("alsa_first_submit_begin",submit_begin,static_cast<double>(written));
                traceMark("alsa_first_submit_complete",std::chrono::steady_clock::now(),static_cast<double>(written));
                first_submission=false;
            }
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
    traceMark("alsa_drain_begin");
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

    traceMark("alsa_drain_complete");
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

## 修改前 13：src/audio/asr_llm_tts_smoke.cpp

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

## 修改后 13：src/audio/asr_llm_tts_smoke.cpp

SHA256：`cb9e603299df7093a4845bd37abd27c3ffa9a5d74150801efc1f54154ff14f35`；1446 行。

```cpp

#include "audio/asr_pipeline.h"
#include "app/pipeline_admission.h"
#include "app/pipeline_metrics.h"
#include "app/profiling_inputs.h"
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
#include <algorithm>
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
            << "[tts_threads=4] "
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

    int tts_threads = 4;
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
    LatestFrameBuffer::FramePtr profiling_frame;
    if(const char* folder=std::getenv("STAGE5_REPLAY_FRAME_DIR")){
        if(!enable_vision || (!std::getenv("STAGE5_REPLAY_FILE") && !std::getenv("STAGE5_REPLAY_AUDIO_FILE")))throw std::invalid_argument("Fixed frame is allowed only with explicit replay and VISION");
        profiling_frame=loadProfilingFrame(folder);
        std::cout<<"[InputMode] fixed NV12 for replay VLM; Camera still captures independently\n";
    }

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
        [&](const std::string& recognized, RequestTracePtr supplied_trace = {})
    {
        const auto request_id = supplied_trace ? supplied_trace->id() : next_id++;
        if(supplied_trace)next_id=std::max(next_id,request_id+1);
        const auto trace=supplied_trace ? std::move(supplied_trace) : makeRequestTrace(request_id);
        RequestTraceScope trace_scope(trace);
        traceMark("business_dispatch_begin");
        DispatchTimer dispatch_timer{print_mutex, ++dispatch_calls};
        // --------------------------------------------------
        // 12.1 意图判断
        // --------------------------------------------------

        const RouteDecision route =
            router.route(recognized);

        auto ticket = admission.tryAcquire(request_id, std::chrono::milliseconds(request_lifetime_ms));
        if (!ticket)
        {
            traceMark("pipeline_rejected_busy");
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
                traceMark("vision_disabled");
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
                    return vlm->infer(profiling_frame?profiling_frame:frames.getLatest(), vlm_question);
                }, {},
                [&, question_at, ticket, trace](std::uint64_t request_id, const InferenceResult& result, double inference_wait_ms)
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
                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms), trace));

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
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms), trace));
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

                [&, prefix_printed, question_at, ticket, trace](
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
                                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms), trace)
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
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms), trace)
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
        {},
        [&](const std::string& text,const AudioSegment& segment){on_text(text,segment.trace);}
    );

    VadAudioWorker producer(
        capture_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");
    const char* audio_replay_path=std::getenv("STAGE5_REPLAY_AUDIO_FILE");
    if(replay_path && audio_replay_path)throw std::invalid_argument("Text and audio replay are mutually exclusive");
    const bool replay_mode=replay_path!=nullptr || audio_replay_path!=nullptr;
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
    else std::cout << (audio_replay_path?"[Replay ready] fixed presegmented audio; real ASR, no microphone/VAD\n":"[Replay ready] controlled text; microphone/VAD/ASR not run\n") << std::flush;

    // ------------------------------------------------------
    // 14. 启动录音/VAD 和 ASR 工作线程
    // ------------------------------------------------------

    if (replay_mode)
    {
        std::ifstream input(audio_replay_path?audio_replay_path:replay_path);
        if (!input) throw std::runtime_error("Cannot open replay input");
        std::cout << (audio_replay_path?"[InputMode] replay_audio REAL_ASR_NO_MICROPHONE_OR_VAD\n":"[InputMode] replay_only NO_MICROPHONE_ASR_OR_VAD_INFERENCE\n") << std::flush;
        if(audio_replay_path)consumer.start();
        const auto replay_start=std::chrono::steady_clock::now();
        std::uint64_t audio_replay_sequence=1; // Producer-only; next_id belongs to the ASR callback thread.
        std::string line;
        while (std::getline(input,line))
        {
            if (line.empty()) continue;
            const auto tab=line.find('\t');
            if (tab==std::string::npos) throw std::runtime_error("Invalid replay line");
            std::size_t used=0;
            const long delay=std::stol(line.substr(0,tab),&used);
            if (used!=tab || delay<0 || delay>120000) throw std::runtime_error("Invalid replay offset");
            const auto scheduled=replay_start+std::chrono::milliseconds(delay);
            while(stop_signals.received()==0 && std::chrono::steady_clock::now()<scheduled)
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            if (stop_signals.received()!=0) break;
            std::cout << "[Replay] scheduled_ms=" << delay << (audio_replay_path?" source=fixed_audio\n":" source=controlled_text\n") << std::flush;
            if(audio_replay_path){
                AudioSegment segment;segment.sequence=audio_replay_sequence++;
                segment.trace=makeRequestTrace(segment.sequence);
                segment.samples=loadProfilingAudio(line.substr(tab+1));
                segment.enqueued_at=std::chrono::steady_clock::now();
                if(segment.trace)segment.trace->mark("offline_audio_ready",segment.enqueued_at);
                if(!audio_queue.push(std::move(segment)))throw std::runtime_error("Audio replay queue closed");
            }else on_text(line.substr(tab+1));
        }
        audio_queue.close();
        if(audio_replay_path)consumer.join();
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

        if ((!replay_mode || audio_replay_path) && !consumer.ok())
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
        (replay_mode ? (!audio_replay_path || consumer.ok()) : (producer.ok() && consumer.ok())) && audio_queue.droppedCount()==0 &&
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

## 修改前 14：src/audio/asr_pipeline.cpp

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

## 修改后 14：src/audio/asr_pipeline.cpp

SHA256：`a6f59d5a52bc996ffb39c893a8cfc177e8cd7f81b110d67e68ae2d0da72ac3b5`；350 行。

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
    const auto trace=segment.trace;
    const auto enqueued_at=segment.enqueued_at;
    std::uint64_t dropped_sequence=0;
    bool dropped=false;
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (closed_)
        {
            if(trace)trace->mark("asr_rejected_closed");
            ++stats_.rejected_closed;
            std::cerr << "[Audio queue rejected #" << segment.sequence << "] closed\n";
            return false;
        }

        // 队列满时丢弃最旧的完整音频段。
        if (items_.size() >= capacity_)
        {
            if(items_.front().trace)items_.front().trace->mark("asr_dropped_replaced");
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
    if(trace)trace->mark("asr_enqueued",enqueued_at);

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
    TextCallback on_text,
    ContextCallback on_context)
    : queue_(queue),
      asr_(asr),
      print_mutex_(print_mutex),
      on_text_(std::move(on_text)),
      on_context_(std::move(on_context))
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
        RequestTraceScope trace_scope(segment.trace);
        traceMark("asr_dequeued",popped_at);

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
        traceMark("asr_begin",infer_start);

        if (!asr_.recognize(
                samples,
                text,
                latency_ms,
                error))
        {
            traceMark("asr_failed");
            error_ = "ASR: " + error;
            queue_.close();
            return;
        }

        // 获取文字结果的时间。
        const auto result_ready = Clock::now();
        traceMark("asr_end",result_ready);

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

        // ASR 完成后调用业务回调；完整语音入口直接路由，未经过 RequestProcessor。
        // 必须在释放 print_mutex_ 后执行。
        if ((on_text_ || on_context_) && !text.empty())
        {
            try
            {
                if(on_context_)on_context_(text,segment);
                else on_text_(text);
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
        else if(text.empty())traceMark("asr_empty_text");
    }

    ok_ = true;
}
```

## 修改前 15：src/audio/asr_service.cpp

```cpp

#include "audio/asr_service.h"

// sherpa-onnx 官方 C API。
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <unistd.h>

// 对象销毁时自动释放模型。
ASRService::~ASRService()
{
    shutdown();
}

// 初始化 SenseVoiceSmall 模型。
bool ASRService::initialize(
    const std::string& model_path,
    const std::string& tokens_path,
    std::string& error)
{
    error.clear();

    // 重新初始化前，先释放旧模型。
    shutdown();

    // 检查模型是否可读。
    if (::access(model_path.c_str(), R_OK) != 0)
    {
        error = "Model file is not readable: " + model_path;
        return false;
    }

    // 检查词表是否可读。
    if (::access(tokens_path.c_str(), R_OK) != 0)
    {
        error = "Tokens file is not readable: " + tokens_path;
        return false;
    }

    // 1. 创建离线识别配置。
    // {} 表示零初始化。
    SherpaOnnxOfflineRecognizerConfig config{};

    // 2. 音频特征配置。
    config.feat_config.sample_rate = 16000;
    config.feat_config.feature_dim = 80;

    // 3. 指定 SenseVoiceSmall INT8 模型。
    config.model_config.sense_voice.model =
        model_path.c_str();

    // 固定中文识别。
    config.model_config.sense_voice.language = "zh";

    // 与之前命令行测试保持一致。
    config.model_config.sense_voice.use_itn = 0;

    // 4. 指定词表。
    config.model_config.tokens = tokens_path.c_str();

    // 5. 使用 ARM CPU 推理。
    config.model_config.provider = "cpu";

    // 初始使用两个 CPU 线程。
    config.model_config.num_threads = 2;

    config.model_config.modeling_unit = "cjkchar";

    // 6. 解码方式。
    config.decoding_method = "greedy_search";

    // 7. 创建 Recognizer。
    // 这里会初始化模型，耗时可能为数秒。
    recognizer_ = SherpaOnnxCreateOfflineRecognizer(&config);

    if (recognizer_ == nullptr)
    {
        error = "Failed to create sherpa-onnx recognizer";
        return false;
    }

    return true;
}

// 执行一次离线语音识别。
bool ASRService::recognize(
    const std::vector<float>& samples,
    std::string& text,
    double& latency_ms,
    std::string& error)
{
    error.clear();
    text.clear();
    latency_ms = 0.0;

    // 1. 检查模型是否初始化。
    if (recognizer_ == nullptr)
    {
        error = "ASR model is not initialized";
        return false;
    }

    // 2. 检查输入音频。
    if (samples.empty() ||
        samples.size() >
            static_cast<std::size_t>(
                std::numeric_limits<int32_t>::max()))
    {
        error = "Invalid audio sample count";
        return false;
    }

    // 开始计时。
    const auto start =
        std::chrono::steady_clock::now();

    // 3. 创建本次识别使用的 OfflineStream。
    //
    // 使用 unique_ptr + SDK 专用销毁函数。
    // 离开作用域时自动释放 Stream。
    using StreamPtr = std::unique_ptr<
        const SherpaOnnxOfflineStream,
        decltype(&SherpaOnnxDestroyOfflineStream)>;

    StreamPtr stream(
        SherpaOnnxCreateOfflineStream(recognizer_),
        &SherpaOnnxDestroyOfflineStream
    );

    if (!stream)
    {
        error = "Failed to create offline stream";
        return false;
    }

    // 4. 将 Float32 PCM 直接传入模型。
    // 输入采样率为 16000 Hz。
    //
    // 离线识别要求一次提交完整语音。
    SherpaOnnxAcceptWaveformOffline(
        stream.get(),
        16000,
        samples.data(),
        static_cast<int32_t>(samples.size())
    );

    // 5. 同步执行推理。
    SherpaOnnxDecodeOfflineStream(
        recognizer_,
        stream.get()
    );

    // 6. 获取识别结果。
    //
    // 结果由 SDK 分配，需要调用 SDK 的销毁接口。
    using ResultPtr = std::unique_ptr<
        const SherpaOnnxOfflineRecognizerResult,
        decltype(&SherpaOnnxDestroyOfflineRecognizerResult)>;

    ResultPtr result(
        SherpaOnnxGetOfflineStreamResult(stream.get()),
        &SherpaOnnxDestroyOfflineRecognizerResult
    );

    if (!result)
    {
        error = "Failed to obtain ASR result";
        return false;
    }

    // 7. 复制识别文本。
    // 不能长期保存 SDK 返回的原始指针。
    if (result->text != nullptr)
    {
        text = result->text;
    }

    // 8. 结束计时。
    const auto end =
        std::chrono::steady_clock::now();

    latency_ms =
        std::chrono::duration<double, std::milli>(
            end - start
        ).count();

    return true;
}

// 释放模型实例。
void ASRService::shutdown() noexcept
{
    if (recognizer_ != nullptr)
    {
        SherpaOnnxDestroyOfflineRecognizer(recognizer_);
        recognizer_ = nullptr;
    }
}
```

## 修改后 15：src/audio/asr_service.cpp

SHA256：`ab396ba89c5055452c6ad231977d7a8dca583a37c1991295e7bdbea2aff5f41c`；210 行。

```cpp

#include "audio/asr_service.h"

// sherpa-onnx 官方 C API。
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <unistd.h>
#include "common/request_trace.h"

// 对象销毁时自动释放模型。
ASRService::~ASRService()
{
    shutdown();
}

// 初始化 SenseVoiceSmall 模型。
bool ASRService::initialize(
    const std::string& model_path,
    const std::string& tokens_path,
    std::string& error)
{
    error.clear();

    // 重新初始化前，先释放旧模型。
    shutdown();

    // 检查模型是否可读。
    if (::access(model_path.c_str(), R_OK) != 0)
    {
        error = "Model file is not readable: " + model_path;
        return false;
    }

    // 检查词表是否可读。
    if (::access(tokens_path.c_str(), R_OK) != 0)
    {
        error = "Tokens file is not readable: " + tokens_path;
        return false;
    }

    // 1. 创建离线识别配置。
    // {} 表示零初始化。
    SherpaOnnxOfflineRecognizerConfig config{};

    // 2. 音频特征配置。
    config.feat_config.sample_rate = 16000;
    config.feat_config.feature_dim = 80;

    // 3. 指定 SenseVoiceSmall INT8 模型。
    config.model_config.sense_voice.model =
        model_path.c_str();

    // 固定中文识别。
    config.model_config.sense_voice.language = "zh";

    // 与之前命令行测试保持一致。
    config.model_config.sense_voice.use_itn = 0;

    // 4. 指定词表。
    config.model_config.tokens = tokens_path.c_str();

    // 5. 使用 ARM CPU 推理。
    config.model_config.provider = "cpu";

    // 初始使用两个 CPU 线程。
    config.model_config.num_threads = 2;

    config.model_config.modeling_unit = "cjkchar";

    // 6. 解码方式。
    config.decoding_method = "greedy_search";

    // 7. 创建 Recognizer。
    // 这里会初始化模型，耗时可能为数秒。
    recognizer_ = SherpaOnnxCreateOfflineRecognizer(&config);

    if (recognizer_ == nullptr)
    {
        error = "Failed to create sherpa-onnx recognizer";
        return false;
    }

    return true;
}

// 执行一次离线语音识别。
bool ASRService::recognize(
    const std::vector<float>& samples,
    std::string& text,
    double& latency_ms,
    std::string& error)
{
    error.clear();
    text.clear();
    latency_ms = 0.0;

    // 1. 检查模型是否初始化。
    if (recognizer_ == nullptr)
    {
        error = "ASR model is not initialized";
        return false;
    }

    // 2. 检查输入音频。
    if (samples.empty() ||
        samples.size() >
            static_cast<std::size_t>(
                std::numeric_limits<int32_t>::max()))
    {
        error = "Invalid audio sample count";
        return false;
    }

    // 开始计时。
    const auto start =
        std::chrono::steady_clock::now();

    // 3. 创建本次识别使用的 OfflineStream。
    //
    // 使用 unique_ptr + SDK 专用销毁函数。
    // 离开作用域时自动释放 Stream。
    using StreamPtr = std::unique_ptr<
        const SherpaOnnxOfflineStream,
        decltype(&SherpaOnnxDestroyOfflineStream)>;

    traceMark("asr_stream_create_begin");
    StreamPtr stream(
        SherpaOnnxCreateOfflineStream(recognizer_),
        &SherpaOnnxDestroyOfflineStream
    );

    traceMark("asr_stream_create_end");
    if (!stream)
    {
        error = "Failed to create offline stream";
        return false;
    }

    // 4. 将 Float32 PCM 直接传入模型。
    // 输入采样率为 16000 Hz。
    //
    // 离线识别要求一次提交完整语音。
    traceMark("asr_accept_wave_begin");
    SherpaOnnxAcceptWaveformOffline(
        stream.get(),
        16000,
        samples.data(),
        static_cast<int32_t>(samples.size())
    );

    // 5. 同步执行推理。
    traceMark("asr_accept_wave_end");
    traceMark("asr_decode_begin");
    SherpaOnnxDecodeOfflineStream(
        recognizer_,
        stream.get()
    );

    // 6. 获取识别结果。
    //
    // 结果由 SDK 分配，需要调用 SDK 的销毁接口。
    traceMark("asr_decode_end");
    using ResultPtr = std::unique_ptr<
        const SherpaOnnxOfflineRecognizerResult,
        decltype(&SherpaOnnxDestroyOfflineRecognizerResult)>;

    ResultPtr result(
        SherpaOnnxGetOfflineStreamResult(stream.get()),
        &SherpaOnnxDestroyOfflineRecognizerResult
    );

    if (!result)
    {
        error = "Failed to obtain ASR result";
        return false;
    }

    // 7. 复制识别文本。
    // 不能长期保存 SDK 返回的原始指针。
    if (result->text != nullptr)
    {
        text = result->text;
    }

    // 8. 结束计时。
    const auto end =
        std::chrono::steady_clock::now();

    latency_ms =
        std::chrono::duration<double, std::milli>(
            end - start
        ).count();

    return true;
}

// 释放模型实例。
void ASRService::shutdown() noexcept
{
    if (recognizer_ != nullptr)
    {
        SherpaOnnxDestroyOfflineRecognizer(recognizer_);
        recognizer_ = nullptr;
    }
}
```

## 修改前 16：src/audio/tts_service.cpp

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

## 修改后 16：src/audio/tts_service.cpp

SHA256：`232031b90c7bf12427fccc326df6e21d46c258142c1d97683294c28968a9b3e9`；343 行。

```cpp

#include "audio/tts_service.h"
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <exception>
#include <memory>
#include <string>
#include <vector>

#include <unistd.h>
#include <atomic>
#include <cstdlib>
#include "common/request_trace.h"

namespace {
struct AudioProgress {
    RequestTracePtr trace;
    std::atomic<bool> seen{false};
};
int32_t audioProgress(const float* samples,int32_t n,float,void* arg) noexcept {
    auto* progress=static_cast<AudioProgress*>(arg);
    if(progress && samples && n>0 && !progress->seen.exchange(true) && progress->trace)
        progress->trace->mark("tts_first_audio_callback",RequestTrace::Clock::now(),n);
    return 1; // Diagnostics must never truncate or cancel speech.
}
}

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
    std::string provider;
    if(const char* profile_config=std::getenv("STAGE5_TTS_ORT_PROFILE_CONFIG")) {
        if(::access(profile_config,R_OK)!=0){error="Cannot read TTS profiling config";return false;}
        provider=std::string("cpu:")+profile_config;cfg.model.provider=provider.c_str();
    }
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

    ImageProfile::instance().request(0,"tts_initialize_begin",RequestTrace::Clock::now(),num_threads);
    const SherpaOnnxOfflineTts* new_tts =
        SherpaOnnxCreateOfflineTts(&cfg);
    ImageProfile::instance().request(0,"tts_initialize_end",RequestTrace::Clock::now(),num_threads);

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
    traceMark("tts_generate_begin",start);
    AudioProgress progress;progress.trace=currentRequestTrace();

    // 真正执行 ONNX TTS 推理。
    AudioOwner audio(
        SherpaOnnxOfflineTtsGenerateWithConfig(
            tts_,
            text.c_str(),
            &gen,
            progress.trace?audioProgress:nullptr,
            progress.trace?&progress:nullptr
        ),
        &SherpaOnnxDestroyOfflineTtsGeneratedAudio
    );

    const auto finish =
        std::chrono::steady_clock::now();
    traceMark("tts_generate_end",finish);

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
        traceMark("tts_pcm_copy_begin");
        // 复制 SDK PCM 到 C++ 自有缓冲区。
        output.samples.assign(
            audio->samples,
            audio->samples + audio->n
        );
        traceMark("tts_pcm_copy_end");
    }
    catch (const std::exception& e)
    {
        error =
            std::string("PCM copy failed: ") +
            e.what();

        return false;
    }

    output.sample_rate = audio->sample_rate;
    traceMark("tts_full_audio_ready",RequestTrace::Clock::now(),static_cast<double>(audio->n));

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

## 修改前 17：src/audio/tts_worker.cpp

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

## 修改后 17：src/audio/tts_worker.cpp

SHA256：`2811c20f0ef2664876821a0ab67f0ae544a6c0bc18ac2f643726ec4de6d7a410`；336 行。

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
    const auto trace=options.trace;std::chrono::steady_clock::time_point enqueued{};std::size_t depth=0;
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
        {
            if(trace)trace->mark("tts_rejected_stopped");
            ++stats_.rejected_stopped;
            return TTSSubmitStatus::NotRunning;
        }

        if (pending_.size() >= capacity_)
        {
            if(trace)trace->mark("tts_rejected_full");
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
        enqueued=task.enqueued_at;

        pending_.push_back(std::move(task));
        ++stats_.accepted;
        stats_.peak_depth = std::max(stats_.peak_depth, pending_.size());
        depth=pending_.size();
    }
    if(trace)trace->mark("tts_enqueued",enqueued,static_cast<double>(depth));

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
        RequestTraceScope trace_scope(task.options.trace);
        traceMark("tts_dequeued",begin);
        const double waited = std::chrono::duration<double,std::milli>(begin-task.enqueued_at).count();
        TTSWorkerResult result;
        result.disposition = task.options.disposition(task.enqueued_at, begin, cancelled);
        const auto disposition = result.disposition;
        const double queue_wait_ms = disposition == TaskDisposition::Cancelled ? -1.0 : waited;
        if (disposition != TaskDisposition::Completed)
        {
            traceMark(disposition==TaskDisposition::Cancelled?"tts_cancelled":"tts_expired");
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
                traceMark("tts_synthesis_begin");

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
        traceMark(result.success?"request_complete":disposition==TaskDisposition::Completed?"tts_failed":"tts_terminal");
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

## 修改前 18：src/audio/vad_audio_worker.cpp

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

## 修改后 18：src/audio/vad_audio_worker.cpp

SHA256：`1ce7116fc5b7f97692b0a9c6d7fc79b481277071b624999e7f6d37527e72ffca`；539 行。

```cpp

#include "audio/vad_audio_worker.h"

#include "audio/audio_capture.h"
#include "audio/audio_preprocessor.h"
#include "app/profiling_inputs.h"

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
    Clock::time_point detected_start_at{};
    bool was_detected=false;
    auto observe_detection=[&]{
        const bool detected=SherpaOnnxVoiceActivityDetectorDetected(vad.get())!=0;
        if(detected && !was_detected)detected_start_at=Clock::now();
        was_detected=detected;
    };

    // ==================================================
    // 3. 从 VAD 中提取完整语音段
    // ==================================================

    auto drain_segments = [&]() -> bool
    {
        while (!SherpaOnnxVoiceActivityDetectorEmpty(
                   vad.get()))
        {
            const auto endpoint_observed_at=Clock::now();
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
            segment.trace=makeRequestTrace(segment.sequence);
            if(segment.trace){
                if(detected_start_at!=Clock::time_point{})segment.trace->mark("vad_detected_start",detected_start_at);
                segment.trace->mark("vad_endpoint_confirmed",endpoint_observed_at);
                segment.trace->mark("audio_read_anchor",latest_read_completed_at,static_cast<double>(latest_read_end_sample));
            }
            detected_start_at={};

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
                if(segment.trace){
                    const auto start_estimated=latest_read_completed_at-std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(double(latest_read_end_sample-speech_start)/kSampleRate));
                    segment.trace->mark("audio_start_estimated",start_estimated);
                    segment.trace->mark("audio_end_estimated",segment.audio_end_estimated_at);
                }
            }
            if(segment.trace)segment.trace->mark("audio_estimate_valid",Clock::now(),segment.timing_valid?1:0);

            // 完整语音已复制，可以从 VAD 内部删除。
            SherpaOnnxVoiceActivityDetectorPop(
                vad.get()
            );

            const auto sequence = segment.sequence;

            // VAD 完成语音段处理的时刻。
            segment.vad_ready_at = Clock::now();
            if(const char* folder=std::getenv("STAGE5_CAPTURE_AUDIO_FIXTURES")){
                if(segment.trace)segment.trace->mark("audio_fixture_write_begin");
                dumpProfilingAudio(folder,segment.sequence,segment.samples);
                if(segment.trace)segment.trace->mark("audio_fixture_write_end");
            }

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
                observe_detection();

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

## 修改前 19：src/router/intent_router.cpp

```cpp

#include "router/intent_router.h"

#include <algorithm>

// UTF-8 子串匹配的最小路由器：
// 只将询问当前相机画面的句子识别为 VISION；
// “摄像头驱动原理是什么”等知识问题仍为 TEXT。
RouteDecision IntentRouter::route(
    const std::string& question) const
{
    std::string normalized = question;

    // ASCII 英文字母转小写；
    // 中文 UTF-8 字节保持不变。
    std::transform(
        normalized.begin(),
        normalized.end(),
        normalized.begin(),
        [](unsigned char c) {
            return c >= 'A' && c <= 'Z'
                ? static_cast<char>(c + 32)
                : static_cast<char>(c);
        }
    );

    const char* vision_phrases[] = {
        u8"前面有什么",
        u8"摄像头里",
        u8"面前是什么",
        u8"看看前方",
        u8"当前画面",
        u8"现在的画面",
        u8"摄像头看到",
        u8"你看到了什么",
        u8"眼前有什么",
        u8"看看这个",
        u8"描述画面",
        u8"前方道路上有什么",
        u8"前方道路有什么",
        u8"前方有什么",
        u8"前面道路有什么",
        "what do you see",
        "what is in front",
        "what's in front",
        "camera view",
        "describe the scene",
        "current image"
    };

    for (const auto* phrase : vision_phrases)
    {
        if (normalized.find(phrase) !=
            std::string::npos)
        {
            return {
                RequestType::Vision,
                std::string("matched: ") + phrase
            };
        }
    }

    return {
        RequestType::Text,
        "default text rule"
    };
}

const char* requestTypeName(RequestType type)
{
    return type == RequestType::Vision
        ? "VISION"
        : "TEXT";
}
```

## 修改后 19：src/router/intent_router.cpp

SHA256：`514ac8a005e7165ae2ca1de251ca4c2bae6555bbf4d18d02e9c2afe9c3e6c765`；78 行。

```cpp

#include "router/intent_router.h"

#include <algorithm>
#include "common/request_trace.h"

// UTF-8 子串匹配的最小路由器：
// 只将询问当前相机画面的句子识别为 VISION；
// “摄像头驱动原理是什么”等知识问题仍为 TEXT。
RouteDecision IntentRouter::route(
    const std::string& question) const
{
    traceMark("router_begin");
    std::string normalized = question;

    // ASCII 英文字母转小写；
    // 中文 UTF-8 字节保持不变。
    std::transform(
        normalized.begin(),
        normalized.end(),
        normalized.begin(),
        [](unsigned char c) {
            return c >= 'A' && c <= 'Z'
                ? static_cast<char>(c + 32)
                : static_cast<char>(c);
        }
    );

    const char* vision_phrases[] = {
        u8"前面有什么",
        u8"摄像头里",
        u8"面前是什么",
        u8"看看前方",
        u8"当前画面",
        u8"现在的画面",
        u8"摄像头看到",
        u8"你看到了什么",
        u8"眼前有什么",
        u8"看看这个",
        u8"描述画面",
        u8"前方道路上有什么",
        u8"前方道路有什么",
        u8"前方有什么",
        u8"前面道路有什么",
        "what do you see",
        "what is in front",
        "what's in front",
        "camera view",
        "describe the scene",
        "current image"
    };

    for (const auto* phrase : vision_phrases)
    {
        if (normalized.find(phrase) !=
            std::string::npos)
        {
            traceMark("router_end",RequestTrace::Clock::now(),1);
            return {
                RequestType::Vision,
                std::string("matched: ") + phrase
            };
        }
    }

    traceMark("router_end",RequestTrace::Clock::now(),0);
    return {
        RequestType::Text,
        "default text rule"
    };
}

const char* requestTypeName(RequestType type)
{
    return type == RequestType::Vision
        ? "VISION"
        : "TEXT";
}
```

## 修改前 20：tests/async_pipeline_tests.cpp

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

## 修改后 20：tests/async_pipeline_tests.cpp

SHA256：`e400df065232c24908c63bffe56d3c0ecd14378bcb03814983ee2ca756931bc8`；150 行。

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
void testTraceOwnership() {
    auto trace=std::make_shared<RequestTrace>(777);std::weak_ptr<RequestTrace> weak=trace;
    {
        RequestTraceScope outer(trace);check(currentRequestTrace()==trace && image_profile_request_id==777,"trace scope enter");
        {RequestTraceScope empty({});check(!currentRequestTrace() && image_profile_request_id==0,"trace nested clear");}
        check(currentRequestTrace()==trace && image_profile_request_id==777,"trace scope restore");
    }
    check(!currentRequestTrace() && image_profile_request_id==0,"trace scope leaked TLS");
    TaskOptions options;options.trace=trace;std::string error;InferenceWorker inference(1);
    check(inference.start(error),"trace inference start");std::atomic<bool> infer_ok{false},done_ok{false};
    inference.submitTask(777,[&](const LLMStreamCallback&){infer_ok=currentRequestTrace()==trace && image_profile_request_id==777;return answer();},{},[&](std::uint64_t,const InferenceResult&,double){done_ok=currentRequestTrace()==trace;},options);
    check(inference.waitIdleFor(2s),"trace inference wait");inference.requestStop();inference.join();
    check(infer_ok && done_ok,"trace did not propagate through inference/callback");
    TTSService tts;AlsaPlaybackService playback;check(tts.initialize("fake",error) && playback.open("fake",16000,error),"trace fake init");
    std::atomic<bool> tts_ok{false};synth_hook=[&]{tts_ok=currentRequestTrace()==trace && image_profile_request_id==777;};
    TTSWorker worker(tts,playback,1);check(worker.start(error),"trace TTS start");
    worker.submit(777,"trace",{},options);check(worker.waitIdleFor(2s),"trace TTS wait");worker.requestStop();worker.join();synth_hook={};check(tts_ok,"trace did not propagate to TTS");
    ASRService asr;AudioBufferQueue queue(1);std::mutex output;std::atomic<bool> context_ok{false};
    ASRWorker consumer(queue,asr,output,{},[&](const std::string&,const AudioSegment& segment){context_ok=segment.sequence==777 && segment.trace==trace && currentRequestTrace()==trace;});
    AudioSegment segment;segment.sequence=777;segment.trace=trace;segment.samples={1};queue.push(std::move(segment));queue.close();consumer.start();consumer.join();check(consumer.ok() && context_ok,"trace ASR context callback");
    options.trace.reset();trace.reset();check(weak.expired(),"completed requests retained profiling ownership");
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
    testASRContinues();testBoundCancelExpireRestart();testStopModes();testAdmission();testTTS();testTraceOwnership();
    std::cout<<"PASS deterministic async pipeline: ASR progression, alternating FIFO, overload, cancel/expiry, restart, callback failures, ticket races, TTS. Fake services only.\n";return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
```

## 修改后 21：tests/request_profile_tests.cpp

SHA256：`b2d70ed7eab511c80e7ff249795f0800963ee0304b328938dacf5b52f8b6da25`；46 行。

```cpp
#include "common/request_trace.h"
#include "app/profiling_inputs.h"
#include <limits>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <thread>
namespace {
void fixtureChecks(const std::filesystem::path& log){
    const auto folder=log.parent_path()/("profiling_fixtures_"+std::to_string(RequestTrace::Clock::now().time_since_epoch().count()));
    if(!std::filesystem::create_directory(folder))throw std::runtime_error("fixture directory collision");
    auto rejects=[](auto action){bool failed=false;try{action();}catch(const std::exception&){failed=true;}if(!failed)throw std::runtime_error("invalid fixture accepted");};
    const std::vector<float> pcm{0.0f,0.5f,-0.5f};dumpProfilingAudio(folder,1,pcm);
    if(loadProfilingAudio(folder/"segment_1.f32")!=pcm)throw std::runtime_error("PCM fixture changed");
    rejects([&]{dumpProfilingAudio(folder,1,pcm);});
    {const float invalid=std::numeric_limits<float>::quiet_NaN();std::ofstream out(folder/"invalid.f32",std::ios::binary);out.write(reinterpret_cast<const char*>(&invalid),sizeof(invalid));}
    rejects([&]{loadProfilingAudio(folder/"invalid.f32");});
    {std::ofstream out(folder/"frame_0.nv12",std::ios::binary);const char nv12[6]={0,1,2,3,4,5};out.write(nv12,6);}
    auto metadata=[&](int stride){std::ofstream out(folder/"frame_0.json");out<<"{\"width\":2,\"height\":2,\"stride\":"<<stride<<",\"bytes\":6,\"frame_id\":7}";};
    metadata(2);auto frame=loadProfilingFrame(folder);
    if(frame->data.size()!=6||frame->width!=2||frame->data[5]!=5||frame->received_at!=std::chrono::steady_clock::time_point{})throw std::runtime_error("fixed frame ownership/timestamp");
    metadata(1);rejects([&]{loadProfilingFrame(folder);});
    for(const auto& file:std::filesystem::directory_iterator(folder))std::filesystem::remove(file.path());std::filesystem::remove(folder);
}
}
int main(int argc,char** argv) try {
    if(argc!=2)throw std::runtime_error("profile log path required");
#ifdef _WIN32
    _putenv_s("STAGE5_PROFILE",argv[1]);
#else
    setenv("STAGE5_PROFILE",argv[1],1);
#endif
    fixtureChecks(argv[1]);
    auto trace=makeRequestTrace(42);if(!trace)throw std::runtime_error("profile did not enable");
    const auto before=RequestTrace::Clock::now();trace->mark("begin",before);
    {RequestTraceScope scope(trace);traceMark("scoped");imageSample("test_stage",1.25,999,8,1);
     std::thread callback([trace]{trace->mark("sdk_callback");});callback.join();}
    if(currentRequestTrace() || image_profile_request_id)throw std::runtime_error("TLS leaked");
    trace->mark("end");std::ifstream input(argv[1]);std::stringstream data;data<<input.rdbuf();const auto text=data.str();
    for(const char* expected:{"\"request_id\":42","\"event\":\"begin\"","\"event\":\"scoped\"","\"event\":\"sdk_callback\"","\"event\":\"end\"","\"stage\":\"test_stage\"","\"id\":999","\"at_ns\":"})
        if(text.find(expected)==std::string::npos)throw std::runtime_error(expected);
    std::size_t count=0;for(char c:text)count+=c=='\n';if(count!=5)throw std::runtime_error("unexpected event count");
    std::cout<<"PASS request profiling: scoped request ID, distinct frame ID, explicit SDK callback, steady timestamps, flushed JSONL\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
```

## 修改后 22：tests/stage5_04_asr_bench.cpp

SHA256：`368ce743bd4b5ef867b2ee712baf163e42e67b83a2e51b97c0327d009ba124f2`；34 行。

```cpp
#include "audio/asr_service.h"
#include "common/request_trace.h"
#include <sherpa-onnx/c-api/c-api.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <memory>
#include <stdexcept>
#include <vector>
static std::string csvText(const std::string& value){std::string out="\"";for(char c:value){if(c=='"')out+='"';out+=c;}return out+'"';}
int main(int argc,char** argv) try {
    if(argc!=5)throw std::runtime_error("usage: asr_bench model_dir mono_16k_wave report_dir measured_repeats");
    const std::filesystem::path out(argv[3]);const int repeats=std::stoi(argv[4]);
    if(!std::filesystem::is_directory(out)||repeats<1||repeats>64)throw std::runtime_error("invalid report/repeats");
    std::unique_ptr<const SherpaOnnxWave,decltype(&SherpaOnnxFreeWave)> wave(SherpaOnnxReadWave(argv[2]),SherpaOnnxFreeWave);
    if(!wave||wave->sample_rate!=16000||wave->num_samples<=0)throw std::runtime_error("expected valid mono 16 kHz wave");
    std::vector<float> samples(wave->samples,wave->samples+wave->num_samples);wave.reset();
    ASRService service;std::string error;
    if(!service.initialize(std::string(argv[1])+"/model.int8.onnx",std::string(argv[1])+"/tokens.txt",error))throw std::runtime_error(error);
    std::ofstream csv(out/"asr_samples.csv");csv<<"iteration,phase,api_ms,wall_ms,audio_seconds,rtf,text\n"<<std::setprecision(12);
    std::string expected;
    for(int i=0;i<repeats+2;++i){
        auto trace=makeRequestTrace(i+1);RequestTraceScope scope(trace);std::string text;double latency=0;
        const auto start=RequestTrace::Clock::now();traceMark("asr_begin",start);
        if(!service.recognize(samples,text,latency,error))throw std::runtime_error(error);
        const auto end=RequestTrace::Clock::now();traceMark("asr_end",end);
        if(i==0)expected=text;else if(text!=expected)throw std::runtime_error("fixed input ASR answer changed");
        const double seconds=double(samples.size())/16000;
        csv<<i<<','<<(i==0?"first_use":i==1?"warmup":"measured")<<','<<latency<<','<<std::chrono::duration<double,std::milli>(end-start).count()<<','<<seconds<<','<<latency/(seconds*1000)<<','<<csvText(text)<<'\n'<<std::flush;
        std::cout<<"[ASRBench] sample="<<i<<" ms="<<latency<<" text="<<text<<'\n'<<std::flush;
    }
    service.shutdown();return 0;
}catch(const std::exception& e){std::cerr<<"[ASRBench ERROR] "<<e.what()<<'\n';return 1;}
```

## 修改后 23：tests/stage5_04_tts_bench.cpp

SHA256：`721bcf205fa82b4839da5ec001927e472a45ac3905878badf77a60196cfef962`；57 行。

```cpp
// Manual benchmark of the existing TTSService, including the frozen 5.3 library.
#include "audio/tts_service.h"
#include <sherpa-onnx/c-api/c-api.h>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#ifdef STAGE5_BENCH_TRACE
#include "common/request_trace.h"
#endif
using Clock=std::chrono::steady_clock;
static double ms(Clock::time_point a){return std::chrono::duration<double,std::milli>(Clock::now()-a).count();}
int main(int argc,char** argv) try {
    if(argc!=5)throw std::runtime_error("usage: tts_bench model_dir report_dir threads measured_repeats");
    const std::filesystem::path report(argv[2]);
    if(!std::filesystem::is_directory(report))throw std::runtime_error("report must already exist");
    const int threads=std::stoi(argv[3]),repeats=std::stoi(argv[4]);
    if(threads<1||threads>8||repeats<1||repeats>64)throw std::runtime_error("argument bounds");
    const std::string texts[]={u8"一加一等于二。","A computer monitor displaying a webpage with some text and images."};
    std::ofstream inputs(report/"inputs.txt");for(auto& text:texts)inputs<<text<<'\n';inputs.close();
    std::cout<<"[SDK] sherpa="<<SherpaOnnxGetVersionStr()<<" git="<<SherpaOnnxGetGitSha1()
             <<" ort="<<SherpaOnnxGetOnnxruntimeVersionStr()<<"\n"<<std::flush;
    TTSService tts;std::string error;const auto init=Clock::now();
    if(!tts.initialize(argv[1],error,threads,17))throw std::runtime_error(error);
    std::cout<<"[TTSInit] ms="<<ms(init)<<" threads="<<threads<<" sid=17 sample_rate="<<tts.sampleRate()<<"\n"<<std::flush;
    std::ofstream csv(report/"tts_samples.csv");
    csv<<"iteration,language,phase,threads,synthesis_ms,call_wall_ms,audio_seconds,rtf,samples,sample_rate,peak,rms,nonfinite,pcm_fnv64\n"<<std::setprecision(12);
    // Iteration 0 is first-use; iteration 1 warms both languages; the remaining N are measured.
    for(int i=0;i<repeats+2;++i)for(int language=0;language!=2;++language){
#ifdef STAGE5_BENCH_TRACE
        auto trace=makeRequestTrace(static_cast<std::uint64_t>(i*2+language+1));RequestTraceScope scope(trace);
        traceMark("tts_synthesis_begin");
#endif
        TTSAudio audio;auto start=Clock::now();
        if(!tts.synthesize(texts[language],audio,error))throw std::runtime_error(error);
#ifdef STAGE5_BENCH_TRACE
        traceMark("tts_api_return");
#endif
        const double wall=ms(start),seconds=double(audio.samples.size())/audio.sample_rate;
        if(audio.samples.empty()||audio.sample_rate!=24000)throw std::runtime_error("invalid PCM shape/rate");
        double peak=0,energy=0;std::size_t nonfinite=0;std::uint64_t hash=14695981039346656037ULL;
        for(float x:audio.samples){if(!std::isfinite(x)){++nonfinite;continue;}peak=std::max(peak,double(std::abs(x)));energy+=double(x)*x;
            unsigned char bytes[sizeof(float)];std::memcpy(bytes,&x,sizeof(x));for(auto c:bytes){hash^=c;hash*=1099511628211ULL;}}
        const char* phase=i==0?"first_use":i==1?"warmup":"measured";
        csv<<i<<','<<(language==0?"zh":"en")<<','<<phase<<','<<threads<<','<<audio.synthesis_ms<<','<<wall<<','<<seconds<<','<<audio.synthesis_ms/(seconds*1000)<<','<<audio.samples.size()<<','<<audio.sample_rate<<','<<peak<<','<<std::sqrt(energy/audio.samples.size())<<','<<nonfinite<<','<<hash<<'\n'<<std::flush;
        if(i==2){std::ofstream pcm(report/(language==0?"zh.f32":"en.f32"),std::ios::binary);pcm.write(reinterpret_cast<const char*>(audio.samples.data()),audio.samples.size()*sizeof(float));if(!pcm)throw std::runtime_error("PCM dump failed");}
        std::cout<<"[TTSBench] iteration="<<i<<" language="<<(language==0?"zh":"en")<<" phase="<<phase<<" synth_ms="<<audio.synthesis_ms<<" wall_ms="<<wall<<" audio_seconds="<<seconds<<" nonfinite="<<nonfinite<<"\n"<<std::flush;
        if(nonfinite)throw std::runtime_error("nonfinite waveform");
    }
    tts.shutdown();std::cout<<"[TTSBench] complete\n";return 0;
}catch(const std::exception& e){std::cerr<<"[TTSBench ERROR] "<<e.what()<<'\n';return 1;}
```

## 修改后 24：tests/stage5_04_vision_bench.cpp

SHA256：`48ed0c483af75f81b3554e19d92c3a6577791b9d2d93e881b52bfe609da4e7c2`；38 行。

```cpp
#include "ai/rk_backends.h"
#include "ai/vlm_engine.h"
#include "common/request_trace.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
namespace fs=std::filesystem;
static std::shared_ptr<ImageFrame> loadFrame(const fs::path& folder,int index){
    const auto name="frame_"+std::to_string(index);std::ifstream meta(folder/(name+".json"));std::stringstream contents;contents<<meta.rdbuf();const auto text=contents.str();
    auto field=[&](const char* key){std::smatch m;if(!std::regex_search(text,m,std::regex(std::string("\"")+key+"\":([0-9]+)")))throw std::runtime_error(std::string("missing ")+key);return std::stoull(m[1]);};
    auto frame=std::make_shared<ImageFrame>();frame->width=field("width");frame->height=field("height");frame->pixel_format=0x3231564e;
    frame->plane_strides={static_cast<std::uint32_t>(field("stride"))};frame->plane_sizes={static_cast<std::size_t>(field("bytes"))};frame->frame_id=field("frame_id");frame->data.resize(field("bytes"));
    std::ifstream input(folder/(name+".nv12"),std::ios::binary);input.read(reinterpret_cast<char*>(frame->data.data()),frame->data.size());if(!input)throw std::runtime_error("fixture read failed");
    return frame;
}
static std::string csvText(const std::string& value){std::string out="\"";for(char c:value){if(c=='"')out+='"';out+=c;}return out+'"';}
int main(int argc,char** argv)try{
    if(argc!=6)throw std::runtime_error("usage: vision_bench language.rkllm vision.rknn fixture_dir report_dir measured_repeats");
    const fs::path report(argv[4]);const int repeats=std::stoi(argv[5]);if(!fs::is_directory(report)||repeats<1||repeats>64)throw std::runtime_error("invalid report/repeats");
    std::shared_ptr<ImageFrame> frames[3];for(int i=0;i<3;++i)frames[i]=loadFrame(argv[3],i);
    VLMEngine engine(std::make_unique<RK3576VLMBackend>());std::string error;
    if(!engine.initialize(BackendConfig{argv[1],argv[2]},error))throw std::runtime_error(error);
    std::ofstream csv(report/"vision_samples.csv");csv<<"iteration,phase,fixture,frame_id,latency_ms,decoder_first_text_ms,success,answer\n"<<std::setprecision(12);
    for(int i=0;i<repeats+2;++i){
        auto trace=makeRequestTrace(i+1);RequestTraceScope scope(trace);traceMark("inference_begin");
        const auto result=engine.infer(frames[i%3],"What do you see? Answer briefly.");
        traceMark(result.success?"inference_end":"inference_failed");
        csv<<i<<','<<(i==0?"first_use":i==1?"warmup":"measured")<<','<<i%3<<','<<result.frame_id<<','<<result.latency_ms<<','<<result.first_text_ms<<','<<result.success<<','<<csvText(result.text)<<'\n'<<std::flush;
        std::cout<<"[VisionBench] sample="<<i<<" fixture="<<i%3<<" success="<<result.success<<" ms="<<result.latency_ms<<" answer="<<result.text<<'\n'<<std::flush;
        if(!result.success)throw std::runtime_error(result.error_message);
    }
    engine.shutdown();return 0;
}catch(const std::exception& e){std::cerr<<"[VisionBench ERROR] "<<e.what()<<'\n';return 1;}
```

## 修改后 25：tools/stage5_04_analyze.py

SHA256：`aac74b4fcc7753c0e0a4fec566d7db532a34691553321bb64596be67ab810482`；166 行。

```python
#!/usr/bin/env python3
"""Analyze raw Stage 5.4 CSV/JSONL; missing observations remain null, never zero."""
from pathlib import Path
import argparse,csv,json,math,re,statistics,collections
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jsonlines(p):return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
def stats(values):
    xs=sorted(x for x in values if x is not None and math.isfinite(x))
    if not xs:return None
    return dict(n=len(xs),mean=statistics.mean(xs),p50=xs[math.ceil(len(xs)*.5)-1],p95=xs[math.ceil(len(xs)*.95)-1],minimum=xs[0],maximum=xs[-1])
PAIRS={
 'vad_endpoint_host_estimate_ms':('audio_end_estimated','vad_endpoint_confirmed'),
 'asr_enqueue_to_first_submit_ms':('asr_enqueued','alsa_first_submit_begin'),
 'asr_enqueue_to_playback_end_ms':('asr_enqueued','alsa_drain_complete'),
 'asr_queue_ms':('asr_enqueued','asr_dequeued'),
 'asr_preprocess_ms':('asr_dequeued','asr_begin'),
 'asr_api_ms':('asr_begin','asr_end'),
 'asr_decode_ms':('asr_decode_begin','asr_decode_end'),
 'router_ms':('router_begin','router_end'),
 'inference_queue_ms':('inference_enqueued','inference_dequeued'),
 'inference_service_ms':('inference_begin','inference_end'),
 'decoder_ms':('decoder_begin','decoder_end'),
 'decoder_first_text_chunk_ms':('decoder_begin','first_text_chunk'),
 'inference_first_text_chunk_ms':('inference_begin','first_text_chunk'),
 'tts_queue_ms':('tts_enqueued','tts_dequeued'),
 'tts_generate_api_ms':('tts_generate_begin','tts_generate_end'),
 'tts_first_audio_callback_ms':('tts_generate_begin','tts_first_audio_callback'),
 'tts_pcm_copy_ms':('tts_pcm_copy_begin','tts_pcm_copy_end'),
 'tts_full_audio_ready_ms':('tts_synthesis_begin','tts_full_audio_ready'),
 'tts_api_return_ms':('tts_synthesis_begin','tts_api_return'),
 'playback_conversion_ms':('playback_convert_begin','playback_convert_end'),
 'first_submit_call_duration_ms':('alsa_first_submit_begin','alsa_first_submit_complete'),
 'synthesis_to_first_submit_ms':('tts_synthesis_begin','alsa_first_submit_begin'),
 'tts_enqueue_to_first_submit_ms':('tts_enqueued','alsa_first_submit_begin'),
 'playback_call_ms':('playback_convert_begin','alsa_drain_complete'),
 'alsa_submit_to_drain_ms':('alsa_first_submit_begin','alsa_drain_complete'),
 'alsa_drain_wait_ms':('alsa_drain_begin','alsa_drain_complete'),
 'business_to_first_submit_ms':('business_dispatch_begin','alsa_first_submit_begin'),
 'business_to_playback_end_ms':('business_dispatch_begin','alsa_drain_complete'),
 'vad_detected_to_first_submit_ms':('vad_detected_start','alsa_first_submit_begin'),
 'speech_start_host_estimate_to_submit_ms':('audio_start_estimated','alsa_first_submit_begin'),
 'speech_end_host_estimate_to_submit_ms':('audio_end_estimated','alsa_first_submit_begin'),
 'speech_start_host_estimate_to_playback_end_ms':('audio_start_estimated','alsa_drain_complete'),
 'speech_end_host_estimate_to_playback_end_ms':('audio_end_estimated','alsa_drain_complete')}
def procstat(text):
    x=text[text.rfind(')')+2:].split()
    return dict(ticks=int(x[11])+int(x[12]),cpu=int(x[36]))
def resources(path):
    if not path.exists():return None
    rows=jsonlines(path);cpu=[];rss=[];hwm=[];threads=[];frequencies=collections.defaultdict(list);temps=collections.defaultdict(list);npu=collections.defaultdict(list);affinity=collections.Counter()
    previous=None
    for row in rows:
        if 'stat' not in row:continue
        current=procstat(row['stat']);now=row['monotonic']
        if previous:
            dt=now-previous[0]
            if dt>0:cpu.append(dict(monotonic=now,percent_one_core=100*(current['ticks']-previous[1])/(100*dt)))
        previous=(now,current['ticks'])
        for line in row['status'].splitlines():
            key,value=line.split(':',1)
            if key in {'VmRSS','VmHWM'}:(rss if key=='VmRSS' else hwm).append(int(value.split()[0])/1024)
            if key=='Threads':threads.append(int(value))
        for task in row.get('tasks',{}).values():
            for allowed in task.get('allowed',[]):affinity[allowed.split(':',1)[-1].strip()]+=1
        for name,value in row.get('sysfs',{}).items():
            if not isinstance(value,str):continue
            if 'scaling_cur_freq' in name:frequencies[name].append(int(value))
            elif '/thermal/' in name and name.endswith('/temp'):temps[name].append(int(value)/1000)
            elif 'npu' in name:npu[name].append(value)
    # The board reports CLK_TCK in system_before.json. Do not assume host HZ.
    hz=load(path.parent/'system_before.json').get('clock_ticks') if (path.parent/'system_before.json').exists() else None
    if hz:
        for row in cpu:row['percent_one_core']*=100/hz
    else:cpu=[]
    start=next((x['monotonic'] for x in rows if 'monotonic' in x),0)
    warm=[x['percent_one_core'] for x in cpu if x['monotonic']>=start+80]
    return dict(samples=len(rows),cpu_percent_one_core=stats([x['percent_one_core'] for x in cpu]),cpu_percent_after_80s=stats(warm),rss_MiB=stats(rss),VmHWM_observed_MiB=stats(hwm),threads=stats(threads),affinity_sample_counts=dict(affinity),cpu_frequency_kHz={k:stats(v) for k,v in frequencies.items()},temperature_C={k:stats(v) for k,v in temps.items()},npu_raw_unique={k:sorted(set(v)) for k,v in npu.items()},npu_utilization_percent=None,cpu_samples=cpu)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);args=parser.parse_args()
    base=args.collection/'files/reports/stage5_04_board';out=ROOT/'reports/stage5_04_local/analysis';out.mkdir(exist_ok=True)
    cases={};requests=[];table=[];tts_raw=[];asr_raw=[];vision_raw=[]
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():continue
        case={};name=folder.name;phases={}
        if (folder/'result.json').exists():case['result']=load(folder/'result.json')
        if (folder/'resources.jsonl').exists():case['resources']=resources(folder/'resources.jsonl')
        if (folder/'terminal.log').exists():
            terminal=(folder/'terminal.log').read_text(encoding='utf-8',errors='replace')
            if (folder/'stderr.log').exists():terminal+='\n'+(folder/'stderr.log').read_text(encoding='utf-8',errors='replace')
            counters={}
            for line in terminal.splitlines():
                marker=re.match(r'^\[(QueueStats|AudioQueueStats|PipelineStats|CameraCounters|FramePool|ALSA)\] (.*)',line)
                if not marker:continue
                values={k:(float(v) if '.' in v else int(v)) if re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?',v) else v for k,v in re.findall(r'(\w+)=([^ ]+)',marker[2])}
                key=marker[1]+('/'+values['stage'] if 'stage' in values else '');counters[key]=values
            case['terminal_counters']=counters
            case['terminal_errors']={'profile_error':terminal.count('[ImageProfile ERROR]'),'asr_error':terminal.count('[ASR ERROR]'),'timeouts':terminal.count('[Timeout]'),'warnings_existing_unknown_phonemes':terminal.count('Skip unknown phonemes')}
            case['answers']={kind:{key:text for key,text in re.findall(pattern,terminal)} for kind,pattern in [('VISION',r'\[VLM Answer #(\d+)\] ([^\n]*)'),('TEXT',r'\[LLM #(\d+)\] ([^\n]*)')]}
            case['downstream_cancelled_ids']=re.findall(r'\[Pipeline downstream cancelled #(\d+)\]',terminal)
        if (folder/'user_feedback.json').exists():case['user_feedback']=load(folder/'user_feedback.json')
        for kind,filename,metrics,raw in [('tts','tts_samples.csv',['synthesis_ms','call_wall_ms','audio_seconds','rtf','peak','rms'],tts_raw),('asr','asr_samples.csv',['api_ms','wall_ms','audio_seconds','rtf'],asr_raw),('vision','vision_samples.csv',['latency_ms','decoder_first_text_ms'],vision_raw)]:
            p=folder/filename
            if not p.exists():continue
            values=list(csv.DictReader(p.open(encoding='utf-8')))
            for row in values:
                raw.append(dict(case=name,**row))
                key=int(row['iteration'])*2+(2 if row.get('language')=='en' else 1) if kind=='tts' else int(row['iteration'])+1
                phases[key]=(row['phase'],row.get('language','vision' if kind=='vision' else 'asr'))
            groups={}
            for row in values:groups.setdefault((row.get('language','fixture_'+row['fixture'] if kind=='vision' else 'zh'),row['phase']),[]).append(row)
            case[kind]={}
            for (language,phase),rows in groups.items():
                key=language+'/'+phase;case[kind][key]={metric:stats([float(r[metric]) for r in rows]) for metric in metrics}
                for metric,s in case[kind][key].items():
                    if s:table.append(dict(case=name,group=kind+'/'+key,metric=metric,**s))
        profile=folder/'profile.jsonl'
        if profile.exists():
            grouped=collections.defaultdict(dict);other=collections.defaultdict(list);counts=collections.Counter();session=[]
            for row in jsonlines(profile):
                if row.get('kind')=='request' and row['request_id']!=0:
                    key=row['request_id'];event=row['event']
                    if event in grouped[key]:raise ValueError(f'duplicate event {name}/{key}/{event}')
                    grouped[key][event]=row
                    if any(x in event for x in ['rejected','cancelled','expired','failed','dropped']):counts[event]+=1
                elif row.get('kind')=='request':session.append(row)
                elif 'stage' in row:other[row['stage']].append(row['ms'])
            case['session_events']=session;case['profile_counts']=dict(counts);case['profile_requests']=len(grouped);case['profile_events']={str(k):v for k,v in grouped.items()}
            case['request_metrics']={};byroute=collections.defaultdict(list)
            for key,events in grouped.items():
                row={'case':name,'request_id':key,'route':'VISION' if events.get('router_end',{}).get('value')==1 else 'TEXT' if 'router_end' in events else 'NOT_ROUTED','phase':phases.get(key,('interactive_or_replay',''))[0]}
                if name in ('baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t'):row['phase']='first_pair' if key<=2 else 'warm_pair'
                row['status']='success' if 'request_complete' in events else 'cancelled' if any('cancelled' in x for x in events) else 'expired' if any('expired' in x for x in events) else 'rejected' if any('rejected' in x for x in events) else 'failed' if any('failed' in x for x in events) else 'cancelled_downstream' if str(key) in case.get('downstream_cancelled_ids',[]) else 'stage_only_or_incomplete'
                for metric,(first,last) in PAIRS.items():
                    row[metric]=(events[last]['at_ns']-events[first]['at_ns'])/1e6 if first in events and last in events else None
                    if row[metric] is not None and row[metric]<0:raise ValueError(f'negative duration {name}/{key}/{metric}')
                requests.append(row);group=row['route']+'/'+row['phase']+'/'+row['status']+('/'+phases[key][1] if key in phases else '');byroute[group].append(row)
            for route,rows in byroute.items():
                case['request_metrics'][route]={metric:stats([r[metric] for r in rows]) for metric in PAIRS}
                for metric,s in case['request_metrics'][route].items():
                    if s:table.append(dict(case=name,group=route,metric=metric,**s))
            case['image_stages']={k:stats(v) for k,v in other.items()}
            for stage,value in case['image_stages'].items():
                if value:table.append(dict(case=name,group='image/all_observed_including_first_use',metric=stage,**value))
        for p in folder.glob('ort_profile*.json'):
            data=load(p);runs=[x for x in data if x.get('name')=='model_run'];nodes=[x for x in data if x.get('cat')=='Node' and x.get('ph')=='X']
            op=collections.defaultdict(list)
            for node in nodes:op[node.get('args',{}).get('op_name','unknown')].append(node.get('dur',0)/1000)
            case['ort_profile']={'file':str(p.relative_to(base)),'model_run_ms':stats([x['dur']/1000 for x in runs]),'model_run_events':runs,'operator_sum_ms':{k:sum(v) for k,v in sorted(op.items(),key=lambda x:-sum(x[1]))},'note':'ORT tracing is a separate diagnostic, not the fair speed comparison; operator sums can overlap threads'}
        if case.get('resources'):
            resource=case['resources']
            for metric in ['cpu_percent_one_core','cpu_percent_after_80s','rss_MiB','VmHWM_observed_MiB','threads']:
                if resource.get(metric):table.append(dict(case=name,group='resources/observed',metric=metric,**resource[metric]))
            for category in ['cpu_frequency_kHz','temperature_C']:
                for sensor,value in resource[category].items():
                    if value:table.append(dict(case=name,group='resources/'+category,metric=sensor,**value))
        if case:cases[name]=case
    def write_csv(name,rows):
        if not rows:return
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (out/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    write_csv('statistics.csv',table);write_csv('requests.csv',requests);write_csv('tts_raw.csv',tts_raw);write_csv('asr_raw.csv',asr_raw);write_csv('vision_raw.csv',vision_raw)
    result={'collection':str(args.collection),'quantiles':'nearest-rank','clock':'C++ steady_clock; recorded raw monotonic ns','cases':cases,'notes':['Request IDs reset per process; pair ID with case name','First text chunk is observable; true token-granular TTFT unmeasured','ALSA submission/drain is not acoustic timing','Estimated speech clocks depend on capture sample mapping; not ADC timestamps','NPU load sysfs raw values retained, utilization unvalidated','Missing values remain null; no synthetic samples']}
    (out/'performance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ANALYZED',len(cases),'cases;',len(requests),'requests;',len(tts_raw),'TTS rows;',len(asr_raw),'ASR rows;',len(vision_raw),'vision rows')
if __name__=='__main__':main()
```

## 修改后 26：tools/stage5_04_collect.py

SHA256：`bc0c2a10daa4642caf452d860bacc9ad81fe297b091f23e434215cf942c4edb5`；41 行。

```python
#!/usr/bin/env python3
"""Read only the isolated Stage 5.4 reports, preserving raw logs locally."""
from datetime import datetime
import hashlib,json,tarfile,argparse
from pathlib import Path,PurePosixPath
import stage5_phase2_deploy as transport

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--complete-only',action='store_true');args=parser.parse_args()
 report=transport.ROOT/'reports/stage5_04_board'/('collected_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
 report.mkdir()
 payload=('ONLY_COMPLETE='+repr(args.complete_only)+'\n').encode()+b'''from pathlib import Path
import sys,tarfile
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
selected=root/'reports/stage5_04_board'
assert selected.is_dir() and not root.is_symlink()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as package:
 for p in sorted(selected.rglob('*')):
  if p.is_file() and not p.is_symlink():
   parts=p.relative_to(selected).parts
   if ONLY_COMPLETE and len(parts)>1 and parts[0] not in {'baseline_5_3_source','raw_baseline_build'} and not (selected/parts[0]/'result.json').exists():continue
   assert p.resolve().is_relative_to(selected) and p.stat().st_size<128*1024**2
   package.add(p,arcname=str(p.relative_to(root)),recursive=False)
'''
 code=transport.run_step(report,'collection',transport.remote_command(),payload,120,binary=True)
 if code:return code
 destination=report/'files';destination.mkdir();manifest=[];total=0
 with tarfile.open(report/'collection.tgz','r:gz') as package:
  for item in package:
   relative=PurePosixPath(item.name)
   assert item.isfile() and not relative.is_absolute() and '..' not in relative.parts
   assert relative.parts[:2]==('reports','stage5_04_board') and item.size<128*1024**2
   total+=item.size;assert total<512*1024**2
   target=destination/Path(*relative.parts);assert target.resolve().is_relative_to(destination.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);content=package.extractfile(item).read()
   with target.open('xb') as output:output.write(content)
   manifest.append(dict(file=item.name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
 (report/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('COLLECTED',report,'files',len(manifest),'bytes',total)
 return 0
if __name__=='__main__':raise SystemExit(main())
```

## 修改后 27：tools/stage5_04_export.py

SHA256：`5e164943bd2ea03511ab34ebf368a89e924d636afd2b501d5852661933519355`；78 行。

```python
#!/usr/bin/env python3
"""Export Stage 5.4 full current source, hashes and Git-format patch; no remote writes."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def main():
 before=ROOT/'backups/stage5_04_before';report=ROOT/'reports/stage5_04_local'
 baseline=json.loads((report/'baseline_manifest.json').read_text())
 assert all(sha(before/r['file'])==r['sha256'] for r in baseline),'baseline snapshot drift'
 paths={Path('CMakeLists.txt')}
 for directory in ['include','src','tests','config']:
  paths.update(p.relative_to(ROOT) for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.h','.cpp','.hpp','.cmake','.txt','.tsv'})
 paths.update(Path(row['file']) for row in baseline)
 paths.update(p.relative_to(ROOT) for p in (ROOT/'tools').glob('stage5_04*.py'))
 paths.update(p.relative_to(ROOT) for p in (ROOT/'docs').glob('stage5_04*.md'))
 changed=sorted(p for p in paths if sha(before/p)!=sha(ROOT/p))
 source=[p for p in changed if p.parts[0]!='docs']
 appendix=['# 5.4 当前修改源码全文\n\n','由 `tools/stage5_04_export.py` 从真实文件生成。逐句语义解释见 [stage5_04_statement_notes.md](stage5_04_statement_notes.md)，架构与实测见 [stage5_04_performance_profiling.md](stage5_04_performance_profiling.md)。本附录不省略入口及测试，不代替板端版本哈希或执行证据。\n\n']
 for i,p in enumerate(source,1):
  lang='cmake' if p.name=='CMakeLists.txt' else {'.py':'python','.sh':'bash','.tsv':'text','.ps1':'powershell'}.get(p.suffix,'cpp')
  content=(ROOT/p).read_text(encoding='utf-8-sig')
  if (before/p).exists():
   previous=(before/p).read_text(encoding='utf-8-sig');appendix.append(f'## 修改前 {i}：{p.as_posix()}\n\n```{lang}\n{previous.rstrip()}\n```\n\n')
  appendix.append(f'## 修改后 {i}：{p.as_posix()}\n\nSHA256：`{sha(ROOT/p)}`；{len(content.splitlines())} 行。\n\n```{lang}\n{content.rstrip()}\n```\n\n')
 (ROOT/'docs/stage5_04_source_appendix.md').write_text(''.join(appendix),encoding='utf-8',newline='\n')
 changed=sorted(set(changed+[Path('docs/stage5_04_source_appendix.md')]))
 manifest=[dict(file=p.as_posix(),before_sha256=sha(before/p),after_sha256=sha(ROOT/p),status='modified' if (before/p).exists() else 'added') for p in changed]
 # Use real git diff --no-index, including byte-level line-ending changes.
 scratch=Path(tempfile.mkdtemp(prefix='stage5_04_diff_'));patch=[]
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
 invariant_paths=['src/video/image_preprocessor.cpp','include/video/image_preprocessor.h','include/video/owned_frame_pool.h','src/video/video_capture.cpp','src/video/camera_service.cpp','src/video/latest_frame_buffer.cpp','src/audio/audio_capture.cpp','src/ai/inference_worker.cpp']
 invariants=[dict(file=n,before=sha(before/n),after=sha(ROOT/n),unchanged=sha(before/n)==sha(ROOT/n)) for n in invariant_paths]
 def block(text,token):
  start=text.index(token);brace=text.index('{',start);depth=1;i=brace+1
  while depth:
   if text[i]=='{':depth+=1
   elif text[i]=='}':depth-=1
   i+=1
  return text[start:i]
 old=(before/'src/audio/asr_llm_tts_smoke.cpp').read_text(encoding='utf-8');new=(ROOT/'src/audio/asr_llm_tts_smoke.cpp').read_text(encoding='utf-8')
 signal_same=block(old,'class StopSignals')==block(new,'class StopSignals')
 candidate=json.loads((report/'candidate_v3_deployment_manifest.json').read_text())
 current_matches=all(sha(ROOT/r['file'])==r['sha256'] for r in candidate)
 parameter_sections={}
 for name,start,end in [('src/audio/tts_service.cpp','    SherpaOnnxGenerationConfig gen{};','    using AudioDeleter'),('src/ai/rkllm_backend.cpp','    RKLLMInput input{};','    RunContext context;'),('src/ai/rk3576_vlm_backend.cpp','    std::string prompt = \"<image>\"','    GenerationState state;')]:
  a=(before/name).read_text(encoding='utf-8');b=(ROOT/name).read_text(encoding='utf-8')
  extract=lambda text:text[text.index(start):text.index(end,text.index(start))]
  parameter_sections[name]=extract(a)==extract(b)
 assert all(parameter_sections.values()),parameter_sections
 (report/'source_invariants.json').write_text(json.dumps(dict(checks=invariants,model_generation_parameters_unchanged=parameter_sections,StopSignals_unchanged=signal_same,final_source_matches_ARM64_candidate_v3=current_matches,scope='Source equality only; runtime evidence is separate'),indent=2))
 assert signal_same and current_matches and all(item['unchanged'] for item in invariants)
 print('EXPORTED',len(source),'source files;',len(manifest),'changes; patch check',result.returncode)
if __name__=='__main__':main()
```

## 修改后 28：tools/stage5_04_local_build.py

SHA256：`fff26f2ffe539373cf5f28ddfb9d5dae0e8263a351e594db016c22861b6f1902`；29 行。

```python
#!/usr/bin/env python3
"""Portable-only validation, explicitly not RK3576/SDK verification."""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args();assert args.label.isidentifier()
    report=ROOT/'reports/stage5_04_local'/args.label;report.mkdir()
    scratch=Path(tempfile.mkdtemp(prefix='rk3576_stage5_04_'));source=scratch/'source';source.mkdir();build=scratch/'build'
    selected=[ROOT/'CMakeLists.txt']
    for name in ['include','src','tests']:
        selected.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and p.suffix in {'.h','.hpp','.cpp','.cmake','.tsv','.txt'})
    manifest=[]
    for path in selected:
        rel=path.relative_to(ROOT);p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,p);manifest.append({'file':rel.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (report/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    commands=[('configure',['cmake','-S',str(source),'-B',str(build),'-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Debug','-DBUILD_TESTING=ON','-DBUILD_WITH_RKLLM=OFF','-DBUILD_WITH_VLM=OFF','-DENABLE_SHERPA_ASR=OFF'],90),('build',['cmake','--build',str(build),'--parallel','3'],240),('ctest',['ctest','--test-dir',str(build),'--output-on-failure','--timeout','30','--output-junit',str(report/'ctest.xml')],120)]
    results=[]
    for label,command,limit in commands:
        start=time.monotonic()
        with (report/(label+'.stdout.log')).open('wb') as out,(report/(label+'.stderr.log')).open('wb') as err:
            code=subprocess.run(command,stdout=out,stderr=err,timeout=limit).returncode
        value={'command':command,'returncode':code,'seconds':time.monotonic()-start};results.append(value);(report/(label+'.result.json')).write_text(json.dumps(value,indent=2))
        print(label,code,round(value['seconds'],3),flush=True)
        if code:
            print((report/(label+'.stdout.log')).read_text(encoding='utf-8',errors='replace')[-6000:]);print((report/(label+'.stderr.log')).read_text(encoding='utf-8',errors='replace')[-5000:]);break
    (report/'result.json').write_text(json.dumps({'platform':'Windows portable SDK off','hardware_verification':False,'steps':results,'successful':len(results)==3 and all(x['returncode']==0 for x in results)},indent=2))
    return 0 if len(results)==3 and all(x['returncode']==0 for x in results) else 1
if __name__=='__main__':raise SystemExit(main())
```

## 修改后 29：tools/stage5_04_plot.py

SHA256：`31c5914ba011e18f50b017e1564ec9324b7b389f32c20c973372ebee49038568`；52 行。

```python
#!/usr/bin/env python3
"""Make shareable plots from measured CSV/JSON; no illustrative/synthetic samples."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--before',required=True);parser.add_argument('--after',required=True);parser.add_argument('--pipeline-case');args=parser.parse_args()
    folder=ROOT/'reports/stage5_04_local/analysis';out=ROOT/'reports/stage5_04_local/plots';out.mkdir(exist_ok=True)
    raw=list(csv.DictReader((folder/'tts_raw.csv').open(encoding='utf-8')))
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
    for ax,language in zip(axes,['zh','en']):
        a=[float(r['synthesis_ms'])/1000 for r in raw if r['case']==args.before and r['language']==language and r['phase']=='measured']
        b=[float(r['synthesis_ms'])/1000 for r in raw if r['case']==args.after and r['language']==language and r['phase']=='measured']
        if not a or not b:raise ValueError('missing measured input groups')
        ax.boxplot([a,b],labels=[f'Before n={len(a)}',f'After n={len(b)}'],showmeans=True)
        for i,values in enumerate([a,b],1):ax.scatter(np.full(len(values),i),values,s=9,alpha=.45)
        ax.set_title('Chinese fixed text' if language=='zh' else 'English fixed text');ax.set_ylabel('Generate API latency (s)');ax.grid(axis='y',alpha=.25)
    fig.suptitle('Same RK3576 / model / speaker 17 / speed 1 / text; warm measurements')
    fig.savefig(out/'tts_latency.png',dpi=160);fig.savefig(out/'tts_latency.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,language in zip(axes,['zh','en']):
        for case,label in [(args.before,'Before'),(args.after,'After')]:
            values=sorted(float(r['rtf']) for r in raw if r['case']==case and r['language']==language and r['phase']=='measured')
            ax.step(values,np.arange(1,len(values)+1)/len(values),where='post',label=f'{label} n={len(values)}')
        ax.set_title('Chinese' if language=='zh' else 'English');ax.set_xlabel('RTF = synthesis / generated duration');ax.set_ylabel('Empirical CDF');ax.grid(alpha=.25);ax.legend()
    fig.savefig(out/'tts_rtf_cdf.png',dpi=160);fig.savefig(out/'tts_rtf_cdf.svg');plt.close(fig)
    data=json.loads((folder/'performance.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained')
    for case,label in [(args.before,'Before'),(args.after,'After')]:
        samples=data['cases'][case]['resources']['cpu_samples']
        if samples:
            start=samples[0]['monotonic'];axes[0].plot([x['monotonic']-start for x in samples],[x['percent_one_core'] for x in samples],label=label)
        axes[1].bar(label,data['cases'][case]['resources']['rss_MiB']['maximum'])
    axes[0].set_ylabel('Process CPU % (one core = 100%)');axes[0].set_xlabel('Seconds since first process sample');axes[0].legend();axes[0].grid(alpha=.25)
    axes[1].set_ylabel('Sampled peak RSS (MiB)');axes[1].set_title('Same standalone TTS workload; not full multimodal process memory')
    fig.savefig(out/'tts_resources.png',dpi=160);fig.savefig(out/'tts_resources.svg');plt.close(fig)
    if args.pipeline_case:
        case=data['cases'][args.pipeline_case];rows=case['profile_events'];fig,ax=plt.subplots(figsize=(11,4.5),layout='constrained');labels=[]
        spans=[('ASR','asr_begin','asr_end'),('Inference queue','inference_enqueued','inference_dequeued'),('Inference','inference_begin','inference_end'),('TTS queue','tts_enqueued','tts_dequeued'),('TTS generate','tts_generate_begin','tts_generate_end'),('Playback call','playback_convert_begin','alsa_drain_complete')]
        colors=plt.get_cmap('tab10')
        for y,(id,events) in enumerate(rows.items()):
            origin=min(v['at_ns'] for v in events.values());labels.append('Request '+id)
            for j,(label,a,b) in enumerate(spans):
                if a in events and b in events:ax.barh(y,(events[b]['at_ns']-events[a]['at_ns'])/1e9,left=(events[a]['at_ns']-origin)/1e9,color=colors(j),label=label if y==0 else None)
        ax.set_yticks(range(len(labels)),labels);ax.set_xlabel('Seconds relative to each request first recorded timestamp');ax.set_title(args.pipeline_case+' (submission timing is not acoustic output)');ax.legend(loc='upper left',bbox_to_anchor=(1,1));ax.grid(axis='x',alpha=.25)
        fig.savefig(out/'pipeline_breakdown.png',dpi=160);fig.savefig(out/'pipeline_breakdown.svg');plt.close(fig)
    print('PLOTS',out)
if __name__=='__main__':main()
```

## 修改后 30：tools/stage5_04_prepare.py

SHA256：`247b9e470e82661320d18326990ce2659c64f608ac7e2f5c38118837d2e3d3c3`；58 行。

```python
#!/usr/bin/env python3
"""Prepare an exclusive Stage5.4 source/build payload, never touch accepted builds."""
from pathlib import Path
import argparse,base64,hashlib,json
import stage5_phase2_deploy as transport
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=['baseline','candidate'],required=True);parser.add_argument('--revision',choices=['v1','v2','v3'],default='v1');args=parser.parse_args();suffix='' if args.revision=='v1' else '_'+args.revision
 baseline={r['file']:r['sha256'] for r in json.loads((ROOT/'reports/stage5_04_local/baseline_manifest.json').read_text(encoding='utf-8'))}
 selected=[Path('CMakeLists.txt')]
 for folder in ['include','src','tests']:
  selected.extend(p.relative_to(ROOT) for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.h','.hpp','.cpp','.tsv','.txt','.cmake'})
 rows=[]
 snapshot=ROOT/'reports/stage5_04_local'/(('instrumented_baseline' if args.variant=='baseline' else 'candidate_snapshot')+suffix);snapshot.mkdir()
 for p in sorted(selected):
  b=(ROOT/p).read_bytes()
  if args.variant=='baseline' and args.revision in ('v2','v3'):
   if p.as_posix()=='include/audio/tts_service.h':b=b.replace(b'num_threads = 4',b'num_threads = 2')
   if p.as_posix()=='src/audio/asr_llm_tts_smoke.cpp':b=b.replace(b'int tts_threads = 4',b'int tts_threads = 2').replace(b'tts_threads=4',b'tts_threads=2')
  target=snapshot/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  rows.append(dict(file=p.as_posix(),before=baseline.get(p.as_posix()),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
 report=ROOT/'reports/stage5_04_local'
 (report/(args.variant+suffix+'_deployment_manifest.json')).write_text(json.dumps([{k:v for k,v in r.items() if k!='data'} for r in rows],indent=2))
 source=transport.fingerprint_code()+'\nimport base64,signal,sys\nROWS='+repr(rows)+'\nVARIANT='+repr(args.variant)+'\nSUFFIX='+repr(suffix)+'\n'
 source+='''
assert os.getuid()==1000 and not REVIEW.is_symlink()
sys.path.insert(0,str(REVIEW/'tools'))
from stage5_02_board_run import discover_audio,devices
assert devices(discover_audio())['clear']
original=fingerprint();accepted={name:hashlib.sha256((REVIEW/name).read_bytes()).hexdigest() for name in ['build/stage5_01_board/asr_llm_tts_smoke','build/stage5_02_board/asr_llm_tts_smoke','build/stage5_03_board/asr_llm_tts_smoke']}
report=REVIEW/'reports/stage5_04_board'/(VARIANT+'_build'+SUFFIX);report.mkdir()
source=REVIEW/(('stage5_04_baseline_source' if VARIANT=='baseline' else 'stage5_04_source')+SUFFIX)
assert not source.exists() and not source.is_symlink()
shutil.copytree(REVIEW/'reports/stage5_04_board/baseline_5_3_source',source)
for row in ROWS:
 p=source/row['file'];assert p.resolve().is_relative_to(source) and not p.is_symlink()
 if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before'],row['file']
 data=base64.b64decode(row['data']);assert hashlib.sha256(data).hexdigest()==row['sha256']
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
(report/'source_manifest.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='data'} for r in ROWS],indent=2))
results=[]
'''
 old=(ROOT/'reports/stage5_02_local/payloads/02_install_build.py').read_text(encoding='utf-8')
 source+=old[old.index('def step(label,cmd,limit):'):old.index('ok=True\nfor variant')]
 source+='''
build=REVIEW/(('build/stage5_04_baseline' if VARIANT=='baseline' else 'build/stage5_04_board')+SUFFIX);assert not build.exists()
config='source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"'
ok=step('configure',['bash','-c',config,'stage5_04',str(REVIEW),str(source),str(build)],180)
if ok:ok=step('build',['cmake','--build',str(build),'--parallel','3'],600)
if ok:
 config='source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"'
 ok=step('ctest',['bash','-c',config,'stage5_04',str(REVIEW),str(build),str(report/'ctest.xml')],120)
summary={'steps':results,'original_321_unchanged':original==fingerprint(),'accepted_binaries_unchanged':all(hashlib.sha256((REVIEW/p).read_bytes()).hexdigest()==h for p,h in accepted.items()),'disk_free_bytes':shutil.disk_usage(REVIEW).free,'successful':ok}
(report/'result.json').write_text(json.dumps(summary,indent=2));print('BUILD_SUMMARY',json.dumps(summary),flush=True)
raise SystemExit(0 if ok and summary['original_321_unchanged'] and summary['accepted_binaries_unchanged'] else 1)
'''
 payload=report/'payloads'/('03_build_'+args.variant+suffix+'.py');payload.write_text(source,encoding='utf-8');print(payload.relative_to(ROOT),len(rows),'files')
if __name__=='__main__':main()
```

## 修改后 31：tools/stage5_04_report.py

SHA256：`0a14c993fb5f85ae4941ceb4cf259b01873a25288acfde55e2bfd006a89f101e`；140 行。

```python
#!/usr/bin/env python3
"""Render measured Stage5.4 results without inventing missing observations."""
from pathlib import Path
import csv,json,shlex,re
ROOT=Path(__file__).resolve().parents[1]

def stat(value):
    if not value:return '未测量'
    return ' / '.join(f'{value[k]:.3f}' for k in ('mean','p50','p95','minimum','maximum'))+f"（n={value['n']}）"

def main():
    analysis=ROOT/'reports/stage5_04_local/analysis'
    data=json.loads((analysis/'performance.json').read_text(encoding='utf-8'));cases=data['cases']
    collection=Path(data['collection']).resolve();base=collection/'files/reports/stage5_04_board'
    selection=ROOT/'reports/stage5_04_local/voice_selection.json'
    voice_case=json.loads(selection.read_text(encoding='utf-8'))['case'] if selection.exists() else 'candidate_voice_4t_final'
    before=cases['raw_tts_baseline_2t'];after=cases['raw_tts_final_4t']
    report=ROOT/'docs/stage5_04_performance_profiling.md'
    previous=report.read_text(encoding='utf-8').split('<!-- STAGE5_04_MEASURED -->')[0]
    previous=previous.replace('状态：源码审计与测量边界设计完成，正在执行未经优化的 5.3 TTS 基线并实现可关联埋点；未作 5.4 验收，未开始 5.5。','状态：下方实测章节记录最终结果；等待用户验收，未进入 5.5。')
    previous=previous.replace('原始未优化基线 `raw_tts_baseline_2t` 已独占执行完成','初期真实未优化基线 `raw_tts_baseline_2t` 独占运行（以下保留当时进度，最终统计见后文）')
    previous=re.sub(r'^初期真实未优化基线.*$', '【真实执行】原冻结5.3 TTS库的独立基线已经完成；固定中英文各30个有效暖态样本，另列首次使用和预热。自动合成不等于人工听音确认，最终人工回归状态见下文。',previous,flags=re.M)
    sections=['\n<!-- STAGE5_04_MEASURED -->\n## 操作 5：最终实现、版本与交付索引\n\n']
    sections.append('【源码确认】生产优化是 Kokoro 默认线程数 2→4，保留显式 2 线程回退。复用现有 RequestTrace/ImageProfile 埋点和有界 Worker，未增加合成线程、切换模型、改音色/语速、截断答案或重构播放流水线。另修复显式回放的长 sleep 等待信号问题及新音频回放的 ASR 成功条件。\n\n')
    sections.append('5.3 原始149项快照、未优化86项板端源码、4个早期/候选构建均保留；最终使用 stage5_04_source_v3 与 build/stage5_04_board_v3。v2→v3 只修正音频回放的错误检查，正常路径模型参数不变。v2 的大样本模型/固定输入回归与 v3 的全构建/CTest、自然语音和信号复测分别标版本，不能互相冒充。\n\n')
    sections.append('完整修改前/后文件见 [源码附录](stage5_04_source_appendix.md)，关键语句与寿命审查见 [逐句说明](stage5_04_statement_notes.md)，命令详解见 [命令记录](stage5_04_commands.md)，14道完整问答见 [面试题](stage5_04_interview.md)。Git 格式补丁、逐文件SHA、应用验证和字节级roundtrip见 reports/stage5_04_local/changes.patch、change_manifest.json、patch_check.json、patch_roundtrip.json。这里没有 Git 仓库元数据，不虚构 commit。\n\n')
    sections.append('## 操作 6：15个观测点与指标定义\n\n| 点 | 原始事件 | 解释 |\n|---|---|---|\n')
    definitions=[('1','vad_detected_start','喂入VAD后观察到detected上升沿的主机时点；不是声学起点'),('2','vad_endpoint_confirmed','完整segment可取，复制前记录'),('3','asr_enqueued','实际音频段入队；fixture写盘额外耗时单列'),('4','asr_begin','预处理后进入ASRService'),('5','asr_end','已得到文本'),('6','router_end','路由完成，value=0 TEXT/1 VISION'),('7','inference_enqueued','现有共同推理队列入队'),('8','inference_begin','既有Worker开始执行'),('9','first_text_chunk','首个非空SDK文本chunk；精确首token未测量'),('10','decoder_end / inference_end','同步decoder返回 / 完整任务返回'),('11','tts_enqueued','原TTS队列入队'),('12','tts_synthesis_begin','TTSWorker进入合成'),('13','tts_first_audio_callback / tts_full_audio_ready','SDK首批借用音频 / 全段自有PCM；当前只在全段返回后播放'),('14','alsa_first_submit_begin / complete','首次成功writei的调用前及返回；不等于实际声学输出'),('15','alsa_drain_complete','ALSA排空完成；不宣称声学尾音测量')]
    for a,b,c in definitions:sections.append(f'| {a} | `{b}` | {c} |\n')
    sections.append('\nASR API 与 Decode、VAD端点估算、router、各队列、decoder、合成、复制/转换、首次提交与drain均独立。区间可以嵌套，不能简单全部相加。语音起/止估算基于主机read和样本索引，无ADC时间戳；无效估算不计算。音频回放真实运行ASR但绕过麦克风/VAD，单列asr_enqueued→首次提交/播放结束；文本回放更不含ASR。缺少的事件保持null，不补零。\n\n')
    sections.append('## 操作 7：统计条件与公平性\n\n【真实执行】主 TTS 对照：同一台 RK3576、同一个直接链接冻结5.3 TTS库的 benchmark、同模型/Runtime/文本、sid17、speed1、silence_scale0.2；唯一参数差为线程2/4。每种语言各 iteration0 first_use、iteration1 warmup，随后30个暖态样本，不混入主统计。英文first_use已是模型的第二次调用，不称整模型冷启动。模型初始化另列。\n\n固定中文：`一加一等于二。`；固定英文：`A computer monitor displaying a webpage with some text and images.`。中英文分别统计。API可能生成略有不同的PCM长度，记录每次长度并计算RTF；不要求随机生成逐字节一致。peak/RMS/非有限数与实际听音共同检查，无客观MOS/声学仪器。\n\nCPU governor保持ondemand，未改频率/亲和性/系统配置。采样`/proc`每秒一次，smaps每5次一次；CPU单核=100%，CLK_TCK取板端sysconf。CPU“80s后”是统一时间截断的尾段口径，不冒称全部预热样本。不同温度/频率和未完全控制的系统负载仍是限制，不是随机交叉试验。P50/P95为nearest-rank，表格均为平均/P50/P95/最小/最大（样本数），时间单位ms；audio_seconds为秒，RTF/peak/RMS无量纲。\n\n')
    sections.append('## 操作 8：TTS主对照与候选筛查\n\n| 语言/指标 | 2线程基线 | 4线程最终 |\n|---|---|---|\n')
    gains=[]
    for language,label in [('zh','中文'),('en','英文')]:
        a=before['tts'][language+'/measured'];b=after['tts'][language+'/measured']
        for metric in ['synthesis_ms','call_wall_ms','audio_seconds','rtf','peak','rms']:sections.append(f'| {label} {metric} | {stat(a[metric])} | {stat(b[metric])} |\n')
        gain=100*(1-b['synthesis_ms']['mean']/a['synthesis_ms']['mean'])
        gains.append(f'\n{label}暖态平均合成耗时下降 **{gain:.2f}%**；此结论仅适用于这组同条件测试，不代表任意文本或完整语音端到端都按此比例加速。\n\n')
    sections.extend(gains)
    sections.append('| 筛查配置 | 中文均值ms / RTF | 英文均值ms / RTF | 结论 |\n|---|---|---|---|\n')
    for name,label,conclusion in [('raw_tts_screen_1t','1线程','更慢，不采用'),('raw_tts_screen_4t','4线程','进入足量复测'),('raw_tts_screen_6t','6线程','中文更慢、英文小幅收益但CPU更高，不采用')]:
        c=cases[name]['tts'];a=c['zh/measured'];b=c['en/measured'];sections.append(f"| {label} 每语言n=3 | {a['synthesis_ms']['mean']:.3f} / {a['rtf']['mean']:.3f} | {b['synthesis_ms']['mean']:.3f} / {b['rtf']['mean']:.3f} | {conclusion} |\n")
    sections.append('\n筛查只用于选候选，不能替代n=30主比较；1/6线程的慢结果保留原CSV。没有先合成和播放重叠改造，也没有模型重新初始化优化，因为源码和日志已经确认初始化只做一次。\n\n![TTS暖态分布](../reports/stage5_04_local/plots/tts_latency.png)\n\n![RTF分布](../reports/stage5_04_local/plots/tts_rtf_cdf.png)\n\n')
    sections.append('### 模型实例初始化与首次使用（不是清空页缓存后的断电冷启动）\n\n| case | initialize墙钟ms | 中文first_use / warmup ms | 英文first_use / warmup ms |\n|---|---|---|---|\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        terminal=(base/name/'terminal.log').read_text(encoding='utf-8');match=re.search(r'\[TTSInit\] ms=([0-9.]+)',terminal);c=cases[name]['tts']
        sections.append(f"| {name} | {match[1] if match else '未测量'} | {c['zh/first_use']['synthesis_ms']['mean']:.3f} / {c['zh/warmup']['synthesis_ms']['mean']:.3f} | {c['en/first_use']['synthesis_ms']['mean']:.3f} / {c['en/warmup']['synthesis_ms']['mean']:.3f} |\n")
    sections.append('\n两组各64次Generate调用、各60个measured样本，波形有限数/采样率/长度在validation检查。固定ASR和VLM前后各32次调用（含2次初始调用），实际成功输出和固定RGB/Embedding逐字节对比另列，不用这些样本替代真实听音。\n\n')
    sections.append('## 操作 9：TTS内部诊断与无法测量的边界\n\n')
    diag=cases['baseline_tts_ort_detail'];rows=list(csv.DictReader((base/'baseline_tts_ort_detail/tts_samples.csv').open(encoding='utf-8')));runs=diag['ort_profile']['model_run_events']
    assert len(rows)==len(runs)==6
    sections.append('| 语言/阶段 | Generate API ms | ORT model_run ms | 差值ms（非纯音素化） |\n|---|---|---|---|\n')
    total=sum(float(x['synthesis_ms']) for x in rows);model=sum(x['dur']/1000 for x in runs)
    for row,run in zip(rows,runs):
        api=float(row['synthesis_ms']);r=run['dur']/1000;sections.append(f"| {row['language']}/{row['phase']} | {api:.3f} | {r:.3f} | {api-r:.3f} |\n")
    sections.append(f'\n该独立诊断六次model_run合计占API **{100*model/total:.4f}%**，支持主要瓶颈是模型计算。诊断有trace开销，不纳入主加速百分比。Conv等算子累计占用在JSON保留，算子可能并行/嵌套，不能当硬件利用率或直接把所有dur相加当总墙钟。SDK文本前端、音素化、内部波形处理没有独立可靠回调，分别标未单独测量；差值包含这些以及其他运行开销。\n\n')
    for name in ['baseline_tts_ort_detail','candidate_tts_profile_4t']:
        c=cases[name];sections.append(f'### {name}\n\n| 组别 | 首批callback | 完整自有音频ready | 应用PCM复制 |\n|---|---|---|---|\n')
        for key,metrics in c['request_metrics'].items():
            sections.append(f"| {key} | {stat(metrics.get('tts_first_audio_callback_ms'))} | {stat(metrics.get('tts_full_audio_ready_ms'))} | {stat(metrics.get('tts_pcm_copy_ms'))} |\n")
    sections.append('\n“首批callback更早”没有在本轮改成更早播放，当前首音频提交仍需完整合成。额外 float复制和S16转换实测很小，本轮保留安全所有权，不声称零拷贝，也不将其当秒级瓶颈。\n\n')
    sections.append('## 操作 10：同音频、同图像完整请求和排队对照\n\n留存自然基线指定的segment1/2，固定NV12 frame0，SHA与TSV在fixed_inputs/paired_inputs。三组VISION(0/40/80s)→TEXT(+1s)，真实ASR、原路由/队列/模型/TTS/ALSA；没有麦克风/VAD，不计算这些阶段的虚假时间。Camera仍独立采集，固定图像的Frame Age不计。两组max_wait=60000ms、request_lifetime=180000ms，避免用默认旧任务过期制造加速；生产默认期限不变。每路n=3有限样本，首组有首次使用，后两组才是暖态重复，不能外推长期P95。\n\n| case/路由 | ASR入队→首提交 | ASR入队→drain | TTS队列等待 | 模型服务 |\n|---|---|---|---|---|\n')
    for name in ['baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        for key,m in cases[name]['request_metrics'].items():
            if not key.endswith('/success'):continue
            sections.append(f"| {name}/{key} | {stat(m['asr_enqueue_to_first_submit_ms'])} | {stat(m['asr_enqueue_to_playback_end_ms'])} | {stat(m['tts_queue_ms'])} | {stat(m['inference_service_ms'])} |\n")
    sections.append('\n固定输入不代表模型输出一定逐字一致，回答文本在各case answers/terminal.log保留。若答案或生成长度不同，只作为完整场景观测，不把全部变化归因于线程数；严格收益依据仍是固定文本n=30主对照。队列等待会包含前一条的合成和完整播放，当前串行语义没有改。【理论分析】服务时间减少通常有助于缩短等待，但受输入间隔和输出长度影响，不能保证任意负载的固定比例收益。\n\n![请求阶段分解](../reports/stage5_04_local/plots/pipeline_breakdown.png)\n\n')
    sections.append('【真实执行】这组n=3的TEXT推理服务均值从约1149.5ms升至1422.1ms；同时其完整ASR入队→播放完成从约29.63s降至24.33s。VISION完整请求从约19.91s降至16.69s。没有把局部回退隐藏在总延迟收益中：CPU竞争/热状态可能影响Qwen，有限样本不足以单独确定因果。4线程是当前整体等待收益与资源开销的折中，不是所有子阶段都加速。默认12秒TTS等待策略仍保留，本轮公平对照才单独使用60秒；生产连续请求仍可能按原策略过期。\n\n')
    sections.append('## 操作 11：真实语音、ASR/VLM、Camera与并发回归\n\n| case | 原始退出码 | 有效样本/结果摘要 |\n|---|---|---|\n')
    for name in ['baseline_asr_30','candidate_asr_30','baseline_vision_30','candidate_vision_30','baseline_voice_2t',voice_case,'candidate_burst_audio','candidate_expiry_audio']:
        c=cases[name];r=c['result'];counter=c.get('terminal_counters',{});brief=counter.get('PipelineStats',{})
        if not brief:
            kind='asr' if 'asr' in name else 'vision';samples=list(csv.DictReader((base/name/(kind+'_samples.csv')).open(encoding='utf-8')))
            brief={'CSV总行数':len(samples),'measured样本':sum(x['phase']=='measured' for x in samples),'成功非空文本':sum(bool(x.get('text',x.get('answer','')).strip()) for x in samples)}
        sections.append(f"| {name} | {r.get('returncode')} | `{json.dumps(brief,ensure_ascii=False,separators=(',',':'))}` |\n")
    sections.append('\n自然基线120秒有额外说话：7段识别、5接收、2忙碌拒绝，不能把全部TEXT回答混作同一固定文本性能。当前用户确认优化前两个指定回答都实际听到；优化版确认单列user_feedback，不复用5.3反馈。语音起/止估算→首提交及播放结束的全量逐请求数据见requests.csv；麦克风不是自动固定输入试验。Camera FPS/FramePool/XRUN均保留terminal_counters，实际释放用fuser及/proc/asound状态复核。\n\n')
    feedback=json.loads((base/voice_case/'user_feedback.json').read_text(encoding='utf-8')) if (base/voice_case/'user_feedback.json').exists() else None
    sections.append('### 最终优化版人工确认与设备终态\n\n用户反馈原文及确认边界：\n\n```json\n'+json.dumps(feedback,ensure_ascii=False,indent=2)+'\n```\n\n最终优化版Camera、队列和ALSA计数（实际日志解析）：\n\n```json\n'+json.dumps(cases[voice_case]['terminal_counters'],ensure_ascii=False,indent=2)+'\n```\n\n')
    requests=list(csv.DictReader((analysis/'requests.csv').open(encoding='utf-8')))
    columns=[]
    for name in ['baseline_voice_2t',voice_case]:
        for route in ['TEXT','VISION']:
            selected=next((r for r in requests if r['case']==name and r['route']==route and r['status']=='success'),None)
            columns.append((name+'/'+route+('/ID'+selected['request_id'] if selected else '/pending'),selected or {}))
    sections.append('### 自然语音的逐阶段时点差（有限样本，不是公平加速主表）\n\n每列为该轮首个成功的对应路由，单位ms；两轮真实说话不完全相同，基线还留存fixture写盘，不能据此作同条件加速百分比。\n\n| 指标 | '+' | '.join(c[0] for c in columns)+' |\n|---|---|---|---|---|\n')
    for metric in ['vad_endpoint_host_estimate_ms','asr_queue_ms','asr_api_ms','asr_decode_ms','router_ms','inference_queue_ms','inference_service_ms','inference_first_text_chunk_ms','tts_queue_ms','tts_generate_api_ms','tts_first_audio_callback_ms','tts_full_audio_ready_ms','playback_conversion_ms','synthesis_to_first_submit_ms','alsa_submit_to_drain_ms','vad_detected_to_first_submit_ms','speech_start_host_estimate_to_submit_ms','speech_end_host_estimate_to_submit_ms','speech_start_host_estimate_to_playback_end_ms']:
        sections.append('| '+metric+' | '+' | '.join('未测量' if not row.get(metric) else f'{float(row[metric]):.3f}' for _,row in columns)+' |\n')
    sections.append('\n应用只有SDK float→自有vector复制及float→S16转换，没有新增应用重采样。plughw内部可能进行格式/采样率转换，其独立耗时未测量；提交/排空墙钟不等于声学时间。\n\n')
    sections.append('## 操作 12：安全退出、排空、取消与错误统计\n\n| case | 信号/模式 | 退出码 | 信号→退出s | 强杀/超时 | 设备释放 |\n|---|---|---|---|---|---|\n')
    for name in ['candidate_sigint_drain','candidate_sigterm_cancel_tts','candidate_sigterm_cancel_waiting','candidate_final_sigterm_drain',voice_case]:
        c=cases[name];r=c['result'];elapsed=r.get('signal_to_exit_seconds');sections.append(f"| {name} | {r.get('sent_signal')}/{r.get('stop_mode')} | {r['returncode']} | {'未测量' if elapsed is None else f'{elapsed:.3f}'} | {r['forced_kill']}/{r['timeout']} | {r['devices_released']} |\n")
    sections.append('\n排空会播完已接收工作；取消等待保留当前同步SDK调用安全完成、撤销未开始TTS或阻止新增下游。取消不是中断NPU/ORT。长等待case第二个输入安排100秒后，候选20ms检查信号，退出时间必须看实际记录，不能用杀进程冒充。所有Worker accepted/completed及pending/active/inflight、cancelled/expired/callback_errors均在JSON和原始日志，测试守护的退出码与SSH传输码分别保存。\n\n')
    default=cases['candidate_default_queue_audio'];sections.append('### 最终v3的原默认期限回归\n\n`tts_queue_ms=12000`、`request_lifetime_ms=45000`，保留原策略。实际终态：\n\n```json\n'+json.dumps(default['terminal_counters'],ensure_ascii=False,indent=2)+'\n```\n\n到期任务有明确日志、计数与终态；它不属于模型推理失败，也不属于性能主对照的成功样本。没有为了加速擅自截断或静默删除。\n\n')
    sections.append('## 操作 13：CPU、内存、热状态与NPU限制\n\n| standalone TTS | CPU%（80s后，单核100%） | RSS峰值MiB | VmHWM采样最大MiB | 线程数最大 |\n|---|---|---|---|---|\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        r=cases[name]['resources'];sections.append(f"| {name} | {stat(r['cpu_percent_after_80s'])} | {r['rss_MiB']['maximum']:.3f} | {r['VmHWM_observed_MiB']['maximum']:.3f} | {r['threads']['maximum']} |\n")
    sections.append('\n![CPU与内存](../reports/stage5_04_local/plots/tts_resources.png)\n\n【真实执行】增加线程的代价是更多CPU与热负载。温度、各核频率分布和完整进程RSS/线程曲线在performance.json，不隐藏降频或额外资源占用。RSS采样峰值不是全进程分配追踪，也不等于完整多模态进程内存；VmHWM为读取到的进程高水位。NPU原始load在CPU-only时也可固定100，不能直接换算有效利用率；带宽/功耗未测量。\n\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        r=cases[name]['resources'];thermal=max((v['maximum'] for v in r['temperature_C'].values() if v),default=None)
        big=next((v for k,v in r['cpu_frequency_kHz'].items() if '/cpu4/' in k),None)
        sections.append(f"{name}：所读thermal传感器最高值 {thermal}°C，CPU4频率kHz {stat(big)}。传感器与频率原路径保留，不将温度当功耗。\n\n")
    failed=cases['candidate_voice_4t_final']['result']
    if failed['returncode']!=0:
        sections.append('### 原始人工回归未完成的保留记录\n\n第一轮最终版120秒监听没有检测到VAD语音段/ASR文本，程序正常释放资源后返回1。没有超时或强杀，不能算听音通过；重试必须使用新目录，不能覆盖这一轮。实际记录：\n\n```json\n'+json.dumps(failed,ensure_ascii=False,indent=2)+'\n```\n\n')
    sections.append('## 操作 14：失败记录、回退和剩余风险\n\n1. MinGW inline TLS shared_ptr链接失败：改函数局部TLS accessor，保留v1失败日志。\n2. 本地portable CLI因测试快照漏.txt而失败：补快照脚本，未改CLI实现。\n3. 1线程明显慢，6线程资源代价较大：未进入生产默认，原始数据保留。\n4. 新音频回放原本沿用文本回放免ASR检查：最终v3明确检查consumer.ok并输出错误，未更改模型/调度。\n5. 回放sleep_until延迟信号：v2起采用有限等待检查；v3继承。\n6. SDK未知音素警告在前后存在，原stderr保留，未擅改词典或文本。\n\n回退可在最终隔离程序显式传tts_threads=2；旧5.3可执行文件和源码仍在原处，不需要覆盖/删除。【尚未验证】未做多小时压力、全部SDK故障注入、声学延迟/MOS、精确token TTFT、可信NPU利用率/功耗；4线程在更高并发或更热环境下仍需重新评估。有限回归中无明显泄漏/死锁/重复释放证据，不宣称覆盖所有内部故障。\n\n')
    validation_path=ROOT/'reports/stage5_04_local/validation_summary.json'
    validation=json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.exists() else None
    sections.append('## 操作 15：最终验收状态与下一步\n\n')
    sections.append('自动验证汇总：\n\n```json\n'+json.dumps(validation,ensure_ascii=False,indent=2)+'\n```\n\n')
    sections.append('本节提交用户验收后暂停，**没有开始5.5**。最终阶段工程手册会在5.5汇编Word/Markdown；本节完整Markdown、源代码、逐句说明、命令、问答、图表和证据均已留档。具体验收边界以validation_summary及当前用户听音反馈为准。\n')
    complete=bool(validation and validation.get('all_checks_passed'))
    status='状态：全部记录内验证完成，等待用户验收；未进入5.5。' if complete else '状态：自动测试与性能测量已完成，最终人工语音/听音回归尚未完成，不能正式验收；未进入5.5。'
    previous=re.sub(r'^状态：.*$',status,previous,flags=re.M)
    if not complete:sections[-1]='人工回归尚未完成，当前不能宣告5.4通过；保持本节，不进入5.5。完整Word/Markdown工程手册留待5.5汇编，本节源码、数据和技术材料按实际完成状态保存。\n'
    report.write_text(previous+''.join(sections),encoding='utf-8')
    commands=['# 5.4 命令、逐项参数及真实输出\n\n','全部操作仅cat用户和已授权隔离目录；`sudo -n fuser -v`仅查询，不含-k。复现必须选新case名和不存在的源码/构建目录，不覆盖冻结证据。以下argv来自实际command.json，shell形式用shlex.join转义；运行前使用`set -a; source "$REVIEW/tools/stage5_board_paths.sh"`导出原SDK/模型路径，环境快照在对应case/environment.json。source只改变本次shell，不编辑系统文件。\n\n']
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():continue
        for file in sorted(folder.glob('*command.json')):
            command=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(command,list):continue
            label=file.name.replace('.command.json','').replace('command.json','run')
            result=folder/(label+'.result.json') if label!='run' else folder/'result.json'
            outcome=json.loads(result.read_text()) if result.exists() else cases.get(folder.name,{}).get('result')
            stdout=folder/(label+'.stdout.log') if label!='run' else folder/'terminal.log'
            stderr=folder/(label+'.stderr.log') if label!='run' else folder/'stderr.log'
            commands.append(f'## 操作 {folder.name}/{label}\n\n目的：'+('独立ARM64配置/构建/确定性测试。' if 'build' in folder.name else '在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。')+'\n\n```bash\n'+shlex.join(command)+'\n```\n\n')
            commands.append('参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。\n\n' if 'build' in folder.name else '参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。\n\n')
            commands.append('真实退出/守护记录：\n\n```json\n'+json.dumps(outcome,ensure_ascii=False,indent=2)+'\n```\n\n')
            for kind,path in [('stdout',stdout),('stderr',stderr)]:
                if path.exists():
                    lines=path.read_text(encoding='utf-8',errors='replace').splitlines();excerpt=lines if len(lines)<=14 else lines[:5]+['[此处省略，完整原始文件见链接]']+lines[-8:]
                    rel=path.relative_to(ROOT).as_posix();commands.append(f'真实{kind}节选（完整[{path.name}](../{rel})）：\n\n```text\n'+'\n'.join(excerpt)+'\n```\n\n')
            commands.append('输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。\n\n')
    commands.append('## 操作 本地分析、绘图、差异与证据收集\n\n```powershell\npython tools/stage5_04_collect.py --complete-only\npython tools/stage5_04_analyze.py --collection '+collection.as_posix()+'\npython tools/stage5_04_plot.py --before raw_tts_baseline_2t --after raw_tts_final_4t --pipeline-case candidate_pipeline_pairs_4t\npython tools/stage5_04_export.py\n```\n\ncollect仅SSH只读打包reports04，--complete-only跳过未完成case，验证普通文件/安全相对路径、文件和总字节上限，SHA清单保留；不收模型。analyze按case+request_id关联steady事件，按原CSV阶段/语言/fixture分组，nearest-rank统计。plot只读真实数据生成PNG/SVG，未生成示意数据。export生成完整前后源码和git diff --no-index；--binary保留换行字节差异，core.autocrlf=false不转换；在新临时树git apply --check、实际apply后逐文件SHA比对，不在真实工作树执行apply。成功输出、SHA及验证在本地报告目录。\n')
    commands.append('\n## 操作 最终材料归档\n\n目的：将本节完整源码、差异、报告和量化结果保存到隔离reports目录，不更新任何运行版本。\n\n```powershell\npython tools/stage5_04_ssh.py --payload reports/stage5_04_local/payloads/30_delivery.py --timeout 120\n```\n\n`--payload`指定已保存在本地的完整远程Python脚本（含归档SHA）；`--timeout 120`限定SSH命令等待。远程先检查目标不存在、普通文件/安全相对路径、SHA与500MiB剩余空间，再用普通cat权限在`reports/stage5_04_board/final_acceptance/`新建归档及材料树；不覆盖已有目录，不启动测试，不写模型或稳定版本。实际退出码、文件数、SHA、空间与保护核验以`reports/stage5_04_local/final_delivery_receipt.json`及SSH原始日志为准。已有完整原始测试帧/ORT trace保留原reports路径，不重复复制模型或大型数据；材料内命令所链接的日志另保留副本。回退只需继续使用未变的旧版本，不需要删除任何文件。\n')
    (ROOT/'docs/stage5_04_commands.md').write_text(''.join(commands),encoding='utf-8')
    print('GENERATED measured report and command explanations')

if __name__=='__main__':main()
```

## 修改后 32：tools/stage5_04_run.py

SHA256：`0dfcdcb1de9befb84a9e8d1399318f32ff20154841b6c2d19eed143eb7707c0b`；73 行。

```python
#!/usr/bin/env python3
"""Bounded manual hardware benchmark runner; writes only isolated Stage 5.4 reports."""
from pathlib import Path
import argparse,glob,json,os,signal,subprocess,sys,time,shutil
ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_03_voice_run import discover_audio,devices,query
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def sample(pid,index):
    result={'monotonic':time.monotonic(),'wall_time':time.time(),'pid':pid}
    try:
        result['stat']=Path(f'/proc/{pid}/stat').read_text()
        result['status']=Path(f'/proc/{pid}/status').read_text()
        result['system_stat']=Path('/proc/stat').read_text().splitlines()[0]
        result['loadavg']=Path('/proc/loadavg').read_text().strip()
        result['tasks']={}
        for folder in Path(f'/proc/{pid}/task').iterdir():
            try:result['tasks'][folder.name]={'stat':(folder/'stat').read_text(),'allowed':[x for x in (folder/'status').read_text().splitlines() if x.startswith('Cpus_allowed_list:')]}
            except OSError:pass
        if index%5==0:result['smaps_rollup']=Path(f'/proc/{pid}/smaps_rollup').read_text()
        result['sysfs']={}
        for pattern in ['/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq','/sys/class/thermal/thermal_zone*/temp','/sys/class/devfreq/*npu*/cur_freq','/sys/class/devfreq/*npu*/load']:
            for name in glob.glob(pattern):
                try:result['sysfs'][name]=Path(name).read_text().strip()
                except OSError as e:result['sysfs'][name]={'error':str(e)}
    except OSError as e:result['sample_error']=str(e)
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--exe',required=True);parser.add_argument('--timeout',type=int,default=1800);parser.add_argument('--affinity');parser.add_argument('--ort-profile',action='store_true');parser.add_argument('--env',action='append',default=[]);parser.add_argument('arguments',nargs=argparse.REMAINDER);args=parser.parse_args()
    assert Path(__file__).resolve().parent==ROOT/'tools' and not ROOT.is_symlink()
    assert args.name and all(x.isalnum() or x in '_-' for x in args.name)
    exe=Path(args.exe).resolve();assert exe.is_relative_to(ROOT) and exe.is_file()
    assert 1<=args.timeout<=3600
    report=ROOT/'reports/stage5_04_board'/args.name;report.mkdir()
    before=fingerprint();save(report/'stable_before.json',before);audio=discover_audio();pre=devices(audio);save(report/'devices_before.json',pre);assert pre['clear']
    envout=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','stage5_04',str(ROOT)],timeout=15)
    env=dict(x.decode().split('=',1) for x in envout.split(b'\0') if b'=' in x)
    for entry in args.env:
        key,value=entry.split('=',1);assert key.startswith('STAGE5_');env[key]=value.replace('{REPORT}',str(report))
    if args.ort_profile:
        config=report/'ort_session.config'
        config.write_text('ProfilingFilePrefix='+str(report/'ort_profile')+'\n')
        env['STAGE5_TTS_ORT_PROFILE_CONFIG']=str(config)
    argv=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    argv=[x.replace('{REPORT}',str(report)).replace('{KOKORO}',env['STAGE5_KOKORO']) for x in argv]
    command=[str(exe),*argv]
    if args.affinity:command=['taskset','-c',args.affinity,*command]
    save(report/'command.json',command);save(report/'parameters.json',vars(args));save(report/'environment.json',{k:v for k,v in env.items() if k.startswith('STAGE5_') or k=='LD_LIBRARY_PATH'})
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'clock_ticks':os.sysconf('SC_CLK_TCK')})
    assert shutil.disk_usage(ROOT).free>=500*1024**2
    with (report/'terminal.log').open('wb') as out,(report/'stderr.log').open('wb') as err,(report/'resources.jsonl').open('w') as samples:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);start=time.monotonic();reason=None;forced=False
        token=Path(f'/proc/{child.pid}/stat').read_text().split()[21];save(report/'pid.json',{'pid':child.pid,'exe':str(exe),'start_token':token})
        index=0
        while child.poll() is None:
            samples.write(json.dumps(sample(child.pid,index))+'\n');samples.flush();index+=1
            if time.monotonic()-start>args.timeout or shutil.disk_usage(ROOT).free<500*1024**2:
                reason='timeout' if time.monotonic()-start>args.timeout else 'disk_below_500MiB'
                assert Path(f'/proc/{child.pid}/exe').resolve()==exe and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==token
                os.kill(child.pid,signal.SIGTERM)
                try:child.wait(timeout=15)
                except subprocess.TimeoutExpired:os.kill(child.pid,signal.SIGKILL);forced=True;child.wait(timeout=10)
                break
            time.sleep(1)
        code=child.wait();seconds=time.monotonic()-start
    post=devices(audio);save(report/'devices_after.json',post);after=fingerprint();save(report/'stable_after.json',after)
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)])})
    result={'returncode':code,'seconds':seconds,'termination_reason':reason,'forced_kill':forced,'process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':before==after,'disk_free_bytes':shutil.disk_usage(ROOT).free}
    save(report/'result.json',result);print('RUN_RESULT',args.name,json.dumps(result),flush=True)
    print((report/'terminal.log').read_text(errors='replace')[-10000:],flush=True);print((report/'stderr.log').read_text(errors='replace')[-2000:],flush=True)
    return 0 if code==0 and not reason and post['clear'] and before==after else 1
if __name__=='__main__':raise SystemExit(main())
```

## 修改后 33：tools/stage5_04_ssh.py

SHA256：`6e6ea83e75b1831c4413970915a8fdfd49024f00127683555e1ee2c5c001a204`；25 行。

```python
#!/usr/bin/env python3
"""Stage 5.4 authorized isolated payload transport; records raw output and status."""
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
    report=transport.ROOT/'reports/stage5_04_board'/('ssh_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    code=transport.run_step(report,'remote',transport.remote_command(),source,args.timeout)
    print('REPORT_DIRECTORY',report.relative_to(transport.ROOT),flush=True)
    for name in ('remote.stdout.log','remote.stderr.log'):
        print((report/name).read_text(encoding='utf-8',errors='replace')[-14000:],flush=True)
    return code

if __name__=='__main__':raise SystemExit(main())
```

## 修改后 34：tools/stage5_04_validate.py

SHA256：`50fed10d1bf6663115c5a1beb2bdc55525dba7c27a4f46fad00530d78e352db4`；78 行。

```python
#!/usr/bin/env python3
"""Validate actual case outcomes; expected backpressure is checked separately."""
from pathlib import Path
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);args=parser.parse_args()
    base=args.collection/'files/reports/stage5_04_board';local=ROOT/'reports/stage5_04_local'
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    data=load(local/'analysis/performance.json');cases=data['cases'];checks={}
    selection=ROOT/'reports/stage5_04_local/voice_selection.json'
    voice_case=json.loads(selection.read_text(encoding='utf-8'))['case'] if selection.exists() else 'candidate_voice_4t_final'
    expected=['raw_tts_baseline_2t','raw_tts_final_4t','baseline_asr_30','candidate_asr_30','baseline_vision_30','candidate_vision_30','baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t','baseline_voice_2t',voice_case,'candidate_burst_audio','candidate_expiry_audio','candidate_sigint_drain','candidate_sigterm_cancel_tts','candidate_sigterm_cancel_waiting','candidate_final_sigterm_drain','candidate_default_queue_audio']
    for name in expected:
        r=cases[name]['result']
        checks[name]=r['returncode']==0 and not r.get('timeout',False) and not r.get('termination_reason') and not r['forced_kill'] and r['devices_released'] and r['process_gone'] and r['original_321_unchanged']
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        rows=list(csv.DictReader((base/name/'tts_samples.csv').open(encoding='utf-8')))
        checks[name+'_30_per_language']=all(sum(x['phase']=='measured' and x['language']==language for x in rows)==30 for language in ('zh','en'))
        checks[name+'_finite_PCM']=all(int(x['nonfinite'])==0 and int(x['sample_rate'])==24000 and float(x['audio_seconds'])>0 and 0<float(x['peak'])<=1.0 and float(x['rms'])>0 for x in rows)
    initial=ROOT/'reports/stage5_04_board/collected_20261017_213845/files/reports/stage5_04_board/raw_baseline_build/tts_bench'
    current=base/'raw_baseline_build/tts_bench'
    checks['frozen_TTS_benchmark_binary_unchanged']=hashlib.sha256(initial.read_bytes()).digest()==hashlib.sha256(current.read_bytes()).digest()
    checks['same_fixed_TTS_input_bytes']=(base/'raw_tts_baseline_2t/inputs.txt').read_bytes()==(base/'raw_tts_final_4t/inputs.txt').read_bytes()
    for name in ['baseline_tts_ort_detail','candidate_tts_profile_4t','baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        events=cases[name].get('session_events',[])
        checks[name+'_TTS_initialized_once']=sum(x['event']=='tts_initialize_begin' for x in events)==1 and sum(x['event']=='tts_initialize_end' for x in events)==1
    for kind in ['asr','vision']:
        rows=[]
        for prefix in ('baseline','candidate'):
            rows.append(list(csv.DictReader((base/(prefix+'_'+kind+'_30')/(kind+'_samples.csv')).open(encoding='utf-8'))))
        checks[kind+'_30_each']=all(sum(x['phase']=='measured' for x in batch)==30 for batch in rows)
        checks[kind+'_output_texts_equal']=all(a.get('text',a.get('answer'))==b.get('text',b.get('answer')) for a,b in zip(*rows)) and len(rows[0])==len(rows[1])==32
    rgb=[];emb=[]
    for i in range(32):
        for suffix,target in [('rgb',rgb),('f32',emb)]:
            # Backend output suffixes are verified against actual files below.
            leaf=f'sample_{i}.'+suffix
            a=base/'baseline_vision_30'/leaf;b=base/'candidate_vision_30'/leaf
            target.append(a.is_file() and b.is_file() and a.read_bytes()==b.read_bytes())
    checks['RGB_32_pairs_byte_equal']=all(rgb);checks['embeddings_32_pairs_byte_equal']=all(emb)
    for name in ['baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        c=cases[name];counter=c['terminal_counters'];pipeline=counter['PipelineStats'];tts=counter['QueueStats/tts']
        checks[name+'_all_six_complete']=pipeline['accepted']==6 and pipeline['dispatched']==6 and pipeline['rejected']==0 and tts['accepted']==tts['completed']==6 and tts['failed']==tts['expired']==tts['cancelled']==0
    for name in expected:
        c=cases[name]
        for key,row in c.get('terminal_counters',{}).items():
            if key.startswith('QueueStats/'):
                checks[name+'_'+key+'_settled']=row['accepted']==row['completed'] and row['pending']==row['active']==row['failed']==row['callback_errors']==0
        if (base/name/'profile.jsonl').exists():checks[name+'_no_profile_errors']=not c.get('terminal_errors',{}).get('profile_error',0)
    checks['burst_exact_backpressure']=cases['candidate_burst_audio']['terminal_counters']['PipelineStats']['rejected']>=1
    checks['expiry_is_observed']=cases['candidate_expiry_audio']['terminal_counters']['QueueStats/tts']['expired']>=1
    checks['cancelled_waiting_TTS_observed']=cases['candidate_sigterm_cancel_tts']['terminal_counters']['QueueStats/tts']['cancelled']>=1
    w=cases['candidate_sigterm_cancel_waiting'];p=w['terminal_counters']['PipelineStats']
    checks['cancel_future_input_did_not_wait_100s']=w['result']['signal_to_exit_seconds']<30 and (p['downstream_cancelled']+p['vision_cancelled']>=1)
    for name in ['candidate_sigint_drain','candidate_final_sigterm_drain']:
        c=cases[name];checks[name+'_drained_active_request']=c['terminal_counters']['QueueStats/tts']['completed']>=1 and c['result']['shutdown_complete_marker'] and c['result']['signal_to_exit_seconds']<60
    for name in ['baseline_voice_2t',voice_case]:
        c=cases[name];feedback=load(base/name/'user_feedback.json') if (base/name/'user_feedback.json').exists() else {}
        checks[name+'_user_actually_heard_both']=feedback.get('both_TEXT_VISION_audible') is True
        checks[name+'_TEXT_VISION_success']=c['result']['text_tts_completed'] and c['result']['vision_tts_completed']
        checks[name+'_zero_XRUN']=c['terminal_counters']['ALSA']['XRUN']==0
        checks[name+'_frame_pool_released']=c['terminal_counters']['FramePool']['in_use']==0
    arm=load(base/'candidate_build_v3/result.json');checks['final_ARM64_config_build_ctest']=arm['successful']
    xml=ET.parse(base/'candidate_build_v3/ctest.xml').getroot();tests=xml.findall('.//testcase');checks['ARM64_CTest_7_passed']=len(tests)==7 and not xml.findall('.//failure') and not xml.findall('.//error')
    portable=load(local/'instrumentation_local_v6/result.json');checks['local_portable_checks']=portable['successful']
    guard=base/('protection_final_after_manual' if (base/'protection_final_after_manual/result.json').exists() else 'protection_final')
    protection=load(guard/'result.json') if (guard/'result.json').exists() else None;checks['protection']=bool(protection and all(protection['checks'].values()) and all(x['all_sha_match'] for x in protection['frozen_stage5_04_sources'].values()))
    patch=load(local/'patch_roundtrip.json');invariants=load(local/'source_invariants.json')
    checks['patch_byte_roundtrip']=patch['exit_code']==0 and patch['all_bytes_match'];checks['source_matches_final_ARM64']=invariants['final_source_matches_ARM64_candidate_v3']
    targets=re.findall(r'Built target (\S+)',(base/'candidate_build_v3/build.stdout.log').read_text())
    summary={'stage':'5.4','engineering_status':'verified within recorded scenarios; user acceptance pending' if all(checks.values()) else 'NOT ACCEPTABLE: checks failed','user_acceptance_pending':True,'next_stage_started':False,'scope':'authorized isolated review directory only','checks':checks,'all_checks_passed':all(checks.values()),'final_ARM64_targets':targets,'final_ARM64_CTest':{'total':len(tests),'passed':sum(not t.findall('failure') and not t.findall('error') for t in tests),'seconds':sum(float(t.attrib.get('time',0)) for t in tests),'type':'Fake/deterministic unit tests; hardware cases separate'},'local_portable':portable,'TTS_warm_measured_each_language':30,'performance_comparison':{language:{'before_mean_ms':cases['raw_tts_baseline_2t']['tts'][language+'/measured']['synthesis_ms']['mean'],'after_mean_ms':cases['raw_tts_final_4t']['tts'][language+'/measured']['synthesis_ms']['mean']} for language in ('zh','en')},'fixed_vision_RGB_pairs':len(rgb),'fixed_vision_embedding_pairs':len(emb),'protection':protection,'source_invariants':invariants,'patch_roundtrip':{'exit_code':patch['exit_code'],'all_bytes_match':patch['all_bytes_match'],'files':len(patch['files'])},'selected_voice_case':voice_case,'retained_failed_voice_trial':cases['candidate_voice_4t_final']['result'] if voice_case!='candidate_voice_4t_final' else None,'collection':str(args.collection),'limitations':['Natural speech and full-pipeline repeats are finite small samples','ALSA submit/drain is not acoustic latency','True token-granular TTFT unmeasured','TTS frontend/phonemization not separately measured','No reliable NPU utilization/bandwidth/power measurement','Higher CPU and temperature with four TTS threads','No long-duration stress, sanitizer proof or full real-SDK failure injection','Full n30 fixed-model and paired regressions use v2; final v3 changes only audio-replay error checks and is separately rebuilt/CTest/live-voice/signal tested']}
    (local/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('VALIDATION',sum(checks.values()),'/',len(checks),'failed',[k for k,v in checks.items() if not v])
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
```

## 修改后 35：tools/stage5_04_voice_run.py

SHA256：`db1a1d3787426672c3711147a756911aa45d22bd36310ac20602d8b059817233`；217 行。

```python
#!/usr/bin/env python3
"""Stage 5.4 hardware/replay comparisons; explicit input mode and PID-safe timeout guards."""
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
from stage5_04_run import sample as profile_sample


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
    parser.add_argument('--tts-threads',type=int,default=2)
    parser.add_argument('--variant',choices=('baseline','candidate'),default='candidate')
    parser.add_argument('--revision',choices=('v1','v2','v3'),default='v3')
    parser.add_argument('--capture-fixtures',action='store_true')
    parser.add_argument('--audio-replay-file')
    parser.add_argument('--fixed-frame-dir')
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
    report=ROOT/'reports/stage5_04_board'/args.name
    report.mkdir()
    before=fingerprint(); save(report/'stable_before.json',before)
    audio=discover_audio(); save(report/'audio_detection.json',audio)
    pre=devices(audio);save(report/'devices_before.json',pre)
    assert pre['clear'],'target device occupied'
    assert os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize>=500*1024**2
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'clock_ticks':os.sysconf('SC_CLK_TCK')})
    envout=subprocess.check_output(['bash','-c','source "$1/tools/stage5_board_paths.sh"; env -0','phase3',str(ROOT)],timeout=15)
    env=dict(part.decode().split('=',1) for part in envout.split(b'\0') if b'=' in part)
    assert 1<=args.tts_threads<=8
    assert 1<=args.tts_queue_ms<=60000 and 1<=args.request_lifetime_ms<=300000
    env.pop('STAGE5_IMAGE_PROFILE',None)
    env['STAGE5_PROFILE']=str(report/'profile.jsonl')
    env['STAGE5_STOP_MODE']=args.stop_mode
    env['STAGE5_TTS_QUEUE_MS']=str(args.tts_queue_ms)
    env['STAGE5_REQUEST_LIFETIME_MS']=str(args.request_lifetime_ms)
    for key in ('STAGE5_CAPTURE_AUDIO_FIXTURES','STAGE5_REPLAY_AUDIO_FILE','STAGE5_REPLAY_FRAME_DIR'):env.pop(key,None)
    assert not (args.replay and args.audio_replay_file)
    if args.capture_fixtures:
        assert not args.replay and not args.audio_replay_file
        (report/'audio_fixtures').mkdir();env['STAGE5_CAPTURE_AUDIO_FIXTURES']=str(report/'audio_fixtures')
    if args.fixed_frame_dir:
        fixed=Path(args.fixed_frame_dir);assert fixed.resolve().is_relative_to(ROOT) and (args.replay or args.audio_replay_file)
        env['STAGE5_REPLAY_FRAME_DIR']=str(fixed)
    if args.audio_replay_file:
        replay=Path(args.audio_replay_file);assert replay.resolve().is_relative_to(ROOT)
        env['STAGE5_REPLAY_AUDIO_FILE']=str(replay)
        save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'text':replay.read_text()})
    if args.replay:
        replay=ROOT/('tests/stage5_02_replay.tsv' if args.replay_source=='four' else 'tests/stage5_02_replay_pair.tsv')
        env['STAGE5_REPLAY_FILE']=str(replay)
        save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'text':replay.read_text()})
    else: env.pop('STAGE5_REPLAY_FILE',None)
    base='/home/cat/projects/RK3576'
    suffix='' if args.revision=='v1' else '_'+args.revision
    exe=ROOT/(('build/stage5_04_baseline' if args.variant=='baseline' else 'build/stage5_04_board')+suffix)/'asr_llm_tts_smoke'
    command=['stdbuf','-oL','-eL',str(exe),audio['alsa_device'],
             base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',
             base+'/asr_runtime/vad/silero_vad.onnx',base+'/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm',
             base+'/tts_runtime/models/kokoro-multi-lang-v1_1',audio['alsa_device'],str(args.seconds),str(args.tts_threads),'17',
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
    sample_number=0; pid_token=None; text_done=False; vision_done=False; lines=[]; next_sample=start
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
                samples.write(json.dumps(profile_sample(child.pid,sample_number))+'\n');samples.flush();next_sample=now+1;sample_number+=1
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
             'image_profile_errors':'[ImageProfile ERROR]' in terminal,'shutdown_complete_marker':'[Shutdown] complete' in terminal,'program_PASS':bool(re.search(r'^PASS\s*$',terminal,re.M)),
             'text_tts_completed':text_done,'vision_tts_completed':vision_done,'user_audible_confirmation':None,'variant':args.variant,'input_mode':'fixed_audio_REAL_ASR_no_microphone_VAD' if args.audio_replay_file else ('controlled_text_no_microphone_ASR' if args.replay else 'real_microphone_ASR'),'stop_mode':args.stop_mode}
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'dmesg':query(['dmesg','--ctime'])})
    save(report/'result.json',summary)
    print('STAGE5_04_RUN_RESULT',json.dumps(summary),flush=True)
    print('REMOTE_REPORT',report,flush=True)
    return 0 # transport succeeded; child return code remains explicitly recorded above


if __name__=='__main__':
    raise SystemExit(main())
```

