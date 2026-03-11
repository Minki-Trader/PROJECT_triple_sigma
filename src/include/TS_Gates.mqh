#ifndef __TS_GATES_MQH__
#define __TS_GATES_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_PackMeta.mqh"
#include "TS_Features.mqh"
#include "TS_Models.mqh"
#include "TS_Decision.mqh"

bool g_ts_gate_config_loaded = false;
bool g_ts_gate_pass = false;
string g_ts_gate_reject_reason = "";
double g_ts_dyn_spread_atr_max = 0.0;
int g_ts_dyn_dev_points = 0;
double g_ts_risk_pct = 0.0;
bool g_ts_needs_sl_adjustment = false;
bool g_ts_order_constraint_hard_reject = false;
int g_ts_min_stop_distance_points = 0;

double g_ts_gc_spread_atr_max_base = 0.30;
double g_ts_gc_spread_atr_max_hard = 0.60;
double g_ts_gc_k_tp_scale_min = 1.0;
double g_ts_gc_k_tp_scale_max = 6.0;
int g_ts_gc_dev_points_base = 3;
int g_ts_gc_dev_points_add_max = 5;
int g_ts_gc_dev_points_hard_max = 10;
double g_ts_gc_risk_pct_base = 0.01;
double g_ts_gc_risk_pct_hard_min = 0.002;
double g_ts_gc_risk_pct_hard_max = 0.03;

bool TS_GateIsFiniteValue(const double value)
{
   return (MathIsValidNumber(value) && MathAbs(value) < (EMPTY_VALUE / 2.0));
}

double TS_GateClamp(const double value, const double lo, const double hi)
{
   if(value < lo)
      return lo;
   if(value > hi)
      return hi;
   return value;
}

void TS_ResetGateBarState()
{
   g_ts_gate_pass = false;
   g_ts_gate_reject_reason = "";
   g_ts_dyn_spread_atr_max = 0.0;
   g_ts_dyn_dev_points = 0;
   g_ts_risk_pct = 0.0;
   g_ts_needs_sl_adjustment = false;
   g_ts_order_constraint_hard_reject = false;
   g_ts_min_stop_distance_points = 0;
}

void TS_ResetGateState()
{
   g_ts_gate_config_loaded = false;
   g_ts_gc_spread_atr_max_base = 0.30;
   g_ts_gc_spread_atr_max_hard = 0.60;
   g_ts_gc_k_tp_scale_min = 1.0;
   g_ts_gc_k_tp_scale_max = 6.0;
   g_ts_gc_dev_points_base = 3;
   g_ts_gc_dev_points_add_max = 5;
   g_ts_gc_dev_points_hard_max = 10;
   g_ts_gc_risk_pct_base = 0.01;
   g_ts_gc_risk_pct_hard_min = 0.002;
   g_ts_gc_risk_pct_hard_max = 0.03;
   TS_ResetGateBarState();
}

