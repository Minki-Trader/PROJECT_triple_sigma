#ifndef __TS_INDICATORS_MQH__
#define __TS_INDICATORS_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_DataIngest.mqh"

struct TS_IndicatorSlice
{
   datetime bar_time_t;
   double ema20_t;
   double ema50_t;
   double rsi14_t;
   double atr14_t;
   double adx14_t;
};

TS_IndicatorSlice g_ts_ind_buffer[];
int g_ts_ind_count = 0;
bool g_ts_indicators_ready = false;
int g_ts_warmup_bars_used = 0;

int g_ts_h_ema20 = INVALID_HANDLE;
int g_ts_h_ema50 = INVALID_HANDLE;
int g_ts_h_rsi14 = INVALID_HANDLE;
int g_ts_h_atr14 = INVALID_HANDLE;
int g_ts_h_adx14 = INVALID_HANDLE;

bool TS_IsIndValueValid(const double v)
{
   return MathIsValidNumber(v) && (MathAbs(v) < (EMPTY_VALUE / 2.0));
}

void TS_ResetIndicatorState()
{
   ArrayResize(g_ts_ind_buffer, TS_HISTORY_KEEP_BARS);
   g_ts_ind_count = 0;
   g_ts_indicators_ready = false;
   g_ts_warmup_bars_used = 0;
}

void TS_ReleaseIndicatorHandles()
{
   if(g_ts_h_ema20 != INVALID_HANDLE)
   {
      IndicatorRelease(g_ts_h_ema20);
      g_ts_h_ema20 = INVALID_HANDLE;
   }

   if(g_ts_h_ema50 != INVALID_HANDLE)
   {
      IndicatorRelease(g_ts_h_ema50);
      g_ts_h_ema50 = INVALID_HANDLE;
   }

   if(g_ts_h_rsi14 != INVALID_HANDLE)
   {
      IndicatorRelease(g_ts_h_rsi14);
      g_ts_h_rsi14 = INVALID_HANDLE;
   }

   if(g_ts_h_atr14 != INVALID_HANDLE)
   {
      IndicatorRelease(g_ts_h_atr14);
      g_ts_h_atr14 = INVALID_HANDLE;
   }

   if(g_ts_h_adx14 != INVALID_HANDLE)
   {
      IndicatorRelease(g_ts_h_adx14);
      g_ts_h_adx14 = INVALID_HANDLE;
   }
}

