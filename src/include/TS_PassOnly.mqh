#ifndef __TS_PASS_ONLY_MQH__
#define __TS_PASS_ONLY_MQH__

#include "TS_Defines.mqh"

enum ENUM_TS_PASS_ONLY_REASON
{
   TS_PASS_REASON_NONE = 0,

   // Hard faults: immediate irreversible latch.
   TS_PASS_REASON_MODEL_LOAD_FAIL = 1001,
   TS_PASS_REASON_PACK_META_FAIL = 1002,
   TS_PASS_REASON_SCHEMA_VERSION_MISMATCH = 1003,
   TS_PASS_REASON_SHAPE_DTYPE_MISMATCH = 1004,
   TS_PASS_REASON_INVALID_CAND = 1005,
   TS_PASS_REASON_BAR_FETCH_FAIL = 1006,
   TS_PASS_REASON_TIME_ORDER_BROKEN = 1007,
   TS_PASS_REASON_INDICATOR_INIT_FAIL = 1008,

   // Soft faults: bar-level PASS with telemetry.
   TS_PASS_REASON_NAN_INF = 2001,
   TS_PASS_REASON_PROB_SUM = 2002,
   TS_PASS_REASON_DATA_GAP = 2003
};

bool g_ts_pass_only_latched = false;
ENUM_TS_PASS_ONLY_REASON g_ts_pass_only_reason = TS_PASS_REASON_NONE;
string g_ts_pass_only_detail = "";

int g_ts_soft_fault_count_total = 0;
int g_ts_soft_fault_streak_current = 0;
ENUM_TS_PASS_ONLY_REASON g_ts_last_soft_fault_reason = TS_PASS_REASON_NONE;

string TS_PassReasonToString(const ENUM_TS_PASS_ONLY_REASON reason)
{
   switch(reason)
   {
      case TS_PASS_REASON_NONE: return "NONE";
      case TS_PASS_REASON_MODEL_LOAD_FAIL: return "MODEL_LOAD_FAIL";
      case TS_PASS_REASON_PACK_META_FAIL: return "PACK_META_FAIL";
      case TS_PASS_REASON_SCHEMA_VERSION_MISMATCH: return "SCHEMA_VERSION_MISMATCH";
      case TS_PASS_REASON_SHAPE_DTYPE_MISMATCH: return "SHAPE_DTYPE_MISMATCH";
      case TS_PASS_REASON_INVALID_CAND: return "INVALID_CAND";
      case TS_PASS_REASON_BAR_FETCH_FAIL: return "BAR_FETCH_FAIL";
      case TS_PASS_REASON_TIME_ORDER_BROKEN: return "TIME_ORDER_BROKEN";
      case TS_PASS_REASON_INDICATOR_INIT_FAIL: return "INDICATOR_INIT_FAIL";
      case TS_PASS_REASON_NAN_INF: return "NAN_INF";
      case TS_PASS_REASON_PROB_SUM: return "PROB_SUM";
      case TS_PASS_REASON_DATA_GAP: return "DATA_GAP";
      default: return "UNKNOWN";
   }
}

bool TS_IsHardPassReason(const ENUM_TS_PASS_ONLY_REASON reason)
{
   switch(reason)
   {
      case TS_PASS_REASON_MODEL_LOAD_FAIL:
      case TS_PASS_REASON_PACK_META_FAIL:
      case TS_PASS_REASON_SCHEMA_VERSION_MISMATCH:
      case TS_PASS_REASON_SHAPE_DTYPE_MISMATCH:
      case TS_PASS_REASON_INVALID_CAND:
      case TS_PASS_REASON_BAR_FETCH_FAIL:
      case TS_PASS_REASON_TIME_ORDER_BROKEN:
      case TS_PASS_REASON_INDICATOR_INIT_FAIL:
         return true;
      default:
         return false;
   }
}

void TS_ResetPassOnlyState()
{
   g_ts_pass_only_latched = false;
   g_ts_pass_only_reason = TS_PASS_REASON_NONE;
   g_ts_pass_only_detail = "";
   g_ts_soft_fault_count_total = 0;
   g_ts_soft_fault_streak_current = 0;
   g_ts_last_soft_fault_reason = TS_PASS_REASON_NONE;
}

bool TS_IsPassOnlyLatched()
{
   return g_ts_pass_only_latched;
}

