
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