bool TS_ValidateGateConfigValues(const string source_tag)
{
   if(!TS_GateIsFiniteValue(g_ts_gc_spread_atr_max_base) ||
      !TS_GateIsFiniteValue(g_ts_gc_spread_atr_max_hard) ||
      g_ts_gc_spread_atr_max_base <= 0.0 ||
      g_ts_gc_spread_atr_max_hard < g_ts_gc_spread_atr_max_base)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "%s invalid spread_atr caps base=%.8f hard=%.8f",
            source_tag,
            g_ts_gc_spread_atr_max_base,
            g_ts_gc_spread_atr_max_hard
         )
      );
      return false;
   }

   if(!TS_GateIsFiniteValue(g_ts_gc_k_tp_scale_min) ||
      !TS_GateIsFiniteValue(g_ts_gc_k_tp_scale_max) ||
      g_ts_gc_k_tp_scale_min <= 0.0 ||
      g_ts_gc_k_tp_scale_max <= g_ts_gc_k_tp_scale_min)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "%s invalid k_tp scale range min=%.8f max=%.8f",
            source_tag,
            g_ts_gc_k_tp_scale_min,
            g_ts_gc_k_tp_scale_max
         )
      );
      return false;
   }

   if(g_ts_gc_dev_points_base < 0 ||
      g_ts_gc_dev_points_add_max < 0 ||
      g_ts_gc_dev_points_hard_max < g_ts_gc_dev_points_base)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "%s invalid dev_points base=%d add=%d hard=%d",
            source_tag,
            g_ts_gc_dev_points_base,
            g_ts_gc_dev_points_add_max,
            g_ts_gc_dev_points_hard_max
         )
      );
      return false;
   }

   if(!TS_GateIsFiniteValue(g_ts_gc_risk_pct_base) ||
      !TS_GateIsFiniteValue(g_ts_gc_risk_pct_hard_min) ||
      !TS_GateIsFiniteValue(g_ts_gc_risk_pct_hard_max) ||
      g_ts_gc_risk_pct_hard_min <= 0.0 ||
      g_ts_gc_risk_pct_hard_max < g_ts_gc_risk_pct_hard_min ||
      g_ts_gc_risk_pct_base < g_ts_gc_risk_pct_hard_min ||
      g_ts_gc_risk_pct_base > g_ts_gc_risk_pct_hard_max)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "%s invalid risk_pct base=%.8f hard_min=%.8f hard_max=%.8f",
            source_tag,
            g_ts_gc_risk_pct_base,
            g_ts_gc_risk_pct_hard_min,
            g_ts_gc_risk_pct_hard_max
         )
      );
      return false;
   }

   return true;
}

bool TS_SetGateConfigDefaults(
   const double spread_atr_max_base,
   const double spread_atr_max_hard,
   const double k_tp_scale_min,
   const double k_tp_scale_max,
   const int dev_points_base,
   const int dev_points_add_max,
   const int dev_points_hard_max,
   const double risk_pct_base,
   const double risk_pct_hard_min,
   const double risk_pct_hard_max
)
{
   g_ts_gc_spread_atr_max_base = spread_atr_max_base;
   g_ts_gc_spread_atr_max_hard = spread_atr_max_hard;
   g_ts_gc_k_tp_scale_min = k_tp_scale_min;
   g_ts_gc_k_tp_scale_max = k_tp_scale_max;
   g_ts_gc_dev_points_base = dev_points_base;
   g_ts_gc_dev_points_add_max = dev_points_add_max;
   g_ts_gc_dev_points_hard_max = dev_points_hard_max;
   g_ts_gc_risk_pct_base = risk_pct_base;
   g_ts_gc_risk_pct_hard_min = risk_pct_hard_min;
   g_ts_gc_risk_pct_hard_max = risk_pct_hard_max;
   return TS_ValidateGateConfigValues("gate EA inputs");
}

void TS_LogGateState()
{
   PrintFormat(
      "[TS][GATE_STATE] config_loaded=%s gate_pass=%s reason=%s dyn_spread_atr_max=%.6f dyn_dev_points=%d risk_pct=%.6f needs_sl_adjustment=%s order_constraint_hard_reject=%s min_stop_distance_points=%d spread_atr_raw=%.6f atr14_raw=%.8f cfg=[spread_base=%.6f spread_hard=%.6f k_tp_min=%.6f k_tp_max=%.6f dev_base=%d dev_add=%d dev_hard=%d risk_base=%.6f risk_min=%.6f risk_max=%.6f]",
      g_ts_gate_config_loaded ? "true" : "false",
      g_ts_gate_pass ? "true" : "false",
      g_ts_gate_reject_reason,
      g_ts_dyn_spread_atr_max,
      g_ts_dyn_dev_points,
      g_ts_risk_pct,
      g_ts_needs_sl_adjustment ? "true" : "false",
      g_ts_order_constraint_hard_reject ? "true" : "false",
      g_ts_min_stop_distance_points,
      g_ts_current_spread_atr,
      g_ts_current_atr14,
      g_ts_gc_spread_atr_max_base,
      g_ts_gc_spread_atr_max_hard,
      g_ts_gc_k_tp_scale_min,
      g_ts_gc_k_tp_scale_max,
      g_ts_gc_dev_points_base,
      g_ts_gc_dev_points_add_max,
      g_ts_gc_dev_points_hard_max,
      g_ts_gc_risk_pct_base,
      g_ts_gc_risk_pct_hard_min,
      g_ts_gc_risk_pct_hard_max
   );
}

