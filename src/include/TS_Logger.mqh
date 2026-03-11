#ifndef __TS_LOGGER_MQH__
#define __TS_LOGGER_MQH__

#include "TS_Defines.mqh"
#include "TS_Execution.mqh"

int g_ts_bar_log_handle = INVALID_HANDLE;
int g_ts_trade_log_handle = INVALID_HANDLE;
string g_ts_bar_log_day = "";

bool TS_LogEnsureDir()
{
   ResetLastError();
   FolderCreate(TS_LOG_DIR);
   return true;
}

string TS_CsvEscape(const string value)
{
   string out = value;
   StringReplace(out, "\"", "\"\"");
   if(StringFind(out, ",") >= 0 || StringFind(out, "\"") >= 0)
      out = "\"" + out + "\"";
   return out;
}

void TS_CsvAppend(string &line, const string value)
{
   if(line != "")
      line += ",";
   line += TS_CsvEscape(value);
}

bool TS_WriteCsvLine(const string rel_path, const string header, const string line)
{
   TS_LogEnsureDir();

   ResetLastError();
   const int handle = FileOpen(rel_path, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[TS][LOG][WARN] open failed path=%s err=%d", rel_path, GetLastError());
      return false;
   }

   const bool need_header = (FileSize(handle) <= 0);
   FileSeek(handle, 0, SEEK_END);
   if(need_header)
      FileWriteString(handle, header + "\r\n");
   FileWriteString(handle, line + "\r\n");
   FileClose(handle);
   return true;
}

void TS_CloseBarLogHandle()
{
   if(g_ts_bar_log_handle == INVALID_HANDLE)
      return;

   FileFlush(g_ts_bar_log_handle);
   FileClose(g_ts_bar_log_handle);
   g_ts_bar_log_handle = INVALID_HANDLE;
   g_ts_bar_log_day = "";
}

void TS_CloseTradeLogHandle()
{
   if(g_ts_trade_log_handle == INVALID_HANDLE)
      return;

   FileFlush(g_ts_trade_log_handle);
   FileClose(g_ts_trade_log_handle);
   g_ts_trade_log_handle = INVALID_HANDLE;
}

void TS_CloseLoggerHandles()
{
   TS_CloseBarLogHandle();
   TS_CloseTradeLogHandle();
}

void TS_ResetLoggerState()
{
   TS_CloseLoggerHandles();
}

bool TS_LogOpenAppendHandle(const string rel_path, const string header, int &handle)
{
   TS_LogEnsureDir();

   ResetLastError();
   handle = FileOpen(rel_path, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[TS][LOG][WARN] open failed path=%s err=%d", rel_path, GetLastError());
      return false;
   }

   const bool need_header = (FileSize(handle) <= 0);
   if(!FileSeek(handle, 0, SEEK_END))
   {
      PrintFormat("[TS][LOG][WARN] seek failed path=%s err=%d", rel_path, GetLastError());
      FileClose(handle);
      handle = INVALID_HANDLE;
      return false;
   }
   if(need_header)
   {
      const uint header_bytes = (uint)FileWriteString(handle, header + "\r\n");
      if(header_bytes == 0)
      {
         PrintFormat("[TS][LOG][WARN] header write failed path=%s err=%d", rel_path, GetLastError());
         FileClose(handle);
         handle = INVALID_HANDLE;
         return false;
      }
      FileFlush(handle);
   }

   return true;
}

bool TS_LogAppendLine(const int handle, const string line)
{
   if(handle == INVALID_HANDLE)
      return false;

   if(!FileSeek(handle, 0, SEEK_END))
   {
      PrintFormat("[TS][LOG][WARN] append seek failed err=%d", GetLastError());
      return false;
   }

   const uint bytes_written = (uint)FileWriteString(handle, line + "\r\n");
   if(bytes_written == 0)
   {
      PrintFormat("[TS][LOG][WARN] append write failed err=%d", GetLastError());
      return false;
   }

   FileFlush(handle);
   return true;
}

