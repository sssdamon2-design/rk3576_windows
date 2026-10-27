#include "audio/asr_pipeline.h"
#include "audio/audio_capture.h"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

// ====================================================
// 2. AudioWorker
// ====================================================

AudioWorker::AudioWorker(
    std::string device,
    AudioBufferQueue& queue,
    std::mutex& print_mutex,
    std::size_t segment_count)
    : device_(std::move(device)),
      queue_(queue),
      print_mutex_(print_mutex),
      segment_count_(segment_count)
{
}

AudioWorker::~AudioWorker()
{
    requestStop();
    join();
}

void AudioWorker::start()
{
    if (started_)
        throw std::logic_error("AudioWorker can only be started once");
    thread_ = std::thread(
        &AudioWorker::run, this
    );
    started_ = true;
}

void AudioWorker::requestStop() noexcept
{
    stop_requested_.store(true);
}

void AudioWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void AudioWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("AudioWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "AudioWorker: unknown exception";
        queue_.close();
    }
}

void AudioWorker::runImpl()
{
    struct QueueCloser {
        AudioBufferQueue& queue;

        ~QueueCloser() {
            queue.close();
        }
    } closer{queue_};

    AudioCapture capture(device_);

    if (!capture.open(error_))
        return;

    constexpr std::size_t kFramesPerRead = 320;
    constexpr std::size_t kReadsPerSegment = 250;

    constexpr std::size_t kFramesPerSegment =
        kFramesPerRead * kReadsPerSegment;

    std::vector<std::int16_t> chunk;

    for (std::size_t id = 1;
         id <= segment_count_ &&
         !stop_requested_.load();
         ++id)
    {
        {
            std::lock_guard<std::mutex> lock(
                print_mutex_
            );

            std::cout
                << "[Capture] Recording #"
                << id
                << " (5 seconds)...\n"
                << std::flush;
        }

        AudioSegment segment;
        segment.sequence = id;

        segment.pcm.reserve(kFramesPerSegment);

        for (std::size_t i = 0;
             i < kReadsPerSegment;
             ++i)
        {
            if (stop_requested_.load())
                break;

            chunk.clear();

            if (!capture.readFrames(
                    chunk,
                    kFramesPerRead,
                    error_))
            {
                return;
            }

            if (chunk.size() != kFramesPerRead)
            {
                error_ = "Unexpected short ALSA chunk";
                return;
            }

            segment.pcm.insert(
                segment.pcm.end(),
                chunk.begin(),
                chunk.end()
            );
        }

        if (stop_requested_.load())
            break;

        if (!queue_.push(std::move(segment)))
        {
            error_ = "Audio queue was closed";
            return;
        }

        ++produced_;
    }

    ok_ = true;
}

