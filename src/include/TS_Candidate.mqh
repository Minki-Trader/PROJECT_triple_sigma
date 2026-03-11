#ifndef __TS_CANDIDATE_MQH__
#define __TS_CANDIDATE_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_DataIngest.mqh"
#include "TS_Indicators.mqh"
#include "TS_PackMeta.mqh"

int g_ts_current_cand_long = 0;
int g_ts_current_cand_short = 0;
bool g_ts_current_entry_allowed = false;
double g_ts_current_dist_atr_max = 0.0;

string g_ts_last_cand_mode = "static";
double g_ts_last_cand_q = 0.0;
int g_ts_last_cand_w = 0;
int g_ts_last_cand_history_len = 0;
double g_ts_last_cand_clamp_lo = 0.0;
double g_ts_last_cand_clamp_hi = 0.0;
double g_ts_last_cand_dist_atr_max = TS_CAND_DIST_ATR_MAX_STATIC;

double TS_CandidateClampValue(const double v, const double lo, const double hi)
{
   if(v < lo)
      return lo;
   if(v > hi)
      return hi;
   return v;
}

double TS_ComputeDistAtrForBar(const TS_BarRecord &bar, const TS_IndicatorSlice &ind)
{
   const double atr = MathMax(ind.atr14_t, TS_EPSILON);
   return MathAbs(bar.bid_close_t - ind.ema20_t) / atr;
}

bool TS_ComputeQuantileLower(const double &values[], const int count, const double q, double &out_value)
{
   out_value = 0.0;

   if(count <= 0 || q <= 0.0 || q >= 1.0)
      return false;

   double sorted[];
   ArrayResize(sorted, count);
   for(int i = 0; i < count; ++i)
      sorted[i] = values[i];

   ArraySort(sorted);

   // Lower quantile without interpolation; STEP11 must mirror this exactly.
   int idx = (int)MathFloor(q * (count - 1));
   if(idx < 0)
      idx = 0;
   if(idx >= count)
      idx = count - 1;

   out_value = sorted[idx];
   return MathIsValidNumber(out_value);
}

void TS_ResetCandidateState()
{
   g_ts_current_cand_long = 0;
   g_ts_current_cand_short = 0;
   g_ts_current_entry_allowed = false;
   g_ts_current_dist_atr_max = 0.0;

   g_ts_last_cand_mode = "static";
   g_ts_last_cand_q = 0.0;
   g_ts_last_cand_w = 0;
   g_ts_last_cand_history_len = 0;
   g_ts_last_cand_clamp_lo = 0.0;
   g_ts_last_cand_clamp_hi = 0.0;
   g_ts_last_cand_dist_atr_max = TS_CAND_DIST_ATR_MAX_STATIC;
}

void TS_ResetCandidateBarState()
{
   g_ts_current_cand_long = 0;
   g_ts_current_cand_short = 0;
   g_ts_current_entry_allowed = false;
   g_ts_current_dist_atr_max = 0.0;

   TS_CandidateLoadPolicySnapshot();
   g_ts_last_cand_history_len = 0;
   g_ts_last_cand_dist_atr_max = TS_CAND_DIST_ATR_MAX_STATIC;
}

void TS_LogCandidateState()
{
   PrintFormat(
      "[TS][CAND_STATE] cand_long=%d cand_short=%d entry_allowed=%s dist_atr_max=%.6f mode=%s q=%.4f w=%d history_len=%d clamp_lo=%.4f clamp_hi=%.4f",
      g_ts_current_cand_long,
      g_ts_current_cand_short,
      g_ts_current_entry_allowed ? "true" : "false",
      g_ts_current_dist_atr_max,
      g_ts_last_cand_mode,
      g_ts_last_cand_q,
      g_ts_last_cand_w,
      g_ts_last_cand_history_len,
      g_ts_last_cand_clamp_lo,
      g_ts_last_cand_clamp_hi
   );
}

void TS_CandidateLoadPolicySnapshot()
{
   g_ts_last_cand_mode = g_ts_pack_meta.dist_atr_max_mode;
   if(g_ts_last_cand_mode == "")
      g_ts_last_cand_mode = "static";

   g_ts_last_cand_q = g_ts_pack_meta.dist_atr_max_q;
   g_ts_last_cand_w = g_ts_pack_meta.dist_atr_max_w;
   g_ts_last_cand_history_len = 0;
   g_ts_last_cand_clamp_lo = g_ts_pack_meta.dist_atr_max_clamp_lo;
   g_ts_last_cand_clamp_hi = g_ts_pack_meta.dist_atr_max_clamp_hi;
   g_ts_last_cand_dist_atr_max = TS_CAND_DIST_ATR_MAX_STATIC;
}