bool TS_InitIndicatorHandles()
{
   TS_ReleaseIndicatorHandles();

   g_ts_h_ema20 = iMA(_Symbol, TS_DECISION_TIMEFRAME, TS_IND_EMA20_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   if(g_ts_h_ema20 == INVALID_HANDLE)
   {
      TS_LatchPassOnly(TS_PASS_REASON_INDICATOR_INIT_FAIL, "iMA EMA20 handle creation failed");
      TS_ReleaseIndicatorHandles();
      return false;
   }

   g_ts_h_ema50 = iMA(_Symbol, TS_DECISION_TIMEFRAME, TS_IND_EMA50_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   if(g_ts_h_ema50 == INVALID_HANDLE)
   {
      TS_LatchPassOnly(TS_PASS_REASON_INDICATOR_INIT_FAIL, "iMA EMA50 handle creation failed");
      TS_ReleaseIndicatorHandles();
      return false;
   }

   g_ts_h_rsi14 = iRSI(_Symbol, TS_DECISION_TIMEFRAME, TS_IND_RSI14_PERIOD, PRICE_CLOSE);
   if(g_ts_h_rsi14 == INVALID_HANDLE)
   {
      TS_LatchPassOnly(TS_PASS_REASON_INDICATOR_INIT_FAIL, "iRSI14 handle creation failed");
      TS_ReleaseIndicatorHandles();
      return false;
   }

   g_ts_h_atr14 = iATR(_Symbol, TS_DECISION_TIMEFRAME, TS_IND_ATR14_PERIOD);
   if(g_ts_h_atr14 == INVALID_HANDLE)
   {
      TS_LatchPassOnly(TS_PASS_REASON_INDICATOR_INIT_FAIL, "iATR14 handle creation failed");
      TS_ReleaseIndicatorHandles();
      return false;
   }

   g_ts_h_adx14 = iADX(_Symbol, TS_DECISION_TIMEFRAME, TS_IND_ADX14_PERIOD);
   if(g_ts_h_adx14 == INVALID_HANDLE)
   {
      TS_LatchPassOnly(TS_PASS_REASON_INDICATOR_INIT_FAIL, "iADX14 handle creation failed");
      TS_ReleaseIndicatorHandles();
      return false;
   }

   return true;
}

bool TS_ValidateLatestAlignment()
{
   if(g_ts_ind_count <= 0 || g_ts_bar_count <= 0)
      return false;

   const datetime ind_latest = g_ts_ind_buffer[g_ts_ind_count - 1].bar_time_t;
   const datetime bar_latest = g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;
   return (ind_latest == bar_latest);
}

bool TS_ValidateFullAlignment()
{
   if(g_ts_ind_count <= 0 || g_ts_bar_count <= 0 || g_ts_ind_count != g_ts_bar_count)
      return false;

   for(int i = 0; i < g_ts_ind_count; ++i)
   {
      if(g_ts_ind_buffer[i].bar_time_t != g_ts_bar_buffer[i].bar_time_t)
         return false;
   }

   return true;
}

bool TS_FetchIndicatorBuffer(
   const int handle,
   const int buffer_index,
   const datetime start_time,
   const datetime stop_time,
   const int requested_count,
   double &out_buf[]
)
{
   ArrayResize(out_buf, requested_count);
   const int copied = CopyBuffer(handle, buffer_index, start_time, stop_time, out_buf);
   return (copied == requested_count);
}

bool TS_UpdateIndicatorsOnNewBar(bool &bar_level_pass, const bool debug_full_alignment)
{
   bar_level_pass = false;
   g_ts_indicators_ready = false;
   if(g_ts_bar_count <= 0)
   {
      g_ts_ind_count = 0;
      g_ts_warmup_bars_used = 0;
      bar_level_pass = true;
      return false;
   }

   double ema20_raw[];
   double ema50_raw[];
   double rsi14_raw[];
   double atr14_raw[];
   double adx14_raw[];
   datetime ind_time_raw[];
   const int requested_count = g_ts_bar_count;
   const datetime start_time = g_ts_bar_buffer[0].bar_time_t;
   const datetime stop_time = g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;

   if(!TS_FetchIndicatorBuffer(g_ts_h_ema20, 0, start_time, stop_time, requested_count, ema20_raw) ||
      !TS_FetchIndicatorBuffer(g_ts_h_ema50, 0, start_time, stop_time, requested_count, ema50_raw) ||
      !TS_FetchIndicatorBuffer(g_ts_h_rsi14, 0, start_time, stop_time, requested_count, rsi14_raw) ||
      !TS_FetchIndicatorBuffer(g_ts_h_atr14, 0, start_time, stop_time, requested_count, atr14_raw) ||
      !TS_FetchIndicatorBuffer(g_ts_h_adx14, TS_ADX_MAIN_BUFFER, start_time, stop_time, requested_count, adx14_raw))
   {
      g_ts_ind_count = 0;
      g_ts_warmup_bars_used = g_ts_bar_count;
      bar_level_pass = true;
      PrintFormat("[TS][IND] CopyBuffer insufficient data (warmup) bar_count=%d", g_ts_bar_count);
      return false;
   }

   ArrayResize(ind_time_raw, requested_count);
   const int copied_times = CopyTime(_Symbol, TS_DECISION_TIMEFRAME, start_time, stop_time, ind_time_raw);
   if(copied_times != requested_count)
   {
      g_ts_ind_count = 0;
      g_ts_warmup_bars_used = g_ts_bar_count;
      bar_level_pass = true;
      PrintFormat(
         "[TS][IND] CopyTime alignment fetch mismatch requested=%d copied=%d start=%s stop=%s",
         requested_count,
         copied_times,
         TimeToString(start_time, TIME_DATE | TIME_MINUTES),
         TimeToString(stop_time, TIME_DATE | TIME_MINUTES)
      );
      return false;
   }

   if(ArraySize(g_ts_ind_buffer) != requested_count)
      ArrayResize(g_ts_ind_buffer, requested_count);

   bool has_invalid_value = false;
   string invalid_detail = "";
   for(int i = 0; i < requested_count; ++i)
   {
      TS_IndicatorSlice slice;
      slice.bar_time_t = ind_time_raw[i];
      slice.ema20_t = ema20_raw[i];
      slice.ema50_t = ema50_raw[i];
      slice.rsi14_t = rsi14_raw[i];
      slice.atr14_t = atr14_raw[i];
      slice.adx14_t = adx14_raw[i];

      if(!TS_IsIndValueValid(slice.ema20_t) ||
         !TS_IsIndValueValid(slice.ema50_t) ||
         !TS_IsIndValueValid(slice.rsi14_t) ||
         !TS_IsIndValueValid(slice.atr14_t) ||
         !TS_IsIndValueValid(slice.adx14_t))
      {
         if(!has_invalid_value)
            invalid_detail = StringFormat("first invalid indicator at idx=%d", i);
         has_invalid_value = true;
      }

      g_ts_ind_buffer[i] = slice;
   }

   // All retained bars are populated (valid or not); indicators_ready controls usability.
   g_ts_ind_count = requested_count;
   g_ts_warmup_bars_used = g_ts_bar_count;

   if(has_invalid_value)
   {
      bar_level_pass = true;
      TS_RecordSoftFault(TS_PASS_REASON_NAN_INF, invalid_detail);
      return false;
   }

   if(!TS_ValidateLatestAlignment())
   {
      bar_level_pass = true;
      PrintFormat(
         "[TS][IND] latest alignment mismatch ind_last=%s bar_last=%s",
         TimeToString(g_ts_ind_buffer[g_ts_ind_count - 1].bar_time_t, TIME_DATE | TIME_MINUTES),
         TimeToString(g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t, TIME_DATE | TIME_MINUTES)
      );
      return false;
   }

   for(int i = 0; i < g_ts_ind_count; ++i)
   {
      if(g_ts_ind_buffer[i].bar_time_t != g_ts_bar_buffer[i].bar_time_t)
      {
         g_ts_ind_count = 0;
         g_ts_indicators_ready = false;
         bar_level_pass = true;
         PrintFormat(
            "[TS][IND] explicit time alignment mismatch idx=%d ind=%s bar=%s",
            i,
            TimeToString(g_ts_ind_buffer[i].bar_time_t, TIME_DATE | TIME_MINUTES),
            TimeToString(g_ts_bar_buffer[i].bar_time_t, TIME_DATE | TIME_MINUTES)
         );
         return false;
      }
   }

   if(debug_full_alignment && !TS_ValidateFullAlignment())
   {
      bar_level_pass = true;
      Print("[TS][IND] full-window alignment mismatch in debug mode");
      return false;
   }

   g_ts_indicators_ready = true;

   if(!TS_IsWindowReady())
   {
      bar_level_pass = true;
      PrintFormat("[TS][IND] feature window warming bars=%d ind_count=%d", g_ts_bar_count, g_ts_ind_count);
      return false;
   }

   if(debug_full_alignment)
   {
      const int latest_idx = g_ts_ind_count - 1;
      PrintFormat(
         "[TS][IND_VALUES] bar=%s ema20=%.6f ema50=%.6f rsi14=%.4f atr14=%.8f adx14=%.4f",
         TimeToString(g_ts_ind_buffer[latest_idx].bar_time_t, TIME_DATE | TIME_MINUTES),
         g_ts_ind_buffer[latest_idx].ema20_t,
         g_ts_ind_buffer[latest_idx].ema50_t,
         g_ts_ind_buffer[latest_idx].rsi14_t,
         g_ts_ind_buffer[latest_idx].atr14_t,
         g_ts_ind_buffer[latest_idx].adx14_t
      );
   }

   return true;
}

void TS_LogIndicatorState()
{
   PrintFormat(
      "[TS][IND_STATE] ready=%s count=%d warmup_bars_used=%d h_ema20=%d h_ema50=%d h_rsi14=%d h_atr14=%d h_adx14=%d",
      g_ts_indicators_ready ? "true" : "false",
      g_ts_ind_count,
      g_ts_warmup_bars_used,
      g_ts_h_ema20,
      g_ts_h_ema50,
      g_ts_h_rsi14,
      g_ts_h_atr14,
      g_ts_h_adx14
   );
}

#endif // __TS_INDICATORS_MQH__
