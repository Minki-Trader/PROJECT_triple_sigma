#ifndef __TS_EXECUTION_MQH__
#define __TS_EXECUTION_MQH__

#include <Trade/Trade.mqh>

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"
#include "TS_DataIngest.mqh"
#include "TS_Indicators.mqh"
#include "TS_PackMeta.mqh"
#include "TS_Candidate.mqh"
#include "TS_Features.mqh"
#include "TS_Models.mqh"
#include "TS_Decision.mqh"
#include "TS_Gates.mqh"

void TS_MonitorOnHoldSoftReached();
void TS_MonitorOnForceExitTriggered();
void TS_MonitorOnInferenceSkipped();
void TS_MonitorOnDecisionSkipped();
void TS_MonitorOnGateSkipped();
void TS_MonitorOnEntryAttempt();
void TS_MonitorOnEntryExecuted(const uint retcode);
void TS_MonitorOnEntryRejected(const uint retcode);
void TS_MonitorOnExitAttempt();
void TS_MonitorOnExitExecuted(const uint retcode);
void TS_MonitorOnExitRejected(const uint retcode);
void TS_MonitorOnEarlyExitEvaluation(const string reason, const bool min_hold_blocked);
void TS_MonitorOnEarlyExitAttempt();
void TS_MonitorOnEarlyExitExecuted();
void TS_MonitorOnEarlyExitRejected();
void TS_MonitorOnModifyEvaluation(const string reason, const bool min_hold_blocked);
void TS_MonitorOnModifyAttempt();
void TS_MonitorOnModifyExecuted();
void TS_MonitorOnModifyRejected();
void TS_MonitorOnModifyPendingCleared();
void TS_MonitorOnRuntimeReloadAttempt();
void TS_MonitorOnRuntimeReloadSuccess();
void TS_MonitorOnRuntimeReloadRollback();
void TS_MonitorOnShadowExitEvaluation(const string reason, const bool triggered, const bool min_hold_blocked);
void TS_MonitorOnTradeTransactionType(const ENUM_TRADE_TRANSACTION_TYPE type);
void TS_MonitorNoteDirectTradeResult(const string phase, const uint retcode, const string desc, const bool synthetic);
void TS_MonitorNoteTradeRequestResult(const ENUM_TRADE_REQUEST_ACTIONS action, const uint retcode, const string comment);
void TS_WriteTradeEntryLog(const ulong deal_ticket, const string tx_authority);
void TS_WriteTradeExitLog(const string exit_reason, const string event_detail, const ulong deal_ticket, const double exit_price, const double pnl, const string tx_authority);
void TS_WriteTradeModifyLog(const string modify_reason, const string event_detail, const ulong deal_ticket, const double new_sl, const double new_tp, const string tx_authority);
void TS_WriteBrokerAuditLog(const string tag, const string detail);
bool TS_ModifyPositionByReason(const string modify_reason, const double new_sl, const double new_tp);

enum ENUM_TS_EXEC_TEST_RECOVERY_RELOAD_MODE
{
   TS_EXEC_TEST_RECOVERY_RELOAD_DISABLED = 0,
   TS_EXEC_TEST_RECOVERY_RELOAD_OPEN_POSITION = 1,
   TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_EXIT = 2,
   TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_MODIFY = 3
};

struct TS_ExecPassOnlySnapshot
{
   bool latched;
   ENUM_TS_PASS_ONLY_REASON reason;
   string detail;
   int soft_total;
   int soft_streak;
   ENUM_TS_PASS_ONLY_REASON last_soft_reason;
};

struct TS_ExecPackMetaSnapshot
{
   TS_PackMetaRecord record;
   bool ready;
   string relpath;
};

struct TS_ExecGateSnapshot
{
   bool config_loaded;
   double spread_atr_max_base;
   double spread_atr_max_hard;
   double k_tp_scale_min;
   double k_tp_scale_max;
   int dev_points_base;
   int dev_points_add_max;
   int dev_points_hard_max;
   double risk_pct_base;
   double risk_pct_hard_min;
   double risk_pct_hard_max;
};

struct TS_ExecScalerSnapshot
{
   bool ready;
   string mode;
   double mean[12];
   double std[12];
};

CTrade g_ts_trade;

bool g_ts_exec_has_position = false;
int g_ts_exec_direction = -1; // 0=LONG 1=SHORT
ulong g_ts_exec_ticket = 0;
long g_ts_exec_position_id = 0;
datetime g_ts_exec_entry_time = 0;
datetime g_ts_exec_entry_bar_time = 0;
double g_ts_exec_entry_price = 0.0;
double g_ts_exec_sl_price = 0.0;
double g_ts_exec_tp_price = 0.0;
double g_ts_exec_lot = 0.0;
int g_ts_exec_bars_held = 0;
int g_ts_exec_hold_bars_soft = TS_PASS_DEFAULT_HOLD_BARS;
double g_ts_exec_k_sl_req = 0.0;
double g_ts_exec_k_tp_req = 0.0;
double g_ts_exec_k_sl_eff = 0.0;
double g_ts_exec_k_tp_eff = 0.0;
int g_ts_exec_regime_id_at_entry = -1;
double g_ts_exec_spread_atr_at_entry = 0.0;
bool g_ts_exec_flip_used_at_entry = false;
string g_ts_exec_pack_ver_at_entry = "";
string g_ts_exec_clf_ver_at_entry = "";
string g_ts_exec_prm_ver_at_entry = "";
string g_ts_exec_cost_ver_at_entry = "";
string g_ts_exec_pack_dir_at_entry = "";
string g_ts_exec_last_exit_reason = "";
string g_ts_exec_last_modify_reason = "";
int g_ts_exec_trade_counter = 0;
int g_ts_exec_trade_seq = 0;
string g_ts_exec_trade_id = "";
int g_ts_exec_modify_count = 0;
datetime g_ts_exec_last_modify_time = 0;
string g_ts_exec_pending_exit_reason = "";
ulong g_ts_exec_pending_exit_deal = 0;
double g_ts_exec_pending_exit_price_hint = 0.0;
string g_ts_exec_pending_modify_reason = "";
double g_ts_exec_pending_modify_sl_hint = 0.0;
double g_ts_exec_pending_modify_tp_hint = 0.0;
double g_ts_exec_initial_sl_price = 0.0;
double g_ts_exec_initial_tp_price = 0.0;
bool g_ts_exec_be_applied = false;
bool g_ts_exec_entry_log_emitted = false;
bool g_ts_exec_exited_this_bar = false;
bool g_ts_exec_block_next_entry_bar = false;
bool g_ts_exec_timer_cycle_active = false;
bool g_ts_exec_early_exit_attempted_this_bar = false;
bool g_ts_exec_state_dirty = false;
bool g_ts_exec_tx_authority_enabled = false;
bool g_ts_exec_broker_audit_enabled = false;
bool g_ts_exec_runtime_hot_reload_enabled = false;
bool g_ts_exec_runtime_rollback_on_fail = true;
string g_ts_exec_runtime_patch_file = "";
string g_ts_exec_active_model_pack_dir = "";
string g_ts_exec_last_runtime_patch_revision = "";
int g_ts_exec_runtime_reload_attempts = 0;
int g_ts_exec_runtime_reload_successes = 0;
int g_ts_exec_runtime_reload_rollbacks = 0;
string g_ts_exec_last_runtime_reload_status = "";
ulong g_ts_exec_last_exit_deal_logged = 0;
bool g_ts_exec_test_early_exit_reject_once_enabled = false;
bool g_ts_exec_test_early_exit_reject_once_consumed = false;
bool g_ts_exec_test_force_opposite_early_exit_enabled = false;
bool g_ts_exec_test_force_break_even_once_enabled = false;
bool g_ts_exec_test_force_break_even_once_consumed = false;
bool g_ts_exec_test_modify_reject_once_enabled = false;
bool g_ts_exec_test_modify_reject_once_consumed = false;
bool g_ts_exec_test_recovery_reload_enabled = false;
int g_ts_exec_test_recovery_reload_mode = TS_EXEC_TEST_RECOVERY_RELOAD_DISABLED;
int g_ts_exec_test_recovery_reload_bars_held = 0;
bool g_ts_exec_test_recovery_reload_completed = false;

bool TS_ExecIsFiniteValue(const double value)
{
   return MathIsValidNumber(value) && (MathAbs(value) < (EMPTY_VALUE / 2.0));
}

string TS_ExecStateRelPath()
{
   return TS_LOG_DIR + "\\exec_state.ini";
}

string TS_ExecStateTempRelPath()
{
   return TS_LOG_DIR + "\\exec_state.tmp";
}

string TS_ExecTradeActionToString(const ENUM_TRADE_REQUEST_ACTIONS action)
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

string TS_ExecTestRecoveryReloadModeToString(const int mode)
{
   switch(mode)
   {
      case TS_EXEC_TEST_RECOVERY_RELOAD_OPEN_POSITION:
         return "OPEN_POSITION";
      case TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_EXIT:
         return "PENDING_EXIT";
      case TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_MODIFY:
         return "PENDING_MODIFY";
      default:
         return "DISABLED";
   }
}

void TS_ExecConfigureTestRecoveryReload(const bool enabled, const int mode, const int bars_held)
{
   g_ts_exec_test_recovery_reload_enabled = enabled;
   g_ts_exec_test_recovery_reload_mode = mode;
   g_ts_exec_test_recovery_reload_bars_held = MathMax(0, bars_held);
   g_ts_exec_test_recovery_reload_completed = false;
}

void TS_ExecConfigureTestEarlyExitRejectOnce(const bool enabled)
{
   const bool tester_mode = (MQLInfoInteger(MQL_TESTER) != 0);
   g_ts_exec_test_early_exit_reject_once_enabled = (enabled && tester_mode);
   g_ts_exec_test_early_exit_reject_once_consumed = false;
}

void TS_ExecConfigureTestForceOppositeEarlyExit(const bool enabled)
{
   const bool tester_mode = (MQLInfoInteger(MQL_TESTER) != 0);
   g_ts_exec_test_force_opposite_early_exit_enabled = (enabled && tester_mode);
}

void TS_ExecConfigureTestForceBreakEvenOnce(const bool enabled)
{
   const bool tester_mode = (MQLInfoInteger(MQL_TESTER) != 0);
   g_ts_exec_test_force_break_even_once_enabled = (enabled && tester_mode);
   g_ts_exec_test_force_break_even_once_consumed = false;
}

void TS_ExecConfigureTestModifyRejectOnce(const bool enabled)
{
   const bool tester_mode = (MQLInfoInteger(MQL_TESTER) != 0);
   g_ts_exec_test_modify_reject_once_enabled = (enabled && tester_mode);
   g_ts_exec_test_modify_reject_once_consumed = false;
}

void TS_ExecConfigureTxAuthority(const bool enabled)
{
   g_ts_exec_tx_authority_enabled = enabled;
}

void TS_ExecConfigureBrokerAudit(const bool enabled)
{
   g_ts_exec_broker_audit_enabled = enabled;
}

void TS_ExecConfigureRuntimeHotReload(
   const bool enabled,
   const bool rollback_on_fail,
   const string patch_file,
   const string initial_model_pack_dir
)
{
   g_ts_exec_runtime_hot_reload_enabled = enabled;
   g_ts_exec_runtime_rollback_on_fail = rollback_on_fail;
   g_ts_exec_runtime_patch_file = TS_PM_Trim(patch_file);
   if(g_ts_exec_active_model_pack_dir == "")
      g_ts_exec_active_model_pack_dir = TS_PM_Trim(initial_model_pack_dir);
   if(g_ts_exec_last_runtime_reload_status == "")
      g_ts_exec_last_runtime_reload_status = "INIT";
}

bool TS_ExecConsumeTestEarlyExitRejectOnce()
{
   if(!g_ts_exec_test_early_exit_reject_once_enabled)
      return false;
   if(g_ts_exec_test_early_exit_reject_once_consumed)
      return false;

   g_ts_exec_test_early_exit_reject_once_consumed = true;
   return true;
}

bool TS_ExecConsumeTestModifyRejectOnce()
{
   if(!g_ts_exec_test_modify_reject_once_enabled)
      return false;
   if(g_ts_exec_test_modify_reject_once_consumed)
      return false;

   g_ts_exec_test_modify_reject_once_consumed = true;
   return true;
}

bool TS_ExecShouldForceBreakEvenOnce()
{
   return (g_ts_exec_test_force_break_even_once_enabled &&
           !g_ts_exec_test_force_break_even_once_consumed);
}

void TS_ExecMarkForceBreakEvenOnceConsumed()
{
   g_ts_exec_test_force_break_even_once_consumed = true;
}

bool TS_ExecRunTestRecoveryProbe(const int checkpoint_mode, const string detail)
{
   if(!g_ts_exec_test_recovery_reload_enabled)
      return false;
   if(g_ts_exec_test_recovery_reload_mode != checkpoint_mode)
      return false;
   if(g_ts_exec_test_recovery_reload_completed)
      return false;

   PrintFormat(
      "[TS][TEST][RECOVERY] probe_begin mode=%s trade_id=%s trade_counter=%d bars_held=%d pending_exit_reason=%s pending_modify_reason=%s detail=%s",
      TS_ExecTestRecoveryReloadModeToString(checkpoint_mode),
      g_ts_exec_trade_id,
      g_ts_exec_trade_counter,
      g_ts_exec_bars_held,
      g_ts_exec_pending_exit_reason,
      g_ts_exec_pending_modify_reason,
      detail
   );

   TS_ResetExecutionState();
   TS_LoadPersistedExecutionState();
   TS_SyncPositionState();
   g_ts_exec_test_recovery_reload_completed = true;
   PrintFormat(
      "[TS][TEST][RECOVERY] probe_complete mode=%s has_position=%s trade_id=%s trade_counter=%d bars_held=%d pending_exit_reason=%s pending_modify_reason=%s exited_this_bar=%s",
      TS_ExecTestRecoveryReloadModeToString(checkpoint_mode),
      g_ts_exec_has_position ? "true" : "false",
      g_ts_exec_trade_id,
      g_ts_exec_trade_counter,
      g_ts_exec_bars_held,
      g_ts_exec_pending_exit_reason,
      g_ts_exec_pending_modify_reason,
      g_ts_exec_exited_this_bar ? "true" : "false"
   );
   return true;
}

