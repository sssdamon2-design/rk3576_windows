#include "video/video_capture.h"
// 引入 VideoCapture 类的声明。
// video_capture.h 中定义了：
// VideoCapture 类、ImageFrame 相关接口、成员变量、成员函数声明等。


#include <cerrno>
#include "common/image_profile.h"
// 提供 errno 以及 Linux/POSIX 错误码。
// 后面会使用：
// EINTR  ：系统调用被信号中断。
// EAGAIN ：当前暂时没有数据，可以稍后重试。


#include <cstring>
// 提供 std::strerror()。
// std::strerror(errno) 可以把 errno 转换成可读的错误字符串。
// 例如：
// errno = EACCES
// strerror(errno) -> "Permission denied"


#include <iostream>
// 提供标准输出和标准错误输出。
// 后面主要使用：
// std::cout
// std::cerr
// std::endl


#include <utility>
#include <array>
// 提供 std::move()。
// 后面会使用：
// frame = std::move(captured);
// 用来转移 ImageFrame 内部 vector 的资源，避免再次复制整幅图像。


#include <fcntl.h>
// Linux/POSIX 文件操作头文件。
// 这里主要提供：
// open()
// O_RDWR
// O_NONBLOCK
// O_CLOEXEC


#include <linux/videodev2.h>
// Linux V4L2 核心头文件。
// V4L2 = Video4Linux2。
//
// 这里定义了大量摄像头相关结构体和 ioctl 命令，例如：
//
// v4l2_capability
// v4l2_format
// v4l2_buffer
// v4l2_plane
// v4l2_requestbuffers
//
// VIDIOC_QUERYCAP
// VIDIOC_S_FMT
// VIDIOC_REQBUFS
// VIDIOC_QUERYBUF
// VIDIOC_QBUF
// VIDIOC_DQBUF
// VIDIOC_STREAMON
// VIDIOC_STREAMOFF


#include <poll.h>
// 提供 poll() 和 pollfd。
//
// poll() 用于等待文件描述符上的事件。
//
// 在这里主要作用是：
// 等待 /dev/video11 有新帧可以获取。
//
// 和 O_NONBLOCK 配合后，可以避免：
// 1. DQBUF 无限阻塞。
// 2. 不断 DQBUF -> EAGAIN 的忙轮询。


#include <sys/ioctl.h>
// 提供 ioctl()。
//
// ioctl = Input/Output Control。
//
// V4L2 很多控制操作最终都通过 ioctl() 完成。


#include <sys/mman.h>
// 提供 mmap() / munmap()。
//
// mmap()：
// 将驱动分配的 V4L2 Buffer 映射到当前进程的用户空间。
//
// munmap()：
// 解除映射。


#include <unistd.h>
// POSIX 基础接口。
// 这里主要使用 close()。
// 这个头文件中还包含 read()、write() 等常见接口。



namespace
// 匿名命名空间（anonymous namespace）。
//
// 里面定义的函数/变量只在当前 video_capture.cpp 内部可见。
//
// 所以 xioctl() 是当前 .cpp 私有的辅助函数，
// 不会暴露给其他 .cpp 文件。
{


int xioctl(int fd, unsigned long request, void* arg)
// 自己封装的一层 ioctl()。
//
// 主要目的：
// 如果 ioctl() 因 EINTR 被信号中断，则自动重试。
//
// 参数：
//
// fd：
// 文件描述符。
// 当前通常是 /dev/video11 对应的 fd_。
//
// request：
// ioctl 命令。
// 例如：
// VIDIOC_QUERYCAP
// VIDIOC_S_FMT
// VIDIOC_DQBUF
//
// arg：
// 指向 ioctl 参数结构体的地址。
// 不同 ioctl 对应不同结构体，因此统一使用 void*。
//
// 返回值：
// 和 ioctl() 的返回值基本一致。
{
    int ret;
    // 保存 ioctl() 的执行结果。


    do
    // do...while：
    // 至少执行一次循环体。
    {
        ret = ::ioctl(fd, request, arg);
        // 真正调用 Linux 提供的 ioctl()。
        //
        // 前面的 :: 表示全局作用域。
        // ::ioctl 表示明确调用全局的 ioctl()，
        // 而不是某个类或命名空间中的同名函数。
    }
    while (ret == -1 && errno == EINTR);
    // 如果：
    //
    // ret == -1
    // 表示 ioctl 调用失败。
    //
    // 同时：
    //
    // errno == EINTR
    // 表示失败原因只是系统调用被信号打断。
    //
    // 这种情况不一定是真正错误，因此重新调用 ioctl。


    return ret;
    // 返回最终 ioctl 的执行结果。
}


} // namespace
// 匿名命名空间结束。



VideoCapture::VideoCapture(
    const std::string& device,
    uint32_t width,
    uint32_t height,
    uint32_t pixel_format
)
// VideoCapture 构造函数实现。
//
// VideoCapture::VideoCapture 中的 :: 表示：
// 当前 VideoCapture() 属于 VideoCapture 类。
//
// 构造函数负责保存 Camera 配置，
// 目前并不会真正 open 摄像头。
    : device_(device),
      // 使用参数 device 初始化成员变量 device_。
      //
      // 例如：
      // device = "/dev/video11"
      //
      // 最终：
      // device_ = "/dev/video11"


      width_(width),
      // 初始化成员变量 width_。
      // 当前通常传入 3840。


      height_(height),
      // 初始化成员变量 height_。
      // 当前通常传入 2160。


      pixel_format_(pixel_format)
      // 初始化成员变量 pixel_format_。
      // 当前通常是 NV12 FourCC。
{
    // 构造函数体为空。
    //
    // 因为成员变量已经通过上面的
    // “成员初始化列表”完成初始化。
}