bool TS_GateReadTextFileAll(const string rel_path, string &content)
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

bool TS_GateExtractJsonNumber(const string content, const string key, double &value)
{
   value = 0.0;

   const string marker = "\"" + key + "\"";
   const int key_pos = StringFind(content, marker);
   if(key_pos < 0)
      return false;

   const int colon_pos = StringFind(content, ":", key_pos + StringLen(marker));
   if(colon_pos < 0)
      return false;

   int pos = colon_pos + 1;
   while(pos < StringLen(content))
   {
      const ushort ch = (ushort)StringGetCharacter(content, pos);
      if(ch != ' ' && ch != '\r' && ch != '\n' && ch != '\t')
         break;
      pos++;
   }

   string token = "";
   bool saw_digit = false;
   while(pos < StringLen(content))
   {
      const ushort ch = (ushort)StringGetCharacter(content, pos);
      const bool is_digit = (ch >= '0' && ch <= '9');
      const bool is_sign = (ch == '+' || ch == '-');
      const bool is_dot = (ch == '.');
      const bool is_exp = (ch == 'e' || ch == 'E');
      if(!is_digit && !is_sign && !is_dot && !is_exp)
         break;

      token += StringSubstr(content, pos, 1);
      if(is_digit)
         saw_digit = true;
      pos++;
   }

   if(!saw_digit)
      return false;

   value = StringToDouble(token);
   return TS_GateIsFiniteValue(value);
}

