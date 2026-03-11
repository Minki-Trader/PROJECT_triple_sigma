#ifndef __TS_DECISION_MQH__
#define __TS_DECISION_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_Features.mqh"
#include "TS_Models.mqh"

int g_ts_final_dir = 2; // assembled model+flip dir; NOT executable action
bool g_ts_flip_used = false;
double g_ts_final_k_sl = TS_PASS_DEFAULT_K_SL;
double g_ts_final_k_tp = TS_PASS_DEFAULT_K_TP;
int g_ts_final_hold_bars = TS_PASS_DEFAULT_HOLD_BARS;
double g_ts_final_y[6];
bool g_ts_decision_ready = false;
string g_ts_fail_safe_reason = "";

string TS_DecisionDirToString(const int dir)
{
   switch(dir)
   {
      case 0: return "LONG";
      case 1: return "SHORT";
      case 2: return "PASS";
      default: return "UNKNOWN";
   }
}

bool TS_DecisionIsFiniteValue(const double value)
{
   return (MathIsValidNumber(value) && MathAbs(value) < (EMPTY_VALUE / 2.0));
}

void TS_DecisionResolveSafeProbabilities(double &p_long, double &p_short, double &p_pass)
{
   p_long = 0.0;
   p_short = 0.0;
   p_pass = 1.0;

   if(!g_ts_stage1_last_ok)
      return;

   if(!TS_DecisionIsFiniteValue(g_ts_stage1_last[0]) ||
      !TS_DecisionIsFiniteValue(g_ts_stage1_last[1]) ||
      !TS_DecisionIsFiniteValue(g_ts_stage1_last[2]))
   {
      return;
   }

   p_long = g_ts_stage1_last[0];
   p_short = g_ts_stage1_last[1];
   p_pass = g_ts_stage1_last[2];
}

void TS_DecisionApplyResult(
   const int final_dir,
   const bool flip_used,
   const double p_long,
   const double p_short,
   const double p_pass,
   const double final_k_sl,
   const double final_k_tp,
   const int final_hold_bars,
   const string fail_safe_reason
)
{
   g_ts_final_dir = final_dir;
   g_ts_flip_used = flip_used;
   g_ts_final_k_sl = final_k_sl;
   g_ts_final_k_tp = final_k_tp;
   g_ts_final_hold_bars = final_hold_bars;
   g_ts_fail_safe_reason = fail_safe_reason;

   g_ts_final_y[0] = p_long;
   g_ts_final_y[1] = p_short;
   g_ts_final_y[2] = p_pass;
   g_ts_final_y[3] = final_k_sl;
   g_ts_final_y[4] = final_k_tp;
   g_ts_final_y[5] = (double)final_hold_bars;

   g_ts_decision_ready = true;
}

void TS_DecisionApplyPassDefaults(const double p_long, const double p_short, const double p_pass, const string fail_safe_reason)
{
   TS_DecisionApplyResult(
      2,
      false,
      p_long,
      p_short,
      p_pass,
      TS_PASS_DEFAULT_K_SL,
      TS_PASS_DEFAULT_K_TP,
      TS_PASS_DEFAULT_HOLD_BARS,
      fail_safe_reason
   );
}

void TS_ResetDecisionState()
{
   g_ts_final_dir = 2;
   g_ts_flip_used = false;
   g_ts_final_k_sl = TS_PASS_DEFAULT_K_SL;
   g_ts_final_k_tp = TS_PASS_DEFAULT_K_TP;
   g_ts_final_hold_bars = TS_PASS_DEFAULT_HOLD_BARS;
   ArrayInitialize(g_ts_final_y, 0.0);
   g_ts_final_y[2] = 1.0;
   g_ts_final_y[3] = TS_PASS_DEFAULT_K_SL;
   g_ts_final_y[4] = TS_PASS_DEFAULT_K_TP;
   g_ts_final_y[5] = (double)TS_PASS_DEFAULT_HOLD_BARS;
   g_ts_decision_ready = false;
   g_ts_fail_safe_reason = "";
}

void TS_LogDecisionState()
{
   PrintFormat(
      "[TS][DECISION_STATE] ready=%s dir=%s flip_used=%s final=[%.6f,%.6f,%d] y=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f] fail_safe_reason=%s",
      g_ts_decision_ready ? "true" : "false",
      TS_DecisionDirToString(g_ts_final_dir),
      g_ts_flip_used ? "true" : "false",
      g_ts_final_k_sl,
      g_ts_final_k_tp,
      g_ts_final_hold_bars,
      g_ts_final_y[0],
      g_ts_final_y[1],
      g_ts_final_y[2],
      g_ts_final_y[3],
      g_ts_final_y[4],
      g_ts_final_y[5],
      g_ts_fail_safe_reason
   );
}

