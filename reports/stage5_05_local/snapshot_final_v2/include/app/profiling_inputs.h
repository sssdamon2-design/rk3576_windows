#pragma once
// Explicit offline benchmark inputs. None of these paths are active by default.
#include "common/types.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
inline std::shared_ptr<const ImageFrame> loadProfilingFrame(const std::filesystem::path& folder){
    std::ifstream meta(folder/"frame_0.json");std::stringstream content;content<<meta.rdbuf();const auto text=content.str();
    if(!meta||text.size()>4096)throw std::runtime_error("Invalid profiling frame metadata");
    auto field=[&](const char* key){std::smatch match;if(!std::regex_search(text,match,std::regex(std::string("\"")+key+"\":\\s*([0-9]+)")))throw std::runtime_error(std::string("Missing frame field: ")+key);return std::stoull(match[1]);};
    const auto width=field("width"),height=field("height"),stride=field("stride"),bytes=field("bytes");
    if(!width||!height||width%2||height%2||width>8192||height>8192||stride<width||stride>16384||bytes>100*1024*1024||bytes<stride*(height+height/2))throw std::runtime_error("Invalid packed NV12 profiling frame");
    const auto file=folder/"frame_0.nv12";if(std::filesystem::file_size(file)!=bytes)throw std::runtime_error("Profiling frame size mismatch");
    auto frame=std::make_shared<ImageFrame>();frame->width=static_cast<std::uint32_t>(width);frame->height=static_cast<std::uint32_t>(height);frame->pixel_format=0x3231564e;
    frame->plane_strides={static_cast<std::uint32_t>(stride)};frame->plane_sizes={static_cast<std::size_t>(bytes)};frame->frame_id=field("frame_id");frame->data.resize(bytes);
    std::ifstream raw(file,std::ios::binary);raw.read(reinterpret_cast<char*>(frame->data.data()),frame->data.size());if(!raw)throw std::runtime_error("Profiling frame read failed");
    return frame; // No live acquisition timestamp; Frame Age remains unavailable.
}
inline std::vector<float> loadProfilingAudio(const std::filesystem::path& file){
    static_assert(sizeof(float)==4,"Profiling fixture requires 32-bit float");
    const auto bytes=std::filesystem::file_size(file);
    if(!bytes||bytes%sizeof(float)||bytes>16000*16*sizeof(float))throw std::runtime_error("Invalid 16kHz mono float profiling audio size");
    std::vector<float> samples(bytes/sizeof(float));std::ifstream input(file,std::ios::binary);input.read(reinterpret_cast<char*>(samples.data()),bytes);
    if(!input||!std::all_of(samples.begin(),samples.end(),[](float x){return std::isfinite(x)&&std::abs(x)<=1.001f;}))throw std::runtime_error("Invalid profiling PCM");
    return samples;
}
inline void dumpProfilingAudio(const std::filesystem::path& folder,std::uint64_t id,const std::vector<float>& samples){
    if(!std::filesystem::is_directory(folder))throw std::runtime_error("Audio fixture directory must exist");
    const auto stem=folder/("segment_"+std::to_string(id));const auto audio=stem.string()+".f32",meta=stem.string()+".json";
    if(std::filesystem::exists(audio)||std::filesystem::exists(meta))throw std::runtime_error("Refusing to overwrite profiling audio");
    std::ofstream output(audio,std::ios::binary);output.write(reinterpret_cast<const char*>(samples.data()),samples.size()*sizeof(float));
    std::ofstream metadata(meta);metadata<<"{\"sample_rate\":16000,\"channels\":1,\"format\":\"f32le\",\"samples\":"<<samples.size()<<",\"request_id\":"<<id<<"}\n";
    if(!output||!metadata)throw std::runtime_error("Profiling audio write failed");
}
