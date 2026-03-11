#ifndef __TS_DATA_INGEST_MQH__
#define __TS_DATA_INGEST_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"

enum ENUM_TS_SPREAD_CAPTURE_MODE
{
   TS_SPREAD_CAPTURE_MODE_UNKNOWN = 0,
   TS_SPREAD_CAPTURE_MODE_FIRST_TICK_APPROX = 1,
   TS_SPREAD_CAPTURE_MODE_LIVE_TICK_FALLBACK = 2,
   TS_SPREAD_CAPTURE_MODE_ZERO_FALLBACK = 3
};

struct TS_BarRecord
{
   datetime bar_time_t;
   double bid_open_t;
   double bid_high_t;
   double bid_low_t;
   double bid_close_t;
   double spread_price_t;
   double spread_points_t;
   ENUM_TS_SPREAD_CAPTURE_MODE spread_capture_mode;
};

TS_BarRecord g_ts_bar_buffer[];
int g_ts_bar_count = 0;
bool g_ts_window_ready = false;
datetime g_ts_window_first_time = 0;
datetime g_ts_window_last_time = 0;

datetime g_ts_last_processed_closed_bar_time = 0;
int g_ts_last_missing_bars_count = 0;

MqlTick g_ts_last_tick_snapshot;
bool g_ts_has_tick_snapshot = false;

string TS_GetLastBarStateKey()
{
   return StringFormat("TS_LAST_CLOSED_%s_%d", _Symbol, (int)TS_DECISION_TIMEFRAME);
}

string TS_SpreadCaptureModeToString(const ENUM_TS_SPREAD_CAPTURE_MODE mode)
{
   switch(mode)
   {
      case TS_SPREAD_CAPTURE_MODE_FIRST_TICK_APPROX: return "first_tick_approx";
      case TS_SPREAD_CAPTURE_MODE_LIVE_TICK_FALLBACK: return "live_tick_fallback";
      case TS_SPREAD_CAPTURE_MODE_ZERO_FALLBACK: return "zero_fallback";
      default: return "unknown";
   }
}

void TS_UpdateWindowMeta()
{
   if(g_ts_bar_count <= 0)
   {
      g_ts_window_first_time = 0;
      g_ts_window_last_time = 0;
      g_ts_window_ready = false;
      return;
   }

   g_ts_window_first_time = g_ts_bar_buffer[0].bar_time_t;
   g_ts_window_last_time = g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;
   g_ts_window_ready = (g_ts_bar_count >= TS_REQUIRED_BARS);
}

void TS_ResetBarWindow()
{
   g_ts_bar_count = 0;
   TS_UpdateWindowMeta();
}

void TS_ResetDataIngestState()
{
   ArrayResize(g_ts_bar_buffer, TS_HISTORY_KEEP_BARS);
   TS_ResetBarWindow();
   g_ts_last_processed_closed_bar_time = 0;
   g_ts_last_missing_bars_count = 0;
   g_ts_has_tick_snapshot = false;
}

void TS_LoadPersistedDataIngestState()
{
   // GlobalVariable is terminal-scoped and persists across EA restart/reload.
   // It is keyed by symbol+timeframe, so instances on same pair+TF share it.
   const string key = TS_GetLastBarStateKey();
   if(!GlobalVariableCheck(key))
      return;

   const double raw = GlobalVariableGet(key);
   if(raw > 0.0)
   {
      g_ts_last_processed_closed_bar_time = (datetime)raw;
      PrintFormat(
         "[TS][INGEST] Loaded persisted last_closed_bar=%s key=%s",
         TimeToString(g_ts_last_processed_closed_bar_time, TIME_DATE | TIME_MINUTES),
         key
      );
   }
}

void TS_SavePersistedDataIngestState()
{
   if(g_ts_last_processed_closed_bar_time <= 0)
      return;

   const string key = TS_GetLastBarStateKey();
   GlobalVariableSet(key, (double)g_ts_last_processed_closed_bar_time);
}

