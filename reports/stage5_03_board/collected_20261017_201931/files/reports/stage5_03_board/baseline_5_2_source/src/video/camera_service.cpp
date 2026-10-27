#include "video/camera_service.h"
// 引入 CameraService 类自己的头文件。
//
// camera_service.h 中已经声明了：
//
// CameraStats
// CameraService
// CameraService::start()
// CameraService::stop()
// CameraService::captureLoop()
// 等。
//
// 当前 .cpp 文件负责给这些成员函数写具体实现。


#include <exception>
// 提供 C++ 标准异常相关类型。
//
// 这里主要使用：
//
// std::exception
//
// catch (const std::exception& e)
//
// 用于捕获大部分标准 C++ 异常，
// 并通过 e.what() 获取异常原因。


#include <utility>
// 提供 std::move()。
//
// 后面会使用：
//
// std::move(frame)
//
// 把 ImageFrame 内部的数据资源转移给 shared_ptr 管理的对象，
// 避免再复制一整幅图像。



CameraService::CameraService(
    const std::string& device,
    uint32_t width,
    uint32_t height,
    uint32_t pixel_format,
    LatestFrameBuffer& latest_frame_buffer
)
// CameraService 构造函数。
//
// 参数：
//
// device：
// Camera 设备路径，例如 "/dev/video11"。
//
// width：
// 请求的图像宽度，例如 3840。
//
// height：
// 请求的图像高度，例如 2160。
//
// pixel_format：
// 像素格式，例如 NV12。
//
// latest_frame_buffer：
// 外部已经存在的 LatestFrameBuffer。
// CameraService 不自己创建新的帧仓库，
// 而是引用外面的那一个。
//
// 例如 main.cpp:
//
// LatestFrameBuffer frames;
//
// CameraService camera(
//     "/dev/video11",
//     3840,
//     2160,
//     nv12,
//     frames
// );
//
// 所以 CameraService 和后面的 VLM
// 使用的是同一个 LatestFrameBuffer。
    : camera_(
        device,
        width,
        height,
        pixel_format
      ),
      // 使用传入的 Camera 配置，
      // 直接构造 CameraService 内部的 VideoCapture 对象 camera_。
      //
      // 等价关系可以理解为：
      //
      // CameraService
      //     │
      //     └── VideoCapture camera_
      //
      // camera_ 由 CameraService 自己拥有。


      latest_frame_buffer_(latest_frame_buffer)
      // 初始化引用成员 latest_frame_buffer_。
      //
      // 注意：
      // 这里不是复制一个 LatestFrameBuffer。
      //
      // 而是：
      //
      // latest_frame_buffer_
      //        ↓
      // 引用 main() 中已有的 frames 对象。
      //
      // 因此外部 frames 的生命周期
      // 必须长于 CameraService。
{
    // 构造函数体为空。
    //
    // camera_ 和 latest_frame_buffer_
    // 已经通过成员初始化列表完成初始化。
}



CameraService::~CameraService()
{
    stop();
    // CameraService 析构时自动停止 Camera 服务。
    //
    // 这是非常重要的生命周期保护。
    //
    // 如果析构时不 stop()：
    //
    // CameraService 对象已经销毁
    // ↓
    // Camera后台线程还在运行
    // ↓
    // captureLoop() 继续访问 this
    // ↓
    // 访问已经失效的对象
    //
    // 就可能产生：
    //
    // 崩溃
    // Use-after-free
    // 未定义行为
    //
    // 所以析构函数必须确保：
    //
    // running_ = false
    // ↓
    // join()
    // ↓
    // Camera线程彻底结束
    // ↓
    // 才允许对象销毁。
}