string TS_BuildBarLogHeader()
{
   string line = "";
   TS_CsvAppend(line, "time");
   TS_CsvAppend(line, "symbol");
   TS_CsvAppend(line, "timeframe");
   TS_CsvAppend(line, "price_basis");
   TS_CsvAppend(line, "open");
   TS_CsvAppend(line, "high");
   TS_CsvAppend(line, "low");
   TS_CsvAppend(line, "close");
   TS_CsvAppend(line, "spread_points");
   TS_CsvAppend(line, "atr14");
   TS_CsvAppend(line, "adx14");
   TS_CsvAppend(line, "atr_pct");
   TS_CsvAppend(line, "regime_id");
   TS_CsvAppend(line, "cand_long");
   TS_CsvAppend(line, "cand_short");
   TS_CsvAppend(line, "entry_allowed");

   for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
      TS_CsvAppend(line, StringFormat("feature_%d", f));

   TS_CsvAppend(line, "onnx_p_long");
   TS_CsvAppend(line, "onnx_p_short");
   TS_CsvAppend(line, "onnx_p_pass");
   TS_CsvAppend(line, "stage1_argmax");

   for(int i = 0; i < 6; ++i)
      TS_CsvAppend(line, StringFormat("prm_raw_%d", i));

   TS_CsvAppend(line, "final_dir");
   TS_CsvAppend(line, "flip_used");
   TS_CsvAppend(line, "k_sl_req");
   TS_CsvAppend(line, "k_tp_req");
   TS_CsvAppend(line, "k_sl_eff");
   TS_CsvAppend(line, "k_tp_eff");
   TS_CsvAppend(line, "hold_bars");
   TS_CsvAppend(line, "gate_pass");
   TS_CsvAppend(line, "gate_reject_reason");
   TS_CsvAppend(line, "dyn_spread_atr_max");
   TS_CsvAppend(line, "dyn_dev_points");
   TS_CsvAppend(line, "risk_pct");
   TS_CsvAppend(line, "dist_atr");
   TS_CsvAppend(line, "dist_atr_max_t");
   TS_CsvAppend(line, "dist_atr_max_mode");
   TS_CsvAppend(line, "has_position");
   TS_CsvAppend(line, "bars_held");
   TS_CsvAppend(line, "ea_version");
   TS_CsvAppend(line, "schema_version");
   TS_CsvAppend(line, "candidate_policy_version");
   TS_CsvAppend(line, "regime_policy_version");
   TS_CsvAppend(line, "model_pack_version");
   TS_CsvAppend(line, "clf_version");
   TS_CsvAppend(line, "prm_version");
   TS_CsvAppend(line, "cost_model_version");
   TS_CsvAppend(line, "pending_exit_reason");
   TS_CsvAppend(line, "pending_modify_reason");
   TS_CsvAppend(line, "last_modify_reason");
   TS_CsvAppend(line, "modify_count");
   TS_CsvAppend(line, "be_applied");
   TS_CsvAppend(line, "entry_log_emitted");
   TS_CsvAppend(line, "tx_authority_enabled");
   TS_CsvAppend(line, "broker_audit_enabled");
   TS_CsvAppend(line, "active_model_pack_dir");
   TS_CsvAppend(line, "pack_dir_at_entry");
   TS_CsvAppend(line, "runtime_reload_attempts");
   TS_CsvAppend(line, "runtime_reload_successes");
   TS_CsvAppend(line, "runtime_reload_rollbacks");
   TS_CsvAppend(line, "runtime_reload_status");
   TS_CsvAppend(line, "log_schema_version");
   return line;
}

