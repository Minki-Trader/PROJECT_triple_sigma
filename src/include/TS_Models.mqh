#ifndef __TS_MODELS_MQH__
#define __TS_MODELS_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_PackMeta.mqh"
#include "TS_Features.mqh"

long g_ts_clf_handles[6];
long g_ts_prm_handles[6];
bool g_ts_models_ready = false;

double g_ts_scaler_mean[12];
double g_ts_scaler_std[12];
bool g_ts_scaler_ready = false;

double g_ts_stage1_last[3];
double g_ts_stage2_last[6];
bool g_ts_stage1_last_ok = false;
bool g_ts_stage2_last_ok = false;
int g_ts_last_model_dir = 2;
string g_ts_last_model_dir_name = "PASS";
int g_ts_last_inference_regime_id = -1;

bool TS_ModelReadTextFileAll(const string rel_path, string &content)
{
   content = "";

   ResetLastError();
   const int handle = FileOpen(rel_path, FILE_READ | FILE_BIN);
   if(handle == INVALID_HANDLE)
      return false;

   const int size = (int)FileSize(handle);
   if(size < 0)
   {
      FileClose(handle);
      return false;
   }

   uchar raw[];
   ArrayResize(raw, size);
   const int read_count = (int)FileReadArray(handle, raw, 0, size);
   FileClose(handle);
   if(read_count < 0)
      return false;

   content = CharArrayToString(raw, 0, read_count, CP_UTF8);
   if(StringLen(content) == 0 && read_count > 0)
      content = CharArrayToString(raw, 0, read_count, CP_ACP);

   return true;
}

bool TS_ModelExtractJsonArray(const string content, const string key, double &out_values[])
{
   ArrayResize(out_values, 0);

   const string marker = "\"" + key + "\"";
   const int key_pos = StringFind(content, marker);
   if(key_pos < 0)
      return false;

   const int left = StringFind(content, "[", key_pos);
   const int right = StringFind(content, "]", left);
   if(left < 0 || right <= left)
      return false;

   string body = StringSubstr(content, left + 1, right - left - 1);
   StringReplace(body, "\r", " ");
   StringReplace(body, "\n", " ");
   StringReplace(body, "\t", " ");

   int start = 0;
   while(start <= StringLen(body))
   {
      int comma = StringFind(body, ",", start);
      string part = "";
      if(comma < 0)
      {
         part = TS_PM_Trim(StringSubstr(body, start));
         start = StringLen(body) + 1;
      }
      else
      {
         part = TS_PM_Trim(StringSubstr(body, start, comma - start));
         start = comma + 1;
      }

      if(part == "")
         continue;

      const int n = ArraySize(out_values);
      ArrayResize(out_values, n + 1);
      out_values[n] = StringToDouble(part);
   }

   return (ArraySize(out_values) > 0);
}

bool TS_ModelSetShape(long handle, const ulong shape0, const ulong shape1, const ulong shape2, const bool is_input)
{
   ulong shape[];
   ArrayResize(shape, 3);
   shape[0] = shape0;
   shape[1] = shape1;
   shape[2] = shape2;

   ResetLastError();
   if(is_input)
      return OnnxSetInputShape(handle, 0, shape);
   return OnnxSetOutputShape(handle, 0, shape);
}

bool TS_ModelSmokeRun(const long handle, const int output_dim, const string tag)
{
   matrixf x_zero;
   x_zero.Resize(TS_X_TIME_STEPS, TS_X_FEATURE_DIM);
   x_zero.Fill(0.0f);

   vectorf y_out;
   y_out.Resize(output_dim);

   ResetLastError();
   // Output shape is verified implicitly here because this MT5 build rejects output-shape forcing.
   if(!OnnxRun(handle, 0, x_zero, y_out))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("%s smoke OnnxRun failed err=%d", tag, GetLastError())
      );
      return false;
   }

   for(int i = 0; i < output_dim; ++i)
   {
      const double value = (double)y_out[i];
      if(!MathIsValidNumber(value) || MathAbs(value) >= (EMPTY_VALUE / 2.0))
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
            StringFormat("%s smoke output invalid idx=%d value=%.8f", tag, i, value)
         );
         return false;
      }
   }

   return true;
}