bool TS_LoadGateConfig(const string model_pack_dir)
{
   string detail = "";
   if(!TS_PM_ValidateModelPackDir(model_pack_dir, detail))
   {
      TS_LatchPassOnly(TS_PASS_REASON_PACK_META_FAIL, detail);
      return false;
   }

   const string rel_path = TS_PM_Trim(model_pack_dir) + "\\gate_config.json";
   if(!FileIsExist(rel_path))
   {
      g_ts_gate_config_loaded = false;
      PrintFormat("[TS][GATE] gate_config.json not found path=%s using EA input defaults", rel_path);
      return true;
   }

   string content = "";
   if(!TS_GateReadTextFileAll(rel_path, content))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("gate_config open failed path=%s err=%d", rel_path, GetLastError())
      );
      return false;
   }

   double spread_atr_max_base = 0.0;
   double spread_atr_max_hard = 0.0;
   double k_tp_scale_min = 0.0;
   double k_tp_scale_max = 0.0;
   double dev_points_base = 0.0;
   double dev_points_add_max = 0.0;
   double dev_points_hard_max = 0.0;
   double risk_pct_base = 0.0;
   double risk_pct_hard_min = 0.0;
   double risk_pct_hard_max = 0.0;

   if(!TS_GateExtractJsonNumber(content, "spread_atr_max_base", spread_atr_max_base) ||
      !TS_GateExtractJsonNumber(content, "spread_atr_max_hard", spread_atr_max_hard) ||
      !TS_GateExtractJsonNumber(content, "k_tp_scale_min", k_tp_scale_min) ||
      !TS_GateExtractJsonNumber(content, "k_tp_scale_max", k_tp_scale_max) ||
      !TS_GateExtractJsonNumber(content, "dev_points_base", dev_points_base) ||
      !TS_GateExtractJsonNumber(content, "dev_points_add_max", dev_points_add_max) ||
      !TS_GateExtractJsonNumber(content, "dev_points_hard_max", dev_points_hard_max) ||
      !TS_GateExtractJsonNumber(content, "risk_pct_base", risk_pct_base) ||
      !TS_GateExtractJsonNumber(content, "risk_pct_hard_min", risk_pct_hard_min) ||
      !TS_GateExtractJsonNumber(content, "risk_pct_hard_max", risk_pct_hard_max))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("gate_config parse failed path=%s", rel_path)
      );
      return false;
   }

   g_ts_gc_spread_atr_max_base = spread_atr_max_base;
   g_ts_gc_spread_atr_max_hard = spread_atr_max_hard;
   g_ts_gc_k_tp_scale_min = k_tp_scale_min;
   g_ts_gc_k_tp_scale_max = k_tp_scale_max;
   g_ts_gc_dev_points_base = (int)MathRound(dev_points_base);
   g_ts_gc_dev_points_add_max = (int)MathRound(dev_points_add_max);
   g_ts_gc_dev_points_hard_max = (int)MathRound(dev_points_hard_max);
   g_ts_gc_risk_pct_base = risk_pct_base;
   g_ts_gc_risk_pct_hard_min = risk_pct_hard_min;
   g_ts_gc_risk_pct_hard_max = risk_pct_hard_max;

   if(!TS_ValidateGateConfigValues("gate_config.json"))
      return false;

   g_ts_gate_config_loaded = true;
   PrintFormat(
      "[TS][GATE] loaded path=%s spread_base=%.6f spread_hard=%.6f k_tp_min=%.6f k_tp_max=%.6f dev_base=%d dev_add=%d dev_hard=%d risk_base=%.6f risk_min=%.6f risk_max=%.6f",
      rel_path,
      g_ts_gc_spread_atr_max_base,
      g_ts_gc_spread_atr_max_hard,
      g_ts_gc_k_tp_scale_min,
      g_ts_gc_k_tp_scale_max,
      g_ts_gc_dev_points_base,
      g_ts_gc_dev_points_add_max,
      g_ts_gc_dev_points_hard_max,
      g_ts_gc_risk_pct_base,
      g_ts_gc_risk_pct_hard_min,
      g_ts_gc_risk_pct_hard_max
   );
   return true;
}

void TS_GateReject(const string reason)
{
   g_ts_gate_pass = false;
   g_ts_gate_reject_reason = reason;
}

datetime TS_GetGateDecisionTime()
{
   if(g_ts_bar_count > 0)
      return g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;
   return TimeCurrent();
}