string TS_BuildTradeLogHeader()
{
   string line = "";
   TS_CsvAppend(line, "trade_id");
   TS_CsvAppend(line, "timestamp");
   TS_CsvAppend(line, "symbol");
   TS_CsvAppend(line, "event_type");
   TS_CsvAppend(line, "direction");
   TS_CsvAppend(line, "lot");
   TS_CsvAppend(line, "entry_price");
   TS_CsvAppend(line, "exit_price");
   TS_CsvAppend(line, "sl_price");
   TS_CsvAppend(line, "tp_price");
   TS_CsvAppend(line, "pnl");
   TS_CsvAppend(line, "k_sl_req");
   TS_CsvAppend(line, "k_tp_req");
   TS_CsvAppend(line, "k_sl_eff");
   TS_CsvAppend(line, "k_tp_eff");
   TS_CsvAppend(line, "hold_bars");
   TS_CsvAppend(line, "bars_held");
   TS_CsvAppend(line, "exit_reason");
   TS_CsvAppend(line, "regime_id_at_entry");
   TS_CsvAppend(line, "spread_atr_at_entry");
   TS_CsvAppend(line, "flip_used");
   TS_CsvAppend(line, "model_pack_version");
   TS_CsvAppend(line, "clf_version");
   TS_CsvAppend(line, "prm_version");
   TS_CsvAppend(line, "cost_model_version");
   TS_CsvAppend(line, "event_detail");
   TS_CsvAppend(line, "deal_ticket");
   TS_CsvAppend(line, "position_id");
   TS_CsvAppend(line, "modify_reason");
   TS_CsvAppend(line, "modify_count");
   TS_CsvAppend(line, "tx_authority");
   TS_CsvAppend(line, "pack_dir_at_entry");
   TS_CsvAppend(line, "active_model_pack_dir");
   TS_CsvAppend(line, "runtime_reload_status");
   TS_CsvAppend(line, "ea_version");
   TS_CsvAppend(line, "log_schema_version");
   return line;
}

string TS_BuildBrokerAuditHeader()
{
   string line = "";
   TS_CsvAppend(line, "timestamp");
   TS_CsvAppend(line, "symbol");
   TS_CsvAppend(line, "tag");
   TS_CsvAppend(line, "detail");
   TS_CsvAppend(line, "trade_id");
   TS_CsvAppend(line, "position_id");
   TS_CsvAppend(line, "pending_exit_reason");
   TS_CsvAppend(line, "pending_modify_reason");
   TS_CsvAppend(line, "modify_count");
   TS_CsvAppend(line, "active_model_pack_dir");
   TS_CsvAppend(line, "pack_dir_at_entry");
   TS_CsvAppend(line, "tx_authority_enabled");
   TS_CsvAppend(line, "runtime_reload_status");
   TS_CsvAppend(line, "account_login");
   TS_CsvAppend(line, "account_server");
   TS_CsvAppend(line, "ea_version");
   TS_CsvAppend(line, "log_schema_version");
   return line;
}

string TS_BarLogRelPath()
{
   datetime bar_time = TimeCurrent();
   if(g_ts_bar_count > 0)
      bar_time = g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;
   string day_str = TimeToString(bar_time, TIME_DATE);
   StringReplace(day_str, ".", "");
   return TS_LOG_DIR + "\\" + StringFormat("bar_log_%s.csv", day_str);
}

string TS_TradeLogRelPath()
{
   return TS_LOG_DIR + "\\trade_log.csv";
}

string TS_BrokerAuditRelPath()
{
   return TS_LOG_DIR + "\\broker_audit.csv";
}

string TS_TensorDebugRelPath()
{
   return TS_LOG_DIR + "\\tensor_debug.csv";
}

