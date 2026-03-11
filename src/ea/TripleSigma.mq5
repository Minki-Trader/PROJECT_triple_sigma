#property strict
// MT5 platform version display (format: "X.XXX", shown in Terminal UI).
// Project semantic version is TS_VER_EA in TS_Defines.mqh and is used in logs.
#property version "1.000"
#property description "PROJECT_triple_sigma STEP21 tx-authoritative protective runtime"
#property tester_file "triple_sigma_pack_v1\\pack_meta.csv"
#property tester_file "triple_sigma_pack_v1\\scaler_stats.json"
#property tester_file "triple_sigma_pack_v1\\gate_config.json"
#property tester_file "triple_sigma_pack_v1\\clf_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\clf_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\clf_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\clf_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\clf_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\clf_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_v1\\prm_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\pack_meta.csv"
#property tester_file "triple_sigma_pack_step15_q1\\scaler_stats.json"
#property tester_file "triple_sigma_pack_step15_q1\\gate_config.json"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\clf_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_step15_q1\\prm_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\pack_meta.csv"
#property tester_file "triple_sigma_pack_long_step16\\scaler_stats.json"
#property tester_file "triple_sigma_pack_long_step16\\gate_config.json"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\clf_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg0_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg1_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg2_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg3_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg4_v0.1.0.onnx"
#property tester_file "triple_sigma_pack_long_step16\\prm_reg5_v0.1.0.onnx"
#property tester_file "triple_sigma_runtime_patch\\step21_runtime_reload_success.ini"
#property tester_file "triple_sigma_runtime_patch\\step21_runtime_reload_rollback.ini"

#include "..\\include\\TS_Defines.mqh"
#include "..\\include\\TS_PassOnly.mqh"
#include "..\\include\\TS_DataIngest.mqh"
#include "..\\include\\TS_PackMeta.mqh"
#include "..\\include\\TS_Indicators.mqh"
#include "..\\include\\TS_Features.mqh"
#include "..\\include\\TS_Models.mqh"
#include "..\\include\\TS_Decision.mqh"
#include "..\\include\\TS_Gates.mqh"
#include "..\\include\\TS_Execution.mqh"
#include "..\\include\\TS_Logger.mqh"
#include "..\\include\\TS_Monitor.mqh"

input bool InpStartupValidation = true;
input bool InpLogHeartbeat = false;
input int InpTimerSeconds = 1;
input bool InpDebugAlignment = false;
input string InpModelPackDir = "triple_sigma_pack_v1";
input double InpPMinTrade = 0.55;
input double InpDeltaFlip = 0.20;
input double InpSpreadAtrMaxBase = 0.30;
input double InpSpreadAtrMaxHard = 0.60;
input double InpKTPScaleMin = 1.0;
input double InpKTPScaleMax = 6.0;
input int InpDevPointsBase = 3;
input int InpDevPointsAddMax = 5;
input int InpDevPointsHardMax = 10;
input double InpRiskPctBase = 0.01;
input double InpRiskPctHardMin = 0.002;
input double InpRiskPctHardMax = 0.03;
input int InpBlockWeekOpenMinutes = 5;
input int InpBlockRolloverMinutes = 5;
// STEP17 keeps the post-decision early-exit family feature-flagged.
// `InpEarlyExitLive=false` preserves the shadow-only STEP16 behavior.
input bool InpEarlyExitEnabled = false;
input bool InpEarlyExitLive = false;
input bool InpEarlyExitOppositeEnabled = false;
input double InpPExitPass = 0.70;
input int InpMinHoldBarsBeforeExit = 3;
input bool InpProtectiveAdjustEnabled = false;
input bool InpBreakEvenEnabled = false;
input double InpBreakEvenRRTrigger = 1.0;
input int InpBreakEvenMinHoldBars = 3;
input int InpBreakEvenOffsetPoints = 0;
input bool InpTrailingEnabled = false;
input double InpTrailingStartRR = 1.50;
input double InpTrailingAtrMultiple = 1.00;
input int InpTrailingStepPoints = 5;
input bool InpTPReshapeEnabled = false;
input double InpTPReshapeRRTrigger = 1.00;
input double InpTPReshapeTargetRR = 1.25;
input bool InpTimePolicyEnabled = false;
input int InpTimePolicyAfterBars = 24;
input double InpTimePolicyStopLockRR = 0.25;
input double InpTimePolicyTPScale = 0.75;
input bool InpTxAuthorityEnabled = true;
input bool InpBrokerAuditEnabled = false;
input bool InpRuntimeHotReloadEnabled = false;
input bool InpRuntimeRollbackOnFailure = true;
input string InpRuntimePatchFile = "";
// Tester-only close-reject injection for the first EARLY_EXIT attempt.
input bool InpTestEarlyExitRejectOnce = false;
// Tester-only trigger fabrication for the opposite-direction close-only branch.
input bool InpTestForceOppositeEarlyExit = false;
// Tester-only trigger/reject fabrication for BE-only modify coverage.
input bool InpTestForceBreakEvenOnce = false;
input bool InpTestModifyRejectOnce = false;
// Tester-only execution-state recovery probe. Defaults keep production semantics unchanged.
input bool InpTestRecoveryReloadEnabled = false;
input int InpTestRecoveryReloadMode = 0;
input int InpTestRecoveryReloadBarsHeld = 3;