VideoCapture::~VideoCapture()
// VideoCapture 析构函数。
//
// 当 VideoCapture 对象生命周期结束时自动执行。
{
    shutdown();
    // 自动释放 Camera 资源。
    //
    // 后面 shutdown() 会执行：
    //
    // STREAMOFF
    // ↓
    // munmap
    // ↓
    // close(fd)
}



bool VideoCapture::initialize()
// 初始化整个 Camera。
//
// 成功返回 true。
// 失败返回 false。
//
// 大致流程：
//
// shutdown旧状态
// ↓
// open
// ↓
// configureDevice
// ↓
// initMMap
// ↓
// startStreaming
{
    shutdown();
    // 初始化之前先清理旧资源。
    //
    // 这样 initialize() 可以安全地被重复调用。
    //
    // 如果上一次还存在：
// fd、mmap、streaming
    // 都会先释放。


    last_error_.clear();
    capture_stats_={};have_sequence_=false;
    // 清空之前保存的错误信息。
    //
    // 因为现在准备开始一次新的初始化流程。


    fd_ = ::open(
        device_.c_str(),
        O_RDWR | O_NONBLOCK | O_CLOEXEC
    );
    // 打开 Camera 设备。
    //
    // device_.c_str()：
    // std::string -> const char*
    // 因为 POSIX open() 接收的是 C 风格字符串。
    //
    // O_RDWR：
    // 以读写方式打开设备。
    //
    // O_NONBLOCK：
    // 非阻塞模式。
    // 注意不是“访问 fd 没数据就整个程序退出”。
    // 更准确地说：
    //
    // 某些本来会阻塞等待的操作，
    // 在当前暂时无法完成时立即返回，
    // 并可能设置 errno = EAGAIN。
    //
    // 后面与 poll() 配合使用。
    //
    // O_CLOEXEC：
    // Close On Exec。
    // 如果进程以后 exec 其他程序，
    // 防止 Camera fd 被意外继承。
    //
    // | 是按位或，用来组合多个 flag。


    if (fd_ < 0)
    // open() 失败返回 -1。
    //
    // 合法 fd 一般 >= 0。
    {
        return fail("open " + device_);
        // 保存错误信息并返回 false。
        //
        // 例如可能形成：
        //
        // /dev/video11: open /dev/video11: Permission denied
    }


    if (!configureDevice())
    // 配置 Camera。
    //
    // configureDevice() 主要负责：
    //
    // QUERYCAP
    // ↓
    // 检查能力
    // ↓
    // S_FMT
    //
    // ! 表示逻辑非。
    //
    // 如果 configureDevice() 返回 false，
    // 条件成立。
    {
        shutdown();
        // 配置失败后，把之前 open 的 fd 等资源释放掉。


        return false;
        // 初始化失败。
    }


    if (!initMMap())
    // 初始化 V4L2 mmap Buffer。
    //
    // 后面主要完成：
    //
    // REQBUFS
    // ↓
    // QUERYBUF
    // ↓
    // mmap
    {
        shutdown();
        // 失败时清理此前已经获得的资源。


        return false;
        // 初始化失败。
    }


    if (!startStreaming())
    // 将 Buffer 全部入队，并启动 V4L2 Streaming。
    {
        shutdown();
        // STREAMING 启动失败，也清理已有资源。


        return false;
        // 初始化失败。
    }


    return true;
    // 所有步骤全部成功。
}