void TS_UpdateLatestTickSnapshot()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   g_ts_last_tick_snapshot = tick;
   g_ts_has_tick_snapshot = true;
}

bool TS_IsWindowReady()
{
   return g_ts_window_ready;
}

void TS_PushBar(const TS_BarRecord &bar)
{
   if(ArraySize(g_ts_bar_buffer) != TS_HISTORY_KEEP_BARS)
      ArrayResize(g_ts_bar_buffer, TS_HISTORY_KEEP_BARS);

   if(g_ts_bar_count < TS_HISTORY_KEEP_BARS)
   {
      g_ts_bar_buffer[g_ts_bar_count] = bar;
      g_ts_bar_count++;
   }
   else
   {
      for(int i = 1; i < TS_HISTORY_KEEP_BARS; ++i)
         g_ts_bar_buffer[i - 1] = g_ts_bar_buffer[i];

      g_ts_bar_buffer[TS_HISTORY_KEEP_BARS - 1] = bar;
   }

   TS_UpdateWindowMeta();
}

bool TS_ValidateMonotonicWindow()
{
   if(g_ts_bar_count <= 1)
      return true;

   for(int i = 1; i < g_ts_bar_count; ++i)
   {
      if(g_ts_bar_buffer[i].bar_time_t <= g_ts_bar_buffer[i - 1].bar_time_t)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_TIME_ORDER_BROKEN,
            StringFormat(
               "window monotonic violation idx=%d prev=%s curr=%s",
               i,
               TimeToString(g_ts_bar_buffer[i - 1].bar_time_t, TIME_DATE | TIME_MINUTES),
               TimeToString(g_ts_bar_buffer[i].bar_time_t, TIME_DATE | TIME_MINUTES)
            )
         );
         return false;
      }
   }

   return true;
}

void TS_ResolveSpreadAtClose(
   const datetime closed_bar_time,
   double &spread_price_t,
   double &spread_points_t,
   ENUM_TS_SPREAD_CAPTURE_MODE &capture_mode
)
{
   spread_price_t = 0.0;
   spread_points_t = 0.0;
   capture_mode = TS_SPREAD_CAPTURE_MODE_ZERO_FALLBACK;

   if(g_ts_has_tick_snapshot && (datetime)g_ts_last_tick_snapshot.time >= closed_bar_time)
   {
      spread_price_t = g_ts_last_tick_snapshot.ask - g_ts_last_tick_snapshot.bid;
      capture_mode = TS_SPREAD_CAPTURE_MODE_FIRST_TICK_APPROX;
   }
   else
   {
      MqlTick live_tick;
      if(SymbolInfoTick(_Symbol, live_tick))
      {
         spread_price_t = live_tick.ask - live_tick.bid;
         capture_mode = TS_SPREAD_CAPTURE_MODE_LIVE_TICK_FALLBACK;
      }
   }

   if(spread_price_t < 0.0)
      spread_price_t = 0.0;

   if(_Point > 0.0)
      spread_points_t = spread_price_t / _Point;
}

void TS_LogIngestEvent(const TS_BarRecord &bar, const bool bar_level_pass, const int missing_bars_count)
{
   PrintFormat(
      "[TS][INGEST] newbar_detect_source=timer bar_time_t=%s pass_this_bar=%s window_ready=%s bar_count=%d window_first_time=%s window_last_time=%s missing_bars_count=%d spread_price_t=%.8f spread_points_t=%.2f spread_capture_mode=%s",
      TimeToString(bar.bar_time_t, TIME_DATE | TIME_MINUTES),
      bar_level_pass ? "true" : "false",
      TS_IsWindowReady() ? "true" : "false",
      g_ts_bar_count,
      TimeToString(g_ts_window_first_time, TIME_DATE | TIME_MINUTES),
      TimeToString(g_ts_window_last_time, TIME_DATE | TIME_MINUTES),
      missing_bars_count,
      bar.spread_price_t,
      bar.spread_points_t,
      TS_SpreadCaptureModeToString(bar.spread_capture_mode)
   );
}

