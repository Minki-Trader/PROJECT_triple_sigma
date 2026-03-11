#ifndef __TS_MONITOR_MQH__
#define __TS_MONITOR_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_Execution.mqh"

const int TS_MONITOR_EMIT_EVERY_BARS = 12;

int g_ts_mon_processed_bars = 0;
int g_ts_mon_cand_00_count = 0;
int g_ts_mon_cand_10_count = 0;
int g_ts_mon_cand_01_count = 0;
int g_ts_mon_cand_other_count = 0;
int g_ts_mon_regime_count[6];
int g_ts_mon_final_dir_count[3];
int g_ts_mon_flip_used_count = 0;
int g_ts_mon_gate_pass_count = 0;
int g_ts_mon_gate_reject_time_block_count = 0;
int g_ts_mon_gate_reject_spread_count = 0;
int g_ts_mon_gate_reject_order_constraint_count = 0;
int g_ts_mon_gate_reject_gate_eval_count = 0;
int g_ts_mon_gate_reject_other_count = 0;
int g_ts_mon_gate_skipped_count = 0;
int g_ts_mon_inference_not_ready_count = 0;
int g_ts_mon_decision_not_ready_count = 0;
int g_ts_mon_entry_attempted_count = 0;
int g_ts_mon_entry_executed_count = 0;
int g_ts_mon_entry_rejected_count = 0;
int g_ts_mon_exit_attempted_count = 0;
int g_ts_mon_exit_executed_count = 0;
int g_ts_mon_exit_rejected_count = 0;
int g_ts_mon_retcode_done_count = 0;
int g_ts_mon_retcode_done_partial_count = 0;
int g_ts_mon_retcode_zero_count = 0;
int g_ts_mon_retcode_other_count = 0;
int g_ts_mon_trade_tx_request_count = 0;
int g_ts_mon_trade_tx_deal_add_count = 0;
int g_ts_mon_trade_tx_position_count = 0;
int g_ts_mon_trade_tx_other_count = 0;
string g_ts_mon_last_direct_phase = "";
uint g_ts_mon_last_direct_retcode = 0;
string g_ts_mon_last_direct_desc = "";
bool g_ts_mon_last_direct_synthetic = false;
uint g_ts_mon_last_entry_retcode = 0;
string g_ts_mon_last_entry_desc = "";
uint g_ts_mon_last_exit_retcode = 0;
string g_ts_mon_last_exit_desc = "";
bool g_ts_mon_last_exit_synthetic = false;
string g_ts_mon_last_tx_action = "";
uint g_ts_mon_last_tx_retcode = 0;
string g_ts_mon_last_tx_comment = "";
uint g_ts_mon_last_other_retcode = 0;
string g_ts_mon_last_other_retcode_desc = "";
bool g_ts_mon_last_other_retcode_synthetic = false;
int g_ts_mon_early_exit_evaluated_count = 0;
int g_ts_mon_early_exit_attempted_count = 0;
int g_ts_mon_early_exit_executed_count = 0;
int g_ts_mon_early_exit_rejected_count = 0;
int g_ts_mon_early_exit_min_hold_blocked_count = 0;
int g_ts_mon_early_exit_reason_pass_count = 0;
int g_ts_mon_early_exit_reason_opposite_count = 0;
int g_ts_mon_early_exit_reason_other_count = 0;
string g_ts_mon_last_early_exit_reason = "";
int g_ts_mon_modify_evaluated_count = 0;
int g_ts_mon_modify_attempted_count = 0;
int g_ts_mon_modify_executed_count = 0;
int g_ts_mon_modify_rejected_count = 0;
int g_ts_mon_modify_min_hold_blocked_count = 0;
int g_ts_mon_modify_reason_break_even_count = 0;
int g_ts_mon_modify_reason_trailing_count = 0;
int g_ts_mon_modify_reason_tp_reshape_count = 0;
int g_ts_mon_modify_reason_time_policy_count = 0;
int g_ts_mon_modify_reason_other_count = 0;
int g_ts_mon_modify_pending_cleared_count = 0;
string g_ts_mon_last_modify_reason = "";
int g_ts_mon_runtime_reload_attempt_count = 0;
int g_ts_mon_runtime_reload_success_count = 0;
int g_ts_mon_runtime_reload_rollback_count = 0;
int g_ts_mon_shadow_exit_evaluated_count = 0;
int g_ts_mon_shadow_exit_triggered_count = 0;
int g_ts_mon_shadow_exit_min_hold_blocked_count = 0;
int g_ts_mon_shadow_exit_reason_pass_count = 0;
int g_ts_mon_shadow_exit_reason_opposite_count = 0;
int g_ts_mon_shadow_exit_reason_other_count = 0;
int g_ts_mon_hold_soft_reached_count = 0;
int g_ts_mon_force_exit_count = 0;
ENUM_TS_PASS_ONLY_REASON g_ts_mon_last_non_none_soft_fault_reason = TS_PASS_REASON_NONE;
ulong g_ts_mon_last_bar_start_us = 0;
ulong g_ts_mon_total_bar_us = 0;
ulong g_ts_mon_max_bar_us = 0;