int OnInit()
{
   TS_ResetPassOnlyState();
   TS_ResetDataIngestState();
   TS_ResetIndicatorState();
   TS_ResetLoggerState();
   TS_ResetMonitorState();
   TS_ResetPackMetaState();
   TS_ResetFeatureState();
   TS_ResetCandidateState();
   TS_ResetModelState();
   TS_ResetDecisionState();
   TS_ResetGateState();
   TS_ResetExecutionState();
   TS_ExecConfigureTestEarlyExitRejectOnce(InpTestEarlyExitRejectOnce);
   TS_ExecConfigureTestForceOppositeEarlyExit(InpTestForceOppositeEarlyExit);
   TS_ExecConfigureTestForceBreakEvenOnce(InpTestForceBreakEvenOnce);
   TS_ExecConfigureTestModifyRejectOnce(InpTestModifyRejectOnce);
   TS_ExecConfigureTestRecoveryReload(
      InpTestRecoveryReloadEnabled,
      InpTestRecoveryReloadMode,
      InpTestRecoveryReloadBarsHeld
   );
   TS_ExecConfigureTxAuthority(InpTxAuthorityEnabled);
   TS_ExecConfigureBrokerAudit(InpBrokerAuditEnabled);
   TS_ExecConfigureRuntimeHotReload(
      InpRuntimeHotReloadEnabled,
      InpRuntimeRollbackOnFailure,
      InpRuntimePatchFile,
      InpModelPackDir
   );
   TS_LoadPersistedDataIngestState();
   TS_LoadPersistedExecutionState();
   TS_LogVersionSnapshot();
   if(InpBrokerAuditEnabled)
      TS_WriteBrokerAuditLog("init", "");

   if(InpStartupValidation)
   {
      if(!TS_ValidateStaticContract())
      {
         TS_LatchPassOnly(TS_PASS_REASON_SCHEMA_VERSION_MISMATCH, "static contract validation failed");
      }
   }

   if(!TS_IsPassOnlyLatched())
      TS_ValidateFeatureIndex();

   if(!TS_IsPassOnlyLatched())
      TS_SetGateConfigDefaults(
         InpSpreadAtrMaxBase,
         InpSpreadAtrMaxHard,
         InpKTPScaleMin,
         InpKTPScaleMax,
         InpDevPointsBase,
         InpDevPointsAddMax,
         InpDevPointsHardMax,
         InpRiskPctBase,
         InpRiskPctHardMin,
         InpRiskPctHardMax
      );

   string startup_model_pack_dir = g_ts_exec_active_model_pack_dir;
   if(startup_model_pack_dir == "")
      startup_model_pack_dir = InpModelPackDir;

   if(!TS_IsPassOnlyLatched())
      TS_LoadPackMeta(startup_model_pack_dir);

   if(!TS_IsPassOnlyLatched())
      TS_LoadScaler(startup_model_pack_dir);

   if(!TS_IsPassOnlyLatched())
      TS_LoadGateConfig(startup_model_pack_dir);

   if(!TS_IsPassOnlyLatched())
      TS_LoadModels(startup_model_pack_dir);

   if(!TS_IsPassOnlyLatched())
      TS_InitIndicatorHandles();

   const int timer_sec = (InpTimerSeconds < 1) ? 1 : InpTimerSeconds;
   EventSetTimer(timer_sec);

   PrintFormat(
      "[TS] OnInit symbol=%s timeframe=%s timer=%d model_pack_dir=%s p_min_trade=%.4f delta_flip=%.4f gate_cfg_loaded=%s block_week_open=%d block_rollover=%d early_exit=[enabled:%s live:%s opposite:%s p_pass:%.4f min_hold:%d reject_once:%s force_opposite:%s] protective=[enabled:%s be:%s rr:%.4f min_hold:%d offset:%d trailing:%s start_rr:%.4f atr_mult:%.4f step:%d tp_reshape:%s tp_rr:%.4f tp_target_rr:%.4f time:%s after:%d lock_rr:%.4f tp_scale:%.4f force_be:%s reject_once:%s] tx_authority=%s runtime_reload=[enabled:%s rollback:%s patch:%s] broker_audit=%s pass_only=%s",
      _Symbol,
      EnumToString(TS_DECISION_TIMEFRAME),
      timer_sec,
      startup_model_pack_dir,
      InpPMinTrade,
      InpDeltaFlip,
      g_ts_gate_config_loaded ? "true" : "false",
      InpBlockWeekOpenMinutes,
      InpBlockRolloverMinutes,
      InpEarlyExitEnabled ? "true" : "false",
      InpEarlyExitLive ? "true" : "false",
      InpEarlyExitOppositeEnabled ? "true" : "false",
      InpPExitPass,
      InpMinHoldBarsBeforeExit,
      InpTestEarlyExitRejectOnce ? "true" : "false",
      InpTestForceOppositeEarlyExit ? "true" : "false",
      InpProtectiveAdjustEnabled ? "true" : "false",
      InpBreakEvenEnabled ? "true" : "false",
      InpBreakEvenRRTrigger,
      InpBreakEvenMinHoldBars,
      InpBreakEvenOffsetPoints,
      InpTrailingEnabled ? "true" : "false",
      InpTrailingStartRR,
      InpTrailingAtrMultiple,
      InpTrailingStepPoints,
      InpTPReshapeEnabled ? "true" : "false",
      InpTPReshapeRRTrigger,
      InpTPReshapeTargetRR,
      InpTimePolicyEnabled ? "true" : "false",
      InpTimePolicyAfterBars,
      InpTimePolicyStopLockRR,
      InpTimePolicyTPScale,
      InpTestForceBreakEvenOnce ? "true" : "false",
      InpTestModifyRejectOnce ? "true" : "false",
      InpTxAuthorityEnabled ? "true" : "false",
      InpRuntimeHotReloadEnabled ? "true" : "false",
      InpRuntimeRollbackOnFailure ? "true" : "false",
      InpRuntimePatchFile,
      InpBrokerAuditEnabled ? "true" : "false",
      TS_IsPassOnlyLatched() ? "true" : "false"
   );

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   TS_SavePersistedDataIngestState();
   PrintFormat("[TS] OnDeinit reason=%d", reason);
   TS_LogDataIngestState();
   TS_LogPackMetaState();
   TS_LogIndicatorState();
   TS_LogFeatureState();
   TS_LogCandidateState();
   TS_LogModelState();
   TS_LogDecisionState();
   TS_LogGateState();
   TS_LogExecutionState();
   TS_LogPassOnlyState();
   TS_MonitorEmitSummary("deinit");
   TS_SavePersistedExecutionState();
   if(InpBrokerAuditEnabled)
      TS_WriteBrokerAuditLog("deinit", "");
   TS_CloseLoggerHandles();
   TS_ReleaseModels();
   TS_ReleaseIndicatorHandles();
}