bool CameraService::start()
// 启动 CameraService。
//
// 整体流程大致为：
//
// 锁住生命周期
// ↓
// 如果已经运行，直接返回
// ↓
// 清理上一次残留线程
// ↓
// 清理 Camera
// ↓
// 清空 LatestFrame
// ↓
// 清空统计信息
// ↓
// 初始化 VideoCapture
// ↓
// running_ = true
// ↓
// 创建 Camera采集线程
// ↓
// 后台执行 captureLoop()
{
    std::lock_guard<std::mutex> lifecycle_lock(lifecycle_mutex_);
    // 使用 lifecycle_mutex_ 保护整个 start() 生命周期操作。
    //
    // std::lock_guard<std::mutex>：
    // RAII 风格的自动加锁工具。
    //
    // 创建 lifecycle_lock 时：
    //
    // lifecycle_mutex_.lock()
    //
    // 当 start() 函数结束，
    // lifecycle_lock 离开作用域时：
    //
    // lifecycle_mutex_.unlock()
    //
    // 所以不需要手写：
    //
    // mutex.lock();
    // ...
    // mutex.unlock();
    //
    // 为什么 start() 要加锁？
    //
    // 防止两个线程同时：
    //
    // start()
    // start()
    //
    // 或：
    //
    // start()
    // stop()
    //
    // 同时操作：
    //
    // capture_thread_
    // camera_
    // running_
    //
    // 导致生命周期状态混乱。


    if (running_.load())
    {
        return true;
    }
    // atomic<bool> 的 load()：
    //
    // 原子读取 running_。
    //
    // 如果 CameraService 已经运行：
    //
    // running_ == true
    //
    // 再次 start() 没必要重复创建线程，
    // 所以直接返回 true。
    //
    // 这种行为称为：
    //
    // start() 对重复调用具有一定“幂等性”。
    //
    // 即：
    //
    // 已经启动
    // ↓
    // 再启动
    // ↓
    // 状态不发生破坏。


    // 出错退出的线程也必须 join，才能重新赋值 std::thread。
    if (capture_thread_.joinable())
    {
        capture_thread_.join();
    }
    // joinable()：
    // 判断 std::thread 当前是否关联着一个线程。
    //
    // 一个线程即使已经执行完 captureLoop()，
    // 对应的 std::thread 对象仍然可能处于 joinable 状态。
    //
    // 例如：
    //
    // captureLoop()
    // ↓
    // Camera发生Error
    // ↓
    // captureLoop结束
    //
    // 但是 capture_thread_ 仍然必须：
    //
    // join()
    //
    // 才算真正把线程资源“回收干净”。
    //
    // 为什么必须在重新赋值前 join？
    //
    // 因为如果一个 std::thread 仍然 joinable，
    // 直接给它赋一个新的 std::thread，
    // 会导致 std::terminate()。
    //
    // 所以这里确保：
    //
    // 旧线程彻底回收
    // ↓
    // 才允许后面创建新的线程。


    camera_.shutdown();
    // 把 VideoCapture 清理到干净状态。
    //
    // 即使前一次已经关闭，
    // shutdown() 也设计成可以安全重复调用。
    //
    // 内部会尝试：
    //
    // STREAMOFF
    // ↓
    // munmap
    // ↓
    // close(fd)


    latest_frame_buffer_.clear();
    // 清空上一轮 CameraService 留下来的最新帧。
    //
    // 为什么要清？
    //
    // 假设 Camera 上一次已经停止，
    // LatestFrameBuffer 里还保存着 Frame 1000。
    //
    // 如果现在重新启动 Camera，
    // 在新帧还没有到达之前，
    // VLM 可能错误读取上一轮的旧帧。
    //
    // 所以：
    //
    // 新的一轮 Camera 生命周期开始
    // ↓
    // 先清空旧帧。


    {
        // 单独创建一个局部作用域。
        //
        // 目的是让下面 stats_mutex_ 的锁
        // 尽早释放。
        //
        // 不让统计锁一直持有到 start() 函数结束。


        std::lock_guard<std::mutex> lock(stats_mutex_);
        // 锁住统计数据。
        //
        // 防止其他线程同时访问 stats_。


        stats_ = {};
        // 把整个 CameraStats 恢复成默认值。
        //
        // 大致等价于：
        //
        // stats_.frame_count = 0;
        // stats_.timeout_count = 0;
        // stats_.approximate_fps = 0;
        // stats_.running = false;
        // stats_.last_error.clear();
        //
        // {} 表示使用默认初始化状态。


        started_at_ = {};
        // 清空上一次 Camera 的启动时间。


        stopped_at_ = {};
        // 清空上一次 Camera 的停止时间。
    }
    // 离开这个作用域。
    //
    // lock 析构。
    //
    // stats_mutex_ 自动解锁。


    try
    // 开始可能发生 C++ 异常的初始化操作。
    //
    // 尤其是：
    //
    // std::thread 创建
    //
    // 可能因为系统资源不足等原因抛异常。
    {
        if (!camera_.initialize())
        // 初始化真正的 V4L2 Camera。
        //
        // camera_.initialize() 内部：
        //
        // open()
        // ↓
        // QUERYCAP / S_FMT
        // ↓
        // mmap
        // ↓
        // QBUF
        // ↓
        // STREAMON
        //
        // 返回 false 表示初始化失败。
        {
            setError(
                "Camera initialization failed: " +
                camera_.lastError()
            );
            // 把 VideoCapture 的底层错误
            // 加上 CameraService 上层描述。
            //
            // 例如最终可能得到：
            //
            // Camera initialization failed:
            // /dev/video11: VIDIOC_S_FMT: Invalid argument


            camera_.shutdown();
            // 初始化失败后再次确保 Camera资源已经释放。


            return false;
            // CameraService 启动失败。
        }


        {
            // 再创建一个小作用域，
            // 让 stats_mutex_ 尽快释放。


            std::lock_guard<std::mutex> lock(stats_mutex_);
            // 保护 started_at_。


            started_at_ =
                std::chrono::steady_clock::now();
            // 记录 CameraService 正式启动的时间。
            //
            // 后面的 stats() 会计算：
            //
            // 当前时间 - started_at_
            //
            // 得到运行秒数。
        }


        running_.store(true);
        // 原子地把运行状态改为 true。
        //
        // 之后 captureLoop() 中：
        //
        // while (running_.load())
        //
        // 才会真正开始循环。
        //
        // 为什么在线程创建前设 true？
        //
        // 因为新线程一旦创建，
        // 可能立即开始执行 captureLoop()。
        //
        // 所以在线程开始之前，
        // running_ 必须已经处于 true 状态。


        capture_thread_ =
            std::thread(
                &CameraService::captureLoop,
                this
            );
        // 创建真正的 Camera 后台采集线程。
        //
        // 这是 CameraService 最重要的一句代码之一。
        //
        // std::thread(...)：
        // 创建一个新的线程。
        //
        // &CameraService::captureLoop：
        // 表示要在线程中执行：
        //
        // CameraService 类的 captureLoop 成员函数。
        //
        // 注意：
        //
        // captureLoop 不是普通全局函数，
        // 它是成员函数。
        //
        // 成员函数必须依赖一个具体对象执行。
        //
        // 所以还要传：
        //
        // this
        //
        // this：
        // 指向当前 CameraService 对象的指针。
        //
        // 相当于告诉新线程：
        //
        // “执行当前这个 CameraService 对象的
        // captureLoop()。”
        //
        // 创建后系统里大致变成：
        //
        // 主线程
        // │
        // ├── CLI
        // ├── Router
        // └── LLM/VLM
        //
        // Camera线程
        // │
        // └── captureLoop()
        //
        // 两个线程并发执行。


        return true;
        // Camera初始化成功，
        // 后台线程也创建成功。
        //
        // start() 成功。
    }


    catch (const std::exception& e)
    // 捕获标准 C++ 异常。
    //
    // const std::exception&：
    // 使用引用，不复制异常对象。
    //
    // e.what()：
    // 返回异常的文字描述。
    {
        setError(
            std::string(
                "Camera initialization/thread start exception: "
            ) +
            e.what()
        );
        // 把异常原因保存到 CameraStats。
        //
        // std::string(...)：
        // 把前面的字符串显式变成 std::string，
        // 然后可以和 e.what() 拼接。
    }


    catch (...)
    // 捕获所有没有被前一个 catch 捕获的异常。
    //
    // ... 表示：
    //
    // “不管是什么异常类型，都接住。”
    {
        setError(
            "Camera initialization/thread start: unknown exception"
        );
        // 因为不知道具体异常类型，
        // 所以记录一个通用错误信息。
    }


    running_.store(false);
    // 如果执行到了这里，
    // 说明 try 中发生了异常。
    //
    // 确保运行状态恢复为 false。


    camera_.shutdown();
    // 清理可能已经部分初始化成功的 Camera资源。


    {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        // 加锁保护 stopped_at_。


        stopped_at_ =
            std::chrono::steady_clock::now();
        // 记录启动失败后的结束时间。
    }


    return false;
    // start() 最终失败。
}