void TS_ModelFillPassOutputs()
{
   g_ts_stage1_last[0] = 0.0;
   g_ts_stage1_last[1] = 0.0;
   g_ts_stage1_last[2] = 1.0;

   g_ts_stage2_last[0] = TS_PASS_DEFAULT_K_SL;
   g_ts_stage2_last[1] = TS_PASS_DEFAULT_K_TP;
   g_ts_stage2_last[2] = (double)TS_PASS_DEFAULT_HOLD_BARS;
   g_ts_stage2_last[3] = TS_PASS_DEFAULT_K_SL;
   g_ts_stage2_last[4] = TS_PASS_DEFAULT_K_TP;
   g_ts_stage2_last[5] = (double)TS_PASS_DEFAULT_HOLD_BARS;

   g_ts_stage1_last_ok = false;
   g_ts_stage2_last_ok = false;
   g_ts_last_model_dir = 2;
   g_ts_last_model_dir_name = "PASS";
}

int TS_ModelArgMax3(const double a, const double b, const double c)
{
   int idx = 0;
   double best = a;
   if(b > best)
   {
      best = b;
      idx = 1;
   }
   if(c > best)
      idx = 2;
   return idx;
}

bool TS_GetLatestRegimeIdFromTensor(int &regime_id)
{
   regime_id = -1;

   if(!g_ts_x_ready || g_ts_x_count != TS_X_TIME_STEPS || ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE)
      return false;

   const int latest_t = TS_X_TIME_STEPS - 1;
   int hits = 0;
   for(int r = 0; r < TS_REGIME_COUNT; ++r)
   {
      const int idx = TS_XIndex(latest_t, TS_FEAT_REG_0 + r);
      if(idx < 0)
         return false;
      if(g_ts_x_tensor[idx] > 0.5f)
      {
         regime_id = r;
         hits++;
      }
   }

   return (hits == 1 && regime_id >= 0 && regime_id < TS_REGIME_COUNT);
}

void TS_ResetModelState()
{
   for(int i = 0; i < TS_REGIME_COUNT; ++i)
   {
      g_ts_clf_handles[i] = INVALID_HANDLE;
      g_ts_prm_handles[i] = INVALID_HANDLE;
   }

   ArrayInitialize(g_ts_scaler_mean, 0.0);
   ArrayInitialize(g_ts_scaler_std, 1.0);
   ArrayInitialize(g_ts_stage1_last, 0.0);
   ArrayInitialize(g_ts_stage2_last, 0.0);

   g_ts_models_ready = false;
   g_ts_scaler_ready = false;
   g_ts_scaler_mode = "unloaded";
   g_ts_last_model_dir = 2;
   g_ts_last_model_dir_name = "PASS";
   g_ts_last_inference_regime_id = -1;
   g_ts_stage1_last_ok = false;
   g_ts_stage2_last_ok = false;
   g_ts_x_infer_ready = false;

   TS_ModelFillPassOutputs();
}

void TS_ResetModelBarState()
{
   g_ts_last_inference_regime_id = -1;
   g_ts_x_infer_ready = false;
   TS_ModelFillPassOutputs();
}

void TS_ReleaseModels()
{
   for(int i = 0; i < TS_REGIME_COUNT; ++i)
   {
      if(g_ts_clf_handles[i] != INVALID_HANDLE)
      {
         OnnxRelease(g_ts_clf_handles[i]);
         g_ts_clf_handles[i] = INVALID_HANDLE;
      }

      if(g_ts_prm_handles[i] != INVALID_HANDLE)
      {
         OnnxRelease(g_ts_prm_handles[i]);
         g_ts_prm_handles[i] = INVALID_HANDLE;
      }
   }

   g_ts_models_ready = false;
}