void TS_ResetMonitorState()
{
   g_ts_mon_processed_bars = 0;
   g_ts_mon_cand_00_count = 0;
   g_ts_mon_cand_10_count = 0;
   g_ts_mon_cand_01_count = 0;
   g_ts_mon_cand_other_count = 0;
   ArrayInitialize(g_ts_mon_regime_count, 0);
   ArrayInitialize(g_ts_mon_final_dir_count, 0);
   g_ts_mon_flip_used_count = 0;
   g_ts_mon_gate_pass_count = 0;
   g_ts_mon_gate_reject_time_block_count = 0;
   g_ts_mon_gate_reject_spread_count = 0;
   g_ts_mon_gate_reject_order_constraint_count = 0;
   g_ts_mon_gate_reject_gate_eval_count = 0;
   g_ts_mon_gate_reject_other_count = 0;
   g_ts_mon_gate_skipped_count = 0;
   g_ts_mon_inference_not_ready_count = 0;
   g_ts_mon_decision_not_ready_count = 0;
   g_ts_mon_entry_attempted_count = 0;
   g_ts_mon_entry_executed_count = 0;
   g_ts_mon_entry_rejected_count = 0;
   g_ts_mon_exit_attempted_count = 0;
   g_ts_mon_exit_executed_count = 0;
   g_ts_mon_exit_rejected_count = 0;
   g_ts_mon_retcode_done_count = 0;
   g_ts_mon_retcode_done_partial_count = 0;
   g_ts_mon_retcode_zero_count = 0;
   g_ts_mon_retcode_other_count = 0;
   g_ts_mon_trade_tx_request_count = 0;
   g_ts_mon_trade_tx_deal_add_count = 0;
   g_ts_mon_trade_tx_position_count = 0;
   g_ts_mon_trade_tx_other_count = 0;
   g_ts_mon_last_direct_phase = "";
   g_ts_mon_last_direct_retcode = 0;
   g_ts_mon_last_direct_desc = "";
   g_ts_mon_last_direct_synthetic = false;
   g_ts_mon_last_entry_retcode = 0;
   g_ts_mon_last_entry_desc = "";
   g_ts_mon_last_exit_retcode = 0;
   g_ts_mon_last_exit_desc = "";
   g_ts_mon_last_exit_synthetic = false;
   g_ts_mon_last_tx_action = "";
   g_ts_mon_last_tx_retcode = 0;
   g_ts_mon_last_tx_comment = "";
   g_ts_mon_last_other_retcode = 0;
   g_ts_mon_last_other_retcode_desc = "";
   g_ts_mon_last_other_retcode_synthetic = false;
   g_ts_mon_early_exit_evaluated_count = 0;
   g_ts_mon_early_exit_attempted_count = 0;
   g_ts_mon_early_exit_executed_count = 0;
   g_ts_mon_early_exit_rejected_count = 0;
   g_ts_mon_early_exit_min_hold_blocked_count = 0;
   g_ts_mon_early_exit_reason_pass_count = 0;
   g_ts_mon_early_exit_reason_opposite_count = 0;
   g_ts_mon_early_exit_reason_other_count = 0;
   g_ts_mon_last_early_exit_reason = "";
   g_ts_mon_modify_evaluated_count = 0;
   g_ts_mon_modify_attempted_count = 0;
   g_ts_mon_modify_executed_count = 0;
   g_ts_mon_modify_rejected_count = 0;
   g_ts_mon_modify_min_hold_blocked_count = 0;
   g_ts_mon_modify_reason_break_even_count = 0;
   g_ts_mon_modify_reason_trailing_count = 0;
   g_ts_mon_modify_reason_tp_reshape_count = 0;
   g_ts_mon_modify_reason_time_policy_count = 0;
   g_ts_mon_modify_reason_other_count = 0;
   g_ts_mon_modify_pending_cleared_count = 0;
   g_ts_mon_last_modify_reason = "";
   g_ts_mon_runtime_reload_attempt_count = 0;
   g_ts_mon_runtime_reload_success_count = 0;
   g_ts_mon_runtime_reload_rollback_count = 0;
   g_ts_mon_shadow_exit_evaluated_count = 0;
   g_ts_mon_shadow_exit_triggered_count = 0;
   g_ts_mon_shadow_exit_min_hold_blocked_count = 0;
   g_ts_mon_shadow_exit_reason_pass_count = 0;
   g_ts_mon_shadow_exit_reason_opposite_count = 0;
   g_ts_mon_shadow_exit_reason_other_count = 0;
   g_ts_mon_hold_soft_reached_count = 0;
   g_ts_mon_force_exit_count = 0;
   g_ts_mon_last_non_none_soft_fault_reason = TS_PASS_REASON_NONE;
   g_ts_mon_last_bar_start_us = 0;
   g_ts_mon_total_bar_us = 0;
   g_ts_mon_max_bar_us = 0;
}