bool VideoCapture::configureDevice()
// 配置 V4L2 Camera。
//
// 主要工作：
//
// 1. 查询设备能力。
// 2. 检查是否支持 multi-planar capture。
// 3. 检查是否支持 streaming。
// 4. 设置图像格式。
// 5. 保存驱动最终接受的宽、高、格式、plane 数量、stride。
{
    v4l2_capability capability{};
    // 创建 V4L2 capability 结构体。
    //
    // {} 表示值初始化/零初始化。
    //
    // 该结构体后面用于接收驱动返回的设备能力。


    if (xioctl(fd_, VIDIOC_QUERYCAP, &capability) < 0)
    // VIDIOC_QUERYCAP：
    // Query Capabilities。
    //
    // 查询当前 /dev/video11 支持哪些能力。
    //
    // &capability：
    // 把结构体地址交给内核，
    // 内核会把查询结果填入 capability。
    {
        return fail("VIDIOC_QUERYCAP");
        // QUERYCAP 失败，保存错误并返回 false。
    }


    const uint32_t caps =
        (capability.capabilities & V4L2_CAP_DEVICE_CAPS)
            ? capability.device_caps
            : capability.capabilities;
    // 确定真正应该检查哪一个 capability 字段。
    //
    // capability.capabilities：
    // 描述整体设备节点能力。
    //
    // V4L2_CAP_DEVICE_CAPS：
    // 表示 device_caps 字段有效。
    //
    // & 是按位与。
    //
    // 三目运算符：
    //
    // 条件 ? 条件为真时的值 : 条件为假时的值
    //
    // 所以：
    //
    // 如果支持 DEVICE_CAPS
    //      使用 capability.device_caps
    //
    // 否则
    //      使用 capability.capabilities


    if (!(caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE))
    // 检查设备是否支持：
    //
    // V4L2 multi-planar video capture。
    //
    // caps & FLAG：
    // 检查对应能力位是否存在。
    //
    // 前面的 !：
    // 表示“不支持”。
    {
        return fail(
            "Device does not support V4L2 multi-planar capture",
            false
        );
        // 这里不是 errno 导致的问题，
        // 所以 include_errno = false。
    }


    if (!(caps & V4L2_CAP_STREAMING))
    // 检查 Camera 是否支持 Streaming I/O。
    //
    // 后面的 MMAP + QBUF/DQBUF 都依赖 Streaming。
    {
        return fail(
            "Device does not support V4L2 streaming",
            false
        );
    }


    v4l2_format format{};
    // 创建 V4L2 格式结构体，并全部初始化为 0。
    //
    // 后面向驱动请求：
    //
    // 3840×2160
    // NV12
    // multi-planar


    format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    // 指定当前操作的是：
    //
    // multi-planar Video Capture Buffer。


    format.fmt.pix_mp.width = width_;
    // 请求图像宽度。


    format.fmt.pix_mp.height = height_;
    // 请求图像高度。


    format.fmt.pix_mp.pixelformat = pixel_format_;
    // 请求像素格式。
    //
    // 当前一般为 NV12。


    format.fmt.pix_mp.field = V4L2_FIELD_ANY;
    // field 表示扫描方式/场格式。
    //
    // V4L2_FIELD_ANY：
    // 让驱动选择合适的场格式。


    if (xioctl(fd_, VIDIOC_S_FMT, &format) < 0)
    // VIDIOC_S_FMT：
    // Set Format。
    //
    // 把我们希望使用的：
    //
    // width
    // height
    // pixel format
    //
    // 交给驱动。
    {
        return fail("VIDIOC_S_FMT");
    }


    width_ = format.fmt.pix_mp.width;
    // 注意：
    // S_FMT 后要重新读取驱动返回值。
    //
    // 因为驱动可能没有完全接受我们请求的宽度，
    // 而是自动调整为自己支持的尺寸。


    height_ = format.fmt.pix_mp.height;
    // 保存驱动最终接受的高度。


    pixel_format_ = format.fmt.pix_mp.pixelformat;
    // 保存驱动最终接受的像素格式。


    num_planes_ = format.fmt.pix_mp.num_planes;
    // 保存驱动返回的 plane 数量。
    //
    // 你当前实机输出：
    //
    // planes=1


    if (num_planes_ == 0 || num_planes_ > VIDEO_MAX_PLANES)
    // 检查 plane 数是否合理。
    //
    // == 0：
    // 不可能正常采图。
    //
    // > VIDEO_MAX_PLANES：
    // 超过 V4L2 允许的最大 plane 数。
    //
    // || 是逻辑或。
    {
        return fail(
            "Driver returned invalid plane count",
            false
        );
    }


    plane_strides_.clear();
    // 清空旧的 stride 信息。
    //
    // 防止重复 initialize 时旧数据残留。


    for (uint32_t p = 0; p < num_planes_; ++p)
    // 遍历每一个 plane。
    //
    // p = 0, 1, 2 ...
    //
    // 当前 RK3576 实际 num_planes_ = 1，
    // 所以目前只循环一次。
    {
        plane_strides_.push_back(
            format.fmt.pix_mp.plane_fmt[p].bytesperline
        );
        // 保存该 plane 的 stride。
        //
        // bytesperline：
        // 一行图像数据在内存中实际占多少字节。
        //
        // 注意 width 不一定永远等于 stride，
        // 因为硬件可能做内存对齐。
    }


    std::cout
        << "Camera format: "
        // 打印提示文字。

        << width_
        // 打印驱动实际宽度。

        << "x"
        // 打印乘号形式的 x。

        << height_
        // 打印实际高度。

        << ", planes="
        // 打印 plane 提示。

        << num_planes_
        // 打印 plane 数。

        << std::endl;
        // 换行并刷新输出缓冲。


    std::cout<<"[CameraFormat] width="<<width_<<" height="<<height_<<" fourcc="<<pixel_format_
             <<" planes="<<num_planes_<<" colorspace="<<format.fmt.pix_mp.colorspace
             <<" ycbcr_enc="<<static_cast<unsigned>(format.fmt.pix_mp.ycbcr_enc)<<" quantization="<<static_cast<unsigned>(format.fmt.pix_mp.quantization)<<'\n';
    for(uint32_t p=0;p<num_planes_;++p)std::cout<<"[CameraPlane] plane="<<p<<" bytesperline="<<format.fmt.pix_mp.plane_fmt[p].bytesperline
        <<" sizeimage="<<format.fmt.pix_mp.plane_fmt[p].sizeimage<<'\n';
    return true;
    // Camera 格式配置成功。
}



