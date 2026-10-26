#include <cuda_runtime.h>
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <set>

#define CUDA_CHECK(call) do { auto err = (call); if (err != cudaSuccess) { \
    fprintf(stderr, "%s: %s\n", #call, cudaGetErrorString(err)); exit(2); } } while (0)

__global__ void record_sms(int* seen) {
    unsigned sm;
    asm("mov.u32 %0, %%smid;" : "=r"(sm));
    if (threadIdx.x == 0) atomicExch(seen + sm, 1);
    auto start = clock64();
    while (clock64() - start < 20000) { }
}

std::set<int> measure(cudaStream_t stream, int* seen, const char* label) {
    CUDA_CHECK(cudaMemsetAsync(seen, 0, 512 * sizeof(int), stream));
    for (int i = 0; i < 10; ++i) record_sms<<<2048, 128, 0, stream>>>(seen);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaStreamSynchronize(stream));
    int host[512];
    CUDA_CHECK(cudaMemcpy(host, seen, sizeof(host), cudaMemcpyDeviceToHost));
    std::set<int> result;
    for (int i = 0; i < 512; ++i) if (host[i]) result.insert(i);
    printf("{\"label\":\"%s\",\"sm_count\":%zu,\"sm_ids\":[", label, result.size());
    bool first = true;
    for (int sm : result) { printf("%s%d", first ? "" : ",", sm); first = false; }
    printf("]}\n");
    fflush(stdout);
    return result;
}

int main(int argc, char** argv) {
    if (argc != 2) { fprintf(stderr, "usage: probe_sm_mask /path/libsmctrl.so\n"); return 2; }
    CUDA_CHECK(cudaSetDevice(0));
    cudaDeviceProp prop;
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    int driver;
    CUDA_CHECK(cudaDriverGetVersion(&driver));
    printf("{\"gpu\":\"%s\",\"physical_sms\":%d,\"cuda_driver_version\":%d}\n", prop.name, prop.multiProcessorCount, driver);
    auto library = dlopen(argv[1], RTLD_NOW);
    if (!library) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    using Mask = void (*)(void*, uint32_t, uint32_t, uint32_t, uint32_t);
    auto mask = reinterpret_cast<Mask>(dlsym(library, "libsmctrl_set_stream_mask_lzc"));
    if (!mask) { fprintf(stderr, "required symbol missing\n"); return 2; }
    cudaStream_t stream;
    CUDA_CHECK(cudaStreamCreate(&stream));
    int* seen;
    CUDA_CHECK(cudaMalloc(&seen, 512 * sizeof(int)));
    auto before = measure(stream, seen, "unmasked");
    mask(stream, 0, 0, 0, 0xfff);
    auto after = measure(stream, seen, "spaceserve_encoder_mask_0xfff");
    bool effective = !after.empty() && after.size() < before.size();
    printf("{\"mask_effect_observed\":%s}\n", effective ? "true" : "false");
    CUDA_CHECK(cudaFree(seen));
    CUDA_CHECK(cudaStreamDestroy(stream));
    return effective ? 0 : 3;
}