void CameraService::stop()
// 停止 CameraService。
//
// 主要顺序：
//
// lifecycle_mutex_
// ↓
// running_ = false
// ↓
// join Camera线程
// ↓
// shutdown VideoCapture
// ↓
// 清空 LatestFrame
{
    std::lock_guard<std::mutex>
        lifecycle_lock(lifecycle_mutex_);
    // 锁住 CameraService 生命周期。
    //
    // 防止：
    //
    // 一个线程正在 stop()
    //
    // 另一个线程同时 start()
    //
    // 对 capture_thread_ / camera_
    // 做并发生命周期操作。


    running_.store(false);
    // 原子地向 Camera采集线程发出：
    //
    // “请停止。”
    //
    // captureLoop() 每次循环都会检查：
    //
    // while (running_.load())
    //
    // 所以它最终会退出循环。


    // join 后才释放设备，不与采集线程并发 close/munmap。
    if (capture_thread_.joinable())
    {
        capture_thread_.join();
    }
    // 如果 Camera线程存在，
    // 主线程在这里等待它彻底结束。
    //
    // join() 的含义可以理解为：
    //
    // “我这个线程在这里等，
    // 直到 capture_thread_ 执行结束。”
    //
    // 为什么先 join，再 camera_.shutdown()？
    //
    // 因为 Camera线程可能正在：
    //
    // poll()
    // DQBUF
    // memcpy
    // QBUF
    //
    // 如果主线程此时同时：
    //
    // close(fd)
    // munmap()
    //
    // 就会出现非常危险的并发资源释放。
    //
    // 正确顺序：
    //
    // running_ = false
    // ↓
    // Camera线程自己退出
    // ↓
    // join确认线程结束
    // ↓
    // 再释放Camera资源。


    camera_.shutdown();
    // Camera线程已经结束，
    // 现在主线程可以安全释放 VideoCapture资源。
    //
    // 即使 captureLoop() 退出时已经调用过 shutdown()，
    // 这里重复 shutdown 也是安全设计。


    latest_frame_buffer_.clear();
    // CameraService 停止以后，
    // 最新帧也一起清空。
    //
    // 避免上层继续拿到“Camera已经停掉之前的旧画面”。
}