bool TS_ExecValidateRelativeFilePath(const string rel_path, string &detail)
{
   const string trimmed = TS_PM_Trim(rel_path);
   if(trimmed == "")
   {
      detail = "path is empty";
      return false;
   }

   if(StringFind(trimmed, "..") >= 0)
   {
      detail = StringFormat("path traversal rejected path=%s", trimmed);
      return false;
   }

   if(StringFind(trimmed, ":") >= 0)
   {
      detail = StringFormat("drive prefix rejected path=%s", trimmed);
      return false;
   }

   const string first = StringSubstr(trimmed, 0, 1);
   if(first == "\\" || first == "/")
   {
      detail = StringFormat("absolute-like path rejected path=%s", trimmed);
      return false;
   }

   detail = "";
   return true;
}

void TS_ExecCapturePassOnlySnapshot(TS_ExecPassOnlySnapshot &snapshot)
{
   snapshot.latched = g_ts_pass_only_latched;
   snapshot.reason = g_ts_pass_only_reason;
   snapshot.detail = g_ts_pass_only_detail;
   snapshot.soft_total = g_ts_soft_fault_count_total;
   snapshot.soft_streak = g_ts_soft_fault_streak_current;
   snapshot.last_soft_reason = g_ts_last_soft_fault_reason;
}

void TS_ExecRestorePassOnlySnapshot(const TS_ExecPassOnlySnapshot &snapshot)
{
   g_ts_pass_only_latched = snapshot.latched;
   g_ts_pass_only_reason = snapshot.reason;
   g_ts_pass_only_detail = snapshot.detail;
   g_ts_soft_fault_count_total = snapshot.soft_total;
   g_ts_soft_fault_streak_current = snapshot.soft_streak;
   g_ts_last_soft_fault_reason = snapshot.last_soft_reason;
}

void TS_ExecCapturePackMetaSnapshot(TS_ExecPackMetaSnapshot &snapshot)
{
   snapshot.record = g_ts_pack_meta;
   snapshot.ready = g_ts_pack_meta_ready;
   snapshot.relpath = g_ts_pack_meta_relpath;
}

void TS_ExecRestorePackMetaSnapshot(const TS_ExecPackMetaSnapshot &snapshot)
{
   g_ts_pack_meta = snapshot.record;
   g_ts_pack_meta_ready = snapshot.ready;
   g_ts_pack_meta_relpath = snapshot.relpath;
}

void TS_ExecCaptureGateSnapshot(TS_ExecGateSnapshot &snapshot)
{
   snapshot.config_loaded = g_ts_gate_config_loaded;
   snapshot.spread_atr_max_base = g_ts_gc_spread_atr_max_base;
   snapshot.spread_atr_max_hard = g_ts_gc_spread_atr_max_hard;
   snapshot.k_tp_scale_min = g_ts_gc_k_tp_scale_min;
   snapshot.k_tp_scale_max = g_ts_gc_k_tp_scale_max;
   snapshot.dev_points_base = g_ts_gc_dev_points_base;
   snapshot.dev_points_add_max = g_ts_gc_dev_points_add_max;
   snapshot.dev_points_hard_max = g_ts_gc_dev_points_hard_max;
   snapshot.risk_pct_base = g_ts_gc_risk_pct_base;
   snapshot.risk_pct_hard_min = g_ts_gc_risk_pct_hard_min;
   snapshot.risk_pct_hard_max = g_ts_gc_risk_pct_hard_max;
}

void TS_ExecRestoreGateSnapshot(const TS_ExecGateSnapshot &snapshot)
{
   g_ts_gate_config_loaded = snapshot.config_loaded;
   g_ts_gc_spread_atr_max_base = snapshot.spread_atr_max_base;
   g_ts_gc_spread_atr_max_hard = snapshot.spread_atr_max_hard;
   g_ts_gc_k_tp_scale_min = snapshot.k_tp_scale_min;
   g_ts_gc_k_tp_scale_max = snapshot.k_tp_scale_max;
   g_ts_gc_dev_points_base = snapshot.dev_points_base;
   g_ts_gc_dev_points_add_max = snapshot.dev_points_add_max;
   g_ts_gc_dev_points_hard_max = snapshot.dev_points_hard_max;
   g_ts_gc_risk_pct_base = snapshot.risk_pct_base;
   g_ts_gc_risk_pct_hard_min = snapshot.risk_pct_hard_min;
   g_ts_gc_risk_pct_hard_max = snapshot.risk_pct_hard_max;
}

void TS_ExecCaptureScalerSnapshot(TS_ExecScalerSnapshot &snapshot)
{
   snapshot.ready = g_ts_scaler_ready;
   snapshot.mode = g_ts_scaler_mode;
   for(int i = 0; i < 12; ++i)
   {
      snapshot.mean[i] = g_ts_scaler_mean[i];
      snapshot.std[i] = g_ts_scaler_std[i];
   }
}

void TS_ExecRestoreScalerSnapshot(const TS_ExecScalerSnapshot &snapshot)
{
   g_ts_scaler_ready = snapshot.ready;
   g_ts_scaler_mode = snapshot.mode;
   for(int i = 0; i < 12; ++i)
   {
      g_ts_scaler_mean[i] = snapshot.mean[i];
      g_ts_scaler_std[i] = snapshot.std[i];
   }
}

void TS_ExecSetRuntimeReloadStatus(const string status)
{
   if(g_ts_exec_last_runtime_reload_status == status)
      return;

   g_ts_exec_last_runtime_reload_status = status;
   TS_ExecMarkStateDirty();
}

string TS_ExecRuntimeReloadFailureDetail()
{
   if(g_ts_pass_only_detail != "")
      return g_ts_pass_only_detail;

   return TS_PassReasonToString(g_ts_pass_only_reason);
}

bool TS_ExecLoadRuntimePatchSpec(
   const string rel_path,
   string &revision,
   string &model_pack_dir,
   bool &force_fail,
   string &detail
)
{
   revision = "";
   model_pack_dir = "";
   force_fail = false;
   detail = "";

   string path_detail = "";
   if(!TS_ExecValidateRelativeFilePath(rel_path, path_detail))
   {
      detail = path_detail;
      return false;
   }

   ResetLastError();
   const int handle = FileOpen(rel_path, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      detail = StringFormat("patch open failed path=%s err=%d", rel_path, GetLastError());
      return false;
   }

   while(!FileIsEnding(handle))
   {
      string line = TS_PM_Trim(FileReadString(handle));
      line = TS_PM_StripBom(line);
      if(line == "")
         continue;

      const string first = StringSubstr(line, 0, 1);
      if(first == "#" || first == ";")
         continue;

      const int eq_pos = StringFind(line, "=");
      if(eq_pos <= 0)
         continue;

      string key = TS_PM_Trim(StringSubstr(line, 0, eq_pos));
      key = TS_PM_StripBom(key);
      StringToLower(key);
      const string value = TS_PM_Trim(StringSubstr(line, eq_pos + 1));

      if(key == "revision")
         revision = value;
      else if(key == "model_pack_dir")
         model_pack_dir = value;
      else if(key == "force_fail")
         force_fail = (StringToInteger(value) != 0);
   }

   FileClose(handle);

   if(revision == "")
   {
      detail = StringFormat("revision missing path=%s", rel_path);
      return false;
   }

   string pack_detail = "";
   if(!TS_PM_ValidateModelPackDir(model_pack_dir, pack_detail))
   {
      detail = pack_detail;
      return false;
   }

   return true;
}

bool TS_ExecReloadRuntimeModelSurface(const string model_pack_dir, string &detail)
{
   detail = "";
   const string trimmed_dir = TS_PM_Trim(model_pack_dir);
   string pack_detail = "";
   if(!TS_PM_ValidateModelPackDir(trimmed_dir, pack_detail))
   {
      detail = pack_detail;
      return false;
   }

   if(!TS_LoadPackMeta(trimmed_dir))
   {
      detail = "pack_meta:" + TS_ExecRuntimeReloadFailureDetail();
      return false;
   }

   if(!TS_LoadScaler(trimmed_dir))
   {
      detail = "scaler:" + TS_ExecRuntimeReloadFailureDetail();
      return false;
   }

   if(!TS_LoadGateConfig(trimmed_dir))
   {
      detail = "gate:" + TS_ExecRuntimeReloadFailureDetail();
      return false;
   }

   if(!TS_LoadModels(trimmed_dir))
   {
      detail = "models:" + TS_ExecRuntimeReloadFailureDetail();
      return false;
   }

   g_ts_exec_active_model_pack_dir = trimmed_dir;
   TS_ExecMarkStateDirty();
   return true;
}

void TS_ExecMaybeApplyRuntimePatch()
{
   if(!g_ts_exec_runtime_hot_reload_enabled)
      return;
   if(TS_IsPassOnlyLatched())
      return;

   const string rel_path = TS_PM_Trim(g_ts_exec_runtime_patch_file);
   if(rel_path == "")
      return;
   if(!FileIsExist(rel_path))
      return;

   string revision = "";
   string target_model_pack_dir = "";
   bool force_fail = false;
   string patch_detail = "";
   if(!TS_ExecLoadRuntimePatchSpec(rel_path, revision, target_model_pack_dir, force_fail, patch_detail))
   {
      TS_ExecSetRuntimeReloadStatus("PATCH_INVALID");
      if(g_ts_exec_broker_audit_enabled)
         TS_WriteBrokerAuditLog("runtime_patch_invalid", patch_detail);
      return;
   }

   if(revision == g_ts_exec_last_runtime_patch_revision)
      return;

   TS_ExecPassOnlySnapshot pass_snapshot;
   TS_ExecPackMetaSnapshot pack_snapshot;
   TS_ExecGateSnapshot gate_snapshot;
   TS_ExecScalerSnapshot scaler_snapshot;
   TS_ExecCapturePassOnlySnapshot(pass_snapshot);
   TS_ExecCapturePackMetaSnapshot(pack_snapshot);
   TS_ExecCaptureGateSnapshot(gate_snapshot);
   TS_ExecCaptureScalerSnapshot(scaler_snapshot);
   const string previous_model_pack_dir = g_ts_exec_active_model_pack_dir;

   g_ts_exec_runtime_reload_attempts++;
   g_ts_exec_last_runtime_patch_revision = revision;
   TS_ExecSetRuntimeReloadStatus("APPLYING");
   TS_MonitorOnRuntimeReloadAttempt();
   if(g_ts_exec_broker_audit_enabled)
      TS_WriteBrokerAuditLog(
         "runtime_reload_attempt",
         StringFormat("revision=%s target=%s force_fail=%s", revision, target_model_pack_dir, force_fail ? "true" : "false")
      );

   string reload_detail = "";
   bool reload_ok = TS_ExecReloadRuntimeModelSurface(target_model_pack_dir, reload_detail);
   if(reload_ok && force_fail)
   {
      reload_ok = false;
      reload_detail = "forced_failure_after_reload";
   }

   if(reload_ok)
   {
      g_ts_exec_runtime_reload_successes++;
      TS_ExecSetRuntimeReloadStatus("RELOADED");
      TS_MonitorOnRuntimeReloadSuccess();
      if(g_ts_exec_broker_audit_enabled)
         TS_WriteBrokerAuditLog(
            "runtime_reload_success",
            StringFormat("revision=%s active=%s", revision, g_ts_exec_active_model_pack_dir)
         );
      TS_SavePersistedExecutionStateIfDirty();
      return;
   }

   if(!g_ts_exec_runtime_rollback_on_fail)
   {
      TS_ExecSetRuntimeReloadStatus("FAILED");
      if(g_ts_exec_broker_audit_enabled)
         TS_WriteBrokerAuditLog(
            "runtime_reload_failed",
            StringFormat("revision=%s detail=%s rollback=false", revision, reload_detail)
         );
      TS_SavePersistedExecutionStateIfDirty();
      return;
   }

   TS_ExecRestorePackMetaSnapshot(pack_snapshot);
   TS_ExecRestoreGateSnapshot(gate_snapshot);
   TS_ExecRestoreScalerSnapshot(scaler_snapshot);

   string rollback_detail = "";
   bool rollback_ok = true;
   if(previous_model_pack_dir != "")
   {
      if(!TS_ExecReloadRuntimeModelSurface(previous_model_pack_dir, rollback_detail))
         rollback_ok = false;
   }

   if(rollback_ok)
   {
      TS_ExecRestorePassOnlySnapshot(pass_snapshot);
      g_ts_exec_runtime_reload_rollbacks++;
      TS_ExecSetRuntimeReloadStatus("ROLLED_BACK");
      TS_MonitorOnRuntimeReloadRollback();
      if(g_ts_exec_broker_audit_enabled)
         TS_WriteBrokerAuditLog(
            "runtime_reload_rollback",
            StringFormat("revision=%s detail=%s restored=%s", revision, reload_detail, previous_model_pack_dir)
         );
   }
   else
   {
      TS_ExecSetRuntimeReloadStatus("ROLLBACK_FAILED");
      if(g_ts_exec_broker_audit_enabled)
         TS_WriteBrokerAuditLog(
            "runtime_reload_rollback_failed",
            StringFormat("revision=%s reload_detail=%s rollback_detail=%s", revision, reload_detail, rollback_detail)
         );
   }

   TS_SavePersistedExecutionStateIfDirty();
}