void TS_LogModelState()
{
   PrintFormat(
      "[TS][MODEL_STATE] ready=%s scaler_ready=%s infer_ready=%s scaler_mode=%s regime_id=%d dir=%s clf0=%d prm0=%d stage1_ok=%s stage2_ok=%s y1=[%.6f,%.6f,%.6f] y2=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]",
      g_ts_models_ready ? "true" : "false",
      g_ts_scaler_ready ? "true" : "false",
      g_ts_x_infer_ready ? "true" : "false",
      g_ts_scaler_mode,
      g_ts_last_inference_regime_id,
      g_ts_last_model_dir_name,
      (int)g_ts_clf_handles[0],
      (int)g_ts_prm_handles[0],
      g_ts_stage1_last_ok ? "true" : "false",
      g_ts_stage2_last_ok ? "true" : "false",
      g_ts_stage1_last[0],
      g_ts_stage1_last[1],
      g_ts_stage1_last[2],
      g_ts_stage2_last[0],
      g_ts_stage2_last[1],
      g_ts_stage2_last[2],
      g_ts_stage2_last[3],
      g_ts_stage2_last[4],
      g_ts_stage2_last[5]
   );
}

bool TS_LoadScaler(const string model_pack_dir)
{
   string detail = "";
   if(!TS_PM_ValidateModelPackDir(model_pack_dir, detail))
   {
      TS_LatchPassOnly(TS_PASS_REASON_PACK_META_FAIL, detail);
      return false;
   }

   const string rel_path = TS_PM_Trim(model_pack_dir) + "\\scaler_stats.json";
   string content = "";
   ResetLastError();
   if(!TS_ModelReadTextFileAll(rel_path, content))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_MODEL_LOAD_FAIL,
         StringFormat("scaler_stats open failed path=%s err=%d", rel_path, GetLastError())
      );
      return false;
   }

   double mean_values[];
   double std_values[];
   if(!TS_ModelExtractJsonArray(content, "mean", mean_values) ||
      !TS_ModelExtractJsonArray(content, "std", std_values))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("scaler_stats parse failed path=%s", rel_path)
      );
      return false;
   }

   if(ArraySize(mean_values) != 12 || ArraySize(std_values) != 12)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("scaler_stats length mismatch mean=%d std=%d", ArraySize(mean_values), ArraySize(std_values))
      );
      return false;
   }

   for(int i = 0; i < 12; ++i)
   {
      if(!MathIsValidNumber(mean_values[i]) || !MathIsValidNumber(std_values[i]) || std_values[i] <= 0.0)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
            StringFormat("scaler_stats invalid value idx=%d mean=%.8f std=%.8f", i, mean_values[i], std_values[i])
         );
         return false;
      }

      g_ts_scaler_mean[i] = mean_values[i];
      g_ts_scaler_std[i] = std_values[i];
   }

   g_ts_scaler_ready = true;
   g_ts_scaler_mode = "zscore_v1";
   PrintFormat("[TS][SCALER] loaded path=%s mode=%s", rel_path, g_ts_scaler_mode);
   return true;
}

bool TS_LoadModels(const string model_pack_dir)
{
   string detail = "";
   if(!TS_PM_ValidateModelPackDir(model_pack_dir, detail))
   {
      TS_LatchPassOnly(TS_PASS_REASON_PACK_META_FAIL, detail);
      return false;
   }

   TS_ReleaseModels();

   const string dir = TS_PM_Trim(model_pack_dir);
   for(int rid = 0; rid < TS_REGIME_COUNT; ++rid)
   {
      const string clf_path = StringFormat("%s\\clf_reg%d_v%s.onnx", dir, rid, g_ts_pack_meta.model_pack_version);
      const string prm_path = StringFormat("%s\\prm_reg%d_v%s.onnx", dir, rid, g_ts_pack_meta.model_pack_version);

      ResetLastError();
      g_ts_clf_handles[rid] = OnnxCreate(clf_path, 0);
      if(g_ts_clf_handles[rid] == INVALID_HANDLE)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_MODEL_LOAD_FAIL,
            StringFormat("OnnxCreate clf failed path=%s err=%d", clf_path, GetLastError())
         );
         TS_ReleaseModels();
         return false;
      }

      ResetLastError();
      g_ts_prm_handles[rid] = OnnxCreate(prm_path, 0);
      if(g_ts_prm_handles[rid] == INVALID_HANDLE)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_MODEL_LOAD_FAIL,
            StringFormat("OnnxCreate prm failed path=%s err=%d", prm_path, GetLastError())
         );
         TS_ReleaseModels();
         return false;
      }

      if(!TS_ModelSetShape(g_ts_clf_handles[rid], 1, TS_X_TIME_STEPS, TS_X_FEATURE_DIM, true))
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
            StringFormat("clf input shape set failed rid=%d err=%d", rid, GetLastError())
         );
         TS_ReleaseModels();
         return false;
      }

      if(!TS_ModelSmokeRun(g_ts_clf_handles[rid], 3, StringFormat("clf rid=%d", rid)))
      {
         TS_ReleaseModels();
         return false;
      }

      if(!TS_ModelSetShape(g_ts_prm_handles[rid], 1, TS_X_TIME_STEPS, TS_X_FEATURE_DIM, true))
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
            StringFormat("prm input shape set failed rid=%d err=%d", rid, GetLastError())
         );
         TS_ReleaseModels();
         return false;
      }

      if(!TS_ModelSmokeRun(g_ts_prm_handles[rid], 6, StringFormat("prm rid=%d", rid)))
      {
         TS_ReleaseModels();
         return false;
      }
   }

   g_ts_models_ready = true;
   PrintFormat("[TS][MODELS] loaded model_pack=%s", g_ts_pack_meta.model_pack_version);
   return true;
}