bool VideoCapture::initMMap()
// 初始化 V4L2 MMAP 缓冲区。
//
// 主要流程：
//
// VIDIOC_REQBUFS
// ↓
// 对每个 Buffer:
//     VIDIOC_QUERYBUF
//     ↓
//     对每个 Plane:
//         mmap()
{
    v4l2_requestbuffers request{};
    // 创建 Buffer 申请结构体。
    //
    // {} 表示全部初始化为 0。


    request.count = 4;
    // 希望驱动分配 4 个 V4L2 Buffer。
    //
    // 注意：
    // 这是“请求 4 个”，
    // 驱动最后实际分配数量可能不同。
    //
    // 所以后面必须重新读取 request.count。


    request.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    // 申请的是 multi-planar 视频采集 Buffer。


    request.memory = V4L2_MEMORY_MMAP;
    // 指定 Buffer 内存访问方式为 MMAP。


    if (xioctl(
            fd_,
            // Camera fd。

            VIDIOC_REQBUFS,
            // Request Buffers。
            // 向驱动申请 Buffer。

            &request
            // 把 request 结构体地址交给驱动。
        ) < 0)
    {
        return fail("VIDIOC_REQBUFS");
        // Buffer 申请失败。
    }


    if (request.count < 2)
    // 检查驱动最终实际分配了多少 Buffer。
    //
    // 当前代码至少要求 2 个。
    //
    // 如果连两个都没有，
    // 不适合正常 Streaming。
    {
        return fail(
            "Not enough V4L2 buffers",
            false
        );
    }


    buffers_.resize(request.count);
    // 调整自己保存的 buffers_ 数组大小。
    //
    // 例如驱动给 4 个：
    //
    // buffers_[0]
    // buffers_[1]
    // buffers_[2]
    // buffers_[3]


    for (uint32_t i = 0;
         i < request.count;
         ++i)
    // 遍历驱动分配的每一个 V4L2 Buffer。
    {
        std::vector<v4l2_plane> planes(num_planes_);
        // 为当前 Buffer 创建 plane 描述数组。
        //
        // V4L2 multi-planar API 要求：
        // buffer.m.planes 指向一个 v4l2_plane 数组。
        //
        // 当前实机 num_planes_ = 1，
        // 所以通常只有 planes[0]。


        v4l2_buffer buffer{};
        // 创建 V4L2 Buffer 描述结构体。
        //
        // 后面 QUERYBUF 会让驱动填充：
        //
        // Buffer 信息
        // Plane 长度
        // mmap offset
        // 等。


        buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        // Buffer 类型：multi-planar capture。


        buffer.memory = V4L2_MEMORY_MMAP;
        // 内存方式：MMAP。


        buffer.index = i;
        // 指定查询第 i 个 Buffer。


        buffer.length = num_planes_;
        // 告诉驱动当前 plane 数组最多容纳多少个 plane。


        buffer.m.planes = planes.data();
        // planes 是 std::vector。
        //
        // planes.data() 返回底层连续数组的地址。
        //
        // 也就是：
        //
        // v4l2_plane*
        //
        // 交给 V4L2 内核接口填写。


        if (xioctl(
                fd_,
                VIDIOC_QUERYBUF,
                &buffer
            ) < 0)
        // 查询第 i 个 Buffer 的详细信息。
        //
        // 主要需要获得：
        //
        // 每个 plane 的 length
        // 每个 plane 的 mmap offset
        {
            return fail(
                "VIDIOC_QUERYBUF buffer=" + std::to_string(i)
            );
            // std::to_string(i)：
            // 把整数 i 转成字符串。
            //
            // 便于错误信息指出是哪个 Buffer 出错。
        }


        if (buffer.length != num_planes_)
        // 检查驱动实际返回的 plane 数是否符合预期。
        {
            return fail(
                "VIDIOC_QUERYBUF plane count mismatch",
                false
            );
        }


        buffers_[i].planes.resize(num_planes_);
        // 为我们自己的第 i 个 MMapBuffer
        // 创建对应数量的 MMapPlane。
        //
        // 用于保存：
        //
        // mmap address
        // mmap length


        for (uint32_t p = 0;
             p < num_planes_;
             ++p)
        // 遍历当前 Buffer 的每一个 Plane。
        {
            void* mapped =
                ::mmap(
                    nullptr,
                    // 第一个参数：
                    // 希望映射到哪个用户空间地址。
                    //
                    // nullptr：
                    // 不指定地址，让内核选择。


                    planes[p].length,
                    // 映射长度。
                    //
                    // 这个长度来自 VIDIOC_QUERYBUF。


                    PROT_READ | PROT_WRITE,
                    // 用户空间映射后的内存权限：
                    //
                    // PROT_READ：
                    // 可以读取。
                    //
                    // PROT_WRITE：
                    // 可以写入。


                    MAP_SHARED,
                    // 建立共享映射。
                    //
                    // 用户空间和驱动共享同一块底层 Buffer。


                    fd_,
                    // Camera 文件描述符。


                    planes[p].m.mem_offset
                    // 当前 V4L2 Plane 对应的 mmap offset。
                    //
                    // 由驱动在 QUERYBUF 时返回。
                );


            if (mapped == MAP_FAILED)
            // mmap 失败时不会返回 nullptr。
            //
            // 而是返回特殊值：
            //
            // MAP_FAILED
            {
                return fail(
                    "mmap buffer=" +
                    std::to_string(i) +
                    " plane=" +
                    std::to_string(p)
                );
            }


            buffers_[i].planes[p].start = mapped;
            // 保存映射后的用户空间地址。


            buffers_[i].planes[p].length = planes[p].length;
            std::cout<<"[CameraMap] buffer="<<i<<" plane="<<p<<" length="<<planes[p].length<<'\n';
            // 保存 mmap 区域长度。
        }
    }


    return true;
    // 所有 Buffer / Plane 都 mmap 成功。
}



bool VideoCapture::startStreaming()
// 将所有 V4L2 Buffer 入队，
// 然后执行 VIDIOC_STREAMON。
//
// 这一步之后 Camera 才正式开始 Streaming。
{
    for (uint32_t i = 0;
         i < buffers_.size();
         ++i)
    // 遍历我们 mmap 的所有 Buffer。
    {
        std::vector<v4l2_plane> planes(num_planes_);
        // 为当前 Buffer 创建临时 plane 描述数组。


        for (uint32_t p = 0;
             p < num_planes_;
             ++p)
        {
            planes[p].length = buffers_[i].planes[p].length;
            // 把当前 mmap Plane 的长度告诉 V4L2。
        }


        v4l2_buffer buffer{};
        // 创建 Buffer 描述结构体。


        buffer.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        // multi-planar capture。


        buffer.memory = V4L2_MEMORY_MMAP;
        // MMAP Buffer。


        buffer.index = i;
        // 当前操作的是第 i 个 Buffer。


        buffer.length = num_planes_;
        // plane 数量。


        buffer.m.planes = planes.data();
        // 让 V4L2 Buffer 指向临时的 plane 数组。


        if (xioctl(
                fd_,
                VIDIOC_QBUF,
                &buffer
            ) < 0)
        // VIDIOC_QBUF：
        // Queue Buffer。
        //
        // 把这个 Buffer 放进驱动的采集队列。
        //
        // 含义可以理解为：
        //
        // “这块 Buffer 已经准备好了，
        // Camera 可以往里面写数据了。”
        {
            return fail(
                "VIDIOC_QBUF buffer=" +
                std::to_string(i)
            );
        }
    }


    v4l2_buf_type type =
        V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    // STREAMON 需要知道启动的是哪一种 Buffer 类型。


    if (xioctl(
            fd_,
            VIDIOC_STREAMON,
            &type
        ) < 0)
    // 正式启动视频流。
    {
        return fail("VIDIOC_STREAMON");
    }


    streaming_ = true;
    // 记录当前对象已经进入 Streaming 状态。


    return true;
    // Streaming 启动成功。
}