bool TS_EvaluateGates(const double p_min_trade, const int block_week_open_min, const int block_rollover_min)
{
   TS_ResetGateBarState();

   if(!g_ts_decision_ready)
   {
      TS_GateReject("GATE_EVAL:decision_not_ready");
      return false;
   }

   if(g_ts_final_dir == 2)
   {
      g_ts_gate_pass = true;
      return true;
   }

   const double conf = MathMax(g_ts_final_y[0], g_ts_final_y[1]);
   const double conf_den = MathMax(1.0 - p_min_trade, TS_EPSILON);
   const double conf_t = TS_GateClamp((conf - p_min_trade) / conf_den, 0.0, 1.0);
   const double tp_den = MathMax(g_ts_gc_k_tp_scale_max - g_ts_gc_k_tp_scale_min, TS_EPSILON);
   const double tp_t = TS_GateClamp((g_ts_final_k_tp - g_ts_gc_k_tp_scale_min) / tp_den, 0.0, 1.0);

   g_ts_dyn_spread_atr_max = MathMin(
      g_ts_gc_spread_atr_max_base * (0.85 + (0.25 * conf_t) + (0.25 * tp_t)),
      g_ts_gc_spread_atr_max_hard
   );
   g_ts_dyn_dev_points = MathMin(
      g_ts_gc_dev_points_base + (int)MathRound(g_ts_gc_dev_points_add_max * conf_t),
      g_ts_gc_dev_points_hard_max
   );
   g_ts_risk_pct = TS_GateClamp(
      g_ts_gc_risk_pct_base * (0.8 + (0.6 * conf_t)),
      g_ts_gc_risk_pct_hard_min,
      g_ts_gc_risk_pct_hard_max
   );

   MqlDateTime dt;
   const datetime decision_time = TS_GetGateDecisionTime();
   TimeToStruct(decision_time, dt);
   const int minutes_since_midnight = (dt.hour * 60) + dt.min;

   if(block_week_open_min > 0 && dt.day_of_week == 1 && minutes_since_midnight < block_week_open_min)
   {
      TS_GateReject(
         StringFormat(
            "TIME_BLOCK:week_open decision_bar=%s minutes_since_midnight=%d block=%d",
            TimeToString(decision_time, TIME_DATE | TIME_MINUTES),
            minutes_since_midnight,
            block_week_open_min
         )
      );
      return true;
   }

   if(block_rollover_min > 0 &&
      (minutes_since_midnight < block_rollover_min || minutes_since_midnight >= (1440 - block_rollover_min)))
   {
      TS_GateReject(
         StringFormat(
            "TIME_BLOCK:rollover decision_bar=%s minutes_since_midnight=%d block=%d",
            TimeToString(decision_time, TIME_DATE | TIME_MINUTES),
            minutes_since_midnight,
            block_rollover_min
         )
      );
      return true;
   }

   if(!TS_GateIsFiniteValue(g_ts_current_spread_atr) || g_ts_current_spread_atr < 0.0)
   {
      TS_GateReject(StringFormat("SPREAD:raw_invalid spread_atr=%.8f", g_ts_current_spread_atr));
      return true;
   }

   if(g_ts_current_spread_atr > g_ts_dyn_spread_atr_max)
   {
      TS_GateReject(
         StringFormat("SPREAD:spread_atr=%.6f>dyn=%.6f", g_ts_current_spread_atr, g_ts_dyn_spread_atr_max)
      );
      return true;
   }

   if(!TS_GateIsFiniteValue(g_ts_current_atr14) || g_ts_current_atr14 <= 0.0)
   {
      TS_GateReject(StringFormat("ORDER_CONSTRAINT:atr14_invalid atr14=%.8f", g_ts_current_atr14));
      return true;
   }

   const double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(!TS_GateIsFiniteValue(point) || point <= 0.0)
   {
      TS_GateReject(StringFormat("ORDER_CONSTRAINT:point_invalid point=%.8f", point));
      return false;
   }

   const int min_stop_distance_points = (int)MathMax(
      0.0,
      MathMax(
         (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL),
         (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL)
      )
   );
   g_ts_min_stop_distance_points = min_stop_distance_points;

   const double sl_distance_points = (g_ts_final_k_sl * g_ts_current_atr14) / point;
   const double tp_distance_points = (g_ts_final_k_tp * g_ts_current_atr14) / point;
   const double max_sl_distance_points = (6.0 * g_ts_current_atr14) / point;
   const double max_tp_distance_points = (12.0 * g_ts_current_atr14) / point;

   g_ts_needs_sl_adjustment =
      (sl_distance_points < (double)min_stop_distance_points) ||
      (tp_distance_points < (double)min_stop_distance_points);
   g_ts_order_constraint_hard_reject =
      ((double)min_stop_distance_points > max_sl_distance_points) ||
      ((double)min_stop_distance_points > max_tp_distance_points);

   if(g_ts_order_constraint_hard_reject)
   {
      TS_GateReject(
         StringFormat(
            "ORDER_CONSTRAINT:min_stop=%d sl_pts=%.2f tp_pts=%.2f max_sl_pts=%.2f max_tp_pts=%.2f",
            min_stop_distance_points,
            sl_distance_points,
            tp_distance_points,
            max_sl_distance_points,
            max_tp_distance_points
         )
      );
      return true;
   }

   g_ts_gate_pass = true;
   return true;
}

#endif // __TS_GATES_MQH__
