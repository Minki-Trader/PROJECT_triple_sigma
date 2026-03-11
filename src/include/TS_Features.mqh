#ifndef __TS_FEATURES_MQH__
#define __TS_FEATURES_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_DataIngest.mqh"
#include "TS_Indicators.mqh"
#include "TS_PackMeta.mqh"
#include "TS_Candidate.mqh"

float g_ts_x_tensor[];
float g_ts_x_infer_tensor[];
bool g_ts_x_ready = false;
bool g_ts_x_infer_ready = false;
int g_ts_x_count = 0;
string g_ts_scaler_mode = "unloaded";
double g_ts_current_spread_atr = 0.0;
double g_ts_current_atr14 = 0.0;
datetime g_ts_x_row_time[];
double g_ts_x_row_dist_atr_max[];

int TS_XIndex(const int t, const int f)
{
   if(t < 0 || t >= TS_X_TIME_STEPS || f < 0 || f >= TS_X_FEATURE_DIM)
   {
      PrintFormat("[TS][X][ERROR] index out of range t=%d f=%d", t, f);
      return -1;
   }

   return (t * TS_X_FEATURE_DIM) + f;
}

bool TS_IsFeatureValueValid(const double v)
{
   return MathIsValidNumber(v) && (MathAbs(v) < (EMPTY_VALUE / 2.0));
}

double TS_ClampValue(const double v, const double lo, const double hi)
{
   if(v < lo)
      return lo;
   if(v > hi)
      return hi;
   return v;
}

int TS_GetWindowBaseIndex()
{
   if(g_ts_bar_count < TS_X_TIME_STEPS)
      return -1;
   return (g_ts_bar_count - TS_X_TIME_STEPS);
}

double TS_ComputeLogReturnAbs(const int abs_idx, const int lookback)
{
   int src = abs_idx - lookback;
   if(src < 0)
      src = 0;

   const double close_t = MathMax(MathAbs(g_ts_bar_buffer[abs_idx].bid_close_t), TS_EPSILON);
   const double close_prev = MathMax(MathAbs(g_ts_bar_buffer[src].bid_close_t), TS_EPSILON);
   return MathLog(close_t / close_prev);
}

int TS_ToIsoWeekday(const int mt5_dow)
{
   return (mt5_dow == 0) ? 6 : (mt5_dow - 1);
}

void TS_ResetFeatureState()
{
   ArrayResize(g_ts_x_tensor, TS_X_FLAT_SIZE);
   ArrayInitialize(g_ts_x_tensor, 0.0);
   ArrayResize(g_ts_x_infer_tensor, TS_X_FLAT_SIZE);
   ArrayInitialize(g_ts_x_infer_tensor, 0.0);
   ArrayResize(g_ts_x_row_time, TS_X_TIME_STEPS);
   ArrayInitialize(g_ts_x_row_time, 0);
   ArrayResize(g_ts_x_row_dist_atr_max, TS_X_TIME_STEPS);
   ArrayInitialize(g_ts_x_row_dist_atr_max, 0.0);
   g_ts_x_ready = false;
   g_ts_x_infer_ready = false;
   g_ts_x_count = 0;
   g_ts_scaler_mode = "unloaded";
   g_ts_current_spread_atr = 0.0;
   g_ts_current_atr14 = 0.0;
}

void TS_ResetFeatureBarState()
{
   g_ts_x_ready = false;
   g_ts_x_infer_ready = false;
   g_ts_x_count = 0;
   g_ts_current_spread_atr = 0.0;
   g_ts_current_atr14 = 0.0;

   if(ArraySize(g_ts_x_row_time) == TS_X_TIME_STEPS)
      ArrayInitialize(g_ts_x_row_time, 0);
   if(ArraySize(g_ts_x_row_dist_atr_max) == TS_X_TIME_STEPS)
      ArrayInitialize(g_ts_x_row_dist_atr_max, 0.0);
}

