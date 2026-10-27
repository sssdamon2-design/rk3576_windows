
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"

#include <chrono>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 6)
    {
        std::cerr
            << "Usage:\n"
            << "tts_playback_smoke "
            << "<model_dir> <device> <text> "
            << "<threads> <speaker_id>\n";

        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];
    const std::string text = argv[3];

    std::int32_t threads = 2;
    std::int32_t speaker_id = 17;

    try
    {
        std::size_t used_threads = 0;
        std::size_t used_speaker = 0;

        const std::string threads_arg = argv[4];
        const std::string speaker_arg = argv[5];

        threads = std::stoi(
            threads_arg, &used_threads
        );

        speaker_id = std::stoi(
            speaker_arg, &used_speaker
        );

        if (used_threads != threads_arg.size() ||
            used_speaker != speaker_arg.size() ||
            threads < 1 || threads > 8 ||
            speaker_id < 0)
        {
            throw std::invalid_argument("Invalid arguments");
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "Invalid threads or speaker_id\n";

        return 2;
    }

    std::string error;
    TTSService tts;
    TTSAudio audio;

    // 1. 初始化 TTS 模型。
    std::cout << "[Init] Loading TTS...\n"
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
        << " init_ms=" << init_ms
        << " sample_rate=" << tts.sampleRate()
        << " speakers=" << tts.numSpeakers()
        << " sid=" << tts.speakerId()
        << '\n';

    // 2. 进行 TTS 推理。
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
        std::cerr
            << "[TTS] Invalid output audio\n";

        return 1;
    }

    const double audio_sec =
        static_cast<double>(audio.samples.size()) /
        audio.sample_rate;

    const double rtf =
        (audio.synthesis_ms / 1000.0) / audio_sec;

    std::cout
        << "[TTS] synth_ms=" << audio.synthesis_ms
        << " audio_sec=" << audio_sec
        << " RTF=" << rtf
        << '\n';

    // 3. 打开 ALSA Playback。
    AlsaPlaybackService playback;

    if (!playback.open(
            device,
            audio.sample_rate,
            error))
    {
        std::cerr
            << "[ALSA] Open FAIL: " << error << '\n';

        return 1;
    }

    std::cout
        << "[ALSA] Device=" << device
        << " sample_rate=" << audio.sample_rate
        << '\n'
        << "[ALSA] Starting playback...\n"
        << std::flush;

    // 4. 直接播放内存中的 float PCM。
    const auto play_start =
        std::chrono::steady_clock::now();

    if (!playback.play(
            audio.samples.data(),
            audio.samples.size(),
            error))
    {
        std::cerr
            << "[ALSA] Playback FAIL: "
            << error << '\n';

        return 1;
    }

    const auto play_end =
        std::chrono::steady_clock::now();

    const double play_ms =
        std::chrono::duration<double, std::milli>(
            play_end - play_start
        ).count();

    std::cout
        << "[ALSA] playback_ms=" << play_ms
        << " xrun_count=" << playback.xrunCount()
        << '\n'
        << "PASS\n";

    return 0;
}