void TS_MonitorOnBarBegin()
{
   g_ts_mon_last_bar_start_us = GetMicrosecondCount();
}

void TS_MonitorCountCandidateState()
{
   if(g_ts_current_cand_long == 0 && g_ts_current_cand_short == 0)
      g_ts_mon_cand_00_count++;
   else if(g_ts_current_cand_long == 1 && g_ts_current_cand_short == 0)
      g_ts_mon_cand_10_count++;
   else if(g_ts_current_cand_long == 0 && g_ts_current_cand_short == 1)
      g_ts_mon_cand_01_count++;
   else
      g_ts_mon_cand_other_count++;
}

void TS_MonitorCountGateState()
{
   if(g_ts_gate_pass)
   {
      g_ts_mon_gate_pass_count++;
      return;
   }

   if(g_ts_gate_reject_reason == "")
      return;

   if(StringFind(g_ts_gate_reject_reason, "TIME_BLOCK:") == 0)
      g_ts_mon_gate_reject_time_block_count++;
   else if(StringFind(g_ts_gate_reject_reason, "SPREAD:") == 0)
      g_ts_mon_gate_reject_spread_count++;
   else if(StringFind(g_ts_gate_reject_reason, "ORDER_CONSTRAINT:") == 0)
      g_ts_mon_gate_reject_order_constraint_count++;
   else if(StringFind(g_ts_gate_reject_reason, "GATE_EVAL:") == 0)
      g_ts_mon_gate_reject_gate_eval_count++;
   else
      g_ts_mon_gate_reject_other_count++;
}

void TS_MonitorCountRetcode(const uint retcode)
{
   if(retcode == 0)
   {
      g_ts_mon_retcode_zero_count++;
      return;
   }

   if(retcode == TRADE_RETCODE_DONE)
   {
      g_ts_mon_retcode_done_count++;
      return;
   }

   if(retcode == TRADE_RETCODE_DONE_PARTIAL)
   {
      g_ts_mon_retcode_done_partial_count++;
      return;
   }

   g_ts_mon_retcode_other_count++;
}

void TS_MonitorOnInferenceSkipped()
{
   g_ts_mon_inference_not_ready_count++;
}