void TS_ComputeRegimeForBar(
   const TS_BarRecord &bar,
   const TS_IndicatorSlice &ind,
   const double atr_thr,
   const double adx_thr1,
   const double adx_thr2,
   int &atr_bin,
   int &adx_bin,
   int &regime_id
)
{
   const double close_abs = MathMax(MathAbs(bar.bid_close_t), TS_EPSILON);
   const double atr_pct_t = ind.atr14_t / close_abs;
   atr_bin = (atr_pct_t < atr_thr) ? 0 : 1;

   if(ind.adx14_t < adx_thr1)
      adx_bin = 0;
   else if(ind.adx14_t < adx_thr2)
      adx_bin = 1;
   else
      adx_bin = 2;

   regime_id = (adx_bin * 2) + atr_bin;
   if(regime_id < 0)
      regime_id = 0;
   if(regime_id >= TS_REGIME_COUNT)
      regime_id = TS_REGIME_COUNT - 1;
}

bool TS_ValidateFeatureIndex()
{
   const int idx[22] =
   {
      TS_FEAT_RET_1, TS_FEAT_RET_3, TS_FEAT_RET_12,
      TS_FEAT_RANGE_ATR, TS_FEAT_BODY_ATR, TS_FEAT_CLOSE_POS,
      TS_FEAT_EMA20_DIST, TS_FEAT_EMA50_DIST, TS_FEAT_EMA20_SLOPE,
      TS_FEAT_RSI_NORM, TS_FEAT_ADX_NORM, TS_FEAT_SPREAD_ATR,
      TS_FEAT_TIME_SIN, TS_FEAT_TIME_COS,
      TS_FEAT_REG_0, TS_FEAT_REG_1, TS_FEAT_REG_2, TS_FEAT_REG_3, TS_FEAT_REG_4, TS_FEAT_REG_5,
      TS_FEAT_CAND_LONG, TS_FEAT_CAND_SHORT
   };

   const string name[22] =
   {
      "ret_1", "ret_3", "ret_12",
      "range_atr", "body_atr", "close_pos",
      "ema20_dist", "ema50_dist", "ema20_slope",
      "rsi_norm", "adx_norm", "spread_atr",
      "time_sin", "time_cos",
      "reg_0", "reg_1", "reg_2", "reg_3", "reg_4", "reg_5",
      "cand_long", "cand_short"
   };

   if(ArraySize(idx) != TS_X_FEATURE_DIM || ArraySize(name) != TS_X_FEATURE_DIM)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
         StringFormat("feature schema size mismatch idx=%d name=%d expected=%d", ArraySize(idx), ArraySize(name), TS_X_FEATURE_DIM)
      );
      return false;
   }

   int seen[];
   ArrayResize(seen, TS_X_FEATURE_DIM);
   ArrayInitialize(seen, 0);

   for(int i = 0; i < TS_X_FEATURE_DIM; ++i)
   {
      if(idx[i] < 0 || idx[i] >= TS_X_FEATURE_DIM)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
            StringFormat("feature index out of range name=%s idx=%d", name[i], idx[i])
         );
         return false;
      }

      if(seen[idx[i]] == 1)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
            StringFormat("feature index duplicate name=%s idx=%d", name[i], idx[i])
         );
         return false;
      }

      seen[idx[i]] = 1;

      if(idx[i] != i)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
            StringFormat("feature index mismatch name=%s expected=%d actual=%d", name[i], i, idx[i])
         );
         return false;
      }
   }

   return true;
}