bool TS_ApplyScaler(float &x_tensor[])
{
   if(!g_ts_scaler_ready)
   {
      TS_LatchPassOnly(TS_PASS_REASON_MODEL_LOAD_FAIL, "scaler not ready");
      return false;
   }

   if(ArraySize(x_tensor) != TS_X_FLAT_SIZE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("scaler input shape mismatch expected=%d actual=%d", TS_X_FLAT_SIZE, ArraySize(x_tensor))
      );
      return false;
   }

   for(int t = 0; t < TS_X_TIME_STEPS; ++t)
   {
      for(int f = 0; f < 12; ++f)
      {
         const int idx = TS_XIndex(t, f);
         if(idx < 0)
         {
            TS_LatchPassOnly(
               TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
               StringFormat("scaler invalid x index t=%d f=%d", t, f)
            );
            return false;
         }

         const double raw = (double)x_tensor[idx];
         const double scaled = (raw - g_ts_scaler_mean[f]) / g_ts_scaler_std[f];
         if(!MathIsValidNumber(scaled) || MathAbs(scaled) >= (EMPTY_VALUE / 2.0))
         {
            TS_LatchPassOnly(
               TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
               StringFormat("scaled x invalid t=%d f=%d raw=%.8f scaled=%.8f", t, f, raw, scaled)
            );
            return false;
         }

         x_tensor[idx] = (float)scaled;
      }
   }

   g_ts_scaler_mode = "zscore_v1";
   return true;
}

bool TS_PrepareScaledTensor()
{
   g_ts_x_infer_ready = false;

   if(!g_ts_x_ready || g_ts_x_count != TS_X_TIME_STEPS || ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("prepare scaled tensor requires raw x ready count=%d flat=%d", g_ts_x_count, ArraySize(g_ts_x_tensor))
      );
      return false;
   }

   if(ArraySize(g_ts_x_infer_tensor) != TS_X_FLAT_SIZE)
      ArrayResize(g_ts_x_infer_tensor, TS_X_FLAT_SIZE);

   if(ArraySize(g_ts_x_infer_tensor) != TS_X_FLAT_SIZE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("infer tensor resize failed expected=%d actual=%d", TS_X_FLAT_SIZE, ArraySize(g_ts_x_infer_tensor))
      );
      return false;
   }

   ArrayCopy(g_ts_x_infer_tensor, g_ts_x_tensor);
   if(!TS_ApplyScaler(g_ts_x_infer_tensor))
      return false;

   g_ts_x_infer_ready = true;
   return true;
}

bool TS_ModelCopyTensor(matrixf &input_matrix)
{
   if(!g_ts_x_infer_ready || ArraySize(g_ts_x_infer_tensor) != TS_X_FLAT_SIZE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("inference tensor not ready infer_ready=%s infer_flat=%d", g_ts_x_infer_ready ? "true" : "false", ArraySize(g_ts_x_infer_tensor))
      );
      return false;
   }

   input_matrix.Resize(TS_X_TIME_STEPS, TS_X_FEATURE_DIM);
   for(int t = 0; t < TS_X_TIME_STEPS; ++t)
   {
      for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
      {
         const int idx = TS_XIndex(t, f);
         input_matrix[t][f] = (float)g_ts_x_infer_tensor[idx];
      }
   }

   return true;
}