bool TS_ResolveDistAtrMaxForBar(const int abs_idx, double &dist_atr_max_t, int &history_len)
{
   dist_atr_max_t = TS_CAND_DIST_ATR_MAX_STATIC;
   history_len = 0;

   if(abs_idx < 0 || abs_idx >= g_ts_bar_count || abs_idx >= g_ts_ind_count)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("adaptive dist history index invalid abs_idx=%d bar_count=%d ind_count=%d", abs_idx, g_ts_bar_count, g_ts_ind_count)
      );
      return false;
   }

   TS_CandidateLoadPolicySnapshot();
   g_ts_last_cand_dist_atr_max = dist_atr_max_t;

   if(g_ts_last_cand_mode != "adaptive_quantile")
      return true;

   history_len = abs_idx;
   g_ts_last_cand_history_len = history_len;

   if(history_len < g_ts_pack_meta.dist_atr_max_w)
      return true;

   history_len = g_ts_pack_meta.dist_atr_max_w;
   const int start_idx = abs_idx - history_len;

   double dist_hist[];
   ArrayResize(dist_hist, history_len);
   for(int i = 0; i < history_len; ++i)
      dist_hist[i] = TS_ComputeDistAtrForBar(g_ts_bar_buffer[start_idx + i], g_ts_ind_buffer[start_idx + i]);

   double quantile_value = 0.0;
   if(!TS_ComputeQuantileLower(dist_hist, history_len, g_ts_pack_meta.dist_atr_max_q, quantile_value))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("adaptive dist quantile failed q=%.4f history_len=%d", g_ts_pack_meta.dist_atr_max_q, history_len)
      );
      return false;
   }

   dist_atr_max_t = TS_CandidateClampValue(
      quantile_value,
      g_ts_pack_meta.dist_atr_max_clamp_lo,
      g_ts_pack_meta.dist_atr_max_clamp_hi
   );

   if(!MathIsValidNumber(dist_atr_max_t) || dist_atr_max_t <= 0.0)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("adaptive dist_atr_max invalid value=%.8f", dist_atr_max_t)
      );
      return false;
   }

   g_ts_last_cand_history_len = history_len;
   g_ts_last_cand_dist_atr_max = dist_atr_max_t;
   return true;
}

void TS_ComputeCandidateForBar(
   const TS_BarRecord &bar,
   const TS_IndicatorSlice &ind,
   const double dist_atr_max_t,
   const int adx_bin,
   int &cand_long,
   int &cand_short
)
{
   cand_long = 0;
   cand_short = 0;

   const double dist_atr = TS_ComputeDistAtrForBar(bar, ind);
   if(dist_atr > dist_atr_max_t)
      return;

   bool long_cond = false;
   bool short_cond = false;

   if(adx_bin >= 1)
   {
      long_cond = (ind.ema20_t > ind.ema50_t) && (ind.rsi14_t >= 52.0) && (bar.bid_close_t >= ind.ema20_t);
      short_cond = (ind.ema20_t < ind.ema50_t) && (ind.rsi14_t <= 48.0) && (bar.bid_close_t <= ind.ema20_t);
   }
   else
   {
      long_cond = (ind.rsi14_t <= 40.0) && (bar.bid_close_t <= ind.ema50_t);
      short_cond = (ind.rsi14_t >= 60.0) && (bar.bid_close_t >= ind.ema50_t);
   }

   if(long_cond && !short_cond)
      cand_long = 1;
   else if(short_cond && !long_cond)
      cand_short = 1;
}

bool TS_UpdateCandidateOnNewBar()
{
   if(!g_ts_x_ready || g_ts_x_count != TS_X_TIME_STEPS || ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("candidate update requires x ready count=%d flat=%d", g_ts_x_count, ArraySize(g_ts_x_tensor))
      );
      return false;
   }

   const int latest_t = TS_X_TIME_STEPS - 1;
   const int idx_long = (latest_t * TS_X_FEATURE_DIM) + TS_FEAT_CAND_LONG;
   const int idx_short = (latest_t * TS_X_FEATURE_DIM) + TS_FEAT_CAND_SHORT;

   g_ts_current_cand_long = (int)g_ts_x_tensor[idx_long];
   g_ts_current_cand_short = (int)g_ts_x_tensor[idx_short];
   g_ts_current_entry_allowed = (g_ts_current_cand_long == 1 || g_ts_current_cand_short == 1);
   g_ts_current_dist_atr_max = g_ts_last_cand_dist_atr_max;

   const int latest_abs_idx = g_ts_bar_count - 1;
   const double dist_atr_t = TS_ComputeDistAtrForBar(g_ts_bar_buffer[latest_abs_idx], g_ts_ind_buffer[latest_abs_idx]);

   PrintFormat(
      "[TS][CAND] mode=%s q=%.2f w=%d history_len=%d dist_atr_max_t=%.6f clamp_lo=%.4f clamp_hi=%.4f dist_atr_t=%.6f cand_long=%d cand_short=%d entry_allowed=%s",
      g_ts_last_cand_mode,
      g_ts_last_cand_q,
      g_ts_last_cand_w,
      g_ts_last_cand_history_len,
      g_ts_current_dist_atr_max,
      g_ts_last_cand_clamp_lo,
      g_ts_last_cand_clamp_hi,
      dist_atr_t,
      g_ts_current_cand_long,
      g_ts_current_cand_short,
      g_ts_current_entry_allowed ? "true" : "false"
   );

   return true;
}

#endif // __TS_CANDIDATE_MQH__