bool TS_EnsureBarLogHandle()
{
   datetime bar_time = TimeCurrent();
   if(g_ts_bar_count > 0)
      bar_time = g_ts_bar_buffer[g_ts_bar_count - 1].bar_time_t;

   string day_str = TimeToString(bar_time, TIME_DATE);
   StringReplace(day_str, ".", "");

   if(g_ts_bar_log_handle != INVALID_HANDLE && g_ts_bar_log_day == day_str)
      return true;

   TS_CloseBarLogHandle();

   const string rel_path = TS_LOG_DIR + "\\" + StringFormat("bar_log_%s.csv", day_str);
   if(!TS_LogOpenAppendHandle(rel_path, TS_BuildBarLogHeader(), g_ts_bar_log_handle))
      return false;

   g_ts_bar_log_day = day_str;
   return true;
}

bool TS_EnsureTradeLogHandle()
{
   if(g_ts_trade_log_handle != INVALID_HANDLE)
      return true;

   return TS_LogOpenAppendHandle(TS_TradeLogRelPath(), TS_BuildTradeLogHeader(), g_ts_trade_log_handle);
}

string TS_BuildTensorDebugHeader()
{
   string line = "";
   TS_CsvAppend(line, "decision_time");
   TS_CsvAppend(line, "window_pos");
   TS_CsvAppend(line, "row_time");
   TS_CsvAppend(line, "dist_atr_max_t");
   for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
      TS_CsvAppend(line, StringFormat("feature_%d", f));
   return line;
}

void TS_TradeLogAppendSuffix(
   string &line,
   const string event_detail,
   const ulong deal_ticket,
   const string modify_reason,
   const string tx_authority
)
{
   TS_CsvAppend(line, event_detail);
   TS_CsvAppend(line, StringFormat("%I64u", deal_ticket));
   TS_CsvAppend(line, StringFormat("%I64d", g_ts_exec_position_id));
   TS_CsvAppend(line, modify_reason);
   TS_CsvAppend(line, IntegerToString(g_ts_exec_modify_count));
   TS_CsvAppend(line, tx_authority);
   TS_CsvAppend(line, g_ts_exec_pack_dir_at_entry);
   TS_CsvAppend(line, g_ts_exec_active_model_pack_dir);
   TS_CsvAppend(line, g_ts_exec_last_runtime_reload_status);
   TS_CsvAppend(line, TS_VER_EA);
   TS_CsvAppend(line, TS_VER_LOG_SCHEMA);
}

void TS_WriteTradeEntryLog(const ulong deal_ticket, const string tx_authority)
{
   if(!TS_EnsureTradeLogHandle())
      return;

   string line = "";
   TS_CsvAppend(line, g_ts_exec_trade_id);
   TS_CsvAppend(line, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   TS_CsvAppend(line, _Symbol);
   TS_CsvAppend(line, "ENTRY");
   TS_CsvAppend(line, TS_DecisionDirToString(g_ts_exec_direction));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_lot, 4));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_entry_price, 8));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, DoubleToString(g_ts_exec_sl_price, 8));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_tp_price, 8));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_eff, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_eff, 6));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_hold_bars_soft));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_bars_held));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, IntegerToString(g_ts_exec_regime_id_at_entry));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_spread_atr_at_entry, 6));
   TS_CsvAppend(line, g_ts_exec_flip_used_at_entry ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_pack_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_clf_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_prm_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_cost_ver_at_entry);
   TS_TradeLogAppendSuffix(line, "", deal_ticket, "", tx_authority);

   if(!TS_LogAppendLine(g_ts_trade_log_handle, line))
      PrintFormat("[TS][LOG][WARN] trade entry append failed trade_id=%s", g_ts_exec_trade_id);
}