void TS_MonitorOnDecisionSkipped()
{
   g_ts_mon_decision_not_ready_count++;
}

void TS_MonitorOnGateSkipped()
{
   g_ts_mon_gate_skipped_count++;
}

void TS_MonitorOnEntryAttempt()
{
   g_ts_mon_entry_attempted_count++;
}

void TS_MonitorOnEntryExecuted(const uint retcode)
{
   g_ts_mon_entry_executed_count++;
   TS_MonitorCountRetcode(retcode);
}

void TS_MonitorOnEntryRejected(const uint retcode)
{
   g_ts_mon_entry_rejected_count++;
   TS_MonitorCountRetcode(retcode);
}

void TS_MonitorOnExitAttempt()
{
   g_ts_mon_exit_attempted_count++;
}

void TS_MonitorOnExitExecuted(const uint retcode)
{
   g_ts_mon_exit_executed_count++;
   TS_MonitorCountRetcode(retcode);
}

void TS_MonitorOnExitRejected(const uint retcode)
{
   g_ts_mon_exit_rejected_count++;
   TS_MonitorCountRetcode(retcode);
}

void TS_MonitorOnEarlyExitEvaluation(const string reason, const bool min_hold_blocked)
{
   g_ts_mon_early_exit_evaluated_count++;
   g_ts_mon_last_early_exit_reason = reason;

   if(reason == "P_EXIT_PASS")
      g_ts_mon_early_exit_reason_pass_count++;
   else if(reason == "OPPOSITE_DIR")
      g_ts_mon_early_exit_reason_opposite_count++;
   else if(reason != "")
      g_ts_mon_early_exit_reason_other_count++;

   if(min_hold_blocked)
      g_ts_mon_early_exit_min_hold_blocked_count++;
}

void TS_MonitorOnEarlyExitAttempt()
{
   g_ts_mon_early_exit_attempted_count++;
}

void TS_MonitorOnEarlyExitExecuted()
{
   g_ts_mon_early_exit_executed_count++;
}

void TS_MonitorOnEarlyExitRejected()
{
   g_ts_mon_early_exit_rejected_count++;
}

void TS_MonitorOnModifyEvaluation(const string reason, const bool min_hold_blocked)
{
   g_ts_mon_modify_evaluated_count++;
   g_ts_mon_last_modify_reason = reason;

   if(reason == "BREAK_EVEN")
      g_ts_mon_modify_reason_break_even_count++;
   else if(reason == "TRAILING")
      g_ts_mon_modify_reason_trailing_count++;
   else if(reason == "TP_RESHAPE")
      g_ts_mon_modify_reason_tp_reshape_count++;
   else if(reason == "TIME_POLICY")
      g_ts_mon_modify_reason_time_policy_count++;
   else if(reason != "")
      g_ts_mon_modify_reason_other_count++;

   if(min_hold_blocked)
      g_ts_mon_modify_min_hold_blocked_count++;
}

void TS_MonitorOnModifyAttempt()
{
   g_ts_mon_modify_attempted_count++;
}

void TS_MonitorOnModifyExecuted()
{
   g_ts_mon_modify_executed_count++;
}

void TS_MonitorOnModifyRejected()
{
   g_ts_mon_modify_rejected_count++;
}

void TS_MonitorOnModifyPendingCleared()
{
   g_ts_mon_modify_pending_cleared_count++;
}

void TS_MonitorOnRuntimeReloadAttempt()
{
   g_ts_mon_runtime_reload_attempt_count++;
}

void TS_MonitorOnRuntimeReloadSuccess()
{
   g_ts_mon_runtime_reload_success_count++;
}

void TS_MonitorOnRuntimeReloadRollback()
{
   g_ts_mon_runtime_reload_rollback_count++;
}

void TS_MonitorOnShadowExitEvaluation(const string reason, const bool triggered, const bool min_hold_blocked)
{
   g_ts_mon_shadow_exit_evaluated_count++;

   if(reason == "P_EXIT_PASS")
      g_ts_mon_shadow_exit_reason_pass_count++;
   else if(reason == "OPPOSITE_DIR")
      g_ts_mon_shadow_exit_reason_opposite_count++;
   else if(reason != "")
      g_ts_mon_shadow_exit_reason_other_count++;

   if(min_hold_blocked)
      g_ts_mon_shadow_exit_min_hold_blocked_count++;

   if(triggered)
      g_ts_mon_shadow_exit_triggered_count++;
}

