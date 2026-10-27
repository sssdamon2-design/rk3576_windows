#pragma once
// 防止当前头文件在一次编译过程中被重复包含。
//
// 例如：
// main.cpp -> camera_service.h
// cli.h  -> camera_service.h
//
// 如果多个地方间接包含这个头文件，#pragma once 可以避免重复定义。


#include <atomic>
// 提供 std::atomic。
//
// 当前主要使用：
//
// std::atomic<bool> running_;
//
// atomic = 原子类型。
//
// 它可以让多个线程安全地读写一个简单变量，
// 而不需要每次都手动加 mutex。
//
// 当前场景：
//
// 主线程：
// running_ = false
//
// Camera 采集线程：
// while (running_)
//
// 两个线程都会访问 running_，
// 所以不能简单使用普通 bool。


#include <chrono>
// 提供 C++ 时间相关功能。
//
// chrono = 时间库。
//
// 当前主要使用：
//
// std::chrono::steady_clock
//
// 用于：
// 1. 记录 Camera 开始运行时间。
// 2. 记录 Camera 停止时间。
// 3. 根据 frame_count / 运行时间计算平均 FPS。


#include <mutex>
// 提供互斥锁相关类型。
//
// 当前主要使用：
//
// std::mutex
//
// 后面的 .cpp 中还会使用：
//
// std::lock_guard<std::mutex>
//
// mutex 主要用于保护：
//
// 1. start / stop 生命周期操作。
// 2. CameraStats 统计数据。


#include <string>
// 提供 std::string。
//
// 当前主要用于：
//
// CameraStats::last_error
//
// 以及 setError() 的错误字符串参数。


#include <thread>
// 提供 std::thread。
//
// 当前 CameraService 会创建一个后台采集线程：
//
// capture_thread_
//
// 这个线程会不断执行：
//
// VideoCapture::captureFrame()
// ↓
// 获取 ImageFrame
// ↓
// 更新 LatestFrameBuffer


#include "video/latest_frame_buffer.h"
// 引入 LatestFrameBuffer。
//
// CameraService 每成功采集一帧之后，
// 会把最新 ImageFrame 放进 LatestFrameBuffer。
//
// 数据流：
//
// Camera
// ↓
// VideoCapture
// ↓
// CameraService
// ↓
// LatestFrameBuffer


#include "video/video_capture.h"
#include "video/owned_frame_pool.h"
// 引入 VideoCapture。
//
// CameraService 内部拥有一个 VideoCapture 对象：
//
// VideoCapture camera_;
//
// VideoCapture 负责：
// “怎么获取一帧”。
//
// CameraService 负责：
// “怎么在独立线程里不断获取一帧”。



struct CameraStats
// 定义 Camera 运行状态和统计信息。
//
// 这个结构体主要用于把 CameraService 的运行情况
// 提供给上层，例如 CLI。
//
// 你之前输入：
//
// stats
//
// 最后看到的：
//
// frame_count=268
// approximate_fps=29.79
// timeout_count=0
//
// 就来自这里。
{
    uint64_t frame_count = 0;
    // 成功采集到的帧数量。
    //
    // CameraService 每成功拿到一帧后：
    //
    // ++stats_.frame_count;
    //
    // 注意：
    // 这是“CameraService 成功处理的帧数”，
    // 不是驱动内部总共产生过多少帧。


    uint64_t timeout_count = 0;
    // captureFrame() 返回 Timeout 的次数。
    //
    // 例如：
    //
    // poll(fd, 200ms)
    // ↓
    // 200ms 内没有新帧
    // ↓
    // CaptureStatus::Timeout
    // ↓
    // ++timeout_count
    //
    // Timeout 通常是可恢复状态，
    // 并不一定说明 Camera 已经坏了。


    double approximate_fps = 0.0;
    // Camera 当前统计得到的“近似平均 FPS”。
    //
    // 计算思想大致是：
    //
    // frame_count
    // ------------
    // 运行总秒数
    //
    // 例如：
    //
    // 298帧 / 10秒
    // ≈ 29.8 FPS
    //
    // approximate：
    // 表示这是一个近似统计值，
    // 不是严格的瞬时 FPS。


    bool running = false;
    // 表示 CameraService 当前是否正在运行。
    //
    // true：
    // Camera 采集线程正在运行。
    //
    // false：
    // CameraService 已停止。


    std::string last_error;
    uint64_t driver_sequence_gaps=0,pool_discarded=0;
    // 保存最近一次 CameraService 错误信息。
    //
    // 例如：
    //
    // Camera capture failed: /dev/video11: VIDIOC_DQBUF: ...
    //
    // 上层 CLI 可以通过 CameraStats 获取并显示这个错误。
};