void TS_WriteTradeExitLog(
   const string exit_reason,
   const string event_detail,
   const ulong deal_ticket,
   const double exit_price,
   const double pnl,
   const string tx_authority
)
{
   if(!TS_EnsureTradeLogHandle())
      return;

   string line = "";
   TS_CsvAppend(line, g_ts_exec_trade_id);
   TS_CsvAppend(line, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   TS_CsvAppend(line, _Symbol);
   TS_CsvAppend(line, "EXIT");
   TS_CsvAppend(line, TS_DecisionDirToString(g_ts_exec_direction));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_lot, 4));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_entry_price, 8));
   TS_CsvAppend(line, DoubleToString(exit_price, 8));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_sl_price, 8));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_tp_price, 8));
   TS_CsvAppend(line, DoubleToString(pnl, 2));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_eff, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_eff, 6));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_hold_bars_soft));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_bars_held));
   TS_CsvAppend(line, exit_reason);
   TS_CsvAppend(line, IntegerToString(g_ts_exec_regime_id_at_entry));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_spread_atr_at_entry, 6));
   TS_CsvAppend(line, g_ts_exec_flip_used_at_entry ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_pack_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_clf_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_prm_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_cost_ver_at_entry);
   TS_TradeLogAppendSuffix(line, event_detail, deal_ticket, "", tx_authority);

   if(!TS_LogAppendLine(g_ts_trade_log_handle, line))
      PrintFormat("[TS][LOG][WARN] trade exit append failed trade_id=%s", g_ts_exec_trade_id);
}

void TS_WriteTradeModifyLog(
   const string modify_reason,
   const string event_detail,
   const ulong deal_ticket,
   const double new_sl,
   const double new_tp,
   const string tx_authority
)
{
   if(!TS_EnsureTradeLogHandle())
      return;

   string line = "";
   TS_CsvAppend(line, g_ts_exec_trade_id);
   TS_CsvAppend(line, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   TS_CsvAppend(line, _Symbol);
   TS_CsvAppend(line, "MODIFY");
   TS_CsvAppend(line, TS_DecisionDirToString(g_ts_exec_direction));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_lot, 4));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_entry_price, 8));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, DoubleToString(new_sl, 8));
   TS_CsvAppend(line, DoubleToString(new_tp, 8));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_eff, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_eff, 6));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_hold_bars_soft));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_bars_held));
   TS_CsvAppend(line, "");
   TS_CsvAppend(line, IntegerToString(g_ts_exec_regime_id_at_entry));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_spread_atr_at_entry, 6));
   TS_CsvAppend(line, g_ts_exec_flip_used_at_entry ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_pack_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_clf_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_prm_ver_at_entry);
   TS_CsvAppend(line, g_ts_exec_cost_ver_at_entry);
   TS_TradeLogAppendSuffix(line, event_detail, deal_ticket, modify_reason, tx_authority);

   if(!TS_LogAppendLine(g_ts_trade_log_handle, line))
      PrintFormat("[TS][LOG][WARN] trade modify append failed trade_id=%s reason=%s", g_ts_exec_trade_id, modify_reason);
}

void TS_WriteBrokerAuditLog(const string tag, const string detail)
{
   string line = "";
   TS_CsvAppend(line, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   TS_CsvAppend(line, _Symbol);
   TS_CsvAppend(line, tag);
   TS_CsvAppend(line, detail);
   TS_CsvAppend(line, g_ts_exec_trade_id);
   TS_CsvAppend(line, StringFormat("%I64d", g_ts_exec_position_id));
   TS_CsvAppend(line, g_ts_exec_pending_exit_reason);
   TS_CsvAppend(line, g_ts_exec_pending_modify_reason);
   TS_CsvAppend(line, IntegerToString(g_ts_exec_modify_count));
   TS_CsvAppend(line, g_ts_exec_active_model_pack_dir);
   TS_CsvAppend(line, g_ts_exec_pack_dir_at_entry);
   TS_CsvAppend(line, g_ts_exec_tx_authority_enabled ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_last_runtime_reload_status);
   TS_CsvAppend(line, IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN)));
   TS_CsvAppend(line, AccountInfoString(ACCOUNT_SERVER));
   TS_CsvAppend(line, TS_VER_EA);
   TS_CsvAppend(line, TS_VER_LOG_SCHEMA);

   if(!TS_WriteCsvLine(TS_BrokerAuditRelPath(), TS_BuildBrokerAuditHeader(), line))
      PrintFormat("[TS][LOG][WARN] broker audit append failed tag=%s", tag);
}