bool TS_ExecEnsureLogDir()
{
   ResetLastError();
   FolderCreate(TS_LOG_DIR);
   return true;
}

void TS_ExecWriteStateLine(const int handle, const string key, const string value)
{
   FileWriteString(handle, key + "=" + value + "\r\n");
}

void TS_ClearExecutionPositionState()
{
   g_ts_exec_has_position = false;
   g_ts_exec_direction = -1;
   g_ts_exec_ticket = 0;
   g_ts_exec_position_id = 0;
   g_ts_exec_entry_time = 0;
   g_ts_exec_entry_bar_time = 0;
   g_ts_exec_entry_price = 0.0;
   g_ts_exec_sl_price = 0.0;
   g_ts_exec_tp_price = 0.0;
   g_ts_exec_lot = 0.0;
   g_ts_exec_bars_held = 0;
   g_ts_exec_hold_bars_soft = TS_PASS_DEFAULT_HOLD_BARS;
   g_ts_exec_k_sl_req = 0.0;
   g_ts_exec_k_tp_req = 0.0;
   g_ts_exec_k_sl_eff = 0.0;
   g_ts_exec_k_tp_eff = 0.0;
   g_ts_exec_regime_id_at_entry = -1;
   g_ts_exec_spread_atr_at_entry = 0.0;
   g_ts_exec_flip_used_at_entry = false;
   g_ts_exec_pack_ver_at_entry = "";
   g_ts_exec_clf_ver_at_entry = "";
   g_ts_exec_prm_ver_at_entry = "";
   g_ts_exec_cost_ver_at_entry = "";
   g_ts_exec_pack_dir_at_entry = "";
   g_ts_exec_last_modify_reason = "";
   g_ts_exec_trade_seq = 0;
   g_ts_exec_trade_id = "";
   g_ts_exec_modify_count = 0;
   g_ts_exec_last_modify_time = 0;
   g_ts_exec_pending_exit_reason = "";
   g_ts_exec_pending_exit_deal = 0;
   g_ts_exec_pending_exit_price_hint = 0.0;
   g_ts_exec_pending_modify_reason = "";
   g_ts_exec_pending_modify_sl_hint = 0.0;
   g_ts_exec_pending_modify_tp_hint = 0.0;
   g_ts_exec_initial_sl_price = 0.0;
   g_ts_exec_initial_tp_price = 0.0;
   g_ts_exec_be_applied = false;
   g_ts_exec_entry_log_emitted = false;
   g_ts_exec_state_dirty = true;
}

void TS_ResetExecutionState()
{
   g_ts_exec_trade_counter = 0;
   g_ts_exec_last_exit_reason = "";
   g_ts_exec_last_runtime_patch_revision = "";
   g_ts_exec_runtime_reload_attempts = 0;
   g_ts_exec_runtime_reload_successes = 0;
   g_ts_exec_runtime_reload_rollbacks = 0;
   g_ts_exec_last_runtime_reload_status = "";
   g_ts_exec_last_exit_deal_logged = 0;
   g_ts_exec_exited_this_bar = false;
   g_ts_exec_block_next_entry_bar = false;
   g_ts_exec_timer_cycle_active = false;
   g_ts_exec_early_exit_attempted_this_bar = false;
   TS_ClearExecutionPositionState();
}

void TS_ExecOnBarCycleBegin()
{
   g_ts_exec_timer_cycle_active = true;
}

void TS_ExecOnBarCycleEnd()
{
   g_ts_exec_timer_cycle_active = false;
}

void TS_ResetExecutionBarState()
{
   g_ts_exec_exited_this_bar = g_ts_exec_block_next_entry_bar;
   g_ts_exec_block_next_entry_bar = false;
   g_ts_exec_early_exit_attempted_this_bar = false;
   if(!g_ts_exec_has_position)
   {
      g_ts_exec_k_sl_req = 0.0;
      g_ts_exec_k_tp_req = 0.0;
      g_ts_exec_k_sl_eff = 0.0;
      g_ts_exec_k_tp_eff = 0.0;
      g_ts_exec_hold_bars_soft = TS_PASS_DEFAULT_HOLD_BARS;
   }
}

void TS_LogExecutionState()
{
   PrintFormat(
      "[TS][EXEC_STATE] has_position=%s dir=%d ticket=%I64u position_id=%I64d trade_id=%s trade_counter=%d entry_time=%s entry_bar_time=%s entry_price=%.8f sl=%.8f tp=%.8f init_sl=%.8f init_tp=%.8f lot=%.4f bars_held=%d hold_soft=%d k_req=[%.6f,%.6f] k_eff=[%.6f,%.6f] regime_at_entry=%d spread_at_entry=%.6f flip_at_entry=%s pack_dir_at_entry=%s pending_exit_reason=%s pending_modify_reason=%s modify_count=%d last_modify_reason=%s entry_log=%s be_applied=%s exited_this_bar=%s last_exit_reason=%s active_pack=%s runtime_reload=[attempt:%d success:%d rollback:%d status:%s] tx_authority=%s",
      g_ts_exec_has_position ? "true" : "false",
      g_ts_exec_direction,
      g_ts_exec_ticket,
      g_ts_exec_position_id,
      g_ts_exec_trade_id,
      g_ts_exec_trade_counter,
      TimeToString(g_ts_exec_entry_time, TIME_DATE | TIME_MINUTES),
      TimeToString(g_ts_exec_entry_bar_time, TIME_DATE | TIME_MINUTES),
      g_ts_exec_entry_price,
      g_ts_exec_sl_price,
      g_ts_exec_tp_price,
      g_ts_exec_initial_sl_price,
      g_ts_exec_initial_tp_price,
      g_ts_exec_lot,
      g_ts_exec_bars_held,
      g_ts_exec_hold_bars_soft,
      g_ts_exec_k_sl_req,
      g_ts_exec_k_tp_req,
      g_ts_exec_k_sl_eff,
      g_ts_exec_k_tp_eff,
      g_ts_exec_regime_id_at_entry,
      g_ts_exec_spread_atr_at_entry,
      g_ts_exec_flip_used_at_entry ? "true" : "false",
      g_ts_exec_pack_dir_at_entry,
      g_ts_exec_pending_exit_reason,
      g_ts_exec_pending_modify_reason,
      g_ts_exec_modify_count,
      g_ts_exec_last_modify_reason,
      g_ts_exec_entry_log_emitted ? "true" : "false",
      g_ts_exec_be_applied ? "true" : "false",
      g_ts_exec_exited_this_bar ? "true" : "false",
      g_ts_exec_last_exit_reason,
      g_ts_exec_active_model_pack_dir,
      g_ts_exec_runtime_reload_attempts,
      g_ts_exec_runtime_reload_successes,
      g_ts_exec_runtime_reload_rollbacks,
      g_ts_exec_last_runtime_reload_status,
      g_ts_exec_tx_authority_enabled ? "true" : "false"
   );
}

void TS_ExecMarkStateDirty()
{
   g_ts_exec_state_dirty = true;
}

void TS_ExecSetPendingExitState(const string exit_reason, const ulong exit_deal, const double exit_price_hint)
{
   if(g_ts_exec_pending_exit_reason == exit_reason &&
      g_ts_exec_pending_exit_deal == exit_deal &&
      g_ts_exec_pending_exit_price_hint == exit_price_hint)
      return;

   g_ts_exec_pending_exit_reason = exit_reason;
   g_ts_exec_pending_exit_deal = exit_deal;
   g_ts_exec_pending_exit_price_hint = exit_price_hint;
   TS_ExecMarkStateDirty();
}

void TS_ClearPendingExitState()
{
   if(g_ts_exec_pending_exit_reason == "" &&
      g_ts_exec_pending_exit_deal == 0 &&
      g_ts_exec_pending_exit_price_hint == 0.0)
      return;

   g_ts_exec_pending_exit_reason = "";
   g_ts_exec_pending_exit_deal = 0;
   g_ts_exec_pending_exit_price_hint = 0.0;
   TS_ExecMarkStateDirty();
}

void TS_ExecSetPendingModifyState(const string modify_reason, const double sl_hint, const double tp_hint)
{
   if(g_ts_exec_pending_modify_reason == modify_reason &&
      g_ts_exec_pending_modify_sl_hint == sl_hint &&
      g_ts_exec_pending_modify_tp_hint == tp_hint)
      return;

   g_ts_exec_pending_modify_reason = modify_reason;
   g_ts_exec_pending_modify_sl_hint = sl_hint;
   g_ts_exec_pending_modify_tp_hint = tp_hint;
   TS_ExecMarkStateDirty();
}

void TS_ClearPendingModifyState()
{
   if(g_ts_exec_pending_modify_reason == "" &&
      g_ts_exec_pending_modify_sl_hint == 0.0 &&
      g_ts_exec_pending_modify_tp_hint == 0.0)
      return;

   g_ts_exec_pending_modify_reason = "";
   g_ts_exec_pending_modify_sl_hint = 0.0;
   g_ts_exec_pending_modify_tp_hint = 0.0;
   TS_ExecMarkStateDirty();
}

bool TS_SavePersistedExecutionState()
{
   TS_ExecEnsureLogDir();

   const string rel_path = TS_ExecStateRelPath();
   const string temp_rel_path = TS_ExecStateTempRelPath();

   if(FileIsExist(temp_rel_path))
      FileDelete(temp_rel_path);

   ResetLastError();
   const int handle = FileOpen(temp_rel_path, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[TS][EXEC][WARN] save state open failed path=%s err=%d", temp_rel_path, GetLastError());
      return false;
   }

   TS_ExecWriteStateLine(handle, "trade_counter", IntegerToString(g_ts_exec_trade_counter));
   TS_ExecWriteStateLine(handle, "has_position", g_ts_exec_has_position ? "1" : "0");
   TS_ExecWriteStateLine(handle, "direction", IntegerToString(g_ts_exec_direction));
   TS_ExecWriteStateLine(handle, "ticket", StringFormat("%I64u", g_ts_exec_ticket));
   TS_ExecWriteStateLine(handle, "position_id", StringFormat("%I64d", g_ts_exec_position_id));
   TS_ExecWriteStateLine(handle, "entry_time", IntegerToString((int)g_ts_exec_entry_time));
   TS_ExecWriteStateLine(handle, "entry_bar_time", IntegerToString((int)g_ts_exec_entry_bar_time));
   TS_ExecWriteStateLine(handle, "entry_price", DoubleToString(g_ts_exec_entry_price, 8));
   TS_ExecWriteStateLine(handle, "sl_price", DoubleToString(g_ts_exec_sl_price, 8));
   TS_ExecWriteStateLine(handle, "tp_price", DoubleToString(g_ts_exec_tp_price, 8));
   TS_ExecWriteStateLine(handle, "initial_sl_price", DoubleToString(g_ts_exec_initial_sl_price, 8));
   TS_ExecWriteStateLine(handle, "initial_tp_price", DoubleToString(g_ts_exec_initial_tp_price, 8));
   TS_ExecWriteStateLine(handle, "lot", DoubleToString(g_ts_exec_lot, 8));
   TS_ExecWriteStateLine(handle, "bars_held", IntegerToString(g_ts_exec_bars_held));
   TS_ExecWriteStateLine(handle, "hold_bars_soft", IntegerToString(g_ts_exec_hold_bars_soft));
   TS_ExecWriteStateLine(handle, "k_sl_req", DoubleToString(g_ts_exec_k_sl_req, 8));
   TS_ExecWriteStateLine(handle, "k_tp_req", DoubleToString(g_ts_exec_k_tp_req, 8));
   TS_ExecWriteStateLine(handle, "k_sl_eff", DoubleToString(g_ts_exec_k_sl_eff, 8));
   TS_ExecWriteStateLine(handle, "k_tp_eff", DoubleToString(g_ts_exec_k_tp_eff, 8));
   TS_ExecWriteStateLine(handle, "regime_id_at_entry", IntegerToString(g_ts_exec_regime_id_at_entry));
   TS_ExecWriteStateLine(handle, "spread_atr_at_entry", DoubleToString(g_ts_exec_spread_atr_at_entry, 8));
   TS_ExecWriteStateLine(handle, "flip_used_at_entry", g_ts_exec_flip_used_at_entry ? "1" : "0");
   TS_ExecWriteStateLine(handle, "pack_ver_at_entry", g_ts_exec_pack_ver_at_entry);
   TS_ExecWriteStateLine(handle, "clf_ver_at_entry", g_ts_exec_clf_ver_at_entry);
   TS_ExecWriteStateLine(handle, "prm_ver_at_entry", g_ts_exec_prm_ver_at_entry);
   TS_ExecWriteStateLine(handle, "cost_ver_at_entry", g_ts_exec_cost_ver_at_entry);
   TS_ExecWriteStateLine(handle, "pack_dir_at_entry", g_ts_exec_pack_dir_at_entry);
   TS_ExecWriteStateLine(handle, "last_exit_reason", g_ts_exec_last_exit_reason);
   TS_ExecWriteStateLine(handle, "last_modify_reason", g_ts_exec_last_modify_reason);
   TS_ExecWriteStateLine(handle, "trade_seq", IntegerToString(g_ts_exec_trade_seq));
   TS_ExecWriteStateLine(handle, "trade_id", g_ts_exec_trade_id);
   TS_ExecWriteStateLine(handle, "modify_count", IntegerToString(g_ts_exec_modify_count));
   TS_ExecWriteStateLine(handle, "last_modify_time", IntegerToString((int)g_ts_exec_last_modify_time));
   TS_ExecWriteStateLine(handle, "pending_exit_reason", g_ts_exec_pending_exit_reason);
   TS_ExecWriteStateLine(handle, "pending_exit_deal", StringFormat("%I64u", g_ts_exec_pending_exit_deal));
   TS_ExecWriteStateLine(handle, "pending_exit_price_hint", DoubleToString(g_ts_exec_pending_exit_price_hint, 8));
   TS_ExecWriteStateLine(handle, "pending_modify_reason", g_ts_exec_pending_modify_reason);
   TS_ExecWriteStateLine(handle, "pending_modify_sl_hint", DoubleToString(g_ts_exec_pending_modify_sl_hint, 8));
   TS_ExecWriteStateLine(handle, "pending_modify_tp_hint", DoubleToString(g_ts_exec_pending_modify_tp_hint, 8));
   TS_ExecWriteStateLine(handle, "entry_log_emitted", g_ts_exec_entry_log_emitted ? "1" : "0");
   TS_ExecWriteStateLine(handle, "be_applied", g_ts_exec_be_applied ? "1" : "0");
   TS_ExecWriteStateLine(handle, "active_model_pack_dir", g_ts_exec_active_model_pack_dir);
   TS_ExecWriteStateLine(handle, "last_runtime_patch_revision", g_ts_exec_last_runtime_patch_revision);
   TS_ExecWriteStateLine(handle, "runtime_reload_attempts", IntegerToString(g_ts_exec_runtime_reload_attempts));
   TS_ExecWriteStateLine(handle, "runtime_reload_successes", IntegerToString(g_ts_exec_runtime_reload_successes));
   TS_ExecWriteStateLine(handle, "runtime_reload_rollbacks", IntegerToString(g_ts_exec_runtime_reload_rollbacks));
   TS_ExecWriteStateLine(handle, "last_runtime_reload_status", g_ts_exec_last_runtime_reload_status);

   FileClose(handle);

   ResetLastError();
   if(!FileMove(temp_rel_path, 0, rel_path, FILE_REWRITE))
   {
      const int move_err = GetLastError();
      PrintFormat("[TS][EXEC][WARN] save state replace move failed src=%s dst=%s err=%d", temp_rel_path, rel_path, move_err);

      if(FileIsExist(rel_path))
      {
         ResetLastError();
         if(!FileDelete(rel_path))
         {
            PrintFormat("[TS][EXEC][WARN] save state delete fallback failed path=%s err=%d", rel_path, GetLastError());
            return false;
         }
      }

      ResetLastError();
      if(!FileMove(temp_rel_path, 0, rel_path, 0))
      {
         PrintFormat("[TS][EXEC][WARN] save state fallback move failed src=%s dst=%s err=%d", temp_rel_path, rel_path, GetLastError());
         return false;
      }
   }

   g_ts_exec_state_dirty = false;
   return true;
}

