#include <cuda_runtime.h>
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <set>
#include <unistd.h>

#define CHECK(call) do { auto code = (call); if (code != cudaSuccess) { \
    fprintf(stderr, "%s: %s\n", #call, cudaGetErrorString(code)); exit(2); } } while (0)

using Sample = int (*)(void*, int*);
using Mask = void (*)(void*, uint32_t, uint32_t, uint32_t, uint32_t);

std::set<int> measure(Sample sample, cudaStream_t stream, const char* label) {
    int seen[512] = {};
    int code = sample(stream, seen);
    if (code) { fprintf(stderr, "stream sample error %d\n", code); exit(2); }
    std::set<int> result;
    for (int number = 0; number < 512; ++number) if (seen[number]) result.insert(number);
    printf("{\"label\":\"%s\",\"sm_count\":%zu,\"sm_ids\":[", label, result.size());
    bool first = true;
    for (int number : result) { printf("%s%d", first ? "" : ",", number); first = false; }
    printf("]}\n"); fflush(stdout);
    return result;
}

int main(int argc, char** argv) {
    if (argc != 3) { fprintf(stderr, "usage: probe_sm_layout /path/libsmctrl.so /path/helper.so\n"); return 2; }
    CHECK(cudaSetDevice(0));
    auto library = dlopen(argv[1], RTLD_NOW);
    auto helper = dlopen(argv[2], RTLD_NOW);
    if (!library || !helper) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    auto mask = reinterpret_cast<Mask>(dlsym(library, "libsmctrl_set_stream_mask_lzc"));
    auto sample = reinterpret_cast<Sample>(dlsym(helper, "repro_sample_actual_stream"));
    if (!mask || !sample) { fprintf(stderr, "required mask or sample symbol missing\n"); return 2; }
    int driver;
    cudaDeviceProp properties;
    CHECK(cudaGetDeviceProperties(&properties, 0));
    CHECK(cudaDriverGetVersion(&driver));
    printf("{\"pid\":%d,\"gpu\":\"%s\",\"physical_sms\":%d,\"driver_api\":%d}\n", getpid(), properties.name, properties.multiProcessorCount, driver);
    cudaStream_t stream;
    CHECK(cudaStreamCreate(&stream));
    auto baseline = measure(sample, stream, "unmasked-stream-default");
    int disabled_sum = 0;
    bool restored = true;
    for (int bit = 0; bit < 12; ++bit) {
        mask(stream, 0, 0, 0, uint32_t(1) << bit);
        char label[64];
        snprintf(label, sizeof(label), "mask-bit-%d", bit);
        auto active = measure(sample, stream, label);
        disabled_sum += int(baseline.size()) - int(active.size());
        mask(stream, 0, 0, 0, 0);
        snprintf(label, sizeof(label), "restored-after-bit-%d", bit);
        restored = (measure(sample, stream, label) == baseline) && restored;
    }
    mask(stream, 0, 0, 0, 0xfff);
    auto combined = measure(sample, stream, "combined-mask-0xfff");
    mask(stream, 0, 0, 0, 0);
    restored = (measure(sample, stream, "restored-after-combined") == baseline) && restored;
    bool consistent = disabled_sum == int(baseline.size()) - int(combined.size());
    printf("{\"all_zero_masks_restored\":%s,\"individual_disabled_sm_sum\":%d,\"combined_disabled_sms\":%zu,\"layout_count_consistent\":%s}\n",
           restored ? "true" : "false", disabled_sum, baseline.size() - combined.size(), consistent ? "true" : "false");
    CHECK(cudaStreamDestroy(stream));
    return restored && consistent && combined.size() < baseline.size() ? 0 : 3;
}
