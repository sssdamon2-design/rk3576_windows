#pragma once
#include "common/work_control.h"
#include <algorithm>
#include <map>
#include <mutex>
#include <stdexcept>

// One credit covers inference, TTS waiting, synthesis and playback, not just one queue.
// Captured shared tickets release credit on all callback/exception/cancellation paths.
class PipelineAdmission {
    struct State;
public:
    struct Stats {std::size_t accepted=0,rejected=0,inflight=0,peak=0;bool closed=false;};
    class Ticket {
    public:
        ~Ticket();
        TaskOptions options(std::chrono::milliseconds max_wait,RequestTracePtr trace={}) const {
            TaskOptions result;result.deadline=deadline_;result.max_queue_wait=max_wait;result.cancelled=cancelled_;result.trace=std::move(trace);return result;
        }
        bool cancelled() const noexcept {return cancelled_->load();}
    private:
        friend class PipelineAdmission;
        Ticket(std::shared_ptr<State> state,std::uint64_t id,TaskOptions::Clock::time_point deadline)
            :state_(std::move(state)),id_(id),deadline_(deadline),cancelled_(std::make_shared<std::atomic<bool>>(false)){}
        std::shared_ptr<State> state_;
        std::uint64_t id_;
        TaskOptions::Clock::time_point deadline_;
        std::shared_ptr<std::atomic<bool>> cancelled_;
        bool admitted_=false;
    };
    explicit PipelineAdmission(std::size_t capacity):state_(std::make_shared<State>(capacity)) {
        if(!capacity)throw std::invalid_argument("Pipeline admission capacity must be positive");
    }
    std::shared_ptr<Ticket> tryAcquire(std::uint64_t id,std::chrono::milliseconds lifetime) {
        std::lock_guard<std::mutex> lock(state_->mutex);
        if(state_->stats.closed || state_->stats.inflight>=state_->capacity || state_->tickets.count(id)) {
            ++state_->stats.rejected;return {};
        }
        auto ticket=std::shared_ptr<Ticket>(new Ticket(state_,id,TaskOptions::Clock::now()+lifetime));
        state_->tickets.emplace(id,ticket->cancelled_);
        ticket->admitted_=true;++state_->stats.accepted;++state_->stats.inflight;
        state_->stats.peak=std::max(state_->stats.peak,state_->stats.inflight);
        return ticket;
    }
    bool cancel(std::uint64_t id) {
        std::lock_guard<std::mutex> lock(state_->mutex);
        const auto found=state_->tickets.find(id);
        if(found==state_->tickets.end())return false;
        if(auto flag=found->second.lock()){flag->store(true);return true;}
        return false;
    }
    void close(bool cancel_waiting) {
        std::lock_guard<std::mutex> lock(state_->mutex);state_->stats.closed=true;
        if(cancel_waiting)for(auto& row:state_->tickets)if(auto flag=row.second.lock())flag->store(true);
    }
    Stats stats() const {std::lock_guard<std::mutex> lock(state_->mutex);return state_->stats;}
private:
    struct State {
        explicit State(std::size_t size):capacity(size){}
        std::mutex mutex;
        const std::size_t capacity;
        Stats stats;
        // Weak cancellation flags avoid destroying a Ticket recursively while this mutex is held.
        std::map<std::uint64_t,std::weak_ptr<std::atomic<bool>>> tickets;
    };
    std::shared_ptr<State> state_;
};
inline PipelineAdmission::Ticket::~Ticket() {
    if(admitted_){std::lock_guard<std::mutex> lock(state_->mutex);--state_->stats.inflight;state_->tickets.erase(id_);}
}
