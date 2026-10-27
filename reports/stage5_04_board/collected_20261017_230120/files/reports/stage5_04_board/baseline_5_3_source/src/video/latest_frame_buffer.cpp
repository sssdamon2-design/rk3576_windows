#include "video/latest_frame_buffer.h"
#include "common/image_profile.h"
void LatestFrameBuffer::update(FramePtr frame) {
    const auto begin=ImageProfile::Clock::now();
    {std::lock_guard<std::mutex> lock(mutex_);latest_frame_.swap(frame);}
    const double swapped=ImageProfile::ms(begin);
    const auto old_id=frame?frame->frame_id:0;
    const auto release_begin=ImageProfile::Clock::now();frame.reset();
    const double released=ImageProfile::ms(release_begin);
    imageSample("latest_publish_swap",swapped,old_id);
    imageSample("latest_release_old",released,old_id);
}
LatestFrameBuffer::FramePtr LatestFrameBuffer::getLatest() const {
    const auto begin=ImageProfile::Clock::now();FramePtr frame;
    {std::lock_guard<std::mutex> lock(mutex_);frame=latest_frame_;}
    const double duration=ImageProfile::ms(begin);
    imageSample("latest_get",duration,frame?frame->frame_id:0);
    return frame;
}
void LatestFrameBuffer::clear(){update(nullptr);}