void OnTick()
{
   TS_UpdateLatestTickSnapshot();
}

void OnTradeTransaction(
   const MqlTradeTransaction &trans,
   const MqlTradeRequest &request,
   const MqlTradeResult &result
)
{
   TS_ExecObserveTradeTransaction(trans, request, result);
}

void OnTimer()
{
   bool bar_level_pass = false;
   const bool has_new_closed_bar = TS_TryProcessNewClosedBarOnTimer(bar_level_pass);
   if(!has_new_closed_bar)
      return;

   TS_MonitorOnBarBegin();
   TS_ExecOnBarCycleBegin();

   int regime_id = -1;
   double y_stage1[];
   double y_stage2[];
   bool inference_attempted = false;
   bool inference_ok = false;
   bool decision_attempted = false;
   bool decision_ok = false;
   bool gate_attempted = false;
   bool gate_ok = false;

   TS_ResetExecutionBarState();
   TS_SyncPositionState();
   TS_ExecMaybeApplyRuntimePatch();
   if(g_ts_exec_has_position)
      TS_ManagePositionPreDecision();

   TS_ResetFeatureBarState();
   TS_ResetCandidateBarState();
   TS_ResetModelBarState();
   TS_ResetDecisionState();
   TS_ResetGateBarState();

   if(!TS_IsPassOnlyLatched() && !bar_level_pass)
   {
      bool indicator_bar_level_pass = false;
      TS_UpdateIndicatorsOnNewBar(indicator_bar_level_pass, InpDebugAlignment);

      if(!indicator_bar_level_pass)
      {
         bool feature_bar_level_pass = false;
         TS_UpdateFeaturesOnNewBar(feature_bar_level_pass, InpDebugAlignment);

         if(!feature_bar_level_pass)
         {
            if(TS_UpdateCandidateOnNewBar() &&
               TS_GetLatestRegimeIdFromTensor(regime_id) &&
               TS_PrepareScaledTensor())
            {
               if(InpDebugAlignment && g_ts_bar_count > 0)
                  TS_WriteTensorDebugSnapshot(g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t);

               inference_attempted = true;
               inference_ok = TS_RunInference(regime_id, y_stage1, y_stage2);
               decision_attempted = true;
               decision_ok = TS_AssembleDecision(inference_ok, InpPMinTrade, InpDeltaFlip);
               gate_attempted = true;
               gate_ok = TS_EvaluateGates(InpPMinTrade, InpBlockWeekOpenMinutes, InpBlockRolloverMinutes);

               if(InpEarlyExitEnabled)
               {
                  if(InpEarlyExitLive)
                  {
                     TS_ManagePositionPostDecisionLiveEarlyExitCloseOnly(
                        InpEarlyExitOppositeEnabled,
                        InpPExitPass,
                        InpMinHoldBarsBeforeExit
                     );
                  }
                  else
                  {
                     TS_ManagePositionPostDecisionShadow(
                        true,
                        InpPExitPass,
                        InpMinHoldBarsBeforeExit
                     );
                  }
               }

               if(InpProtectiveAdjustEnabled &&
                  g_ts_exec_has_position &&
                  !g_ts_exec_exited_this_bar &&
                  g_ts_exec_pending_exit_reason == "")
               {
                  TS_ManagePositionPostDecisionLiveProtectiveAdjustments(
                     InpBreakEvenEnabled,
                     InpBreakEvenRRTrigger,
                     InpBreakEvenMinHoldBars,
                     InpBreakEvenOffsetPoints,
                     InpTrailingEnabled,
                     InpTrailingStartRR,
                     InpTrailingAtrMultiple,
                     InpTrailingStepPoints,
                     InpTPReshapeEnabled,
                     InpTPReshapeRRTrigger,
                     InpTPReshapeTargetRR,
                     InpTimePolicyEnabled,
                     InpTimePolicyAfterBars,
                     InpTimePolicyStopLockRR,
                     InpTimePolicyTPScale
                  );
               }

               if(!g_ts_exec_has_position &&
                  !g_ts_exec_exited_this_bar &&
                  g_ts_current_entry_allowed &&
                  g_ts_decision_ready &&
                  g_ts_final_dir != 2 &&
                  g_ts_gate_pass)
               {
                  TS_TryEnterPosition(regime_id);
               }
            }
            else if(!TS_IsPassOnlyLatched())
            {
               TS_LatchPassOnly(TS_PASS_REASON_SHAPE_DTYPE_MISMATCH, "latest regime one-hot invalid");
            }
         }
      }
   }

   if(!inference_attempted)
      TS_MonitorOnInferenceSkipped();
   if(!decision_attempted)
      TS_MonitorOnDecisionSkipped();
   if(!gate_attempted)
      TS_MonitorOnGateSkipped();

   if(!TS_WriteBarLog(regime_id))
      Print("[TS][LOG][WARN] bar log append failed");

   if(InpLogHeartbeat)
   {
      PrintFormat(
         "[TS][STEP10] OnTimer processed closed bar. pass_only=%s bar_level_pass=%s window_ready=%s pack_meta_ready=%s indicators_ready=%s x_ready=%s models_ready=%s inference_ok=%s decision_ready=%s gate_eval_ok=%s regime_id=%d entry_allowed=%s cand_long=%d cand_short=%d dist_atr_max=%.6f scaler_mode=%s stage1=[%.6f,%.6f,%.6f] model_dir=%s stage2=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f] final_dir=%s flip_used=%s final=[%.6f,%.6f,%d] final_y=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f] fail_safe_reason=%s gate_pass=%s gate_reason=%s spread_atr_raw=%.6f atr14_raw=%.8f dyn_spread_atr_max=%.6f dyn_dev_points=%d risk_pct=%.6f needs_sl_adjustment=%s order_constraint_hard_reject=%s min_stop_distance_points=%d has_position=%s trade_id=%s bars_held=%d exited_this_bar=%s entry_bar_time=%s",
         TS_IsPassOnlyLatched() ? "true" : "false",
         bar_level_pass ? "true" : "false",
         TS_IsWindowReady() ? "true" : "false",
         g_ts_pack_meta_ready ? "true" : "false",
         g_ts_indicators_ready ? "true" : "false",
         g_ts_x_ready ? "true" : "false",
         g_ts_models_ready ? "true" : "false",
         inference_ok ? "true" : "false",
         decision_ok && g_ts_decision_ready ? "true" : "false",
         gate_ok ? "true" : "false",
         regime_id,
         g_ts_current_entry_allowed ? "true" : "false",
         g_ts_current_cand_long,
         g_ts_current_cand_short,
         g_ts_current_dist_atr_max,
         g_ts_scaler_mode,
         g_ts_stage1_last[0],
         g_ts_stage1_last[1],
         g_ts_stage1_last[2],
         g_ts_last_model_dir_name,
         g_ts_stage2_last[0],
         g_ts_stage2_last[1],
         g_ts_stage2_last[2],
         g_ts_stage2_last[3],
         g_ts_stage2_last[4],
         g_ts_stage2_last[5],
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
         g_ts_fail_safe_reason,
         g_ts_gate_pass ? "true" : "false",
         g_ts_gate_reject_reason,
         g_ts_current_spread_atr,
         g_ts_current_atr14,
         g_ts_dyn_spread_atr_max,
         g_ts_dyn_dev_points,
         g_ts_risk_pct,
         g_ts_needs_sl_adjustment ? "true" : "false",
         g_ts_order_constraint_hard_reject ? "true" : "false",
         g_ts_min_stop_distance_points,
         g_ts_exec_has_position ? "true" : "false",
         g_ts_exec_trade_id,
         g_ts_exec_bars_held,
         g_ts_exec_exited_this_bar ? "true" : "false",
         TimeToString(g_ts_exec_entry_bar_time, TIME_DATE | TIME_MINUTES)
      );
   }

   TS_ExecOnBarCycleEnd();
   TS_MonitorOnBarEnd(regime_id);
}