void TS_MonitorOnHoldSoftReached()
{
   g_ts_mon_hold_soft_reached_count++;
}

void TS_MonitorOnForceExitTriggered()
{
   g_ts_mon_force_exit_count++;
}

void TS_MonitorOnTradeTransactionType(const ENUM_TRADE_TRANSACTION_TYPE type)
{
   switch(type)
   {
      case TRADE_TRANSACTION_REQUEST:
         g_ts_mon_trade_tx_request_count++;
         break;
      case TRADE_TRANSACTION_DEAL_ADD:
         g_ts_mon_trade_tx_deal_add_count++;
         break;
      case TRADE_TRANSACTION_POSITION:
         g_ts_mon_trade_tx_position_count++;
         break;
      default:
         g_ts_mon_trade_tx_other_count++;
         break;
   }
}

string TS_MonitorCompactText(const string value)
{
   string out = value;
   StringReplace(out, " ", "_");
   StringReplace(out, ",", ";");
   StringReplace(out, "[", "(");
   StringReplace(out, "]", ")");
   if(StringLen(out) > 48)
      out = StringSubstr(out, 0, 48);
   if(out == "")
      out = "-";
   return out;
}

string TS_MonitorTradeActionToString(const ENUM_TRADE_REQUEST_ACTIONS action)
{
   switch(action)
   {
      case TRADE_ACTION_DEAL:
         return "DEAL";
      case TRADE_ACTION_PENDING:
         return "PENDING";
      case TRADE_ACTION_SLTP:
         return "SLTP";
      case TRADE_ACTION_MODIFY:
         return "MODIFY";
      case TRADE_ACTION_REMOVE:
         return "REMOVE";
      case TRADE_ACTION_CLOSE_BY:
         return "CLOSE_BY";
      default:
         return "UNKNOWN";
   }
}

void TS_MonitorNoteDirectTradeResult(const string phase, const uint retcode, const string desc, const bool synthetic)
{
   g_ts_mon_last_direct_phase = phase;
   g_ts_mon_last_direct_retcode = retcode;
   g_ts_mon_last_direct_desc = TS_MonitorCompactText(desc);
   g_ts_mon_last_direct_synthetic = synthetic;

   if(StringFind(phase, "ENTRY") == 0)
   {
      g_ts_mon_last_entry_retcode = retcode;
      g_ts_mon_last_entry_desc = g_ts_mon_last_direct_desc;
   }
   else if(StringFind(phase, "EXIT:") == 0)
   {
      g_ts_mon_last_exit_retcode = retcode;
      g_ts_mon_last_exit_desc = g_ts_mon_last_direct_desc;
      g_ts_mon_last_exit_synthetic = synthetic;
   }

   if(retcode != 0 &&
      retcode != TRADE_RETCODE_DONE &&
      retcode != TRADE_RETCODE_DONE_PARTIAL)
   {
      g_ts_mon_last_other_retcode = retcode;
      g_ts_mon_last_other_retcode_desc = g_ts_mon_last_direct_desc;
      g_ts_mon_last_other_retcode_synthetic = synthetic;
   }
}

void TS_MonitorNoteTradeRequestResult(const ENUM_TRADE_REQUEST_ACTIONS action, const uint retcode, const string comment)
{
   g_ts_mon_last_tx_action = TS_MonitorTradeActionToString(action);
   g_ts_mon_last_tx_retcode = retcode;
   g_ts_mon_last_tx_comment = TS_MonitorCompactText(comment);

   if(retcode != 0 &&
      retcode != TRADE_RETCODE_DONE &&
      retcode != TRADE_RETCODE_DONE_PARTIAL)
   {
      g_ts_mon_last_other_retcode = retcode;
      g_ts_mon_last_other_retcode_desc = g_ts_mon_last_tx_comment;
      g_ts_mon_last_other_retcode_synthetic = false;
   }
}

