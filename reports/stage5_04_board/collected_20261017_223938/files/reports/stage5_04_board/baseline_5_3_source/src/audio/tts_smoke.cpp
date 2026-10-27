
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