bool TS_SavePersistedExecutionStateIfDirty()
{
   if(!g_ts_exec_state_dirty)
      return true;
   return TS_SavePersistedExecutionState();
}

void TS_LoadPersistedExecutionState()
{
   TS_ExecEnsureLogDir();

   string rel_path = TS_ExecStateRelPath();
   if(!FileIsExist(rel_path))
      rel_path = TS_ExecStateTempRelPath();

   if(!FileIsExist(rel_path))
      return;

   ResetLastError();
   const int handle = FileOpen(rel_path, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[TS][EXEC][WARN] load state open failed path=%s err=%d", rel_path, GetLastError());
      return;
   }

   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      line = TS_PM_StripBom(TS_PM_Trim(line));
      if(line == "")
         continue;

      const int eq_pos = StringFind(line, "=");
      if(eq_pos <= 0)
         continue;

      string key = TS_PM_Trim(StringSubstr(line, 0, eq_pos));
      string value = TS_PM_Trim(StringSubstr(line, eq_pos + 1));
      StringToLower(key);

      if(key == "trade_counter")
         g_ts_exec_trade_counter = (int)StringToInteger(value);
      else if(key == "has_position")
         g_ts_exec_has_position = (StringToInteger(value) != 0);
      else if(key == "direction")
         g_ts_exec_direction = (int)StringToInteger(value);
      else if(key == "ticket")
         g_ts_exec_ticket = (ulong)StringToInteger(value);
      else if(key == "position_id")
         g_ts_exec_position_id = (long)StringToInteger(value);
      else if(key == "entry_time")
         g_ts_exec_entry_time = (datetime)StringToInteger(value);
      else if(key == "entry_bar_time")
         g_ts_exec_entry_bar_time = (datetime)StringToInteger(value);
      else if(key == "entry_price")
         g_ts_exec_entry_price = StringToDouble(value);
      else if(key == "sl_price")
         g_ts_exec_sl_price = StringToDouble(value);
      else if(key == "tp_price")
         g_ts_exec_tp_price = StringToDouble(value);
      else if(key == "initial_sl_price")
         g_ts_exec_initial_sl_price = StringToDouble(value);
      else if(key == "initial_tp_price")
         g_ts_exec_initial_tp_price = StringToDouble(value);
      else if(key == "lot")
         g_ts_exec_lot = StringToDouble(value);
      else if(key == "bars_held")
         g_ts_exec_bars_held = (int)StringToInteger(value);
      else if(key == "hold_bars_soft")
         g_ts_exec_hold_bars_soft = (int)StringToInteger(value);
      else if(key == "k_sl_req")
         g_ts_exec_k_sl_req = StringToDouble(value);
      else if(key == "k_tp_req")
         g_ts_exec_k_tp_req = StringToDouble(value);
      else if(key == "k_sl_eff")
         g_ts_exec_k_sl_eff = StringToDouble(value);
      else if(key == "k_tp_eff")
         g_ts_exec_k_tp_eff = StringToDouble(value);
      else if(key == "regime_id_at_entry")
         g_ts_exec_regime_id_at_entry = (int)StringToInteger(value);
      else if(key == "spread_atr_at_entry")
         g_ts_exec_spread_atr_at_entry = StringToDouble(value);
      else if(key == "flip_used_at_entry")
         g_ts_exec_flip_used_at_entry = (StringToInteger(value) != 0);
      else if(key == "pack_ver_at_entry")
         g_ts_exec_pack_ver_at_entry = value;
      else if(key == "clf_ver_at_entry")
         g_ts_exec_clf_ver_at_entry = value;
      else if(key == "prm_ver_at_entry")
         g_ts_exec_prm_ver_at_entry = value;
      else if(key == "cost_ver_at_entry")
         g_ts_exec_cost_ver_at_entry = value;
      else if(key == "pack_dir_at_entry")
         g_ts_exec_pack_dir_at_entry = value;
      else if(key == "last_exit_reason")
         g_ts_exec_last_exit_reason = value;
      else if(key == "last_modify_reason")
         g_ts_exec_last_modify_reason = value;
      else if(key == "trade_seq")
         g_ts_exec_trade_seq = (int)StringToInteger(value);
      else if(key == "trade_id")
         g_ts_exec_trade_id = value;
      else if(key == "modify_count")
         g_ts_exec_modify_count = (int)StringToInteger(value);
      else if(key == "last_modify_time")
         g_ts_exec_last_modify_time = (datetime)StringToInteger(value);
      else if(key == "pending_exit_reason")
         g_ts_exec_pending_exit_reason = value;
      else if(key == "pending_exit_deal")
         g_ts_exec_pending_exit_deal = (ulong)StringToInteger(value);
      else if(key == "pending_exit_price_hint")
         g_ts_exec_pending_exit_price_hint = StringToDouble(value);
      else if(key == "pending_modify_reason")
         g_ts_exec_pending_modify_reason = value;
      else if(key == "pending_modify_sl_hint")
         g_ts_exec_pending_modify_sl_hint = StringToDouble(value);
      else if(key == "pending_modify_tp_hint")
         g_ts_exec_pending_modify_tp_hint = StringToDouble(value);
      else if(key == "entry_log_emitted")
         g_ts_exec_entry_log_emitted = (StringToInteger(value) != 0);
      else if(key == "be_applied")
         g_ts_exec_be_applied = (StringToInteger(value) != 0);
      else if(key == "active_model_pack_dir")
         g_ts_exec_active_model_pack_dir = value;
      else if(key == "last_runtime_patch_revision")
         g_ts_exec_last_runtime_patch_revision = value;
      else if(key == "runtime_reload_attempts")
         g_ts_exec_runtime_reload_attempts = (int)StringToInteger(value);
      else if(key == "runtime_reload_successes")
         g_ts_exec_runtime_reload_successes = (int)StringToInteger(value);
      else if(key == "runtime_reload_rollbacks")
         g_ts_exec_runtime_reload_rollbacks = (int)StringToInteger(value);
      else if(key == "last_runtime_reload_status")
         g_ts_exec_last_runtime_reload_status = value;
   }

   FileClose(handle);
   if(g_ts_exec_initial_sl_price <= 0.0)
      g_ts_exec_initial_sl_price = g_ts_exec_sl_price;
   if(g_ts_exec_initial_tp_price <= 0.0)
      g_ts_exec_initial_tp_price = g_ts_exec_tp_price;
   if(g_ts_exec_pack_dir_at_entry == "")
      g_ts_exec_pack_dir_at_entry = g_ts_exec_active_model_pack_dir;
   g_ts_exec_state_dirty = false;
   PrintFormat("[TS][EXEC] loaded persisted state path=%s has_position=%s trade_id=%s trade_counter=%d", rel_path, g_ts_exec_has_position ? "true" : "false", g_ts_exec_trade_id, g_ts_exec_trade_counter);
}

int TS_ExecVolumeDigits(const double lot_step)
{
   int digits = 0;
   double scaled = lot_step;
   while(digits < 8 && MathAbs(scaled - MathRound(scaled)) > TS_EPSILON)
   {
      scaled *= 10.0;
      digits++;
   }
   return digits;
}

