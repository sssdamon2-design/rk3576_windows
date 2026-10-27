#include <exception>
#include <iostream>
#include <memory>
#include "ai/rk_backends.h"
#include "app/cli.h"

int main(int argc, char** argv)
{
    try
    {
        AppConfig config;                //定义一个config类
        std::string error;
        if (!parseArguments(argc, argv, config, error))      //解析`argc/argv`，填充 config；失败返回 false，把错误信息写入`error`字符串
        {
            std::cerr << error << '\n';
            printUsage();
            return 2;
        }
        if (config.help) { printUsage(); return 0; }

        LatestFrameBuffer frames; // 创建最新帧 类 
        // NV12 FourCC 是格式标识，不依赖 Linux 头文件；V4L2 实现在 video 模块。
        constexpr uint32_t nv12 = uint32_t('N') | (uint32_t('V') << 8) |
                                  (uint32_t('1') << 16) | (uint32_t('2') << 24);  //写一个类似命令码的东西， 代替v4l2命令码
        CameraService camera(config.camera_device, 3840, 2160, nv12, frames);  //创建 摄像头类
        if (config.use_camera && !camera.start())
            std::cerr << camera.stats().last_error << '\n';
        if (!config.use_camera) std::cout << "Camera disabled by --no-camera.\n";

        LLMEngine llm(std::make_unique<RKLLMBackend>());  //unique_ptr 独占智能指针  std::make_unique<RKLLMBackend>()
        // 是一个智能指针      作为参数传给llm        RKLLMBackend 也是自己定义的一个类    
        //std::make_unique<T>()   创建一个 T 对象，并把它交给 unique_ptr 管理  约等于C中的创建一个T类的内存并且返回地址
        VLMEngine vlm(std::make_unique<RK3576VLMBackend>());
        if (!llm.initialize(config.llm, error)) std::cerr << "LLM initialization: " << error << '\n';
        if (!vlm.initialize(config.vlm, error)) std::cerr << "VLM initialization: " << error << '\n';

        RequestProcessor processor(frames, llm, vlm);  //调度
        const int status = runCli(processor, camera, frames);
        camera.stop();
        llm.shutdown();
        vlm.shutdown();
        return status;
        // 异常路径同样通过各模块析构函数释放资源。
    }
    catch (const std::exception& e)
    {
        std::cerr << "Fatal application exception: " << e.what() << '\n';
    }
    catch (...) { std::cerr << "Fatal application exception: unknown exception\n"; }
    return 1;
}
