#include "video/image_preprocessor.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace { constexpr size_t kWidth=512,kHeight=512,kImageBytes=kWidth*kHeight*3;
constexpr uint32_t kNV12=0x3231564e;
inline uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::max(0.0f, std::min(255.0f, std::round(v))));
}

// MVP CPU preprocessing: packed NV12, BT.709 limited range -> RGB, resize 512x512.
// Unlike PIL/Lanczos this uses bilinear Y and nearest chroma; quality validation is pending.
// Only read LatestFrameBuffer's owned ImageFrame (do not access mmap after QBUF).
}
bool frameToRgb512Reference(const ImageFrame& f, std::vector<uint8_t>& rgb, std::string& error) {
    if (f.pixel_format != kNV12 || f.width == 0 || f.height == 0 ||
        (f.width % 2) || (f.height % 2)) {
        error = "Expected packed NV12 frame with even width/height";
        return false;
    }
    // VideoCapture concatenates mmap plane payloads. Current IMX415 returns one plane.
    if (f.plane_sizes.size() != 1 || f.plane_strides.size() != 1) {
        error = "This first VLM adapter expects one packed NV12 plane";
        return false;
    }
    const size_t stride = f.plane_strides[0];
    const size_t width = f.width;
    const size_t height = f.height;
    if (stride < width || stride > 16384 || width > 8192 || height > 8192 ||
        stride * (height + height / 2) > f.data.size()) {
        error = "Invalid NV12 stride/data size";
        return false;
    }
    const uint8_t* yPlane = f.data.data();
    const uint8_t* uvPlane = f.data.data() + stride * height;
    rgb.resize(kImageBytes);
    for (size_t dy = 0; dy < kHeight; ++dy) {
        const float sy = (static_cast<float>(dy) + 0.5f) * height / kHeight - 0.5f;
        const float fy = std::max(0.0f, sy);
        const size_t y0 = std::min(height - 1, static_cast<size_t>(fy));
        const size_t y1 = std::min(height - 1, y0 + 1);
        const float wy = std::min(1.0f, fy - y0);
        for (size_t dx = 0; dx < kWidth; ++dx) {
            const float sx = (static_cast<float>(dx) + 0.5f) * width / kWidth - 0.5f;
            const float fx = std::max(0.0f, sx);
            const size_t x0 = std::min(width - 1, static_cast<size_t>(fx));
            const size_t x1 = std::min(width - 1, x0 + 1);
            const float wx = std::min(1.0f, fx - x0);
            const float yy = (1-wy) * ((1-wx) * yPlane[y0*stride+x0] + wx * yPlane[y0*stride+x1]) +
                                   wy  * ((1-wx) * yPlane[y1*stride+x0] + wx * yPlane[y1*stride+x1]);
            const size_t ux = (std::min(width - 1, static_cast<size_t>(fx)) / 2) * 2;
            const size_t uy = std::min(height - 1, static_cast<size_t>(fy)) / 2;
            const float u = float(uvPlane[uy*stride+ux]) - 128.0f;
            const float v = float(uvPlane[uy*stride+ux+1]) - 128.0f;
            const float Y = 1.164383f * (yy - 16.0f);
            const size_t out = (dy*kWidth+dx)*3;
            rgb[out+0] = toByte(Y + 1.792741f*v);
            rgb[out+1] = toByte(Y - 0.213249f*u - 0.532909f*v);
            rgb[out+2] = toByte(Y + 2.112402f*u);
        }
    }
    return true;
}


bool Rgb512Preprocessor::convert(const ImageFrame& f,std::vector<uint8_t>& rgb,std::string& error) {
    if (f.pixel_format != kNV12 || f.width == 0 || f.height == 0 ||
        (f.width % 2) || (f.height % 2)) {
        error = "Expected packed NV12 frame with even width/height";
        return false;
    }
    // VideoCapture concatenates mmap plane payloads. Current IMX415 returns one plane.
    if (f.plane_sizes.size() != 1 || f.plane_strides.size() != 1) {
        error = "This first VLM adapter expects one packed NV12 plane";
        return false;
    }
    const size_t stride = f.plane_strides[0];
    const size_t width = f.width;
    const size_t height = f.height;
    if (stride < width || stride > 16384 || width > 8192 || height > 8192 ||
        stride * (height + height / 2) > f.data.size() ||
        f.plane_sizes[0] < stride*(height+height/2) || f.plane_sizes[0] > f.data.size()) {
        error = "Invalid NV12 stride/data size";
        return false;
    }

    if(width_!=width || height_!=height) {
        for(size_t dx=0;dx<kWidth;++dx) {
            const float sx=(static_cast<float>(dx)+0.5f)*width/kWidth-0.5f;
            const float fx=std::max(0.0f,sx);
            auto& x=columns_[dx];x.x0=std::min(width-1,static_cast<size_t>(fx));
            x.x1=std::min(width-1,x.x0+1);x.weight=std::min(1.0f,fx-x.x0);
            x.uv=(std::min(width-1,static_cast<size_t>(fx))/2)*2;
        }
        for(size_t dy=0;dy<kHeight;++dy) {
            const float sy=(static_cast<float>(dy)+0.5f)*height/kHeight-0.5f;
            const float fy=std::max(0.0f,sy);
            auto& y=rows_[dy];y.y0=std::min(height-1,static_cast<size_t>(fy));
            y.y1=std::min(height-1,y.y0+1);y.weight=std::min(1.0f,fy-y.y0);
            y.uv=std::min(height-1,static_cast<size_t>(fy))/2;
        }
        width_=static_cast<uint32_t>(width);height_=static_cast<uint32_t>(height);
    }
    const uint8_t* yPlane=f.data.data();const uint8_t* uvPlane=yPlane+stride*height;
    rgb.resize(kImageBytes);
    for(size_t dy=0;dy<kHeight;++dy) {
        const auto& y=rows_[dy];const float wy=y.weight;
        for(size_t dx=0;dx<kWidth;++dx) {
            const auto& x=columns_[dx];const float wx=x.weight;
            const float yy=(1-wy)*((1-wx)*yPlane[y.y0*stride+x.x0]+wx*yPlane[y.y0*stride+x.x1])+
                          wy*((1-wx)*yPlane[y.y1*stride+x.x0]+wx*yPlane[y.y1*stride+x.x1]);
            const float u=float(uvPlane[y.uv*stride+x.uv])-128.0f;
            const float v=float(uvPlane[y.uv*stride+x.uv+1])-128.0f;
            const float Y=1.164383f*(yy-16.0f);const size_t out=(dy*kWidth+dx)*3;
            rgb[out+0]=toByte(Y+1.792741f*v);
            rgb[out+1]=toByte(Y-0.213249f*u-0.532909f*v);
            rgb[out+2]=toByte(Y+2.112402f*u);
        }
    }
    return true;
}
