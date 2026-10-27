
#include "audio/audio_capture.h"

#include <cerrno>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

// POSIX write 可能短写，需要循环写入。
bool writeAll(int fd, const void* buffer, std::size_t bytes)
{
    const auto* ptr = static_cast<const uint8_t*>(buffer);

    while (bytes > 0)
    {
        ssize_t ret = ::write(fd, ptr, bytes);

        if (ret < 0 && errno == EINTR)
            continue;

        if (ret <= 0)
            return false;

        ptr += ret;
        bytes -= static_cast<std::size_t>(ret);
    }

    return true;
}

int main(int argc, char** argv)
{
    // 可通过命令行指定实际 ALSA 设备，避免写死声卡编号。
    const std::string device =
        argc > 1 ? argv[1] : "plughw:3,0";

    const std::string output_file =
        argc > 2 ? argv[2] : "asr_cpp_5s.pcm";

    AudioCapture capture(device);
    std::string error;

    if (!capture.open(error))
    {
        std::cerr << "Open failed: " << error << '\n';
        return 1;
    }

    int fd = ::open(
        output_file.c_str(),
        O_CREAT | O_WRONLY | O_TRUNC,
        0644
    );

    if (fd < 0)
    {
        std::cerr << "File open failed: "
                  << std::strerror(errno) << '\n';
        return 1;
    }

    constexpr std::size_t sample_rate = 16000;
    constexpr std::size_t duration = 5;
    constexpr std::size_t chunk_frames = 320;

    constexpr std::size_t total_chunks =
        sample_rate * duration / chunk_frames;

    std::vector<int16_t> samples;
    bool success = true;

    std::cout << "Recording 5 seconds from "
              << device << "...\n";

    for (std::size_t i = 0; i < total_chunks; ++i)
    {
        if (!capture.readFrames(
                samples, chunk_frames, error))
        {
            std::cerr << error << '\n';
            success = false;
            break;
        }

        if (!writeAll(
                fd,
                samples.data(),
                samples.size() * sizeof(int16_t)))
        {
            std::cerr << "PCM write failed\n";
            success = false;
            break;
        }
    }

    if (::close(fd) != 0)
    {
        std::cerr << "File close failed\n";
        success = false;
    }

    capture.close();

    if (!success)
        return 1;

    std::cout << "Saved: " << output_file << '\n';
    std::cout << "Format: 16000 Hz, Mono, S16_LE\n";
    return 0;
}