bool TS_UpdateFeaturesOnNewBar(bool &bar_level_pass, const bool debug_log)
{
   bar_level_pass = false;
   g_ts_x_ready = false;
   g_ts_x_infer_ready = false;
   g_ts_current_spread_atr = 0.0;
   g_ts_current_atr14 = 0.0;

   if(!g_ts_pack_meta_ready)
   {
      TS_LatchPassOnly(TS_PASS_REASON_PACK_META_FAIL, "pack meta not ready before feature update");
      return false;
   }

   if(!TS_IsWindowReady() || !g_ts_indicators_ready || g_ts_bar_count < TS_REQUIRED_BARS || g_ts_ind_count < g_ts_bar_count)
   {
      g_ts_x_count = 0;
      bar_level_pass = true;
      PrintFormat(
         "[TS][X] prerequisites not ready window=%s indicators_ready=%s bar_count=%d ind_count=%d",
         TS_IsWindowReady() ? "true" : "false",
         g_ts_indicators_ready ? "true" : "false",
         g_ts_bar_count,
         g_ts_ind_count
      );
      return false;
   }

   if(ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE)
      ArrayResize(g_ts_x_tensor, TS_X_FLAT_SIZE);
   if(ArraySize(g_ts_x_infer_tensor) != TS_X_FLAT_SIZE)
      ArrayResize(g_ts_x_infer_tensor, TS_X_FLAT_SIZE);
   if(ArraySize(g_ts_x_row_time) != TS_X_TIME_STEPS)
      ArrayResize(g_ts_x_row_time, TS_X_TIME_STEPS);
   if(ArraySize(g_ts_x_row_dist_atr_max) != TS_X_TIME_STEPS)
      ArrayResize(g_ts_x_row_dist_atr_max, TS_X_TIME_STEPS);

   if(ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE ||
      ArraySize(g_ts_x_infer_tensor) != TS_X_FLAT_SIZE ||
      ArraySize(g_ts_x_row_time) != TS_X_TIME_STEPS ||
      ArraySize(g_ts_x_row_dist_atr_max) != TS_X_TIME_STEPS)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat(
            "feature buffers resize failed raw=%d infer=%d row_time=%d row_dist=%d",
            ArraySize(g_ts_x_tensor),
            ArraySize(g_ts_x_infer_tensor),
            ArraySize(g_ts_x_row_time),
            ArraySize(g_ts_x_row_dist_atr_max)
         )
      );
      return false;
   }

   const double atr_thr = g_ts_pack_meta.atr_thr;
   const double adx_thr1 = g_ts_pack_meta.adx_thr1;
   const double adx_thr2 = g_ts_pack_meta.adx_thr2;
   const int window_base = TS_GetWindowBaseIndex();
   if(window_base < 0)
   {
      g_ts_x_count = 0;
      bar_level_pass = true;
      return false;
   }

   for(int t = 0; t < TS_X_TIME_STEPS; ++t)
   {
      const int abs_idx = window_base + t;
      const TS_BarRecord bar = g_ts_bar_buffer[abs_idx];
      const TS_IndicatorSlice ind = g_ts_ind_buffer[abs_idx];

      const double atr = MathMax(ind.atr14_t, TS_EPSILON);
      const double high_low = MathMax(bar.bid_high_t - bar.bid_low_t, TS_EPSILON);

      double feature[22];
      for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
         feature[f] = 0.0;

      feature[TS_FEAT_RET_1] = TS_ComputeLogReturnAbs(abs_idx, 1);
      feature[TS_FEAT_RET_3] = TS_ComputeLogReturnAbs(abs_idx, 3);
      feature[TS_FEAT_RET_12] = TS_ComputeLogReturnAbs(abs_idx, 12);

      feature[TS_FEAT_RANGE_ATR] = (bar.bid_high_t - bar.bid_low_t) / atr;
      feature[TS_FEAT_BODY_ATR] = (bar.bid_close_t - bar.bid_open_t) / atr;
      feature[TS_FEAT_CLOSE_POS] = TS_ClampValue(
         (2.0 * ((bar.bid_close_t - bar.bid_low_t) / high_low)) - 1.0,
         -1.0,
         1.0
      );

      feature[TS_FEAT_EMA20_DIST] = (bar.bid_close_t - ind.ema20_t) / atr;
      feature[TS_FEAT_EMA50_DIST] = (bar.bid_close_t - ind.ema50_t) / atr;
      {
         int prev_abs_idx = abs_idx - 1;
         if(prev_abs_idx < 0)
            prev_abs_idx = 0;
         feature[TS_FEAT_EMA20_SLOPE] = (ind.ema20_t - g_ts_ind_buffer[prev_abs_idx].ema20_t) / atr;
      }

      feature[TS_FEAT_RSI_NORM] = (ind.rsi14_t - 50.0) / 50.0;
      feature[TS_FEAT_ADX_NORM] = ind.adx14_t / 100.0;
      feature[TS_FEAT_SPREAD_ATR] = bar.spread_price_t / atr;

      {
         MqlDateTime dt;
         TimeToStruct(bar.bar_time_t, dt);
         const int iso_dow = TS_ToIsoWeekday(dt.day_of_week);
         const int minute_of_week = (iso_dow * 1440) + (dt.hour * 60) + dt.min;
         const double angle = TS_TWO_PI * ((double)minute_of_week / 10080.0);
         feature[TS_FEAT_TIME_SIN] = MathSin(angle);
         feature[TS_FEAT_TIME_COS] = MathCos(angle);
      }

      {
         int atr_bin = 0;
         int adx_bin = 0;
         int regime_id = 0;
         double dist_atr_max_t = TS_CAND_DIST_ATR_MAX_STATIC;
         int history_len = 0;
         TS_ComputeRegimeForBar(bar, ind, atr_thr, adx_thr1, adx_thr2, atr_bin, adx_bin, regime_id);
         feature[TS_FEAT_REG_0 + regime_id] = 1.0;

         if(!TS_ResolveDistAtrMaxForBar(abs_idx, dist_atr_max_t, history_len))
            return false;
         g_ts_last_cand_history_len = history_len;

         int cand_long = 0;
         int cand_short = 0;
         TS_ComputeCandidateForBar(bar, ind, dist_atr_max_t, adx_bin, cand_long, cand_short);
         if(!TS_ValidateCandidateOneHotOrZero(cand_long, cand_short))
            return false;
         feature[TS_FEAT_CAND_LONG] = (double)cand_long;
         feature[TS_FEAT_CAND_SHORT] = (double)cand_short;
         g_ts_x_row_time[t] = bar.bar_time_t;
         g_ts_x_row_dist_atr_max[t] = dist_atr_max_t;
      }

      for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
      {
         if(!TS_IsFeatureValueValid(feature[f]))
         {
            g_ts_x_count = 0;
            bar_level_pass = true;
            TS_RecordSoftFault(TS_PASS_REASON_NAN_INF, StringFormat("invalid x value t=%d f=%d", t, f));
            return false;
         }

         const int idx = TS_XIndex(t, f);
         if(idx < 0)
         {
            TS_LatchPassOnly(
               TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
               StringFormat("invalid x index t=%d f=%d", t, f)
            );
            return false;
         }

         g_ts_x_tensor[idx] = (float)feature[f];
      }
   }

   g_ts_x_count = TS_X_TIME_STEPS;
   g_ts_x_ready = true;
   const int latest_abs_idx = g_ts_bar_count - 1;
   g_ts_current_atr14 = MathMax(g_ts_ind_buffer[latest_abs_idx].atr14_t, TS_EPSILON);
   g_ts_current_spread_atr = g_ts_bar_buffer[latest_abs_idx].spread_price_t / g_ts_current_atr14;

   if(debug_log)
   {
      const int latest_t = TS_X_TIME_STEPS - 1;
      int latest_regime = 0;
      for(int r = 0; r < TS_REGIME_COUNT; ++r)
      {
         if(g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_REG_0 + r)] > 0.5f)
         {
            latest_regime = r;
            break;
         }
      }

      PrintFormat(
         "[TS][X_VALUES] bar=%s ret_1=%.8f rsi_norm=%.6f adx_norm=%.6f spread_atr=%.6f regime=%d cand_long=%d cand_short=%d dist_atr_max=%.6f",
         TimeToString(g_ts_x_row_time[latest_t], TIME_DATE | TIME_MINUTES),
         (double)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_RET_1)],
         (double)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_RSI_NORM)],
         (double)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_ADX_NORM)],
         (double)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_SPREAD_ATR)],
         latest_regime,
         (int)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_CAND_LONG)],
         (int)g_ts_x_tensor[TS_XIndex(latest_t, TS_FEAT_CAND_SHORT)],
         g_ts_x_row_dist_atr_max[latest_t]
      );
   }

   return true;
}

void TS_LogFeatureState()
{
   PrintFormat(
      "[TS][X_STATE] ready=%s infer_ready=%s x_count=%d x_flat_size=%d scaler_mode=%s spread_atr_raw=%.6f atr14_raw=%.8f",
      g_ts_x_ready ? "true" : "false",
      g_ts_x_infer_ready ? "true" : "false",
      g_ts_x_count,
      ArraySize(g_ts_x_tensor),
      g_ts_scaler_mode,
      g_ts_current_spread_atr,
      g_ts_current_atr14
   );
}

#endif // __TS_FEATURES_MQH__