bool VideoCapture::captureFrame(
    ImageFrame& frame
)
// 旧版 captureFrame() 接口。
//
// 这个版本只接受 frame，
// 不让调用者指定 timeout。
//
// 内部固定使用 200ms 超时。
{
    const auto status = captureFrame(frame, 200);
    // 调用新版重载：
//
// captureFrame(ImageFrame&, int timeout_ms)
//
// auto：
// 让编译器自动推导类型。
//
// 这里实际类型为：
//
// VideoCapture::CaptureStatus


    if (status == CaptureStatus::Timeout)
    {
        fail(
            "captureFrame timed out or was interrupted",
            false
        );
        // 旧版 bool 接口无法向调用者返回
        // Frame / Timeout / Error 三种状态。
        //
        // 所以如果发生 Timeout，
        // 这里只能把错误字符串保存下来。
    }


    return status == CaptureStatus::Frame;
    // 如果真正成功得到一帧，返回 true。
    //
    // Timeout 或 Error 均返回 false。
}



VideoCapture::CaptureStatus VideoCapture::captureFrame(ImageFrame& frame,int timeout_ms) {
    return captureFrameImpl(&frame,false,timeout_ms);
}
VideoCapture::CaptureStatus VideoCapture::captureReusableFrame(ImageFrame& frame,int timeout_ms) {
    return captureFrameImpl(&frame,true,timeout_ms);
}
VideoCapture::CaptureStatus VideoCapture::discardFrame(int timeout_ms) {
    return captureFrameImpl(nullptr,false,timeout_ms);
}
VideoCapture::CaptureStatus VideoCapture::captureFrameImpl(ImageFrame* output,bool reuse,int timeout_ms)
{
    if (!streaming_ ||
        fd_ < 0 ||
        timeout_ms < 0)
    // 进入采集之前先检查状态。
    //
    // !streaming_：
    // Camera 根本没有 STREAMON。
    //
    // fd_ < 0：
    // Camera 没有有效 fd。
    //
    // timeout_ms < 0：
    // 当前接口不接受负数 timeout。
    {
        fail(
            "captureFrame requires initialized stream and nonnegative timeout",
            false
        );


        return CaptureStatus::Error;
        // 这属于调用状态错误，直接返回 Error。
    }


    pollfd descriptor{};
    // Linux pollfd 结构体。
    //
    // 用于描述：
    //
    // 我要监控哪个 fd？
    // 我关心什么事件？
    // 最后实际发生了什么事件？


    descriptor.fd = fd_;
    // 指定监控 Camera 文件描述符。
    //
    // fd_ 对应当前打开的 /dev/video11。


    descriptor.events = POLLIN;
    // 表示我们关心：
    //
    // “这个 fd 是否已经有数据可读。”
    //
    // 对 V4L2 来说：
    //
    // 通常意味着有已完成的采集 Buffer 可以 DQBUF。


    const auto poll_begin=ImageProfile::Clock::now();
    const int ready =
        ::poll(
            &descriptor,
            // 要监控的 pollfd 数组地址。

            1,
            // 数组里只有 1 个 fd。

            timeout_ms
            // 最大等待时间，单位 ms。
        );
    const auto poll_ms=ImageProfile::ms(poll_begin);



    // poll 返回：
    //
    // ready > 0
    // 有事件发生。
    //
    // ready == 0
    // 等待超时。
    //
    // ready < 0
    // poll 本身出错。


    if (ready == 0 ||
        (ready < 0 && errno == EINTR))
    {
        return CaptureStatus::Timeout;
        // ready == 0：
        // 真正超时。
        //
        // errno == EINTR：
        // poll 被信号中断。
        //
        // 当前设计统一看成可重试的 Timeout。
    }


    if (ready < 0)
    // 这里表示 poll 真正发生错误，
    // 并且不是 EINTR。
    {
        fail("poll");
        // 保存 poll 错误。


        return CaptureStatus::Error;
        // 返回致命采集错误。
    }


    if (descriptor.revents &
        (POLLERR | POLLHUP | POLLNVAL))
    // revents：
    // poll 实际返回的事件。
    //
    // POLLERR：
    // fd 发生错误。
    //
    // POLLHUP：
    // hang up，设备/连接挂断。
    //
    // POLLNVAL：
    // fd 无效。
    //
    // & 是按位与，用于检查这些 bit 是否出现。
    {
        fail(
            "poll device error revents=" +
            std::to_string(descriptor.revents),
            false
        );


        return CaptureStatus::Error;
    }


    if (!(descriptor.revents & POLLIN))
    {
        return CaptureStatus::Timeout;
        // poll 返回了，
        // 但并没有我们期待的 POLLIN。
        //
        // 当前代码把它当成一次可重试状态。
    }


    const auto plane_begin=ImageProfile::Clock::now();
    std::array<v4l2_plane,VIDEO_MAX_PLANES> planes{};
    const double plane_alloc_ms=ImageProfile::ms(plane_begin);
    // 创建 Plane 数组。
    //
    // 后面的 DQBUF 会把每个 Plane 的：
    //
    // bytesused
    // data_offset
    // 等信息写进这里。


    v4l2_buffer buffer{};
    // 创建 V4L2 Buffer 描述结构体。


    buffer.type =
        V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    // 当前操作的是 multi-planar capture Buffer。


    buffer.memory =
        V4L2_MEMORY_MMAP;
    // Buffer 内存类型是 MMAP。


    buffer.length = num_planes_;
    // Plane 数。


    buffer.m.planes = planes.data();
    // 指向 Plane 数组。
    //
    // 让驱动能够把 Plane 信息写进去。


    const auto dq_begin=ImageProfile::Clock::now();
    if (xioctl(
            fd_,
            VIDIOC_DQBUF,
            &buffer
        ) < 0)
    // VIDIOC_DQBUF：
    // Dequeue Buffer。
    //
    // 从驱动“已采集完成的 Buffer 队列”
    // 中取出一个 Buffer。
    //
    // poll 只负责告诉我们：
    // “现在应该有 Buffer 可拿。”
    //
    // 真正把 Buffer 从队列拿出来的是 DQBUF。
    {
        if (errno == EAGAIN)
        {
            return CaptureStatus::Timeout;
        }
        // poll 返回以后设备状态仍可能变化。
        //
        // 而且 fd 使用 O_NONBLOCK，
        // 如果此刻又没有 Buffer，
        // DQBUF 会立即失败并返回 EAGAIN。
        //
        // EAGAIN 不属于致命错误，
        // 下一轮重新 poll 即可。


        fail("VIDIOC_DQBUF");
        // 其他 DQBUF 错误则记录。


        return CaptureStatus::Error;
    }


    const double dq_ms=ImageProfile::ms(dq_begin);
    if (buffer.index >= buffers_.size())
    // 检查驱动返回的 Buffer index 是否越界。
    //
    // 我们自己的 buffers_ 必须存在对应元素。
    {
        fail(
            "VIDIOC_DQBUF invalid buffer index",
            false
        );


        return CaptureStatus::Error;
    }


    if (buffer.length != num_planes_ ||
        (buffer.flags & V4L2_BUF_FLAG_ERROR))
    // 检查两个问题。
    //
    // 1. 驱动返回的 Plane 数与预期不一致。
    //
    // 2. Buffer 带有 V4L2_BUF_FLAG_ERROR。
    //
    // V4L2_BUF_FLAG_ERROR：
    // 表示该 Buffer 采集过程中发生错误。
    {
        fail(
            "VIDIOC_DQBUF invalid planes or V4L2_BUF_FLAG_ERROR",
            false
        );


        return CaptureStatus::Error;
        // CameraService 收到 Error 后会退出采集循环，
        // 后续 shutdown -> STREAMOFF，
        // 由驱动回收 Buffer。
    }


    ++capture_stats_.dequeued;
    if(have_sequence_) {
        const uint32_t distance=buffer.sequence-last_sequence_;
        if(distance>1 && distance<0x80000000u)capture_stats_.sequence_gaps+=distance-1;
    }
    have_sequence_=true;last_sequence_=buffer.sequence;
    if(!output) {
        if(xioctl(fd_,VIDIOC_QBUF,&buffer)<0){fail("VIDIOC_QBUF after discard");return CaptureStatus::Error;}
        ++capture_stats_.discarded;++frame_id_;
        imageSample("capture_pool_discard",0,frame_id_);
        return CaptureStatus::Frame;
    }
    const auto allocation_begin=ImageProfile::Clock::now();
    std::size_t capacity_growths=0;
    ImageFrame fresh;
    ImageFrame& captured=reuse?*output:fresh;
    captured.plane_sizes.clear();captured.data.clear();
    // 创建临时 ImageFrame。
    //
    // 当前帧所有数据先填进 captured，
    // 最后再 move 给调用者的 frame。
    //
    // 这样只有一帧完整有效时，
    // 才会覆盖调用者原来的 frame。


    captured.received_at =
        std::chrono::steady_clock::now();
    // 记录“当前帧被应用层拿到”的本地时间。
    //
    // steady_clock：
    // 单调时钟。
    //
    // 主要用于计算 Frame Age。
    //
    // 使用 steady_clock 的好处：
    // 系统时间修改不会导致它倒退。


    capacity_growths+=plane_strides_.size()>captured.plane_strides.capacity();
    captured.plane_strides = plane_strides_;
    // 把 configureDevice() 保存的
    // 每个 Plane stride 放进当前 ImageFrame。
    //
    // 这里会复制一个很小的 vector，
    // 通常 Plane 数量很少。


    captured.width = width_;
    // 当前图像宽度。


    captured.height = height_;
    // 当前图像高度。


    captured.pixel_format = pixel_format_;
    // 当前像素格式。


    captured.frame_id = ++frame_id_;
    // 帧编号加 1。
    //
    // 第一次成功采集：
    //
    // frame_id_ 0 -> 1
    //
    // captured.frame_id = 1
    //
    // 后面：
    //
    // 2
    // 3
    // ...
    // 1133


    captured.timestamp_ns =
        static_cast<uint64_t>(
            buffer.timestamp.tv_sec
        ) * 1000000000ULL
        +
        static_cast<uint64_t>(
            buffer.timestamp.tv_usec
        ) * 1000ULL;
    // 把 V4L2 Buffer 时间戳转换成纳秒。
    //
    // buffer.timestamp：
    // 驱动提供的 timeval。
    //
    // tv_sec：
    // 秒。
    //
    // 1 秒 = 1,000,000,000 ns。
    //
    // tv_usec：
    // 微秒。
    //
    // 1 微秒 = 1000 ns。
    //
    // static_cast<uint64_t>：
    // 显式转换成 uint64_t，
    // 避免较小整数类型计算时发生问题。
    //
    // ULL：
    // unsigned long long 常量后缀。
    //
    // 注意：
    // 驱动 timestamp 的时钟域不一定和
    // std::chrono::steady_clock 相同。
    //
    // 所以 Frame Age 当前使用 received_at，
    // 而不是直接用 timestamp_ns。


    std::size_t total_size = 0;
    // 计算这一帧所有 Plane
    // 真正有效数据一共多少字节。
    //
    // 后面用于 vector.reserve()。


    for (uint32_t p = 0;
         p < num_planes_;
         ++p)
    // 第一遍遍历所有 Plane。
    //
    // 主要完成：
    //
    // 1. 边界检查。
    // 2. 记录每个 Plane 有效大小。
    // 3. 计算总数据长度。
    {
        if (planes[p].data_offset >
                planes[p].bytesused ||
            planes[p].bytesused >
                buffers_[buffer.index].planes[p].length)
        // 做内存边界检查。
        //
        // data_offset：
        // 当前 Plane 真正有效数据的起始偏移。
        //
        // bytesused：
        // 驱动报告的当前 Plane 使用到了多少字节。
        //
        // 合法关系应该是：
        //
        // data_offset <= bytesused <= mmap Plane长度
        //
        // 如果不满足，后面复制就可能越界。
        {
            fail(
                "VIDIOC_DQBUF plane bounds invalid, plane=" +
                std::to_string(p),
                false
            );


            return CaptureStatus::Error;
        }


        capacity_growths+=captured.plane_sizes.size()==captured.plane_sizes.capacity();
        captured.plane_sizes.push_back(
            planes[p].bytesused -
            planes[p].data_offset
        );
        // 保存当前 Plane 真正有效数据大小。
        //
        // 有效大小：
        //
        // bytesused - data_offset


        if (planes[p].bytesused >
            planes[p].data_offset)
        // 如果确实有有效数据。
        {
            total_size +=
                planes[p].bytesused -
                planes[p].data_offset;
            // 累加到整帧有效数据总长度。
        }
    }


    capacity_growths+=total_size>captured.data.capacity();
    const auto reserve_begin=ImageProfile::Clock::now();
    captured.data.reserve(total_size);
    const double reserve_ms=ImageProfile::ms(reserve_begin);
    const double allocation_ms=ImageProfile::ms(allocation_begin);
    const auto copy_begin=ImageProfile::Clock::now();
    // 给 ImageFrame::data 预留足够容量。
    //
    // reserve()：
    // 只改变 vector 的 capacity，
    // 不改变 size。
    //
    // 目的：
    // 后面 insert() 多个 Plane 时，
    // 尽量避免 vector 多次扩容和重新分配。
    //
    // 当前 3840×2160 NV12 一帧：
    //
    // 12,441,600 Bytes。


    for (uint32_t p = 0;
         p < num_planes_;
         ++p)
    // 第二遍遍历 Plane。
    //
    // 这一遍真正把 mmap Buffer 中的数据
    // CPU Copy 到 ImageFrame::data。
    {
        std::size_t offset =
            planes[p].data_offset;
        // 当前 Plane 中，
        // 真正有效数据的起始偏移。


        std::size_t bytes = 0;
        // 当前 Plane 需要复制多少字节。


        if (planes[p].bytesused > offset)
        {
            bytes =
                planes[p].bytesused -
                offset;
            // 有效数据长度：
            //
            // bytesused - data_offset
        }


        if (bytes == 0)
        {
            continue;
        }
        // 当前 Plane 没有有效数据，
        // 跳到下一个 Plane。


        const uint8_t* start =
            static_cast<const uint8_t*>(
                buffers_[buffer.index]
                    .planes[p]
                    .start
            )
            + offset;
        // 获取当前 Plane 真正有效数据的起始地址。
        //
        // buffers_[buffer.index]
        // 找到 DQBUF 返回的那一块 Buffer。
        //
        // .planes[p]
        // 找到其中第 p 个 Plane。
        //
        // .start
        // 是 mmap() 返回的 void* 地址。
        //
        // static_cast<const uint8_t*>：
        // 把 void* 转换成字节指针。
        //
        // 为什么变成 uint8_t*？
        //
        // 因为图像本质可以按一个个 byte 复制。
        //
        // + offset：
        // 跳过 data_offset。


        captured.data.insert(
            captured.data.end(),
            // 把新数据插到 vector 末尾。

            start,
            // 数据起点。

            start + bytes
            // 数据终点。
        );
        // 这一行真正发生：
        //
        // V4L2 MMAP Buffer
        //       ↓
        //      CPU Copy
        //       ↓
        // ImageFrame::data
        //
        // 当前版本仍然有一次整帧 CPU Copy。
        //
        // 以后做 DMA-BUF / zero-copy 时，
        // 这里就是重点优化位置之一。
    }


    const double copy_ms=ImageProfile::ms(copy_begin);
    const auto qbuf_begin=ImageProfile::Clock::now();
    if (xioctl(
            fd_,
            VIDIOC_QBUF,
            &buffer
        ) < 0)
    // 数据复制完成后，
    // 把这块 V4L2 Buffer 重新放回驱动队列。
    //
    // QBUF：
    // Queue Buffer。
    //
    // 含义：
    //
    // “我已经用完这块 Buffer，
    // 驱动可以继续往里面采下一帧了。”
    {
        fail("VIDIOC_QBUF after capture");


        return CaptureStatus::Error;
    }


    const double qbuf_ms=ImageProfile::ms(qbuf_begin);
    imageSample("camera_poll_wait",poll_ms,captured.frame_id);
    imageSample("camera_dqbuf",dq_ms,captured.frame_id);
    imageSample("capture_plane_descriptor_alloc",plane_alloc_ms,captured.frame_id,0,0);
    imageSample("capture_alloc_prepare",allocation_ms,captured.frame_id,total_size,capacity_growths);
    imageSample("capture_payload_reserve",reserve_ms,captured.frame_id);
    imageSample("capture_owned_copy",copy_ms,captured.frame_id,total_size);
    imageSample("camera_qbuf",qbuf_ms,captured.frame_id);
    if(!reuse)*output=std::move(captured);
    // 把临时 ImageFrame 的资源转移给调用者的 frame。
    //
    // 这里非常重要。
    //
    // captured.data 是一个约 12MB 的 vector。
    //
    // 如果普通复制：
    //
    // frame = captured;
    //
    // 会再次复制整幅图像。
    //
    // 使用：
    //
    // std::move(captured)
    //
    // 主要是把 vector 内部管理的堆内存所有权
    // 转移给 frame。
    //
    // 通常不会再次复制那 12MB 图像数据。


    return CaptureStatus::Frame;
    // 成功得到完整的一帧。
}