void TS_LatchPassOnly(const ENUM_TS_PASS_ONLY_REASON reason, const string detail = "")
{
   if(g_ts_pass_only_latched)
   {
      PrintFormat(
         "[TS][WARN] Latch already set reason=%s, ignoring new reason=%s",
         TS_PassReasonToString(g_ts_pass_only_reason),
         TS_PassReasonToString(reason)
      );
      return;
   }

   if(!TS_IsHardPassReason(reason))
   {
      PrintFormat(
         "[TS][WARN] Non-hard reason passed to TS_LatchPassOnly reason=%s(%d)",
         TS_PassReasonToString(reason),
         reason
      );
   }

   g_ts_pass_only_latched = true;
   g_ts_pass_only_reason = reason;
   g_ts_pass_only_detail = detail;

   PrintFormat(
      "[TS][PASS_ONLY][LATCH] reason=%s(%d) detail=%s",
      TS_PassReasonToString(reason),
      reason,
      detail
   );
}

void TS_RecordSoftFault(const ENUM_TS_PASS_ONLY_REASON reason, const string detail = "")
{
   g_ts_soft_fault_count_total++;

   if(g_ts_last_soft_fault_reason == reason)
      g_ts_soft_fault_streak_current++;
   else
      g_ts_soft_fault_streak_current = 1;

   g_ts_last_soft_fault_reason = reason;

   PrintFormat(
      "[TS][SOFT_FAULT] reason=%s(%d) total=%d streak=%d detail=%s",
      TS_PassReasonToString(reason),
      reason,
      g_ts_soft_fault_count_total,
      g_ts_soft_fault_streak_current,
      detail
   );
}

void TS_RecordSoftHealthyBar()
{
   g_ts_soft_fault_streak_current = 0;
   g_ts_last_soft_fault_reason = TS_PASS_REASON_NONE;
}

void TS_LogPassOnlyState()
{
   PrintFormat(
      "[TS][STATE] pass_only_latched=%s reason=%s(%d) detail=%s soft_total=%d soft_streak=%d",
      g_ts_pass_only_latched ? "true" : "false",
      TS_PassReasonToString(g_ts_pass_only_reason),
      g_ts_pass_only_reason,
      g_ts_pass_only_detail,
      g_ts_soft_fault_count_total,
      g_ts_soft_fault_streak_current
   );
}

bool TS_ValidateProbabilities(const double p_long, const double p_short, const double p_pass)
{
   if(!MathIsValidNumber(p_long) || !MathIsValidNumber(p_short) || !MathIsValidNumber(p_pass))
   {
      TS_RecordSoftFault(TS_PASS_REASON_NAN_INF, "probability contains NaN/Inf");
      return false;
   }

   if(p_long < 0.0 || p_long > 1.0 ||
      p_short < 0.0 || p_short > 1.0 ||
      p_pass < 0.0 || p_pass > 1.0)
   {
      TS_RecordSoftFault(TS_PASS_REASON_PROB_SUM, "probability range is outside [0,1]");
      return false;
   }

   const double prob_sum = p_long + p_short + p_pass;
   const double delta = MathAbs(prob_sum - 1.0);

   if(delta > TS_PROB_SUM_TOLERANCE)
   {
      TS_RecordSoftFault(
         TS_PASS_REASON_PROB_SUM,
         StringFormat("probability sum out of tolerance delta=%.8f", delta)
      );
      return false;
   }

   if(delta > TS_PROB_SUM_WARN_THRESHOLD)
   {
      PrintFormat(
         "[TS][WARN] Probability sum near tolerance sum=%.8f delta=%.8f",
         prob_sum,
         delta
      );
   }

   TS_RecordSoftHealthyBar();
   return true;
}

bool TS_ValidateCandidateOneHotOrZero(const int cand_long, const int cand_short)
{
   if((cand_long != 0 && cand_long != 1) || (cand_short != 0 && cand_short != 1))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_INVALID_CAND,
         StringFormat("candidate must be binary cand_long=%d cand_short=%d", cand_long, cand_short)
      );
      return false;
   }

   if(cand_long == 1 && cand_short == 1)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_INVALID_CAND,
         StringFormat("invalid candidate (1,1) cand_long=%d cand_short=%d", cand_long, cand_short)
      );
      return false;
   }

   return true;
}

#endif // __TS_PASS_ONLY_MQH__
