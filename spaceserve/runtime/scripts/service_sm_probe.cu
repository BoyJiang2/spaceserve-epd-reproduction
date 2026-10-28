#include <cuda_runtime.h>

__global__ void repro_record_actual_stream_sms(int* seen) {
    unsigned sm;
    asm("mov.u32 %0, %%smid;" : "=r"(sm));
    if (threadIdx.x == 0 && sm < 512) atomicExch(seen + sm, 1);
    auto begin = clock64();
    while (clock64() - begin < 20000) { }
}

extern "C" int repro_sample_actual_stream(void* pointer, int* host) {
    cudaStream_t stream = reinterpret_cast<cudaStream_t>(pointer);
    int* seen = nullptr;
    cudaError_t error = cudaMalloc(&seen, 512 * sizeof(int));
    if (error != cudaSuccess) return error;
    error = cudaMemsetAsync(seen, 0, 512 * sizeof(int), stream);
    if (error == cudaSuccess) {
        for (int repeat = 0; repeat < 10; ++repeat)
            repro_record_actual_stream_sms<<<2048, 128, 0, stream>>>(seen);
        error = cudaGetLastError();
    }
    if (error == cudaSuccess)
        error = cudaMemcpyAsync(host, seen, 512 * sizeof(int), cudaMemcpyDeviceToHost, stream);
    if (error == cudaSuccess) error = cudaStreamSynchronize(stream);
    cudaError_t released = cudaFree(seen);
    return error == cudaSuccess ? released : error;
}
