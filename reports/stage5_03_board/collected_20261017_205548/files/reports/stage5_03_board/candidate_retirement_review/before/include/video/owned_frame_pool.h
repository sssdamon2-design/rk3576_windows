#pragma once
#include "common/types.h"
#include <array>
#include <memory>
#include <mutex>

// Bounded owned CPU frames. A lease returns only when its shared_ptr control block dies.
// Old weak_ptrs cannot lock a later lease even if the ImageFrame address is reused.
class OwnedFramePool {
    struct State {
        std::mutex mutex;
        std::array<std::unique_ptr<ImageFrame>,3> free;
        std::size_t allocated=0,in_use=0,acquired=0,reused=0,exhausted=0;
    };
public:
    struct Stats {std::size_t allocated=0,in_use=0,acquired=0,reused=0,exhausted=0;};
    OwnedFramePool():state_(std::make_shared<State>()){}
    std::shared_ptr<ImageFrame> acquire() {
        std::unique_ptr<ImageFrame> owned;
        {
            std::lock_guard<std::mutex> lock(state_->mutex);
            for(auto& slot:state_->free)if(slot){owned=std::move(slot);++state_->reused;break;}
            if(!owned) {
                if(state_->allocated==state_->free.size()){++state_->exhausted;return {};}
                owned=std::make_unique<ImageFrame>();++state_->allocated;
            }
            ++state_->in_use;++state_->acquired;
        }
        // Construct outside the mutex: shared_ptr allocation failure invokes the deleter.
        return std::shared_ptr<ImageFrame>(owned.release(),[state=state_](ImageFrame* frame) mutable noexcept {
            auto owner=std::move(state); // weak control blocks must not retain the pool after return.
            std::lock_guard<std::mutex> lock(owner->mutex);
            --owner->in_use;
            for(auto& slot:owner->free)if(!slot){slot.reset(frame);return;}
            // Unreachable unless the fixed-capacity invariant is broken.
            std::terminate();
        });
    }
    Stats stats() const {
        std::lock_guard<std::mutex> lock(state_->mutex);
        return {state_->allocated,state_->in_use,state_->acquired,state_->reused,state_->exhausted};
    }
private:
    std::shared_ptr<State> state_;
};