void VideoCapture::stopStreaming()
// 停止 V4L2 Streaming。
{
    if (!streaming_)
    // 如果本来就没有启动 Streaming，
    // 不需要执行 STREAMOFF。
    {
        return;
    }


    v4l2_buf_type type =
        V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    // 指定要停止的是 multi-planar capture。


    if (::ioctl(
            fd_,
            VIDIOC_STREAMOFF,
            &type
        ) < 0)
    // 调用 STREAMOFF。
    //
    // 这里没有使用 xioctl，
    // 因为清理路径尽量直接尝试释放资源。
    {
        std::cerr
            << "VIDIOC_STREAMOFF: "
            << std::strerror(errno)
            << std::endl;
        // STREAMOFF 失败时直接打印错误。
    }


    streaming_ = false;
    // 无论 ioctl 是否成功，
    // 当前对象都不再把自己视为 streaming 状态。
}



void VideoCapture::releaseMMap()
// 释放所有 mmap 映射。
{
    for (auto& buffer : buffers_)
    // 遍历 buffers_ 中所有 MMapBuffer。
    //
    // auto&：
    // 自动推导类型，并且使用引用，
    // 不复制整个 MMapBuffer。
    {
        for (auto& plane : buffer.planes)
        // 遍历当前 Buffer 内的所有 Plane。
        //
        // 同样使用引用，
        // 直接操作原来的 MMapPlane。
        {
            if (plane.start != nullptr)
            // 如果当前 Plane 确实存在有效 mmap 地址。
            {
                if (::munmap(
                        plane.start,
                        // mmap 起始地址。

                        plane.length
                        // mmap 长度。
                    ) < 0)
                // 解除用户空间内存映射。
                {
                    std::cerr
                        << "munmap: "
                        << std::strerror(errno)
                        << std::endl;
                }


                plane.start = nullptr;
                // 映射已经释放，
                // 把指针重置为空。


                plane.length = 0;
                // 长度也重置。
            }
        }
    }


    buffers_.clear();
    // 清空保存 Buffer 信息的 vector。
    //
    // 注意：
    // 真正 mmap 的内存已经在前面的 munmap() 中释放。
    //
    // clear() 这里负责清除 C++ 容器中的描述信息。
}



