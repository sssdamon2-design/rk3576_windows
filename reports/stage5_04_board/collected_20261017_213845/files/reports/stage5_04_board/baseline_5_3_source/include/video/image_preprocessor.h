#pragma once
#include "common/types.h"
#include <string>
#include <array>
#include <vector>
// Frozen Stage5.2 arithmetic: fused luma bilinear resize + nearest UV + BT.709 limited RGB.
bool frameToRgb512Reference(const ImageFrame& frame,std::vector<uint8_t>& rgb,std::string& error);

// Reuses sampling coordinates for unchanged dimensions; one owner/Engine mutex serializes use.
class Rgb512Preprocessor {
public:
    bool convert(const ImageFrame& frame,std::vector<uint8_t>& rgb,std::string& error);
private:
    struct X {std::size_t x0=0,x1=0,uv=0;float weight=0;};
    struct Y {std::size_t y0=0,y1=0,uv=0;float weight=0;};
    std::array<X,512> columns_{};
    std::array<Y,512> rows_{};
    uint32_t width_=0,height_=0;
};