bool CameraService::isRunning() const
{
    return running_.load();
}
// 查询 CameraService 是否运行。
//
// running_ 是 atomic<bool>，
// 所以使用 load() 原子读取。
//
// 后面的 const 表示：
// 这个函数不会改变 CameraService 的业务状态。



void CameraService::setError(
    const std::string& message
)
// 统一设置 CameraService 的错误信息。
//
// message 使用 const 引用传入，
// 避免复制字符串，同时不允许修改调用者字符串。
{
    std::lock_guard<std::mutex> lock(stats_mutex_);
    // 锁住统计数据。
    //
    // 因为：
//
// Camera线程
    // 可能调用 setError()
    //
    // 主线程
    // 可能同时调用 stats()
    //
    // 所以必须同步访问 stats_。


    stats_.last_error = message;
    // 保存最新错误信息。
}



CameraStats CameraService::stats() const
// 获取当前 Camera 统计状态。
//
// 注意返回的是 CameraStats 的“副本”。
//
// 外部拿到 result 后随便修改，
// 不会直接修改 CameraService 内部 stats_。
{
    std::lock_guard<std::mutex> lock(stats_mutex_);
    // 锁住 stats_。
    //
    // 为什么 stats() 是 const，
    // 却还能 lock stats_mutex_？
    //
    // 因为头文件里 stats_mutex_ 声明成：
    //
    // mutable std::mutex stats_mutex_;
    //
    // mutable 允许 const 成员函数
    // 修改这个“内部实现状态”。


    CameraStats result = stats_;
    // 把内部统计信息复制一份出来。
    //
    // 之后我们修改的是 result，
    // 不直接修改原来的 stats_。
    //
    // 这有一个好处：
    //
    // stats_ 主要保存原始统计数据，
    // approximate_fps 可以在查询时动态计算。


    result.running = running_.load();
    // running 状态不直接依赖 stats_.running。
    //
    // 而是读取真正的 atomic：
    //
    // running_
    //
    // 保证返回的是当前实时状态。


    if (
        started_at_ !=
        std::chrono::steady_clock::time_point{}
    )
    // 判断 CameraService 是否已经记录过启动时间。
    //
    // std::chrono::steady_clock::time_point{}
    //
    // 表示一个默认构造的“空时间点”。
    //
    // 如果 started_at_ 不等于空时间点，
    // 说明 Camera曾经成功启动过。
    {
        const auto end =
            stopped_at_ ==
                    std::chrono::steady_clock::time_point{}
                ? std::chrono::steady_clock::now()
                : stopped_at_;
        // 使用三目运算符决定统计结束时间。
        //
        // 条件：
        //
        // stopped_at_ 是否为空？
        //
        // 如果为空：
        //
        // Camera目前还在运行
        // ↓
        // end = 当前时间
        //
        // 如果不为空：
        //
        // Camera已经停止
        // ↓
        // end = 实际停止时间
        //
        // 三目运算符形式：
        //
        // condition ? value_if_true : value_if_false


        const double seconds =
            std::chrono::duration<double>(
                end - started_at_
            ).count();
        // 计算 CameraService 总共运行了多少秒。
        //
        // end - started_at_
        //
        // 得到一个 duration（时间间隔）。
        //
        // std::chrono::duration<double>
        //
        // 把时间间隔转换成以“秒”为单位的 double。
        //
        // .count()
        //
        // 取出具体数值。
        //
        // 例如：
        //
        // seconds = 9.0


        if (seconds > 0)
        {
            result.approximate_fps =
                result.frame_count / seconds;
        }
        // 计算近似平均 FPS：
        //
        // 成功采集帧数
        // ------------
        // 运行秒数
        //
        // 例如：
        //
        // 268 / 8.996
        // ≈ 29.79 FPS
        //
        // 这就是你之前实机看到的：
        //
        // approximate_fps=29.79
    }


    return result;
    // 返回统计信息副本。
}



