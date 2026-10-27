#pragma once
// 防止当前头文件在一次编译过程中被重复包含。
// 例如多个 .h 间接 include video_capture.h 时，只会展开一次。


#include <cstddef>
// 提供 std::size_t。
// std::size_t 常用于表示内存大小、数组长度、缓冲区长度等。

#include <cstdint>
// 提供固定长度整数类型，例如：
// uint32_t：32 位无符号整数。
// uint64_t：64 位无符号整数。

#include <string>
// 提供 std::string 字符串类型。

#include <vector>
// 提供 std::vector 动态数组容器。
// vector 的大小可以动态变化，并且会自动管理内存。


#include "common/types.h"
// 引入我们项目自己的公共数据类型。
// 这里主要需要里面定义的 ImageFrame。
// VideoCapture 抓取一帧之后，会把图像数据保存到 ImageFrame 中。


class VideoCapture
// 定义 VideoCapture 类。
// 这个类负责管理一个 V4L2 Camera 设备。
// 主要职责：
// 1. 初始化摄像头。
// 2. 配置 V4L2。
// 3. mmap 映射缓冲区。
// 4. 获取一帧图像。
// 5. 关闭摄像头并释放资源。
{
public:
    // public：下面这些成员可以被类外部调用。
    // 例如 main.cpp、CameraService 都可以调用这些函数。


    enum class CaptureStatus
    // 定义一个“强类型枚举”。
    // 注意：这里不是“类里面套了一个类”。
    // enum class 本质仍然是枚举，只是类型更加安全。
    {
        Frame,
        // 成功获取到一帧图像。

        Timeout,
        // 等待图像超时。
        // 这通常不是致命错误，可以继续下一次采集。

        Error
        // 真正发生了采集错误。
        // 通常意味着当前 Camera 采集应该停止。
    };


    VideoCapture(
    // VideoCapture 的构造函数。
    // 构造函数名字必须和类名相同，并且没有返回值。
    // 创建 VideoCapture 对象时会自动调用。

        const std::string& device,
        // device：摄像头设备路径，例如 "/dev/video11"。
        //
        // std::string：字符串类型。
        // &：引用，不复制整个字符串。
        // const：函数不能通过这个引用修改调用者原来的字符串。
        //
        // const std::string& 是 C++ 中很常见的只读参数传递方式。

        uint32_t width,
        // 请求的图像宽度。
        // 当前项目中通常是 3840。

        uint32_t height,
        // 请求的图像高度。
        // 当前项目中通常是 2160。

        uint32_t pixel_format
        // 请求的像素格式。
        // 当前使用 NV12，对应一个 32 位 FourCC 编码。
    );


    ~VideoCapture();
    // 析构函数。
    // 对象生命周期结束时会自动执行。
    //
    // ~ 表示析构函数。
    //
    // 在 .cpp 中析构函数会调用 shutdown()，
    // 用来关闭 Stream、munmap、close fd 等资源。


    bool initialize();
    // 初始化摄像头。
    //
    // 内部大致完成：
    //
    // open()
    //   ↓
    // VIDIOC_QUERYCAP
    //   ↓
    // VIDIOC_S_FMT
    //   ↓
    // VIDIOC_REQBUFS
    //   ↓
    // VIDIOC_QUERYBUF
    //   ↓
    // mmap()
    //   ↓
    // VIDIOC_QBUF
    //   ↓
    // VIDIOC_STREAMON
    //
    // 返回 true：初始化成功。
    // 返回 false：初始化失败。


    VideoCapture(const VideoCapture&) = delete;
    // 删除“复制构造函数”。
    //
    // 即禁止：
    //
    // VideoCapture camera1(...);
    // VideoCapture camera2 = camera1;   // 不允许
    //
    // 原因：
    // VideoCapture 内部拥有 fd、mmap 地址、V4L2 Buffer 等系统资源。
    // 如果简单复制，就可能出现两个对象同时认为自己拥有同一个 fd，
    // 最终发生重复 close、重复 munmap 等严重问题。
    //
    // = delete：
    // 明确告诉编译器“不允许使用这个函数”。
    // 就是禁用： VideoCapture(const VideoCapture&) 这个函数

    VideoCapture& operator=(const VideoCapture&) = delete;
    // 删除“复制赋值运算符”。
    //
    // 即禁止：
    //
    // camera2 = camera1;
    //
    // 原因和上面一样：
    // VideoCapture 管理的是独占的系统资源，不能简单复制。
    //
    // VideoCapture&：
    // 这里原本表示赋值运算符返回当前 VideoCapture 对象的引用。
    // 但因为 = delete，所以这个操作被禁止了。


    CaptureStatus captureFrame(ImageFrame& frame, int timeout_ms);
    // Caller owns an exclusive fresh lease; failure may leave this destination partially filled.
    CaptureStatus captureReusableFrame(ImageFrame& frame,int timeout_ms);
    CaptureStatus discardFrame(int timeout_ms);
    struct CaptureStats {uint64_t dequeued=0,sequence_gaps=0,discarded=0;};
    // Capture-thread only, or after join. CameraService publishes a locked snapshot.
    CaptureStats captureStats() const {return capture_stats_;}

    // 获取一帧图像，这是现在主要使用的采集接口。
    //
    // ImageFrame& frame：
    // frame 是引用。
    // 函数直接修改调用者传入的 ImageFrame，
    // 不会复制一整个 ImageFrame 作为形参。
    //
    // timeout_ms：
    // 最多等待多少毫秒。
    // CameraService 当前调用时传入 200。
    //
    // 返回值 CaptureStatus 有三种：
    //
    // Frame   ：成功获取一帧。
    // Timeout ：等待超时，可以继续重试。
    // Error   ：真正采集错误。


    const std::string& lastError() const
    // 获取最近一次错误信息。
    //
    // 前面的：
    //
    // const std::string&
    //
    // 表示返回 last_error_ 的“只读引用”，
    // 不复制整个字符串，也不允许调用者通过该引用修改它。
    //
    // 后面的：
    //
    // lastError() const
    //
    // 表示这个成员函数承诺：
    // 不修改当前 VideoCapture 对象内部状态。
    {
        return last_error_;
        // 返回类内部保存的最近一次错误字符串。
    }


    bool captureFrame(ImageFrame& frame);
    // 保留下来的旧版 captureFrame 接口。
    //
    // 只有一个参数，没有显式传 timeout_ms。
    //
    // 这里和上面的 captureFrame 名字相同，
    // 但参数数量不同。
    //
    // 这叫“函数重载（Function Overloading）”。
    //
    // 可以分别调用：
    //
    // captureFrame(frame);
    //
    // 或：
    //
    // captureFrame(frame, 200);
    //
    // 这个旧接口主要用于兼容之前已经写好的代码。


    void shutdown();
    // 关闭 Camera，并释放摄像头相关资源。
    //
    // 内部主要会完成：
    //
    // STREAMOFF
    //   ↓
    // munmap
    //   ↓
    // close(fd)
    //
    // void 表示函数没有返回值。


private:
    // private：下面的内容只能由 VideoCapture 类内部使用。
    //
    // 外部代码不应该直接操作：
    //
    // fd_
    // buffers_
    // mmap 地址
    // STREAMON / STREAMOFF
    //
    // 这些底层资源全部由 VideoCapture 自己管理。


    struct MMapPlane
    // 定义一个内部结构体。
    //
    // 表示 V4L2 Buffer 中的一个 plane 对应的 mmap 内存区域。
    //
    // 一个 plane 至少需要记录：
    // 1. 用户空间映射地址。
    // 2. 映射区域长度。
    {
        void* start = nullptr;
        // mmap() 返回的用户空间起始地址。
        //
        // void* 表示“没有指定具体数据类型的内存地址”。
        //
        // 初始值 nullptr：
        // 表示当前还没有映射任何有效内存。

        std::size_t length = 0;
        // 当前 mmap 区域的长度，单位是字节。
        //
        // std::size_t 专门适合表示内存大小。
        //
        // 初始值 0：
        // 表示还没有有效映射。
    };


    struct MMapBuffer
    // 表示一个完整的 V4L2 Buffer。
    //
    // V4L2 multi-planar 模式下，
    // 一个 Buffer 可能包含一个或多个 plane。
    {
        std::vector<MMapPlane> planes;
        // 保存这个 V4L2 Buffer 中所有 plane 的 mmap 信息。
        //
        // 例如：
        //
        // Buffer 0
        //   ├── Plane 0
        //   └── Plane 1
        //
        // 你目前 RK3576 实际输出：
        //
        // planes = 1
        //
        // 所以当前一个 Buffer 实际只有一个 Plane。
    };


    CaptureStatus captureFrameImpl(ImageFrame* output,bool reuse,int timeout_ms);
    CaptureStats capture_stats_;
    uint32_t last_sequence_=0;
    bool have_sequence_=false;
    bool configureDevice();
    // 配置 V4L2 Camera 设备。
    //
    // 主要完成：
    //
    // VIDIOC_QUERYCAP
    //   ↓
    // 检查是否支持 Video Capture Multiplanar
    //   ↓
    // 检查是否支持 Streaming
    //   ↓
    // VIDIOC_S_FMT
    //   ↓
    // 获取驱动最终接受的宽、高、格式、plane 数量、stride 等。


    bool initMMap();
    // 初始化 V4L2 mmap Buffer。
    //
    // 主要完成：
    //
    // VIDIOC_REQBUFS
    //   ↓
    // VIDIOC_QUERYBUF
    //   ↓
    // mmap()
    //
    // 把驱动分配的 Buffer 映射到用户空间。


    bool startStreaming();
    // 启动 V4L2 Streaming。
    //
    // 主要完成：
    //
    // 所有 Buffer 先 VIDIOC_QBUF 入队
    //   ↓
    // VIDIOC_STREAMON
    //
    // 之后摄像头才正式开始往 Buffer 中填充图像。


    void stopStreaming();
    // 停止 V4L2 Streaming。
    //
    // 主要执行：
    //
    // VIDIOC_STREAMOFF


    void releaseMMap();
    // 释放之前通过 mmap() 建立的用户空间映射。
    //
    // 主要执行：
    //
    // munmap()


    bool fail(
        const std::string& operation,
        // operation 表示发生错误的操作名称。
        // 例如：
        //
        // "VIDIOC_DQBUF"
        // "VIDIOC_S_FMT"
        // "mmap buffer=0"

        bool include_errno = true
        // 是否把当前 errno 对应的 Linux 错误字符串一起记录。
        //
        // 默认值 true。
        //
        // 所以调用：
        //
        // fail("VIDIOC_DQBUF");
        //
        // 等价于：
        //
        // fail("VIDIOC_DQBUF", true);
    );
    // 统一记录错误信息。
    //
    // 最终把错误保存在：
    //
    // last_error_
    //
    // 返回 false，
    // 所以可以直接写：
    //
    // return fail("VIDIOC_S_FMT");


private:
    // 下面这些是真正保存 VideoCapture 状态的成员变量。


    std::string device_;
    // 摄像头设备节点路径。
    //
    // 当前一般为：
    //
    // /dev/video11


    uint32_t width_;
    // 当前图像宽度。
    //
    // 初始来自构造函数。
    // VIDIOC_S_FMT 后会更新成驱动真正接受的宽度。


    uint32_t height_;
    // 当前图像高度。
    //
    // 当前实际为 2160。


    uint32_t pixel_format_;
    // 当前像素格式。
    //
    // 当前使用 NV12。


    int fd_ = -1;
    // 摄像头设备的 Linux 文件描述符。
    //
    // open("/dev/video11", ...)
    //
    // 成功以后可能变成：
    //
    // fd_ = 3
    // fd_ = 7
    // 等。
    //
    // 初始值 -1 表示：
    //
    // 当前没有打开有效的 Camera fd。


    uint32_t num_planes_ = 0;
    // 当前 V4L2 图像格式有多少个 plane。
    //
    // 由 VIDIOC_S_FMT 返回的：
    //
    // format.fmt.pix_mp.num_planes
    //
    // 得到。
    //
    // 当前实机输出：
    //
    // planes=1
    //
    // 所以现在通常：
    //
    // num_planes_ = 1。


    std::vector<MMapBuffer> buffers_;
    // 保存所有 V4L2 mmap Buffer 的用户空间映射信息。
    //
    // 当前代码申请：
    //
    // request.count = 4
    //
    // 如果驱动最终也提供 4 个 Buffer，
    // buffers_ 大致为：
    //
    // buffers_[0]
    // buffers_[1]
    // buffers_[2]
    // buffers_[3]
    //
    // 每个 Buffer 内部又有自己的 planes。


    bool streaming_ = false;
    // 记录当前 Camera 是否已经处于 Streaming 状态。
    //
    // false：
    // 还没有 STREAMON，或者已经 STREAMOFF。
    //
    // true：
    // 已经成功执行 VIDIOC_STREAMON。
    //
    // 主要用于避免重复 STREAMOFF 等操作。


    uint64_t frame_id_ = 0;
    // 当前成功采集到的帧编号。
    //
    // 每成功获取一帧：
    //
    // ++frame_id_
    //
    // 所以会依次变成：
    //
    // 1
    // 2
    // 3
    // ...
    // 268
    // ...
    // 1133
    //
    // 你之前 CLI 看到的 Frame ID 就来自这里。


    std::vector<uint32_t> plane_strides_;
    // 保存每个 plane 的 stride。
    //
    // stride 可以理解为：
    //
    // “图像一行在内存中实际占多少字节。”
    //
    // 它来自：
    //
    // format.fmt.pix_mp.plane_fmt[p].bytesperline
    //
    // 注意：
    //
    // width 并不一定永远等于 stride。
    //
    // 因为硬件可能为了：
    //
    // DMA 对齐
    // 内存对齐
    // 访问效率
    //
    // 在每行末尾增加 padding。


    std::string last_error_;
    // 保存最近一次错误信息。
    //
    // 例如：
    //
    // /dev/video11: VIDIOC_DQBUF: Input/output error
    //
    // 上层 CameraService 可以通过：
    //
    // camera_.lastError()
    //
    // 读取这个错误，并继续传给 CLI。
};