void TS_MonitorEmitSummary(const string tag)
{
   const double avg_bar_us =
      (g_ts_mon_processed_bars > 0)
      ? ((double)g_ts_mon_total_bar_us / (double)g_ts_mon_processed_bars)
      : 0.0;
   const string early_summary = StringFormat(
      "eval:%d attempt:%d exec:%d reject:%d min_hold:%d pass:%d opposite:%d other:%d last:%s",
      g_ts_mon_early_exit_evaluated_count,
      g_ts_mon_early_exit_attempted_count,
      g_ts_mon_early_exit_executed_count,
      g_ts_mon_early_exit_rejected_count,
      g_ts_mon_early_exit_min_hold_blocked_count,
      g_ts_mon_early_exit_reason_pass_count,
      g_ts_mon_early_exit_reason_opposite_count,
      g_ts_mon_early_exit_reason_other_count,
      TS_MonitorCompactText(g_ts_mon_last_early_exit_reason)
   );
   const string modify_summary = StringFormat(
      "eval:%d attempt:%d exec:%d reject:%d min_hold:%d be:%d trail:%d tp:%d time:%d other:%d cleared:%d last:%s",
      g_ts_mon_modify_evaluated_count,
      g_ts_mon_modify_attempted_count,
      g_ts_mon_modify_executed_count,
      g_ts_mon_modify_rejected_count,
      g_ts_mon_modify_min_hold_blocked_count,
      g_ts_mon_modify_reason_break_even_count,
      g_ts_mon_modify_reason_trailing_count,
      g_ts_mon_modify_reason_tp_reshape_count,
      g_ts_mon_modify_reason_time_policy_count,
      g_ts_mon_modify_reason_other_count,
      g_ts_mon_modify_pending_cleared_count,
      TS_MonitorCompactText(g_ts_mon_last_modify_reason)
   );
   const string runtime_summary = StringFormat(
      "attempt:%d success:%d rollback:%d",
      g_ts_mon_runtime_reload_attempt_count,
      g_ts_mon_runtime_reload_success_count,
      g_ts_mon_runtime_reload_rollback_count
   );
   const string shadow_summary = StringFormat(
      "eval:%d trig:%d min_hold:%d pass:%d opposite:%d other:%d",
      g_ts_mon_shadow_exit_evaluated_count,
      g_ts_mon_shadow_exit_triggered_count,
      g_ts_mon_shadow_exit_min_hold_blocked_count,
      g_ts_mon_shadow_exit_reason_pass_count,
      g_ts_mon_shadow_exit_reason_opposite_count,
      g_ts_mon_shadow_exit_reason_other_count
   );
   const string diag_summary = StringFormat(
      "entry:%u/%s_exit:%u/%s_exit_synth:%s_tx:%s/%u/%s_other:%u/%s_other_synth:%s",
      g_ts_mon_last_entry_retcode,
      g_ts_mon_last_entry_desc,
      g_ts_mon_last_exit_retcode,
      g_ts_mon_last_exit_desc,
      g_ts_mon_last_exit_synthetic ? "true" : "false",
      TS_MonitorCompactText(g_ts_mon_last_tx_action),
      g_ts_mon_last_tx_retcode,
      g_ts_mon_last_tx_comment,
      g_ts_mon_last_other_retcode,
      g_ts_mon_last_other_retcode_desc,
      g_ts_mon_last_other_retcode_synthetic ? "true" : "false"
   );

   PrintFormat(
      "[TS][MON][%s] bars=%d cand=[00:%d 10:%d 01:%d other:%d] regime=[%d,%d,%d,%d,%d,%d] final=[PASS:%d LONG:%d SHORT:%d] flip=%d gate_pass=%d gate_reject=[TIME_BLOCK:%d SPREAD:%d ORDER_CONSTRAINT:%d GATE_EVAL:%d OTHER:%d] gate_skipped=%d stage_not_ready=[infer:%d decision:%d] entry=[attempt:%d exec:%d reject:%d] exit=[attempt:%d exec:%d reject:%d] retcode=[done:%d partial:%d zero:%d other:%d] tx=[request:%d deal_add:%d position:%d other:%d] diag=[%s] early=[%s] modify=[%s] runtime_reload=[%s] shadow=[%s] hold_soft=%d force_exit=%d soft_total=%d last_soft=%s sticky_soft=%s bar_us=[avg:%.2f max:%I64u]",
      tag,
      g_ts_mon_processed_bars,
      g_ts_mon_cand_00_count,
      g_ts_mon_cand_10_count,
      g_ts_mon_cand_01_count,
      g_ts_mon_cand_other_count,
      g_ts_mon_regime_count[0],
      g_ts_mon_regime_count[1],
      g_ts_mon_regime_count[2],
      g_ts_mon_regime_count[3],
      g_ts_mon_regime_count[4],
      g_ts_mon_regime_count[5],
      g_ts_mon_final_dir_count[2],
      g_ts_mon_final_dir_count[0],
      g_ts_mon_final_dir_count[1],
      g_ts_mon_flip_used_count,
      g_ts_mon_gate_pass_count,
      g_ts_mon_gate_reject_time_block_count,
      g_ts_mon_gate_reject_spread_count,
      g_ts_mon_gate_reject_order_constraint_count,
      g_ts_mon_gate_reject_gate_eval_count,
      g_ts_mon_gate_reject_other_count,
      g_ts_mon_gate_skipped_count,
      g_ts_mon_inference_not_ready_count,
      g_ts_mon_decision_not_ready_count,
      g_ts_mon_entry_attempted_count,
      g_ts_mon_entry_executed_count,
      g_ts_mon_entry_rejected_count,
      g_ts_mon_exit_attempted_count,
      g_ts_mon_exit_executed_count,
      g_ts_mon_exit_rejected_count,
      g_ts_mon_retcode_done_count,
      g_ts_mon_retcode_done_partial_count,
      g_ts_mon_retcode_zero_count,
      g_ts_mon_retcode_other_count,
      g_ts_mon_trade_tx_request_count,
      g_ts_mon_trade_tx_deal_add_count,
      g_ts_mon_trade_tx_position_count,
      g_ts_mon_trade_tx_other_count,
      diag_summary,
      early_summary,
      modify_summary,
      runtime_summary,
      shadow_summary,
      g_ts_mon_hold_soft_reached_count,
      g_ts_mon_force_exit_count,
      g_ts_soft_fault_count_total,
      TS_PassReasonToString(g_ts_last_soft_fault_reason),
      TS_PassReasonToString(g_ts_mon_last_non_none_soft_fault_reason),
      avg_bar_us,
      g_ts_mon_max_bar_us
   );
}