bool TS_WriteTensorDebugSnapshot(const datetime decision_time)
{
   if(!g_ts_x_ready || g_ts_x_count != TS_X_TIME_STEPS || ArraySize(g_ts_x_tensor) != TS_X_FLAT_SIZE)
      return false;
   if(ArraySize(g_ts_x_row_time) != TS_X_TIME_STEPS || ArraySize(g_ts_x_row_dist_atr_max) != TS_X_TIME_STEPS)
      return false;

   const string header = TS_BuildTensorDebugHeader();
   const string rel_path = TS_TensorDebugRelPath();

   for(int t = 0; t < TS_X_TIME_STEPS; ++t)
   {
      string line = "";
      TS_CsvAppend(line, TimeToString(decision_time, TIME_DATE | TIME_MINUTES));
      TS_CsvAppend(line, IntegerToString(t));
      TS_CsvAppend(line, TimeToString(g_ts_x_row_time[t], TIME_DATE | TIME_MINUTES));
      TS_CsvAppend(line, DoubleToString(g_ts_x_row_dist_atr_max[t], 8));

      for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
      {
         const int idx = TS_XIndex(t, f);
         TS_CsvAppend(line, DoubleToString((double)g_ts_x_tensor[idx], 8));
      }

      if(!TS_WriteCsvLine(rel_path, header, line))
         return false;
   }

   return true;
}