ENUM_ORDER_TYPE_FILLING TS_ExecResolveFillingType()
{
   const long filling_flags = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((filling_flags & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   if((filling_flags & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
#ifdef SYMBOL_FILLING_RETURN
   if((filling_flags & SYMBOL_FILLING_RETURN) == SYMBOL_FILLING_RETURN)
      return ORDER_FILLING_RETURN;
#endif
   return ORDER_FILLING_FOK;
}

int TS_ExecComputeBarsHeldBeforeManage(const datetime entry_bar_time)
{
   if(entry_bar_time <= 0)
      return 0;

   int entry_shift = iBarShift(_Symbol, TS_DECISION_TIMEFRAME, entry_bar_time);
   if(entry_shift < 0)
      entry_shift = 0;

   entry_shift--;
   if(entry_shift < 0)
      entry_shift = 0;

   return entry_shift;
}

string TS_ExecFormatTradeId(const int seq)
{
   return StringFormat("TS_%05d", seq);
}

string TS_ExecExitReasonFromDeal(const long deal_reason)
{
   if(deal_reason == DEAL_REASON_SL)
      return "SL";
   if(deal_reason == DEAL_REASON_TP)
      return "TP";
   if(g_ts_exec_pending_exit_reason != "")
      return g_ts_exec_pending_exit_reason;
   return "FORCE_EXIT";
}

void TS_ExecCaptureEntryVersions()
{
   g_ts_exec_pack_ver_at_entry = g_ts_pack_meta.model_pack_version;
   // Runtime-specific per-model versioning is not implemented yet, so clf/prm
   // versions currently remain aliases of the pack version.
   g_ts_exec_clf_ver_at_entry = g_ts_pack_meta.model_pack_version;
   g_ts_exec_prm_ver_at_entry = g_ts_pack_meta.model_pack_version;
   g_ts_exec_cost_ver_at_entry = g_ts_pack_meta.cost_model_version;
   g_ts_exec_pack_dir_at_entry = g_ts_exec_active_model_pack_dir;
}

double TS_ExecPriceTolerance()
{
   if(TS_ExecIsFiniteValue(_Point) && _Point > 0.0)
      return (_Point * 0.5);
   return 1e-6;
}

bool TS_ExecHintMatches(const double live_value, const double hinted_value)
{
   const double tol = TS_ExecPriceTolerance();
   if(!TS_ExecIsFiniteValue(hinted_value) || hinted_value <= 0.0)
      return (!TS_ExecIsFiniteValue(live_value) || MathAbs(live_value) <= tol);

   if(!TS_ExecIsFiniteValue(live_value))
      return false;

   return (MathAbs(live_value - hinted_value) <= tol);
}

bool TS_ExecWouldImproveStop(const double target_sl)
{
   const double tol = TS_ExecPriceTolerance();
   if(!TS_ExecIsFiniteValue(target_sl) || target_sl <= 0.0)
      return false;

   if(!TS_ExecIsFiniteValue(g_ts_exec_sl_price) || g_ts_exec_sl_price <= 0.0)
      return true;

   if(g_ts_exec_direction == 0)
      return (target_sl > (g_ts_exec_sl_price + tol));

   if(g_ts_exec_direction == 1)
      return (target_sl < (g_ts_exec_sl_price - tol));

   return false;
}

bool TS_ExecWouldTightenTarget(const double target_tp)
{
   const double tol = TS_ExecPriceTolerance();
   if(!TS_ExecIsFiniteValue(target_tp) || target_tp <= 0.0)
      return false;

   if(!TS_ExecIsFiniteValue(g_ts_exec_tp_price) || g_ts_exec_tp_price <= 0.0)
      return true;

   if(g_ts_exec_direction == 0)
      return (target_tp < (g_ts_exec_tp_price - tol));

   if(g_ts_exec_direction == 1)
      return (target_tp > (g_ts_exec_tp_price + tol));

   return false;
}

void TS_ExecMarkBreakEvenApplied()
{
   if(g_ts_exec_be_applied)
      return;

   g_ts_exec_be_applied = true;
   TS_ExecMarkStateDirty();
}

void TS_ExecRecordModifyApplied(const string modify_reason, const string tx_authority)
{
   g_ts_exec_modify_count++;
   g_ts_exec_last_modify_reason = modify_reason;
   g_ts_exec_last_modify_time = TimeCurrent();
   if(modify_reason == "BREAK_EVEN")
      TS_ExecMarkBreakEvenApplied();
   TS_WriteTradeModifyLog(
      modify_reason,
      "",
      0,
      g_ts_exec_sl_price,
      g_ts_exec_tp_price,
      tx_authority
   );
   if(g_ts_exec_broker_audit_enabled)
      TS_WriteBrokerAuditLog(
         "modify_applied",
         StringFormat("trade_id=%s reason=%s tx=%s sl=%.8f tp=%.8f", g_ts_exec_trade_id, modify_reason, tx_authority, g_ts_exec_sl_price, g_ts_exec_tp_price)
      );
   TS_ExecMarkStateDirty();
}

void TS_ExecEmitEntryLogIfNeeded(const ulong deal_ticket, const string tx_authority)
{
   if(g_ts_exec_trade_id == "" || g_ts_exec_entry_log_emitted)
      return;

   TS_WriteTradeEntryLog(deal_ticket, tx_authority);
   g_ts_exec_entry_log_emitted = true;
   if(g_ts_exec_broker_audit_enabled)
      TS_WriteBrokerAuditLog(
         "entry_logged",
         StringFormat("trade_id=%s tx=%s deal=%I64u", g_ts_exec_trade_id, tx_authority, deal_ticket)
      );
   TS_ExecMarkStateDirty();
}

bool TS_ExecPopulateCurrentPositionSnapshot()
{
   if(!PositionSelect(_Symbol))
      return false;

   g_ts_exec_has_position = true;
   g_ts_exec_ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   g_ts_exec_position_id = (long)PositionGetInteger(POSITION_IDENTIFIER);
   g_ts_exec_direction = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 0 : 1;
   g_ts_exec_entry_time = (datetime)PositionGetInteger(POSITION_TIME);
   g_ts_exec_entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
   g_ts_exec_sl_price = PositionGetDouble(POSITION_SL);
   g_ts_exec_tp_price = PositionGetDouble(POSITION_TP);
   g_ts_exec_lot = PositionGetDouble(POSITION_VOLUME);

   if(g_ts_exec_entry_bar_time <= 0)
   {
      int shift = iBarShift(_Symbol, TS_DECISION_TIMEFRAME, g_ts_exec_entry_time);
      if(shift < 0)
         shift = 0;
      g_ts_exec_entry_bar_time = iTime(_Symbol, TS_DECISION_TIMEFRAME, shift);
   }

   g_ts_exec_bars_held = TS_ExecComputeBarsHeldBeforeManage(g_ts_exec_entry_bar_time);
   return true;
}

void TS_ExecSyncPendingModifyState()
{
   if(g_ts_exec_pending_modify_reason == "")
      return;

   const bool sl_matches = TS_ExecHintMatches(g_ts_exec_sl_price, g_ts_exec_pending_modify_sl_hint);
   const bool tp_matches = TS_ExecHintMatches(g_ts_exec_tp_price, g_ts_exec_pending_modify_tp_hint);
   if(!sl_matches || !tp_matches)
      return;

   TS_ExecRecordModifyApplied(g_ts_exec_pending_modify_reason, g_ts_exec_tx_authority_enabled ? "TX_OR_SYNC" : "SYNC");

   PrintFormat(
      "[TS][EXEC] pending_modify_cleared trade_id=%s reason=%s sl=%.8f tp=%.8f",
      g_ts_exec_trade_id,
      g_ts_exec_pending_modify_reason,
      g_ts_exec_sl_price,
      g_ts_exec_tp_price
   );
   TS_MonitorOnModifyPendingCleared();
   TS_ClearPendingModifyState();
}

void TS_ExecAdoptRecoveredPosition()
{
   if(g_ts_exec_trade_seq <= 0)
      g_ts_exec_trade_seq = g_ts_exec_trade_counter + 1;

   if(g_ts_exec_trade_seq > g_ts_exec_trade_counter)
      g_ts_exec_trade_counter = g_ts_exec_trade_seq;

   g_ts_exec_trade_id = TS_ExecFormatTradeId(g_ts_exec_trade_seq);
   if(g_ts_exec_hold_bars_soft < 1 || g_ts_exec_hold_bars_soft > TS_HOLD_BARS_MAX)
      g_ts_exec_hold_bars_soft = TS_PASS_DEFAULT_HOLD_BARS;
   if(g_ts_exec_initial_sl_price <= 0.0)
      g_ts_exec_initial_sl_price = g_ts_exec_sl_price;
   if(g_ts_exec_initial_tp_price <= 0.0)
      g_ts_exec_initial_tp_price = g_ts_exec_tp_price;
   if(g_ts_exec_pack_dir_at_entry == "")
      g_ts_exec_pack_dir_at_entry = g_ts_exec_active_model_pack_dir;
   TS_ExecCaptureEntryVersions();
   TS_ExecMarkStateDirty();
}

void TS_SyncPositionState()
{
   if(PositionSelect(_Symbol))
   {
      const long live_position_id = (long)PositionGetInteger(POSITION_IDENTIFIER);

      if(!g_ts_exec_has_position || (g_ts_exec_position_id != 0 && live_position_id != g_ts_exec_position_id))
      {
         TS_ClearExecutionPositionState();
      }

      TS_ExecPopulateCurrentPositionSnapshot();
      if(g_ts_exec_trade_id == "")
         TS_ExecAdoptRecoveredPosition();
      TS_ExecEmitEntryLogIfNeeded(0, g_ts_exec_tx_authority_enabled ? "TX_POSITION" : "SYNC_POSITION");

      TS_ExecSyncPendingModifyState();

      if(g_ts_exec_bars_held >= TS_HOLD_BARS_MAX && g_ts_exec_pending_exit_reason != "FORCE_EXIT")
         TS_ExecSetPendingExitState("FORCE_EXIT", g_ts_exec_pending_exit_deal, g_ts_exec_pending_exit_price_hint);

      TS_SavePersistedExecutionStateIfDirty();
      return;
   }

   if(!g_ts_exec_has_position)
      return;

   datetime history_from = g_ts_exec_entry_time;
   if(history_from > 60)
      history_from -= 60;

   ResetLastError();
   HistorySelect(history_from, TimeCurrent());

   ulong exit_deal = 0;
   if(g_ts_exec_pending_exit_deal != 0 && HistoryDealSelect(g_ts_exec_pending_exit_deal))
      exit_deal = g_ts_exec_pending_exit_deal;

   for(int i = HistoryDealsTotal() - 1; i >= 0 && exit_deal == 0; --i)
   {
      const ulong deal_ticket = HistoryDealGetTicket(i);
      if(deal_ticket == 0)
         continue;

      const long deal_position_id = (long)HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
      const long deal_entry = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
      if(deal_position_id != g_ts_exec_position_id)
         continue;
      if(deal_entry != DEAL_ENTRY_OUT && deal_entry != DEAL_ENTRY_OUT_BY)
         continue;

      exit_deal = deal_ticket;
      break;
   }

   double exit_price = 0.0;
   double pnl = 0.0;
   string exit_reason = (g_ts_exec_pending_exit_reason != "") ? g_ts_exec_pending_exit_reason : "FORCE_EXIT";
   if(exit_deal != 0)
   {
      exit_price = HistoryDealGetDouble(exit_deal, DEAL_PRICE);
      pnl =
         HistoryDealGetDouble(exit_deal, DEAL_PROFIT) +
         HistoryDealGetDouble(exit_deal, DEAL_SWAP) +
         HistoryDealGetDouble(exit_deal, DEAL_COMMISSION);
      exit_reason = TS_ExecExitReasonFromDeal(HistoryDealGetInteger(exit_deal, DEAL_REASON));
   }
   else if(TS_ExecIsFiniteValue(g_ts_exec_pending_exit_price_hint) && g_ts_exec_pending_exit_price_hint > 0.0)
   {
      exit_price = g_ts_exec_pending_exit_price_hint;
   }
   else
   {
      PrintFormat("[TS][EXEC][WARN] exit deal not found position_id=%I64d trade_id=%s", g_ts_exec_position_id, g_ts_exec_trade_id);
   }

   if(!(exit_deal != 0 && g_ts_exec_last_exit_deal_logged == exit_deal))
   {
      TS_WriteTradeExitLog(exit_reason, "", exit_deal, exit_price, pnl, "SYNC_POSITION");
      g_ts_exec_last_exit_deal_logged = exit_deal;
   }
   g_ts_exec_last_exit_reason = exit_reason;
   g_ts_exec_exited_this_bar = true;
   if(!g_ts_exec_timer_cycle_active && g_ts_exec_pending_exit_reason == "")
      g_ts_exec_block_next_entry_bar = true;
   TS_ClearExecutionPositionState();
   TS_SavePersistedExecutionStateIfDirty();
}

bool TS_ExecResolveEffectiveStops(
   const int direction,
   const double entry_price,
   double &sl_price,
   double &tp_price
)
{
   g_ts_exec_k_sl_req = g_ts_final_k_sl;
   g_ts_exec_k_tp_req = g_ts_final_k_tp;
   g_ts_exec_k_sl_eff = g_ts_final_k_sl;
   g_ts_exec_k_tp_eff = g_ts_final_k_tp;
   g_ts_exec_hold_bars_soft = g_ts_final_hold_bars;

   if(!TS_ExecIsFiniteValue(g_ts_current_atr14) || g_ts_current_atr14 <= 0.0)
   {
      PrintFormat("[TS][EXEC][SKIP] ORDER_CONSTRAINT:atr14_invalid atr14=%.8f", g_ts_current_atr14);
      return false;
   }

   if(!TS_ExecIsFiniteValue(_Point) || _Point <= 0.0)
   {
      PrintFormat("[TS][EXEC][SKIP] ORDER_CONSTRAINT:point_invalid point=%.8f", _Point);
      return false;
   }

   const double min_stop = (double)g_ts_min_stop_distance_points;
   const double sl_pts_req = g_ts_exec_k_sl_req * g_ts_current_atr14 / _Point;
   const double tp_pts_req = g_ts_exec_k_tp_req * g_ts_current_atr14 / _Point;
   const double sl_pts_eff = MathMax(sl_pts_req, min_stop);
   const double tp_pts_eff = MathMax(tp_pts_req, min_stop);

   g_ts_exec_k_sl_eff = sl_pts_eff * _Point / MathMax(g_ts_current_atr14, TS_EPSILON);
   g_ts_exec_k_tp_eff = tp_pts_eff * _Point / MathMax(g_ts_current_atr14, TS_EPSILON);

   if(g_ts_exec_k_sl_eff > 6.0)
   {
      PrintFormat("[TS][EXEC][SKIP] ORDER_CONSTRAINT:sl_correction_exceeds_clamp k_sl_eff=%.8f", g_ts_exec_k_sl_eff);
      return false;
   }

   if(g_ts_exec_k_tp_eff > 12.0)
   {
      PrintFormat("[TS][EXEC][SKIP] ORDER_CONSTRAINT:tp_correction_exceeds_clamp k_tp_eff=%.8f", g_ts_exec_k_tp_eff);
      return false;
   }

   const int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   const double sl_dist = g_ts_exec_k_sl_eff * g_ts_current_atr14;
   const double tp_dist = g_ts_exec_k_tp_eff * g_ts_current_atr14;

   if(direction == 0)
   {
      sl_price = NormalizeDouble(entry_price - sl_dist, digits);
      tp_price = NormalizeDouble(entry_price + tp_dist, digits);
   }
   else
   {
      sl_price = NormalizeDouble(entry_price + sl_dist, digits);
      tp_price = NormalizeDouble(entry_price - tp_dist, digits);
   }

   return TS_ExecIsFiniteValue(sl_price) && TS_ExecIsFiniteValue(tp_price);
}

bool TS_ExecOrderCheck(
   const int direction,
   const double lot,
   const double entry_price,
   const double sl_price,
   const double tp_price,
   const int deviation_points
)
{
   MqlTradeRequest request;
   MqlTradeCheckResult check;
   ZeroMemory(request);
   ZeroMemory(check);

   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = lot;
   request.price = entry_price;
   request.sl = sl_price;
   request.tp = tp_price;
   request.deviation = deviation_points;
   request.type = (direction == 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.type_filling = TS_ExecResolveFillingType();
   request.type_time = ORDER_TIME_GTC;

   ResetLastError();
   if(!OrderCheck(request, check))
   {
      PrintFormat("[TS][EXEC][SKIP] RISK:margin_check_fail err=%d", GetLastError());
      return false;
   }

   if(check.retcode != TRADE_RETCODE_DONE &&
      check.retcode != TRADE_RETCODE_DONE_PARTIAL &&
      check.retcode != TRADE_RETCODE_NO_CHANGES)
   {
      if(check.retcode == 0)
      {
         Print("[TS][EXEC][WARN] OrderCheck returned retcode=0; proceeding to send order");
         return true;
      }

      PrintFormat("[TS][EXEC][SKIP] RISK:margin_check_fail retcode=%u comment=%s", check.retcode, check.comment);
      return false;
   }

   return true;
}

bool TS_ExecTradeRetcodeIsExecuted(const uint retcode)
{
   return (retcode == TRADE_RETCODE_DONE || retcode == TRADE_RETCODE_DONE_PARTIAL);
}

bool TS_ExecHasOppositeCurrentDecision()
{
   if(!g_ts_decision_ready)
      return false;

   if(g_ts_final_dir == 2 || g_ts_exec_direction < 0)
      return false;

   return ((g_ts_exec_direction == 0 && g_ts_final_dir == 1) ||
           (g_ts_exec_direction == 1 && g_ts_final_dir == 0));
}

string TS_ExecResolveShadowExitReason(const double p_exit_pass_threshold)
{
   if(!g_ts_decision_ready)
      return "";

   if(TS_ExecHasOppositeCurrentDecision())
      return "OPPOSITE_DIR";

   if(TS_ExecIsFiniteValue(g_ts_final_y[2]) && g_ts_final_y[2] >= p_exit_pass_threshold)
      return "P_EXIT_PASS";

   return "";
}

string TS_ExecResolveLiveEarlyExitReason(const double p_exit_pass_threshold)
{
   if(!g_ts_decision_ready)
      return "";

   if(TS_ExecIsFiniteValue(g_ts_final_y[2]) && g_ts_final_y[2] >= p_exit_pass_threshold)
      return "P_EXIT_PASS";

   return "";
}

string TS_ExecResolveLiveEarlyExitReasonCloseOnly(const bool opposite_enabled, const double p_exit_pass_threshold)
{
   if(!g_ts_decision_ready)
      return "";

   if(opposite_enabled)
   {
      if(TS_ExecHasOppositeCurrentDecision())
         return "OPPOSITE_DIR";

      if(g_ts_exec_test_force_opposite_early_exit_enabled)
         return "OPPOSITE_DIR";
   }

   return TS_ExecResolveLiveEarlyExitReason(p_exit_pass_threshold);
}

bool TS_ExecWouldImproveBreakEvenStop(const double target_sl)
{
   return TS_ExecWouldImproveStop(target_sl);
}

bool TS_ExecResolveRiskContext(
   double &initial_sl,
   double &initial_tp,
   double &initial_risk,
   double &favorable_price,
   double &favorable_move
)
{
   initial_sl = 0.0;
   initial_tp = 0.0;
   initial_risk = 0.0;
   favorable_price = 0.0;
   favorable_move = 0.0;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      if(!g_ts_has_tick_snapshot)
         return false;
      tick = g_ts_last_tick_snapshot;
   }

   favorable_price = (g_ts_exec_direction == 0) ? tick.bid : tick.ask;
   if(!TS_ExecIsFiniteValue(favorable_price) || favorable_price <= 0.0)
      return false;

   initial_sl =
      (TS_ExecIsFiniteValue(g_ts_exec_initial_sl_price) && g_ts_exec_initial_sl_price > 0.0)
      ? g_ts_exec_initial_sl_price
      : g_ts_exec_sl_price;
   initial_tp =
      (TS_ExecIsFiniteValue(g_ts_exec_initial_tp_price) && g_ts_exec_initial_tp_price > 0.0)
      ? g_ts_exec_initial_tp_price
      : g_ts_exec_tp_price;
   if(!TS_ExecIsFiniteValue(initial_sl) || initial_sl <= 0.0)
      return false;

   if(g_ts_exec_direction == 0)
   {
      initial_risk = g_ts_exec_entry_price - initial_sl;
      favorable_move = favorable_price - g_ts_exec_entry_price;
   }
   else if(g_ts_exec_direction == 1)
   {
      initial_risk = initial_sl - g_ts_exec_entry_price;
      favorable_move = g_ts_exec_entry_price - favorable_price;
   }
   else
   {
      return false;
   }

   if(initial_risk <= TS_EPSILON || favorable_move <= 0.0)
      return false;

   return true;
}

bool TS_ExecResolveBreakEvenRequest(
   const double rr_trigger,
   const int min_hold_bars_before_modify,
   const int offset_points,
   double &new_sl,
   double &new_tp,
   bool &min_hold_blocked,
   bool &synthetic_trigger
)
{
   new_sl = 0.0;
   new_tp = 0.0;
   min_hold_blocked = false;
   synthetic_trigger = false;

   if(!g_ts_exec_has_position)
      return false;
   if(g_ts_exec_pending_exit_reason != "")
      return false;
   if(g_ts_exec_pending_modify_reason != "")
      return false;
   if(g_ts_exec_be_applied)
      return false;

   const bool force_break_even = TS_ExecShouldForceBreakEvenOnce();
   double favorable_price = 0.0;
   if(force_break_even)
   {
      synthetic_trigger = true;
   }
   else
   {
      double initial_sl = 0.0;
      double initial_tp = 0.0;
      double initial_risk = 0.0;
      double favorable_move = 0.0;
      if(!TS_ExecResolveRiskContext(initial_sl, initial_tp, initial_risk, favorable_price, favorable_move))
         return false;

      const double rr_threshold = MathMax(0.0, rr_trigger);
      if(favorable_move + TS_EPSILON < (rr_threshold * initial_risk))
         return false;
   }

   min_hold_blocked = (g_ts_exec_bars_held < MathMax(0, min_hold_bars_before_modify));

   const int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   const double offset_price = MathMax(0, offset_points) * _Point;
   const double target_sl =
      (g_ts_exec_direction == 0)
      ? NormalizeDouble(g_ts_exec_entry_price + offset_price, digits)
      : NormalizeDouble(g_ts_exec_entry_price - offset_price, digits);

   if(!TS_ExecWouldImproveBreakEvenStop(target_sl))
   {
      TS_ExecMarkBreakEvenApplied();
      if(force_break_even)
         TS_ExecMarkForceBreakEvenOnceConsumed();
      return false;
   }

   new_sl = target_sl;
   new_tp = g_ts_exec_tp_price;
   return true;
}

bool TS_ExecResolveTrailingRequest(
   const double start_rr,
   const double atr_multiple,
   const int step_points,
   double &new_sl,
   double &new_tp
)
{
   new_sl = 0.0;
   new_tp = 0.0;

   if(!g_ts_exec_has_position || g_ts_exec_pending_exit_reason != "" || g_ts_exec_pending_modify_reason != "")
      return false;

   double initial_sl = 0.0;
   double initial_tp = 0.0;
   double initial_risk = 0.0;
   double favorable_price = 0.0;
   double favorable_move = 0.0;
   if(!TS_ExecResolveRiskContext(initial_sl, initial_tp, initial_risk, favorable_price, favorable_move))
      return false;

   if(favorable_move + TS_EPSILON < (MathMax(0.0, start_rr) * initial_risk))
      return false;
   if(!TS_ExecIsFiniteValue(g_ts_current_atr14) || g_ts_current_atr14 <= 0.0)
      return false;

   const int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   const double stop_buffer = MathMax(
      MathMax(0.25, atr_multiple) * g_ts_current_atr14,
      (double)MathMax(0, g_ts_min_stop_distance_points) * _Point
   );
   double target_sl =
      (g_ts_exec_direction == 0)
      ? NormalizeDouble(favorable_price - stop_buffer, digits)
      : NormalizeDouble(favorable_price + stop_buffer, digits);
   if(!TS_ExecWouldImproveStop(target_sl))
      return false;

   const double min_step = MathMax(0, step_points) * _Point;
   if(min_step > 0.0 &&
      TS_ExecIsFiniteValue(g_ts_exec_sl_price) &&
      MathAbs(target_sl - g_ts_exec_sl_price) + TS_EPSILON < min_step)
      return false;

   new_sl = target_sl;
   new_tp = g_ts_exec_tp_price;
   return true;
}

bool TS_ExecResolveTPReshapeRequest(
   const double rr_trigger,
   const double target_rr,
   double &new_sl,
   double &new_tp
)
{
   new_sl = 0.0;
   new_tp = 0.0;

   if(!g_ts_exec_has_position || g_ts_exec_pending_exit_reason != "" || g_ts_exec_pending_modify_reason != "")
      return false;

   double initial_sl = 0.0;
   double initial_tp = 0.0;
   double initial_risk = 0.0;
   double favorable_price = 0.0;
   double favorable_move = 0.0;
   if(!TS_ExecResolveRiskContext(initial_sl, initial_tp, initial_risk, favorable_price, favorable_move))
      return false;

   if(favorable_move + TS_EPSILON < (MathMax(0.0, rr_trigger) * initial_risk))
      return false;

   const int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   const double target_dist = MathMax(
      MathMax(0.25, target_rr) * initial_risk,
      (double)MathMax(0, g_ts_min_stop_distance_points) * _Point
   );
   const double target_tp =
      (g_ts_exec_direction == 0)
      ? NormalizeDouble(g_ts_exec_entry_price + target_dist, digits)
      : NormalizeDouble(g_ts_exec_entry_price - target_dist, digits);
   if(!TS_ExecWouldTightenTarget(target_tp))
      return false;

   new_sl = g_ts_exec_sl_price;
   new_tp = target_tp;
   return true;
}

bool TS_ExecResolveTimePolicyRequest(
   const int after_bars,
   const double stop_lock_rr,
   const double tp_scale,
   double &new_sl,
   double &new_tp
)
{
   new_sl = 0.0;
   new_tp = 0.0;

   if(!g_ts_exec_has_position || g_ts_exec_pending_exit_reason != "" || g_ts_exec_pending_modify_reason != "")
      return false;
   if(g_ts_exec_bars_held < MathMax(0, after_bars))
      return false;

   double initial_sl = 0.0;
   double initial_tp = 0.0;
   double initial_risk = 0.0;
   double favorable_price = 0.0;
   double favorable_move = 0.0;
   if(!TS_ExecResolveRiskContext(initial_sl, initial_tp, initial_risk, favorable_price, favorable_move))
      return false;

   const int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   bool has_change = false;
   double target_sl = g_ts_exec_sl_price;
   double target_tp = g_ts_exec_tp_price;

   if(stop_lock_rr > 0.0)
   {
      const double lock_dist = MathMax(0.0, stop_lock_rr) * initial_risk;
      const double candidate_sl =
         (g_ts_exec_direction == 0)
         ? NormalizeDouble(g_ts_exec_entry_price + lock_dist, digits)
         : NormalizeDouble(g_ts_exec_entry_price - lock_dist, digits);
      if(TS_ExecWouldImproveStop(candidate_sl))
      {
         target_sl = candidate_sl;
         has_change = true;
      }
   }

   const double initial_tp_dist = MathAbs(initial_tp - g_ts_exec_entry_price);
   if(initial_tp_dist > TS_EPSILON)
   {
      const double scale = MathMax(0.10, MathMin(1.0, tp_scale));
      const double scaled_dist = MathMax(
         initial_tp_dist * scale,
         (double)MathMax(0, g_ts_min_stop_distance_points) * _Point
      );
      const double candidate_tp =
         (g_ts_exec_direction == 0)
         ? NormalizeDouble(g_ts_exec_entry_price + scaled_dist, digits)
         : NormalizeDouble(g_ts_exec_entry_price - scaled_dist, digits);
      if(TS_ExecWouldTightenTarget(candidate_tp))
      {
         target_tp = candidate_tp;
         has_change = true;
      }
   }

   if(!has_change)
      return false;

   new_sl = target_sl;
   new_tp = target_tp;
   return true;
}

bool TS_ExecResolveProtectiveModifyRequest(
   const bool break_even_enabled,
   const double break_even_rr_trigger,
   const int break_even_min_hold_bars,
   const int break_even_offset_points,
   const bool trailing_enabled,
   const double trailing_start_rr,
   const double trailing_atr_multiple,
   const int trailing_step_points,
   const bool tp_reshape_enabled,
   const double tp_reshape_rr_trigger,
   const double tp_reshape_target_rr,
   const bool time_policy_enabled,
   const int time_policy_after_bars,
   const double time_policy_stop_lock_rr,
   const double time_policy_tp_scale,
   string &modify_reason,
   double &new_sl,
   double &new_tp,
   bool &min_hold_blocked,
   bool &synthetic_trigger
)
{
   modify_reason = "";
   new_sl = 0.0;
   new_tp = 0.0;
   min_hold_blocked = false;
   synthetic_trigger = false;

   if(break_even_enabled &&
      TS_ExecResolveBreakEvenRequest(
         break_even_rr_trigger,
         break_even_min_hold_bars,
         break_even_offset_points,
         new_sl,
         new_tp,
         min_hold_blocked,
         synthetic_trigger
      ))
   {
      modify_reason = "BREAK_EVEN";
      return true;
   }

   if(trailing_enabled &&
      TS_ExecResolveTrailingRequest(
         trailing_start_rr,
         trailing_atr_multiple,
         trailing_step_points,
         new_sl,
         new_tp
      ))
   {
      modify_reason = "TRAILING";
      return true;
   }

   if(tp_reshape_enabled &&
      TS_ExecResolveTPReshapeRequest(
         tp_reshape_rr_trigger,
         tp_reshape_target_rr,
         new_sl,
         new_tp
      ))
   {
      modify_reason = "TP_RESHAPE";
      return true;
   }

   if(time_policy_enabled &&
      TS_ExecResolveTimePolicyRequest(
         time_policy_after_bars,
         time_policy_stop_lock_rr,
         time_policy_tp_scale,
         new_sl,
         new_tp
      ))
   {
      modify_reason = "TIME_POLICY";
      return true;
   }

   return false;
}

void TS_ManagePositionPreDecision()
{
   if(!g_ts_exec_has_position)
      return;

   g_ts_exec_bars_held++;
   TS_ExecMarkStateDirty();
   if(g_ts_exec_bars_held >= TS_HOLD_BARS_MAX)
   {
      if(g_ts_exec_bars_held == TS_HOLD_BARS_MAX)
         TS_MonitorOnForceExitTriggered();
      TS_ForceExitPosition("FORCE_EXIT");
      return;
   }

   if(g_ts_exec_bars_held == g_ts_exec_hold_bars_soft)
      TS_MonitorOnHoldSoftReached();

   if(g_ts_exec_bars_held >= g_ts_exec_hold_bars_soft)
   {
      PrintFormat("[TS][EXEC] hold_soft_reached trade_id=%s bars_held=%d hold_soft=%d", g_ts_exec_trade_id, g_ts_exec_bars_held, g_ts_exec_hold_bars_soft);
   }

   TS_SavePersistedExecutionStateIfDirty();
   if(g_ts_exec_bars_held == g_ts_exec_test_recovery_reload_bars_held)
      TS_ExecRunTestRecoveryProbe(TS_EXEC_TEST_RECOVERY_RELOAD_OPEN_POSITION, "open_position_checkpoint");
}

void TS_ManagePositionPostDecisionShadow(const bool shadow_enabled, const double p_exit_pass_threshold, const int min_hold_bars_before_exit)
{
   if(!shadow_enabled || !g_ts_exec_has_position || !g_ts_decision_ready)
      return;

   const double threshold = MathMax(0.0, MathMin(1.0, p_exit_pass_threshold));
   const int min_hold = MathMax(0, min_hold_bars_before_exit);
   const string shadow_reason = TS_ExecResolveShadowExitReason(threshold);
   if(shadow_reason == "")
      return;

   const bool min_hold_blocked = (g_ts_exec_bars_held < min_hold);
   const bool shadow_triggered = !min_hold_blocked;
   TS_MonitorOnShadowExitEvaluation(shadow_reason, shadow_triggered, min_hold_blocked);

   if(!shadow_triggered)
   {
      PrintFormat(
         "[TS][SHADOW_EXIT] blocked trade_id=%s reason=%s bars_held=%d min_hold=%d p_pass=%.6f final_dir=%s",
         g_ts_exec_trade_id,
         shadow_reason,
         g_ts_exec_bars_held,
         min_hold,
         g_ts_final_y[2],
         TS_DecisionDirToString(g_ts_final_dir)
      );
      return;
   }

   PrintFormat(
      "[TS][SHADOW_EXIT] trigger trade_id=%s reason=%s bars_held=%d p_pass=%.6f final_dir=%s",
      g_ts_exec_trade_id,
      shadow_reason,
      g_ts_exec_bars_held,
      g_ts_final_y[2],
      TS_DecisionDirToString(g_ts_final_dir)
   );
}

void TS_ManagePositionPostDecisionLiveEarlyExitCloseOnly(
   const bool opposite_enabled,
   const double p_exit_pass_threshold,
   const int min_hold_bars_before_exit
)
{
   if(!g_ts_exec_has_position || !g_ts_decision_ready)
      return;
   if(g_ts_exec_pending_exit_reason != "")
      return;

   const double threshold = MathMax(0.0, MathMin(1.0, p_exit_pass_threshold));
   const int min_hold = MathMax(0, min_hold_bars_before_exit);
   const string exit_detail = TS_ExecResolveLiveEarlyExitReasonCloseOnly(opposite_enabled, threshold);
   if(exit_detail == "")
      return;

   const bool min_hold_blocked = (g_ts_exec_bars_held < min_hold);
   TS_MonitorOnEarlyExitEvaluation(exit_detail, min_hold_blocked);
   if(min_hold_blocked)
   {
      PrintFormat(
         "[TS][EARLY_EXIT] blocked trade_id=%s reason=%s bars_held=%d min_hold=%d p_pass=%.6f final_dir=%s",
         g_ts_exec_trade_id,
         exit_detail,
         g_ts_exec_bars_held,
         min_hold,
         g_ts_final_y[2],
         TS_DecisionDirToString(g_ts_final_dir)
      );
      return;
   }

   PrintFormat(
      "[TS][EARLY_EXIT] trigger trade_id=%s reason=%s bars_held=%d p_pass=%.6f final_dir=%s",
      g_ts_exec_trade_id,
      exit_detail,
      g_ts_exec_bars_held,
      g_ts_final_y[2],
      TS_DecisionDirToString(g_ts_final_dir)
   );
   g_ts_exec_early_exit_attempted_this_bar = true;
   TS_ClosePositionByReason("EARLY_EXIT", exit_detail);
}

void TS_ManagePositionPostDecisionLiveProtectiveAdjustments(
   const bool break_even_enabled,
   const double break_even_rr_trigger,
   const int break_even_min_hold_bars,
   const int break_even_offset_points,
   const bool trailing_enabled,
   const double trailing_start_rr,
   const double trailing_atr_multiple,
   const int trailing_step_points,
   const bool tp_reshape_enabled,
   const double tp_reshape_rr_trigger,
   const double tp_reshape_target_rr,
   const bool time_policy_enabled,
   const int time_policy_after_bars,
   const double time_policy_stop_lock_rr,
   const double time_policy_tp_scale
)
{
   if(!g_ts_exec_has_position)
      return;
   if(g_ts_exec_exited_this_bar)
      return;
   if(g_ts_exec_early_exit_attempted_this_bar)
      return;
   if(g_ts_exec_pending_exit_reason != "")
      return;

   string modify_reason = "";
   double new_sl = 0.0;
   double new_tp = 0.0;
   bool min_hold_blocked = false;
   bool synthetic_trigger = false;
   if(!TS_ExecResolveProtectiveModifyRequest(
      break_even_enabled,
      break_even_rr_trigger,
      break_even_min_hold_bars,
      break_even_offset_points,
      trailing_enabled,
      trailing_start_rr,
      trailing_atr_multiple,
      trailing_step_points,
      tp_reshape_enabled,
      tp_reshape_rr_trigger,
      tp_reshape_target_rr,
      time_policy_enabled,
      time_policy_after_bars,
      time_policy_stop_lock_rr,
      time_policy_tp_scale,
      modify_reason,
      new_sl,
      new_tp,
      min_hold_blocked,
      synthetic_trigger
   ))
      return;

   TS_MonitorOnModifyEvaluation(modify_reason, min_hold_blocked);
   if(min_hold_blocked)
   {
      PrintFormat(
         "[TS][MODIFY] blocked trade_id=%s reason=%s bars_held=%d min_hold=%d synthetic=%s target_sl=%.8f target_tp=%.8f",
         g_ts_exec_trade_id,
         modify_reason,
         g_ts_exec_bars_held,
         break_even_min_hold_bars,
         synthetic_trigger ? "true" : "false",
         new_sl,
         new_tp
      );
      return;
   }

   PrintFormat(
      "[TS][MODIFY] trigger trade_id=%s reason=%s bars_held=%d synthetic=%s target_sl=%.8f current_sl=%.8f target_tp=%.8f current_tp=%.8f",
      g_ts_exec_trade_id,
      modify_reason,
      g_ts_exec_bars_held,
      synthetic_trigger ? "true" : "false",
      new_sl,
      g_ts_exec_sl_price,
      new_tp,
      g_ts_exec_tp_price
   );
   TS_ModifyPositionByReason(modify_reason, new_sl, new_tp);
}

void TS_ExecFinalizeExitByDeal(const ulong deal_ticket, const string tx_authority)
{
   if(deal_ticket == 0)
      return;
   if(deal_ticket == g_ts_exec_last_exit_deal_logged)
   {
      if(HistoryDealSelect(deal_ticket))
         g_ts_exec_last_exit_reason = TS_ExecExitReasonFromDeal(HistoryDealGetInteger(deal_ticket, DEAL_REASON));
      g_ts_exec_exited_this_bar = true;
      if(!g_ts_exec_timer_cycle_active && g_ts_exec_pending_exit_reason == "")
         g_ts_exec_block_next_entry_bar = true;
      TS_ClearExecutionPositionState();
      TS_SavePersistedExecutionStateIfDirty();
      return;
   }
   if(!HistoryDealSelect(deal_ticket))
      return;

   const string deal_symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
   if(deal_symbol != _Symbol)
      return;

   const double exit_price = HistoryDealGetDouble(deal_ticket, DEAL_PRICE);
   const double pnl =
      HistoryDealGetDouble(deal_ticket, DEAL_PROFIT) +
      HistoryDealGetDouble(deal_ticket, DEAL_SWAP) +
      HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
   const string exit_reason = TS_ExecExitReasonFromDeal(HistoryDealGetInteger(deal_ticket, DEAL_REASON));

   TS_WriteTradeExitLog(exit_reason, "", deal_ticket, exit_price, pnl, tx_authority);
   if(g_ts_exec_broker_audit_enabled)
      TS_WriteBrokerAuditLog(
         "exit_logged",
         StringFormat("trade_id=%s tx=%s deal=%I64u reason=%s price=%.8f pnl=%.2f", g_ts_exec_trade_id, tx_authority, deal_ticket, exit_reason, exit_price, pnl)
      );
   g_ts_exec_last_exit_deal_logged = deal_ticket;
   g_ts_exec_last_exit_reason = exit_reason;
   g_ts_exec_exited_this_bar = true;
   if(!g_ts_exec_timer_cycle_active && g_ts_exec_pending_exit_reason == "")
      g_ts_exec_block_next_entry_bar = true;
   TS_ClearExecutionPositionState();
   TS_SavePersistedExecutionStateIfDirty();
}

void TS_ExecHandleDealTransaction(const ulong deal_ticket)
{
   if(deal_ticket == 0)
      return;
   if(!HistoryDealSelect(deal_ticket))
      return;

   const string deal_symbol = HistoryDealGetString(deal_ticket, DEAL_SYMBOL);
   if(deal_symbol != _Symbol)
      return;

   const long deal_entry = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
   const long deal_position_id = HistoryDealGetInteger(deal_ticket, DEAL_POSITION_ID);
   if(deal_entry == DEAL_ENTRY_IN || deal_entry == DEAL_ENTRY_INOUT)
   {
      if(PositionSelect(_Symbol))
         TS_ExecPopulateCurrentPositionSnapshot();
      if(g_ts_exec_trade_id == "")
         TS_ExecAdoptRecoveredPosition();
      TS_ExecEmitEntryLogIfNeeded(deal_ticket, "TX_DEAL");
      TS_SavePersistedExecutionStateIfDirty();
   }

   if(deal_entry == DEAL_ENTRY_OUT || deal_entry == DEAL_ENTRY_OUT_BY || deal_entry == DEAL_ENTRY_INOUT)
   {
      if(g_ts_exec_position_id != 0 && deal_position_id != 0 && deal_position_id != g_ts_exec_position_id && g_ts_exec_trade_id != "")
         return;
      TS_ExecFinalizeExitByDeal(deal_ticket, "TX_DEAL");
   }
}

void TS_ExecHandlePositionTransaction()
{
   if(!PositionSelect(_Symbol))
      return;

   TS_ExecPopulateCurrentPositionSnapshot();
   if(g_ts_exec_trade_id == "")
      TS_ExecAdoptRecoveredPosition();
   TS_ExecEmitEntryLogIfNeeded(0, "TX_POSITION");
   TS_ExecSyncPendingModifyState();
   TS_SavePersistedExecutionStateIfDirty();
}

void TS_ExecObserveTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD &&
      trans.symbol != "" &&
      trans.symbol != _Symbol)
      return;

   TS_MonitorOnTradeTransactionType(trans.type);
   if(trans.type == TRADE_TRANSACTION_REQUEST)
      TS_MonitorNoteTradeRequestResult(request.action, result.retcode, result.comment);

   if(!g_ts_exec_tx_authority_enabled)
      return;

   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      TS_ExecHandleDealTransaction(trans.deal);
      return;
   }

   if(trans.type == TRADE_TRANSACTION_POSITION)
      TS_ExecHandlePositionTransaction();
}

bool TS_TryEnterPosition(const int regime_id)
{
   if(g_ts_exec_has_position || g_ts_exec_exited_this_bar)
      return false;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
   {
      PrintFormat("[TS][EXEC][SKIP] entry tick unavailable err=%d", GetLastError());
      return false;
   }

   const int deviation_points = (g_ts_dyn_dev_points > 0) ? g_ts_dyn_dev_points : g_ts_gc_dev_points_base;
   const double entry_price = (g_ts_final_dir == 0) ? tick.ask : tick.bid;
   double sl_price = 0.0;
   double tp_price = 0.0;
   if(!TS_ExecResolveEffectiveStops(g_ts_final_dir, entry_price, sl_price, tp_price))
      return false;

   const double risk_amount = AccountInfoDouble(ACCOUNT_BALANCE) * g_ts_risk_pct;
   const double sl_dist_price = g_ts_exec_k_sl_eff * g_ts_current_atr14;
   const double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   const double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   const double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   const double lot_min = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   const double lot_max = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   if(!TS_ExecIsFiniteValue(risk_amount) || risk_amount <= 0.0 ||
      !TS_ExecIsFiniteValue(sl_dist_price) || sl_dist_price <= 0.0 ||
      !TS_ExecIsFiniteValue(tick_size) || tick_size <= 0.0 ||
      !TS_ExecIsFiniteValue(tick_value) || tick_value <= 0.0 ||
      !TS_ExecIsFiniteValue(lot_step) || lot_step <= 0.0 ||
      !TS_ExecIsFiniteValue(lot_min) || lot_min <= 0.0 ||
      !TS_ExecIsFiniteValue(lot_max) || lot_max < lot_min)
   {
      PrintFormat("[TS][EXEC][SKIP] RISK:invalid_lot_inputs risk=%.8f sl_dist=%.8f tick_size=%.8f tick_value=%.8f step=%.8f min=%.8f max=%.8f", risk_amount, sl_dist_price, tick_size, tick_value, lot_step, lot_min, lot_max);
      return false;
   }

   const double lot_raw = risk_amount * tick_size / (sl_dist_price * tick_value);
   double lot_norm = MathFloor(lot_raw / lot_step) * lot_step;
   lot_norm = NormalizeDouble(lot_norm, TS_ExecVolumeDigits(lot_step));
   if(lot_norm + TS_EPSILON < lot_min)
   {
      PrintFormat("[TS][EXEC][SKIP] RISK:lot_below_min lot_raw=%.8f lot_norm=%.8f lot_min=%.8f", lot_raw, lot_norm, lot_min);
      return false;
   }

   double lot = MathMin(lot_norm, lot_max);
   lot = NormalizeDouble(lot, TS_ExecVolumeDigits(lot_step));

   if(!TS_ExecOrderCheck(g_ts_final_dir, lot, entry_price, sl_price, tp_price, deviation_points))
      return false;

   const int provisional_trade_seq = g_ts_exec_trade_counter + 1;
   g_ts_exec_trade_seq = provisional_trade_seq;
   g_ts_exec_trade_id = TS_ExecFormatTradeId(provisional_trade_seq);
   g_ts_exec_direction = g_ts_final_dir;
   g_ts_exec_entry_time = TimeCurrent();
   g_ts_exec_entry_bar_time = iTime(_Symbol, TS_DECISION_TIMEFRAME, 0);
   g_ts_exec_entry_price = entry_price;
   g_ts_exec_sl_price = sl_price;
   g_ts_exec_tp_price = tp_price;
   g_ts_exec_lot = lot;
   g_ts_exec_bars_held = 0;
   g_ts_exec_regime_id_at_entry = regime_id;
   g_ts_exec_spread_atr_at_entry = g_ts_current_spread_atr;
   g_ts_exec_flip_used_at_entry = g_ts_flip_used;
   g_ts_exec_last_exit_reason = "";
   g_ts_exec_last_modify_reason = "";
   g_ts_exec_modify_count = 0;
   g_ts_exec_last_modify_time = 0;
   g_ts_exec_initial_sl_price = sl_price;
   g_ts_exec_initial_tp_price = tp_price;
   g_ts_exec_entry_log_emitted = false;
   TS_ClearPendingExitState();
   TS_ClearPendingModifyState();
   TS_ExecCaptureEntryVersions();

   TS_MonitorOnEntryAttempt();
   g_ts_trade.SetDeviationInPoints(deviation_points);
   g_ts_trade.SetTypeFillingBySymbol(_Symbol);

   ResetLastError();
   const bool send_ok =
      (g_ts_final_dir == 0)
      ? g_ts_trade.Buy(lot, _Symbol, 0.0, sl_price, tp_price, "TS_ENTRY")
      : g_ts_trade.Sell(lot, _Symbol, 0.0, sl_price, tp_price, "TS_ENTRY");
   if(!send_ok)
   {
      TS_MonitorNoteDirectTradeResult("ENTRY", g_ts_trade.ResultRetcode(), g_ts_trade.ResultRetcodeDescription(), false);
      TS_MonitorOnEntryRejected(g_ts_trade.ResultRetcode());
      TS_ClearExecutionPositionState();
      PrintFormat("[TS][EXEC][SKIP] entry send failed dir=%s retcode=%u desc=%s err=%d", TS_DecisionDirToString(g_ts_final_dir), g_ts_trade.ResultRetcode(), g_ts_trade.ResultRetcodeDescription(), GetLastError());
      return false;
   }

   const uint entry_retcode = g_ts_trade.ResultRetcode();
   const ulong entry_deal = g_ts_trade.ResultDeal();
   TS_MonitorNoteDirectTradeResult("ENTRY", entry_retcode, g_ts_trade.ResultRetcodeDescription(), false);
   if(!TS_ExecTradeRetcodeIsExecuted(entry_retcode))
   {
      TS_MonitorOnEntryRejected(entry_retcode);
      PrintFormat(
         "[TS][EXEC][SKIP] entry not executed dir=%s retcode=%u desc=%s order=%I64u deal=%I64u",
         TS_DecisionDirToString(g_ts_final_dir),
         entry_retcode,
         g_ts_trade.ResultRetcodeDescription(),
         g_ts_trade.ResultOrder(),
         entry_deal
      );
      TS_ClearExecutionPositionState();
      return false;
   }

   if(entry_deal == 0)
   {
      TS_MonitorOnEntryRejected(entry_retcode);
      PrintFormat(
         "[TS][EXEC][WARN] entry result missing deal dir=%s retcode=%u desc=%s order=%I64u",
         TS_DecisionDirToString(g_ts_final_dir),
         entry_retcode,
         g_ts_trade.ResultRetcodeDescription(),
         g_ts_trade.ResultOrder()
      );
      TS_ClearExecutionPositionState();
      return false;
   }

   TS_MonitorOnEntryExecuted(entry_retcode);

   g_ts_exec_trade_counter = MathMax(g_ts_exec_trade_counter, provisional_trade_seq);
   g_ts_exec_entry_price =
      (TS_ExecIsFiniteValue(g_ts_trade.ResultPrice()) && g_ts_trade.ResultPrice() > 0.0)
      ? g_ts_trade.ResultPrice()
      : entry_price;
   TS_ExecMarkStateDirty();

   if(HistoryDealSelect(entry_deal))
      g_ts_exec_position_id = (long)HistoryDealGetInteger(entry_deal, DEAL_POSITION_ID);

   if(!TS_ExecPopulateCurrentPositionSnapshot())
   {
      g_ts_exec_has_position = true;
      g_ts_exec_ticket = 0;
      TS_ExecMarkStateDirty();
   }

   TS_SavePersistedExecutionStateIfDirty();
   if(!g_ts_exec_tx_authority_enabled)
      TS_ExecEmitEntryLogIfNeeded(entry_deal, "DIRECT");
   return true;
}

bool TS_ClosePositionByReason(const string exit_reason, const string exit_detail = "")
{
   if(!g_ts_exec_has_position)
      return true;

   const bool is_early_exit = (exit_reason == "EARLY_EXIT");
   const int deviation_points = (g_ts_dyn_dev_points > 0) ? g_ts_dyn_dev_points : g_ts_gc_dev_points_base;
   ulong exit_ticket = g_ts_exec_ticket;
   if(exit_ticket == 0 && PositionSelect(_Symbol))
      exit_ticket = (ulong)PositionGetInteger(POSITION_TICKET);

   g_ts_trade.SetDeviationInPoints(deviation_points);
   g_ts_trade.SetTypeFillingBySymbol(_Symbol);

   if(is_early_exit)
      TS_MonitorOnEarlyExitAttempt();
   TS_MonitorOnExitAttempt();
   if(is_early_exit && TS_ExecConsumeTestEarlyExitRejectOnce())
   {
      TS_MonitorNoteDirectTradeResult("EXIT:" + exit_reason, TRADE_RETCODE_REJECT, "synthetic_reject_once", true);
      TS_MonitorOnExitRejected(TRADE_RETCODE_REJECT);
      TS_MonitorOnEarlyExitRejected();
      PrintFormat(
         "[TS][TEST][EARLY_EXIT] reject_once trade_id=%s detail=%s bars_held=%d p_pass=%.6f synthetic=true",
         g_ts_exec_trade_id,
         exit_detail,
         g_ts_exec_bars_held,
         g_ts_final_y[2]
      );
      return false;
   }

   TS_ExecSetPendingExitState(exit_reason, 0, 0.0);
   ResetLastError();
   const bool close_ok =
      (exit_ticket != 0)
      ? g_ts_trade.PositionClose(exit_ticket, deviation_points)
      : g_ts_trade.PositionClose(_Symbol, deviation_points);

   if(!close_ok)
   {
      TS_MonitorNoteDirectTradeResult("EXIT:" + exit_reason, g_ts_trade.ResultRetcode(), g_ts_trade.ResultRetcodeDescription(), false);
      TS_MonitorOnExitRejected(g_ts_trade.ResultRetcode());
      if(is_early_exit)
         TS_MonitorOnEarlyExitRejected();
      TS_RecordSoftFault(
         TS_PASS_REASON_DATA_GAP,
         StringFormat("position close failed reason=%s detail=%s retcode=%u desc=%s err=%d", exit_reason, exit_detail, g_ts_trade.ResultRetcode(), g_ts_trade.ResultRetcodeDescription(), GetLastError())
      );
      TS_ClearPendingExitState();
      return false;
   }

   const uint close_retcode = g_ts_trade.ResultRetcode();
   const ulong close_deal = g_ts_trade.ResultDeal();
   const double close_price =
      (TS_ExecIsFiniteValue(g_ts_trade.ResultPrice()) && g_ts_trade.ResultPrice() > 0.0)
      ? g_ts_trade.ResultPrice()
      : 0.0;
   TS_MonitorNoteDirectTradeResult("EXIT:" + exit_reason, close_retcode, g_ts_trade.ResultRetcodeDescription(), false);

   if(!TS_ExecTradeRetcodeIsExecuted(close_retcode))
   {
      TS_MonitorOnExitRejected(close_retcode);
      if(is_early_exit)
         TS_MonitorOnEarlyExitRejected();
      TS_RecordSoftFault(
         TS_PASS_REASON_DATA_GAP,
         StringFormat(
            "position close not executed reason=%s detail=%s retcode=%u desc=%s order=%I64u deal=%I64u",
            exit_reason,
            exit_detail,
            close_retcode,
            g_ts_trade.ResultRetcodeDescription(),
            g_ts_trade.ResultOrder(),
            close_deal
         )
      );
      TS_ClearPendingExitState();
      return false;
   }

   TS_MonitorOnExitExecuted(close_retcode);
   if(is_early_exit)
      TS_MonitorOnEarlyExitExecuted();

   if(close_deal == 0)
   {
      PrintFormat(
         "[TS][EXEC][WARN] position close result missing deal reason=%s retcode=%u desc=%s order=%I64u",
         exit_reason,
         close_retcode,
         g_ts_trade.ResultRetcodeDescription(),
         g_ts_trade.ResultOrder()
      );
   }

   if(!(g_ts_exec_trade_id == "" && !g_ts_exec_has_position && g_ts_exec_exited_this_bar))
      TS_ExecSetPendingExitState(exit_reason, close_deal, close_price);
   TS_SavePersistedExecutionStateIfDirty();
   const string recovery_detail =
      (exit_detail != "")
      ? (exit_reason + ":" + exit_detail)
      : exit_reason;
   if(TS_ExecRunTestRecoveryProbe(TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_EXIT, recovery_detail))
      return true;
   if(g_ts_exec_tx_authority_enabled)
      return true;
   TS_SyncPositionState();
   return true;
}

bool TS_ModifyPositionByReason(const string modify_reason, const double new_sl, const double new_tp)
{
   if(!g_ts_exec_has_position)
      return false;
   if(g_ts_exec_pending_exit_reason != "")
      return false;
   if(g_ts_exec_pending_modify_reason != "")
      return false;

   ulong modify_ticket = g_ts_exec_ticket;
   if(modify_ticket == 0 && PositionSelect(_Symbol))
      modify_ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   if(modify_ticket == 0)
      return false;

   if(!PositionSelect(_Symbol))
      return false;

   TS_MonitorOnModifyAttempt();
   if(TS_ExecConsumeTestModifyRejectOnce())
   {
      TS_MonitorNoteDirectTradeResult("MODIFY:" + modify_reason, TRADE_RETCODE_REJECT, "synthetic_reject_once", true);
      TS_MonitorOnModifyRejected();
      PrintFormat(
         "[TS][TEST][MODIFY] reject_once trade_id=%s reason=%s target_sl=%.8f target_tp=%.8f synthetic=true",
         g_ts_exec_trade_id,
         modify_reason,
         new_sl,
         new_tp
      );
      return false;
   }

   TS_ExecSetPendingModifyState(modify_reason, new_sl, new_tp);
   ResetLastError();
   const bool modify_ok = g_ts_trade.PositionModify(modify_ticket, new_sl, new_tp);
   const uint modify_retcode = g_ts_trade.ResultRetcode();
   TS_MonitorNoteDirectTradeResult("MODIFY:" + modify_reason, modify_retcode, g_ts_trade.ResultRetcodeDescription(), false);

   if(!modify_ok)
   {
      TS_MonitorOnModifyRejected();
      TS_RecordSoftFault(
         TS_PASS_REASON_DATA_GAP,
         StringFormat(
            "position modify failed reason=%s retcode=%u desc=%s err=%d",
            modify_reason,
            modify_retcode,
            g_ts_trade.ResultRetcodeDescription(),
            GetLastError()
         )
      );
      TS_ClearPendingModifyState();
      return false;
   }

   if(modify_retcode != TRADE_RETCODE_DONE &&
      modify_retcode != TRADE_RETCODE_DONE_PARTIAL &&
      modify_retcode != TRADE_RETCODE_NO_CHANGES)
   {
      TS_MonitorOnModifyRejected();
      TS_RecordSoftFault(
         TS_PASS_REASON_DATA_GAP,
         StringFormat(
            "position modify not executed reason=%s retcode=%u desc=%s",
            modify_reason,
            modify_retcode,
            g_ts_trade.ResultRetcodeDescription()
         )
      );
      TS_ClearPendingModifyState();
      return false;
   }

   if(modify_reason == "BREAK_EVEN")
      TS_ExecMarkForceBreakEvenOnceConsumed();

   TS_MonitorOnModifyExecuted();
   if(modify_retcode == TRADE_RETCODE_NO_CHANGES)
   {
      TS_ClearPendingModifyState();
      TS_SavePersistedExecutionStateIfDirty();
      return true;
   }

   TS_SavePersistedExecutionStateIfDirty();
   if(TS_ExecRunTestRecoveryProbe(TS_EXEC_TEST_RECOVERY_RELOAD_PENDING_MODIFY, modify_reason))
      return true;
   if(g_ts_exec_tx_authority_enabled)
      return true;
   TS_SyncPositionState();
   return true;
}

bool TS_ForceExitPosition(const string exit_reason)
{
   return TS_ClosePositionByReason(exit_reason);
}

#endif // __TS_EXECUTION_MQH__
