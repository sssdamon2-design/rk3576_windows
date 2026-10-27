#pragma once
#include "common/types.h"
#include <string>
#include <vector>
// Frozen Stage5.2 arithmetic: fused luma bilinear resize + nearest UV + BT.709 limited RGB.
bool frameToRgb512Reference(const ImageFrame& frame,std::vector<uint8_t>& rgb,std::string& error);