bool TS_WriteBarLog(const int regime_id)
{
   if(g_ts_bar_count <= 0)
      return false;
   if(!TS_EnsureBarLogHandle())
      return false;

   const int latest_t = g_ts_bar_count - 1;
   const TS_BarRecord bar = g_ts_bar_buffer[latest_t];

   double atr14 = 0.0;
   double adx14 = 0.0;
   double atr_pct = 0.0;
   double dist_atr = 0.0;
   if(g_ts_ind_count > latest_t)
   {
      atr14 = g_ts_ind_buffer[latest_t].atr14_t;
      adx14 = g_ts_ind_buffer[latest_t].adx14_t;
      const double close_abs = MathMax(MathAbs(bar.bid_close_t), TS_EPSILON);
      atr_pct = atr14 / close_abs;
      dist_atr = TS_ComputeDistAtrForBar(bar, g_ts_ind_buffer[latest_t]);
   }

   string line = "";
   TS_CsvAppend(line, TimeToString(bar.bar_time_t, TIME_DATE | TIME_MINUTES));
   TS_CsvAppend(line, _Symbol);
   TS_CsvAppend(line, EnumToString(TS_DECISION_TIMEFRAME));
   TS_CsvAppend(line, "Bid");
   TS_CsvAppend(line, DoubleToString(bar.bid_open_t, 8));
   TS_CsvAppend(line, DoubleToString(bar.bid_high_t, 8));
   TS_CsvAppend(line, DoubleToString(bar.bid_low_t, 8));
   TS_CsvAppend(line, DoubleToString(bar.bid_close_t, 8));
   TS_CsvAppend(line, DoubleToString(bar.spread_points_t, 2));
   TS_CsvAppend(line, DoubleToString(atr14, 8));
   TS_CsvAppend(line, DoubleToString(adx14, 6));
   TS_CsvAppend(line, DoubleToString(atr_pct, 8));
   TS_CsvAppend(line, IntegerToString(regime_id));
   TS_CsvAppend(line, IntegerToString(g_ts_current_cand_long));
   TS_CsvAppend(line, IntegerToString(g_ts_current_cand_short));
   TS_CsvAppend(line, g_ts_current_entry_allowed ? "1" : "0");

   for(int f = 0; f < TS_X_FEATURE_DIM; ++f)
   {
      double value = 0.0;
      if(g_ts_x_ready && g_ts_x_count == TS_X_TIME_STEPS && ArraySize(g_ts_x_tensor) == TS_X_FLAT_SIZE)
         value = (double)g_ts_x_tensor[TS_XIndex(TS_X_TIME_STEPS - 1, f)];
      TS_CsvAppend(line, DoubleToString(value, 8));
   }

   TS_CsvAppend(line, DoubleToString(g_ts_stage1_last[0], 6));
   TS_CsvAppend(line, DoubleToString(g_ts_stage1_last[1], 6));
   TS_CsvAppend(line, DoubleToString(g_ts_stage1_last[2], 6));
   TS_CsvAppend(line, g_ts_last_model_dir_name);

   for(int i = 0; i < 6; ++i)
      TS_CsvAppend(line, DoubleToString(g_ts_stage2_last[i], 6));

   TS_CsvAppend(line, TS_DecisionDirToString(g_ts_final_dir));
   TS_CsvAppend(line, g_ts_flip_used ? "1" : "0");
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_req, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_sl_eff, 6));
   TS_CsvAppend(line, DoubleToString(g_ts_exec_k_tp_eff, 6));
   TS_CsvAppend(line, IntegerToString(g_ts_final_hold_bars));
   TS_CsvAppend(line, g_ts_gate_pass ? "1" : "0");
   TS_CsvAppend(line, g_ts_gate_reject_reason);
   TS_CsvAppend(line, DoubleToString(g_ts_dyn_spread_atr_max, 6));
   TS_CsvAppend(line, IntegerToString(g_ts_dyn_dev_points));
   TS_CsvAppend(line, DoubleToString(g_ts_risk_pct, 6));
   TS_CsvAppend(line, DoubleToString(dist_atr, 8));
   TS_CsvAppend(line, DoubleToString(g_ts_current_dist_atr_max, 8));
   TS_CsvAppend(line, g_ts_last_cand_mode);
   TS_CsvAppend(line, g_ts_exec_has_position ? "1" : "0");
   TS_CsvAppend(line, IntegerToString(g_ts_exec_bars_held));
   TS_CsvAppend(line, TS_VER_EA);
   TS_CsvAppend(line, TS_VER_SCHEMA);
   TS_CsvAppend(line, TS_VER_CANDIDATE_POLICY);
   TS_CsvAppend(line, TS_VER_REGIME_POLICY);
   TS_CsvAppend(line, g_ts_pack_meta.model_pack_version);
   TS_CsvAppend(line, g_ts_pack_meta.model_pack_version);
   TS_CsvAppend(line, g_ts_pack_meta.model_pack_version);
   TS_CsvAppend(line, g_ts_pack_meta.cost_model_version);
   TS_CsvAppend(line, g_ts_exec_pending_exit_reason);
   TS_CsvAppend(line, g_ts_exec_pending_modify_reason);
   TS_CsvAppend(line, g_ts_exec_last_modify_reason);
   TS_CsvAppend(line, IntegerToString(g_ts_exec_modify_count));
   TS_CsvAppend(line, g_ts_exec_be_applied ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_entry_log_emitted ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_tx_authority_enabled ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_broker_audit_enabled ? "1" : "0");
   TS_CsvAppend(line, g_ts_exec_active_model_pack_dir);
   TS_CsvAppend(line, g_ts_exec_pack_dir_at_entry);
   TS_CsvAppend(line, IntegerToString(g_ts_exec_runtime_reload_attempts));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_runtime_reload_successes));
   TS_CsvAppend(line, IntegerToString(g_ts_exec_runtime_reload_rollbacks));
   TS_CsvAppend(line, g_ts_exec_last_runtime_reload_status);
   TS_CsvAppend(line, TS_VER_LOG_SCHEMA);

   return TS_LogAppendLine(g_ts_bar_log_handle, line);
}

#endif // __TS_LOGGER_MQH__
