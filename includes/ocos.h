// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

#pragma once

#define ORT_API_MANUAL_INIT
#define EXCLUDE_REFERENCE_TO_ORT_DLL
#include "onnxruntime_cxx_api.h"
#undef EXCLUDE_REFERENCE_TO_ORT_DLL
#undef ORT_API_MANUAL_INIT

const char c_OpDomain[] = "ai.onnx.contrib";

#if defined(PYTHON_OP_SUPPORT)

const OrtCustomOp* FetchPyCustomOps(size_t& count);
bool EnablePyCustomOps(bool enable=true);

#endif