bool TS_AssembleDecision(const bool inference_ok, const double p_min_trade, const double delta_flip)
{
   g_ts_decision_ready = false;
   g_ts_fail_safe_reason = "";

   double p_long = 0.0;
   double p_short = 0.0;
   double p_pass = 1.0;
   TS_DecisionResolveSafeProbabilities(p_long, p_short, p_pass);

   if(!inference_ok)
   {
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "inference failed");
      return true;
   }

   if(g_ts_last_model_dir < 0 || g_ts_last_model_dir > 2)
   {
      TS_RecordSoftFault(TS_PASS_REASON_SHAPE_DTYPE_MISMATCH, StringFormat("assembled dir invalid=%d", g_ts_last_model_dir));
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "assembled dir invalid");
      return true;
   }

   if(g_ts_last_model_dir != 2 && !g_ts_stage2_last_ok)
   {
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "stage2 not ok");
      return true;
   }

   if(g_ts_last_model_dir == 2)
   {
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "");
      return true;
   }

   const int stage2_base = (g_ts_last_model_dir == 0) ? 0 : 3;
   const double raw_k_sl = g_ts_stage2_last[stage2_base + 0];
   const double raw_k_tp = g_ts_stage2_last[stage2_base + 1];
   const double raw_hold = g_ts_stage2_last[stage2_base + 2];

   if(!TS_DecisionIsFiniteValue(raw_k_sl) ||
      !TS_DecisionIsFiniteValue(raw_k_tp) ||
      !TS_DecisionIsFiniteValue(raw_hold))
   {
      TS_RecordSoftFault(
         TS_PASS_REASON_NAN_INF,
         StringFormat("stage2 selected invalid dir=%s raw=[%.8f,%.8f,%.8f]", TS_DecisionDirToString(g_ts_last_model_dir), raw_k_sl, raw_k_tp, raw_hold)
      );
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "stage2 selected invalid");
      return true;
   }

   const double clamped_k_sl = MathMax(0.5, MathMin(6.0, raw_k_sl));
   const double clamped_k_tp = MathMax(0.5, MathMin(12.0, raw_k_tp));
   const double clamped_hold = MathMax(1.0, MathMin((double)TS_HOLD_BARS_MAX, raw_hold));
   const int final_hold = (int)MathRound(clamped_hold);

   if(!TS_DecisionIsFiniteValue(clamped_k_sl) ||
      !TS_DecisionIsFiniteValue(clamped_k_tp) ||
      final_hold < 1 || final_hold > TS_HOLD_BARS_MAX)
   {
      TS_RecordSoftFault(
         TS_PASS_REASON_SHAPE_DTYPE_MISMATCH,
         StringFormat("stage2 clamped invalid dir=%s val=[%.8f,%.8f,%d]", TS_DecisionDirToString(g_ts_last_model_dir), clamped_k_sl, clamped_k_tp, final_hold)
      );
      TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "stage2 clamped invalid");
      return true;
   }

   bool flip_used = false;
   int final_dir = g_ts_last_model_dir;

   const bool long_model_short_candidate_conflict =
      (g_ts_current_cand_short == 1 && g_ts_current_cand_long == 0 && final_dir == 0);
   const bool short_model_long_candidate_conflict =
      (g_ts_current_cand_long == 1 && g_ts_current_cand_short == 0 && final_dir == 1);

   if(long_model_short_candidate_conflict)
   {
      if(p_long >= p_min_trade && (p_long - p_short) >= delta_flip)
         flip_used = true;
      else
      {
         TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "flip rejected");
         return true;
      }
   }
   else if(short_model_long_candidate_conflict)
   {
      if(p_short >= p_min_trade && (p_short - p_long) >= delta_flip)
         flip_used = true;
      else
      {
         TS_DecisionApplyPassDefaults(p_long, p_short, p_pass, "flip rejected");
         return true;
      }
   }

   TS_DecisionApplyResult(
      final_dir,
      flip_used,
      p_long,
      p_short,
      p_pass,
      clamped_k_sl,
      clamped_k_tp,
      final_hold,
      ""
   );
   return true;
}

#endif // __TS_DECISION_MQH__