void VideoCapture::shutdown()
// 统一关闭 Camera。
// 
// 清理顺序：
//
// STREAMOFF
// ↓
// munmap
// ↓
// close
//
// 这个顺序是有意义的：
// 先让设备停止使用 Buffer，
// 再解除 Buffer 映射，
// 最后关闭 fd。
{
    stopStreaming();
    // 如果正在 Streaming，先 STREAMOFF。


    releaseMMap();
    // 解除所有 mmap。


    if (fd_ >= 0)
    // fd >= 0 表示 Camera fd 仍然有效。
    {
        if (::close(fd_) < 0)
        // 关闭 Camera 文件描述符。
        {
            std::cerr
                << "close camera: "
                << std::strerror(errno)
                << std::endl;
        }


        fd_ = -1;
        // close 后立即把成员变量改回 -1。
        //
        // 避免后续代码误认为 fd 仍然有效，
        // 也避免再次 close 同一个 fd。
    }
}



bool VideoCapture::fail(
    const std::string& operation,
    bool include_errno
)
// 统一生成并保存错误信息。
//
// 参数：
//
// operation：
// 哪一个操作失败。
// 例如：
//
// VIDIOC_DQBUF
// VIDIOC_S_FMT
// mmap buffer=0 plane=0
//
// include_errno：
// 是否把当前 errno 对应的系统错误信息一起加进去。
//
// 最终始终返回 false。
{
    last_error_ =
        device_ +
        ": " +
        operation;
    // 先形成基础错误信息。
    //
    // 例如：
    //
    // /dev/video11: VIDIOC_DQBUF


    if (include_errno)
    // 如果需要系统 errno 信息。
    {
        last_error_ +=
            ": " +
            std::string(
                std::strerror(errno)
            );
        // strerror(errno) 返回 C 风格字符串：
        //
        // const char*
        //
        // std::string(...) 把它转换为 C++ string。
        //
        // 最终可能得到：
        //
        // /dev/video11: VIDIOC_DQBUF: Input/output error
    }


    return false;
    // fail() 统一返回 false。
    //
    // 所以其他函数可以方便地写：
    //
    // return fail("VIDIOC_S_FMT");
}