void CameraService::captureLoop()
// Camera后台线程真正执行的函数。
//
// 当 start() 中执行：
//
// capture_thread_ =
//     std::thread(
//         &CameraService::captureLoop,
//         this
//     );
//
// 新线程就会进入这里。
//
// 这是 CameraService 最核心的函数。
{
    try
    // 整个采集循环放在 try 中。
    //
    // 防止后台线程发生 C++ 异常后
    // 直接触发 std::terminate()。
    {
        while (running_.load())
        // 只要 running_ 仍然为 true，
        // Camera线程就持续采集。
        //
        // 主线程调用 stop()：
        //
        // running_.store(false)
        //
        // 之后 Camera线程下一次检查
        // running_.load()
        // 就会退出循环。
        {
            ImageFrame frame;
            // 创建一个当前循环使用的临时 ImageFrame。
            //
            // 每次循环对应一帧。
            //
            // VideoCapture 会把新图像写进这里。


            const auto status =
                camera_.captureFrame(
                    frame,
                    200
                );
            // 调用底层 VideoCapture 获取一帧。
            //
            // 最多 poll 等待 200ms。
            //
            // 返回值类型实际为：
            //
            // VideoCapture::CaptureStatus
            //
            // 因为使用 auto，
            // 编译器自动推导类型。
            //
            // 三种结果：
            //
            // Frame
            // Timeout
            // Error


            if (
                status ==
                VideoCapture::CaptureStatus::Timeout
            )
            // 本轮 200ms 没等到新帧。
            //
            // Timeout 是“可恢复状态”，
            // 不是立刻终止 Camera线程。
            {
                std::lock_guard<std::mutex>
                    lock(stats_mutex_);
                // 修改统计数据前加锁。


                ++stats_.timeout_count;
                // 超时次数 +1。


                continue;
                // 结束当前这一轮循环，
                // 直接开始下一轮 while。
                //
                // 相当于：
                //
                // Timeout
                // ↓
                // 记一次
                // ↓
                // 再 poll 下一帧
            }


            if (
                status ==
                VideoCapture::CaptureStatus::Error
            )
            // 发生真正的 Camera采集错误。
            {
                setError(
                    "Camera capture failed: " +
                    camera_.lastError()
                );
                // 把 VideoCapture 底层错误
                // 转换成 CameraService 错误。


                break;
                // 退出 while 循环。
                //
                // Error 和 Timeout 的区别就在这里：
                //
                // Timeout
                // ↓
                // continue
                //
                // Error
                // ↓
                // break
            }


            if (!running_.load())
            {
                break;
            }
            // 这是一个非常重要的“二次停止检查”。
            //
            // 为什么 while 开头已经检查 running_，
            // 这里还要再检查？
            //
            // 因为可能出现：
            //
            // Camera线程：
            // captureFrame(frame, 200)
            // 正在 poll 等帧
            //
            // 同时主线程：
            // stop()
            // running_ = false
            //
            // 然后 poll 返回了一个 Frame。
            //
            // 如果这里不再检查 running_，
            // Camera线程可能仍然把这最后一帧
            // 写进 LatestFrameBuffer。
            //
            // 所以：
            //
            // captureFrame 返回以后
            // ↓
            // 再检查一次 stop 请求
            // ↓
            // 如果已经 stop
            // 就直接退出，不再发布新帧。


            latest_frame_buffer_.update(std::make_shared<const ImageFrame>(std::move(frame)));
            // 这是整个 Camera → LatestFrame
            // 数据链路最关键的一行。
            //
            // 从里向外看。
            //
            //
            // 1.
            //
            // std::move(frame)
            //
            // 把当前 ImageFrame 的资源
            // 转移出去。
            //
            // frame.data 里面可能有约 12MB 图像数据。
            //
            // move 的目的：
            // 不再复制一次这 12MB。
            //
            //
            // 2.
            //
            // std::make_shared<const ImageFrame>(...)
            //
            // 在堆上创建一个 ImageFrame 对象，
            // 并使用 shared_ptr 管理它。
            //
            // 返回类型大致是：
            //
            // std::shared_ptr<const ImageFrame>
            //
            // const ImageFrame：
            // 后面的消费者只能读这一帧，
            // 不能修改它。
            //
            //
            // 为什么用 shared_ptr？
            //
            // 因为一张 Frame 可能同时被：
            //
            // LatestFrameBuffer
            // VLM
            // YOLO
            // 其他消费者
            //
            // 共同持有。
            //
            // 即使 LatestFrameBuffer 已经被新帧覆盖，
            // 只要 VLM 还持有旧 Frame 的 shared_ptr，
            // 旧 Frame 就不会被销毁。
            //
            //
            // 3.
            //
            // latest_frame_buffer_.update(...)
            //
            // 把这一帧设为“当前最新帧”。
            //
            // 注意：
            //
            // LatestFrameBuffer 不是 FIFO队列。
            //
            // 它只保存：
            //
            // 最新的一帧。
            //
            // 因此：
            //
            // Frame 100
            // ↓
            // Frame 101
            //
            // 101 会取代 100 成为“最新帧”。
            //
            // 这正符合 VLM 按需取最新画面的场景。


            std::lock_guard<std::mutex>
                lock(stats_mutex_);
            // 更新统计信息之前加锁。


            ++stats_.frame_count;
            // 成功发布一帧以后，
            // 成功帧数 +1。
            //
            // 所以你之前：
            //
            // frame_count=268
            //
            // 就是这里一直累加得到的。
        }
    }


    catch (const std::exception& e)
    {
        setError(
            std::string(
                "Camera capture exception: "
            ) +
            e.what()
        );
    }
    // 捕获 Camera线程中的标准异常。
    //
    // 非常重要：
    //
    // 如果一个 std::thread 中的异常
    // 一直冒出线程函数而没有被捕获，
    // 程序可能调用：
    //
    // std::terminate()
    //
    // 所以后台线程一般必须自己处理异常。


    catch (...)
    {
        setError(
            "Camera capture: unknown exception"
        );
    }
    // 捕获其他未知异常。


    latest_frame_buffer_.clear();
    // captureLoop 即将退出。
    //
    // 不管退出原因是：
    //
    // stop()
    // Camera Error
    // C++异常
    //
    // 都把最新帧清空。
    //
    // 避免 Camera 已经停止，
    // 但系统还把旧图像当成“当前画面”。


    camera_.shutdown();
    // Camera采集线程自己清理 VideoCapture。
    //
    // 注意：
    //
    // stop() 在 join() 后还会再调用：
    //
    // camera_.shutdown()
    //
    // 所以 VideoCapture::shutdown()
    // 必须支持重复调用。
    //
    // 目前它确实通过：
    //
    // streaming_
    // fd_ >= 0
    // buffers_.clear()
    //
    // 做到了这一点。


    {
        std::lock_guard<std::mutex>
            lock(stats_mutex_);
        // 保护停止时间。


        stopped_at_ =
            std::chrono::steady_clock::now();
        // 记录 Camera线程真正结束的时间。
    }


    running_.store(false);
    // 最后把运行状态改成 false。
    //
    // 无论退出原因是：
    //
    // 用户 stop
    // Camera故障
    // exception
    //
    // 最终 CameraService 都进入：
    //
    // running = false
}