bool TS_TryProcessNewClosedBarOnTimer(bool &bar_level_pass)
{
   bar_level_pass = false;

   MqlRates rates[];
   const int copied = CopyRates(_Symbol, TS_DECISION_TIMEFRAME, 1, 1, rates);
   if(copied != 1)
   {
      const int err = GetLastError();
      TS_LatchPassOnly(
         TS_PASS_REASON_BAR_FETCH_FAIL,
         StringFormat("CopyRates(shift=1,count=1) failed copied=%d err=%d", copied, err)
      );
      return false;
   }

   const datetime closed_bar_time = rates[0].time;
   if(closed_bar_time <= 0)
      return false;

   if(g_ts_last_processed_closed_bar_time == closed_bar_time)
      return false;

   if(g_ts_last_processed_closed_bar_time > 0 && closed_bar_time < g_ts_last_processed_closed_bar_time)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_TIME_ORDER_BROKEN,
         StringFormat(
            "closed bar moved backward prev=%s curr=%s",
            TimeToString(g_ts_last_processed_closed_bar_time, TIME_DATE | TIME_MINUTES),
            TimeToString(closed_bar_time, TIME_DATE | TIME_MINUTES)
         )
      );
      return false;
   }

   int missing_bars_count = 0;
   const int period_sec = PeriodSeconds(TS_DECISION_TIMEFRAME);
   if(g_ts_last_processed_closed_bar_time > 0 && period_sec > 0)
   {
      const long delta_sec = (long)(closed_bar_time - g_ts_last_processed_closed_bar_time);

      if(delta_sec <= 0 || (delta_sec % period_sec) != 0)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_TIME_ORDER_BROKEN,
            StringFormat("invalid bar delta delta_sec=%d period_sec=%d", (int)delta_sec, period_sec)
         );
         return false;
      }

      const long step_count = delta_sec / period_sec;
      if(step_count > 1)
      {
         missing_bars_count = (int)(step_count - 1);
         bar_level_pass = true;
         TS_RecordSoftFault(
            TS_PASS_REASON_DATA_GAP,
            StringFormat("data gap detected missing_bars_count=%d", missing_bars_count)
         );
         // Option A: any gap >= 1 bar resets the active window.
         TS_ResetBarWindow();
      }
   }

   double spread_price_t = 0.0;
   double spread_points_t = 0.0;
   ENUM_TS_SPREAD_CAPTURE_MODE capture_mode = TS_SPREAD_CAPTURE_MODE_UNKNOWN;
   TS_ResolveSpreadAtClose(closed_bar_time, spread_price_t, spread_points_t, capture_mode);

   TS_BarRecord bar;
   bar.bar_time_t = closed_bar_time;
   bar.bid_open_t = rates[0].open;
   bar.bid_high_t = rates[0].high;
   bar.bid_low_t = rates[0].low;
   bar.bid_close_t = rates[0].close;
   bar.spread_price_t = spread_price_t;
   bar.spread_points_t = spread_points_t;
   bar.spread_capture_mode = capture_mode;

   TS_PushBar(bar);
   g_ts_last_processed_closed_bar_time = closed_bar_time;
   g_ts_last_missing_bars_count = missing_bars_count;
   TS_SavePersistedDataIngestState();

   if(!TS_ValidateMonotonicWindow())
      return false;

   TS_LogIngestEvent(bar, bar_level_pass, missing_bars_count);
   return true;
}

void TS_LogDataIngestState()
{
   PrintFormat(
      "[TS][INGEST_STATE] bars=%d window_ready=%s first=%s last=%s missing_last=%d persisted_last=%s",
      g_ts_bar_count,
      g_ts_window_ready ? "true" : "false",
      TimeToString(g_ts_window_first_time, TIME_DATE | TIME_MINUTES),
      TimeToString(g_ts_window_last_time, TIME_DATE | TIME_MINUTES),
      g_ts_last_missing_bars_count,
      TimeToString(g_ts_last_processed_closed_bar_time, TIME_DATE | TIME_MINUTES)
   );
}

#endif // __TS_DATA_INGEST_MQH__