class CameraService
// 定义 CameraService 类。
//
// CameraService 是 VideoCapture 的上一层。
//
// VideoCapture：
// 负责“获取一帧”。
//
// CameraService：
// 负责：
//
// 1. 创建 Camera 后台线程。
// 2. 持续调用 VideoCapture::captureFrame()。
// 3. 把最新帧写入 LatestFrameBuffer。
// 4. 管理线程启动和停止。
// 5. 统计 FPS、超时次数和错误。
//
// 整体关系：
//
// Camera Hardware
//      ↓
// VideoCapture
//      ↓
// CameraService
//      ↓
// LatestFrameBuffer
{
public:
    // public：
    // 外部模块可以调用这些接口。


    CameraService(
        const std::string& device,
        // Camera 设备节点。
        //
        // 例如：
        //
        // "/dev/video11"
        //
        // const std::string&：
        // 只读引用，不复制整个字符串。

        uint32_t width,
        // 请求的图像宽度。
        //
        // 当前通常为：
        //
        // 3840

        uint32_t height,
        // 请求的图像高度。
        //
        // 当前通常为：
        //
        // 2160

        uint32_t pixel_format,
        // 请求的 Camera 像素格式。
        //
        // 当前为 NV12 对应的 FourCC。

        LatestFrameBuffer& latest_frame_buffer
        // 外部传进来的 LatestFrameBuffer。
        //
        // 注意这里是“引用”：
        //
        // CameraService 自己并不创建一个新的
        // LatestFrameBuffer。
        //
        // 它引用 main() 中已经存在的那个：
        //
        // LatestFrameBuffer frames;
        //
        // CameraService camera(..., frames);
        //
        // 因此 CameraService 和 VLM 等模块
        // 可以共享同一个最新帧仓库。
    );


    ~CameraService();
    // 析构函数。
    //
    // CameraService 对象销毁时自动调用。
    //
    // .cpp 中会执行：
    //
    // stop();
    //
    // 也就是确保：
    //
    // 1. 请求采集线程退出。
    // 2. join 线程。
    // 3. 关闭 Camera。
    //
    // 避免 CameraService 对象销毁后，
    // 后台线程还继续访问已经失效的 this 指针。


    CameraService(const CameraService&) = delete;
    // 删除复制构造函数。
    //
    // 禁止：
    //
    // CameraService camera1(...);
    // CameraService camera2 = camera1;
    //
    // 为什么不能复制？
    //
    // CameraService 内部拥有：
    //
    // std::thread
    // VideoCapture
    // mutex
    // atomic
    //
    // 这些资源不能简单复制。
    //
    // 特别是 std::thread 本身就不可复制。


    CameraService& operator=(const CameraService&) = delete;
    // 删除复制赋值运算符。
    //
    // 禁止：
    //
    // camera2 = camera1;
    //
    // 原因同上：
    // CameraService 管理线程和系统资源，
    // 所以不允许通过普通复制方式复制整个服务。


    bool start();
    // 启动 CameraService。
    //
    // 主要流程大致为：
    //
    // 检查是否已经运行
    // ↓
    // 初始化 VideoCapture
    // ↓
    // running_ = true
    // ↓
    // 创建 capture_thread_
    // ↓
    // 后台执行 captureLoop()
    //
    // 返回：
    //
    // true：
    // 启动成功。
    //
    // false：
    // Camera 初始化或线程创建失败。


    void stop();
    // 停止 CameraService。
    //
    // 主要流程大致为：
    //
    // running_ = false
    // ↓
    // 等待 capture_thread_ 退出
    // ↓
    // join()
    // ↓
    // camera_.shutdown()
    //
    // void：
    // 不返回业务结果。


    bool isRunning() const;
    // 查询 CameraService 当前是否正在运行。
    //
    // 返回：
    //
    // true：
    // 正在运行。
    //
    // false：
    // 已停止。
    //
    // 后面的 const：
    //
    // isRunning() const
    //
    // 表示这个函数承诺：
    // 不修改 CameraService 对象本身。


    CameraStats stats() const;
    // 获取 Camera 当前统计信息。
    //
    // 返回一个 CameraStats 副本。
    //
    // 里面包括：
//
// frame_count
    // timeout_count
    // approximate_fps
    // running
    // last_error
    //
    // 这个函数后面需要读取 stats_，
    // 因此会使用 stats_mutex_ 进行加锁保护。
    //
    // 后面的 const：
    // 表示从逻辑上讲，
    // “读取统计信息”不改变 CameraService 的业务状态。


private:
    // private：
    // 下面的函数和成员变量只能由 CameraService 内部使用。


    void captureLoop();
    // Camera 后台采集线程真正执行的循环函数。
    //
    // capture_thread_ 创建以后，
    // 会进入这个函数。
    //
    // 大致逻辑：
    //
    // while (running_)
    // {
    //     创建 ImageFrame
    //
    //     camera_.captureFrame(...)
    //
    //     成功：
    //         更新 LatestFrameBuffer
    //         frame_count++
    //
    //     Timeout：
    //         timeout_count++
    //         continue
    //
    //     Error：
    //         保存错误
    //         break
    // }
    //
    // 这是 CameraService 最核心的函数。


    void setError(const std::string& message);
    // 设置 CameraService 最近一次错误信息。
    //
    // 因为 stats_.last_error
    // 可能被多个线程访问，
    //
    // 所以 setError() 内部会使用 stats_mutex_ 加锁。
    //
    // const std::string&：
    // 使用只读引用传入错误字符串，
    // 避免不必要的字符串复制。


    std::unique_ptr<OwnedFramePool> frame_pool_;
    VideoCapture camera_;
    // CameraService 内部拥有一个 VideoCapture 对象。
    //
    // VideoCapture：
    // 管理底层 V4L2。
    //
    // CameraService：
    // 使用 VideoCapture 实现持续采集。
    //
    // 对象关系：
//
// CameraService
    //     │
    //     └── owns
    //          VideoCapture
    //
    // 也就是说：
    // VideoCapture 的生命周期由 CameraService 管理。


    LatestFrameBuffer& latest_frame_buffer_;
    // 保存对外部 LatestFrameBuffer 的引用。
    //
    // 注意：
    //
    // 这里不是：
    //
    // LatestFrameBuffer latest_frame_buffer_;
    //
    // 而是：
    //
    // LatestFrameBuffer&
    //
    // 表示引用已有对象。
    //
    // CameraService 不拥有这个对象。
    //
    // 所以必须保证：
    //
    // latest_frame_buffer_
    // 指向的对象比 CameraService 活得更久。
    //
    // 例如 main.cpp：
    //
    // LatestFrameBuffer frames;
    // CameraService camera(..., frames);
    //
    // 创建顺序：
    //
    // frames
    // ↓
    // camera
    //
    // C++ 局部变量析构顺序相反：
    //
    // camera
    // ↓
    // frames
    //
    // 因此 CameraService 析构时，
    // frames 仍然有效。


    std::thread capture_thread_;
    // Camera 后台采集线程对象。
    //
    // start() 中会创建：
    //
    // capture_thread_ =
    //     std::thread(
    //         &CameraService::captureLoop,
    //         this
    //     );
    //
    // 之后：
    //
    // 主线程
    //     ↓
    // CLI / LLM / VLM
    //
    // Camera线程
    //     ↓
    // captureLoop()
    //
    // 两个线程可以同时运行。
    //
    // 所以用户在 CLI 输入问题时，
    // Camera仍然可以继续维持约30 FPS采集。


    std::atomic<bool> running_{false};
    // CameraService 的线程运行标志。
    //
    // atomic<bool>：
    // 原子布尔变量。
    //
    // 初始：
    //
    // false
    //
    // start()：
    //
    // running_.store(true);
    //
    // stop()：
    //
    // running_.store(false);
    //
    // captureLoop()：
    //
    // while (running_.load())
    //
    // 为什么不用普通 bool？
    //
    // 因为：
    //
    // 主线程会写 running_，
    // Camera线程会读 running_。
    //
    // 这是典型的跨线程共享变量。
    //
    // 如果使用普通 bool，
    // 会产生数据竞争（data race）。
    //
    // atomic 可以保证这种简单读写的线程安全。
    //
    // 注意：
    // atomic 并不是“任何复杂操作都不需要 mutex”。
    // 它这里只适合保护 running_ 这种简单状态。


    std::mutex lifecycle_mutex_;
    // 生命周期互斥锁。
    //
    // lifecycle：
    // 生命周期。
    //
    // 主要用于串行化：
    //
    // start()
    // stop()
    //
    // 防止两个线程同时调用：
    //
    // start() 与 stop()
    // 或两个 start()
    // 或两个 stop()
    //
    // 导致线程对象和 Camera 状态混乱。
    //
    // 例如：
    //
    // 线程A：start()
    // 线程B：stop()
    //
    // 如果没有锁，
    // 可能同时修改：
    //
    // capture_thread_
    // running_
    // camera_
    //
    // 所以 start/stop 都会锁住 lifecycle_mutex_。
    //
    // 特别注意：
    //
    // captureLoop() 不持有这个 mutex。
    //
    // 否则：
    //
    // stop()
    // 锁 lifecycle_mutex_
    // ↓
    // join()
    // ↓
    // 等 captureLoop()
    //
    // 如果 captureLoop() 又等待同一个 mutex，
    // 就可能死锁。


    mutable std::mutex stats_mutex_;
    // 用于保护 stats_ 以及部分统计时间信息。
    //
    // 为什么需要 mutex？
    //
    // Camera线程可能在修改：
    //
    // frame_count
    // timeout_count
    // last_error
    //
    // 同时主线程可能调用：
    //
    // stats()
    //
    // 如果不加锁，
    // 多线程同时读写 stats_
    // 会产生数据竞争。
    //
    // 前面的 mutable 非常重要。
    //
    // stats() 被声明成：
    //
    // CameraStats stats() const;
    //
    // const 成员函数通常不能修改成员变量。
    //
    // 但是 stats() 为了“读取统计信息”
    // 必须临时 lock / unlock mutex。
    //
    // 锁 mutex 从业务逻辑上并不算
    // “修改 CameraService 状态”。
    //
    // 所以把 mutex 声明成 mutable，
    // 允许 const 成员函数对它加锁。
    //
    // mutable 可以先理解成：
    //
    // “即使对象处于 const 访问场景，
    // 这个成员仍允许发生必要的内部修改。”


    CameraStats stats_;
    // 真正保存 Camera 统计数据。
    //
    // 包括：
//
// frame_count
    // timeout_count
    // approximate_fps
    // running
    // last_error
    //
    // 注意：
    //
    // 对 stats_ 的并发访问
    // 需要通过 stats_mutex_ 保护。


    std::chrono::steady_clock::time_point started_at_{};
    // 记录 CameraService 开始运行的时间点。
    //
    // steady_clock：
    // 单调时钟。
    //
    // time_point：
    // 某一个时间点。
    //
    // {}：
    // 默认初始化。
    //
    // start() 成功后会记录：
    //
    // started_at_ =
    //     std::chrono::steady_clock::now();
    //
    // 后面用于计算运行时长。


    std::chrono::steady_clock::time_point stopped_at_{};
    // 记录 CameraService 停止的时间点。
    //
    // Camera运行时：
    // 通常 stopped_at_ 为空。
    //
    // Camera停止后：
    //
    // stopped_at_ =
    //     std::chrono::steady_clock::now();
    //
    // 后面 stats() 可以使用：
    //
    // stopped_at_ - started_at_
    //
    // 得到总运行时间。
    //
    // 然后计算：
    //
    // approximate_fps =
    //     frame_count / seconds
};