void TS_MonitorOnBarEnd(const int regime_id)
{
   const ulong end_us = GetMicrosecondCount();
   const ulong elapsed_us =
      (end_us >= g_ts_mon_last_bar_start_us)
      ? (end_us - g_ts_mon_last_bar_start_us)
      : 0;

   g_ts_mon_processed_bars++;
   g_ts_mon_total_bar_us += elapsed_us;
   if(elapsed_us > g_ts_mon_max_bar_us)
      g_ts_mon_max_bar_us = elapsed_us;

   TS_MonitorCountCandidateState();

   if(regime_id >= 0 && regime_id < TS_REGIME_COUNT)
      g_ts_mon_regime_count[regime_id]++;

   if(g_ts_final_dir >= 0 && g_ts_final_dir <= 2)
      g_ts_mon_final_dir_count[g_ts_final_dir]++;

   if(g_ts_flip_used)
      g_ts_mon_flip_used_count++;

   TS_MonitorCountGateState();

   if(g_ts_last_soft_fault_reason != TS_PASS_REASON_NONE)
      g_ts_mon_last_non_none_soft_fault_reason = g_ts_last_soft_fault_reason;

   if(g_ts_mon_processed_bars % TS_MONITOR_EMIT_EVERY_BARS == 0)
      TS_MonitorEmitSummary("periodic");
}

#endif // __TS_MONITOR_MQH__