bool TS_RunInference(const int regime_id, double &y_stage1[], double &y_stage2[])
{
   ArrayResize(y_stage1, 3);
   ArrayResize(y_stage2, 6);
   ArrayInitialize(y_stage1, 0.0);
   ArrayInitialize(y_stage2, 0.0);

   TS_ModelFillPassOutputs();
   g_ts_last_inference_regime_id = regime_id;

   if(!g_ts_models_ready)
   {
      TS_RecordSoftFault(TS_PASS_REASON_MODEL_LOAD_FAIL, "models not ready");
      ArrayCopy(y_stage1, g_ts_stage1_last);
      ArrayCopy(y_stage2, g_ts_stage2_last);
      return false;
   }

   if(regime_id < 0 || regime_id >= TS_REGIME_COUNT)
   {
      TS_RecordSoftFault(TS_PASS_REASON_SHAPE_DTYPE_MISMATCH, StringFormat("regime_id invalid=%d", regime_id));
      ArrayCopy(y_stage1, g_ts_stage1_last);
      ArrayCopy(y_stage2, g_ts_stage2_last);
      return false;
   }

   matrixf x_input;
   if(!TS_ModelCopyTensor(x_input))
   {
      ArrayCopy(y_stage1, g_ts_stage1_last);
      ArrayCopy(y_stage2, g_ts_stage2_last);
      return false;
   }

   vectorf y1;
   y1.Resize(3);
   ResetLastError();
   if(!OnnxRun(g_ts_clf_handles[regime_id], 0, x_input, y1))
   {
      TS_RecordSoftFault(TS_PASS_REASON_MODEL_LOAD_FAIL, StringFormat("stage1 OnnxRun failed rid=%d err=%d", regime_id, GetLastError()));
      ArrayCopy(y_stage1, g_ts_stage1_last);
      ArrayCopy(y_stage2, g_ts_stage2_last);
      return false;
   }

   for(int i = 0; i < 3; ++i)
   {
      g_ts_stage1_last[i] = (double)y1[i];
      y_stage1[i] = g_ts_stage1_last[i];
   }

   if(!TS_ValidateProbabilities(g_ts_stage1_last[0], g_ts_stage1_last[1], g_ts_stage1_last[2]))
   {
      ArrayCopy(y_stage2, g_ts_stage2_last);
      return false;
   }

   g_ts_stage1_last_ok = true;
   g_ts_last_model_dir = TS_ModelArgMax3(g_ts_stage1_last[0], g_ts_stage1_last[1], g_ts_stage1_last[2]);
   g_ts_last_model_dir_name = (g_ts_last_model_dir == 0) ? "LONG" : ((g_ts_last_model_dir == 1) ? "SHORT" : "PASS");

   if(g_ts_last_model_dir == 2)
   {
      ArrayCopy(y_stage2, g_ts_stage2_last);
      TS_RecordSoftHealthyBar();
      return true;
   }

   vectorf y2;
   y2.Resize(6);
   ResetLastError();
   if(!OnnxRun(g_ts_prm_handles[regime_id], 0, x_input, y2))
   {
      TS_RecordSoftFault(TS_PASS_REASON_MODEL_LOAD_FAIL, StringFormat("stage2 OnnxRun failed rid=%d err=%d", regime_id, GetLastError()));
      return false;
   }

   for(int i = 0; i < 6; ++i)
   {
      g_ts_stage2_last[i] = (double)y2[i];
      y_stage2[i] = g_ts_stage2_last[i];
      if(!MathIsValidNumber(g_ts_stage2_last[i]) || MathAbs(g_ts_stage2_last[i]) >= (EMPTY_VALUE / 2.0))
      {
         TS_RecordSoftFault(TS_PASS_REASON_NAN_INF, StringFormat("stage2 output invalid idx=%d value=%.8f", i, g_ts_stage2_last[i]));
         return false;
      }
   }

   g_ts_stage2_last_ok = true;
   TS_RecordSoftHealthyBar();
   return true;
}

#endif // __TS_MODELS_MQH__
