#ifndef __TS_PACK_META_MQH__
#define __TS_PACK_META_MQH__

#include "TS_Defines.mqh"
#include "TS_PassOnly.mqh"

struct TS_PackMetaRecord
{
   double atr_thr;
   double adx_thr1;
   double adx_thr2;
   string dist_atr_max_mode;
   double dist_atr_max_q;
   int dist_atr_max_w;
   double dist_atr_max_clamp_lo;
   double dist_atr_max_clamp_hi;

   string model_pack_version;
   string schema_version;
   string regime_policy_version;
   string candidate_policy_version;
   string cost_model_version;

   string thr_method;
   string thr_seed;
   string thr_notes;
};

TS_PackMetaRecord g_ts_pack_meta;
bool g_ts_pack_meta_ready = false;
string g_ts_pack_meta_relpath = "";

string TS_PM_Trim(const string value)
{
   string out = value;
   StringTrimLeft(out);
   StringTrimRight(out);
   return out;
}

string TS_PM_StripBom(const string value)
{
   if(StringLen(value) == 0)
      return value;

   if((ushort)StringGetCharacter(value, 0) == 0xFEFF)
      return StringSubstr(value, 1);

   return value;
}

bool TS_PM_HasSeenKey(const string &seen_keys[], const string key)
{
   const int n = ArraySize(seen_keys);
   for(int i = 0; i < n; ++i)
   {
      if(seen_keys[i] == key)
         return true;
   }
   return false;
}

void TS_PM_RegisterSeenKey(string &seen_keys[], const string key)
{
   const int n = ArraySize(seen_keys);
   ArrayResize(seen_keys, n + 1);
   seen_keys[n] = key;
}

bool TS_PM_ValidateModelPackDir(const string model_pack_dir, string &detail)
{
   const string dir = TS_PM_Trim(model_pack_dir);
   if(dir == "")
   {
      detail = "model pack dir is empty";
      return false;
   }

   if(StringFind(dir, "..") >= 0)
   {
      detail = StringFormat("path traversal rejected dir=%s", dir);
      return false;
   }

   if(StringFind(dir, ":") >= 0)
   {
      detail = StringFormat("drive prefix rejected dir=%s", dir);
      return false;
   }

   if(StringLen(dir) > 0)
   {
      const string first = StringSubstr(dir, 0, 1);
      if(first == "\\" || first == "/")
      {
         detail = StringFormat("absolute-like path rejected dir=%s", dir);
         return false;
      }
   }

   detail = "";
   return true;
}

bool TS_PM_IsSafeVersionToken(const string token)
{
   if(token == "")
      return false;

   const int len = StringLen(token);
   for(int i = 0; i < len; ++i)
   {
      const ushort ch = (ushort)StringGetCharacter(token, i);
      const bool is_lower = (ch >= 'a' && ch <= 'z');
      const bool is_digit = (ch >= '0' && ch <= '9');
      const bool is_safe_punct = (ch == '.' || ch == '_' || ch == '-');
      if(!is_lower && !is_digit && !is_safe_punct)
         return false;
   }

   return true;
}

void TS_ResetPackMetaState()
{
   g_ts_pack_meta.atr_thr = TS_REGIME_ATR_THR;
   g_ts_pack_meta.adx_thr1 = TS_REGIME_ADX_THR1;
   g_ts_pack_meta.adx_thr2 = TS_REGIME_ADX_THR2;
   g_ts_pack_meta.dist_atr_max_mode = "static";
   g_ts_pack_meta.dist_atr_max_q = 0.0;
   g_ts_pack_meta.dist_atr_max_w = 0;
   g_ts_pack_meta.dist_atr_max_clamp_lo = 0.0;
   g_ts_pack_meta.dist_atr_max_clamp_hi = 0.0;
   g_ts_pack_meta.model_pack_version = "";
   g_ts_pack_meta.schema_version = "";
   g_ts_pack_meta.regime_policy_version = "";
   g_ts_pack_meta.candidate_policy_version = "";
   g_ts_pack_meta.cost_model_version = "";
   g_ts_pack_meta.thr_method = "";
   g_ts_pack_meta.thr_seed = "";
   g_ts_pack_meta.thr_notes = "";

   g_ts_pack_meta_ready = false;
   g_ts_pack_meta_relpath = "";
}

void TS_LogPackMetaState()
{
   PrintFormat(
      "[TS][PACK_META_STATE] ready=%s path=%s atr_thr=%.8f adx_thr1=%.6f adx_thr2=%.6f dist_mode=%s dist_q=%.4f dist_w=%d clamp_lo=%.4f clamp_hi=%.4f model_pack=%s schema=%s regime_policy=%s candidate_policy=%s cost_model=%s",
      g_ts_pack_meta_ready ? "true" : "false",
      g_ts_pack_meta_relpath,
      g_ts_pack_meta.atr_thr,
      g_ts_pack_meta.adx_thr1,
      g_ts_pack_meta.adx_thr2,
      g_ts_pack_meta.dist_atr_max_mode,
      g_ts_pack_meta.dist_atr_max_q,
      g_ts_pack_meta.dist_atr_max_w,
      g_ts_pack_meta.dist_atr_max_clamp_lo,
      g_ts_pack_meta.dist_atr_max_clamp_hi,
      g_ts_pack_meta.model_pack_version,
      g_ts_pack_meta.schema_version,
      g_ts_pack_meta.regime_policy_version,
      g_ts_pack_meta.candidate_policy_version,
      g_ts_pack_meta.cost_model_version
   );
}

bool TS_LoadPackMeta(const string model_pack_dir)
{
   string detail = "";
   if(!TS_PM_ValidateModelPackDir(model_pack_dir, detail))
   {
      TS_LatchPassOnly(TS_PASS_REASON_PACK_META_FAIL, detail);
      return false;
   }

   const string dir = TS_PM_Trim(model_pack_dir);
   const string rel_path = dir + "\\pack_meta.csv";

   ResetLastError();
   const int handle = FileOpen(rel_path, FILE_READ | FILE_TXT | FILE_ANSI);
   if(handle == INVALID_HANDLE)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("pack_meta open failed path=%s err=%d", rel_path, GetLastError())
      );
      return false;
   }

   TS_PackMetaRecord loaded = g_ts_pack_meta;
   bool has_atr_thr = false;
   bool has_adx_thr1 = false;
   bool has_adx_thr2 = false;
   bool has_model_pack_version = false;
   bool has_schema_version = false;
   bool has_regime_policy_version = false;
   bool has_candidate_policy_version = false;
   bool has_dist_atr_max_q = false;
   bool has_dist_atr_max_w = false;
   bool has_dist_atr_max_clamp_lo = false;
   bool has_dist_atr_max_clamp_hi = false;

   string seen_keys[];
   ArrayResize(seen_keys, 0);

   while(!FileIsEnding(handle))
   {
      string line = TS_PM_Trim(FileReadString(handle));
      line = TS_PM_StripBom(line);
      if(line == "")
         continue;

      const string first = StringSubstr(line, 0, 1);
      if(first == "#")
         continue;

      const int eq_pos = StringFind(line, "=");
      if(eq_pos <= 0)
      {
         PrintFormat("[TS][PACK_META][WARN] invalid line format (expected key=value): %s", line);
         continue;
      }

      string key = TS_PM_Trim(StringSubstr(line, 0, eq_pos));
      key = TS_PM_StripBom(key);
      StringToLower(key);
      const string value = TS_PM_Trim(StringSubstr(line, eq_pos + 1));

      if(key == "")
      {
         PrintFormat("[TS][PACK_META][WARN] empty key ignored line=%s", line);
         continue;
      }

      if(TS_PM_HasSeenKey(seen_keys, key))
      {
         PrintFormat("[TS][PACK_META][WARN] duplicate key ignored key=%s", key);
         continue;
      }

      if(key == "atr_thr")
      {
         loaded.atr_thr = StringToDouble(value);
         has_atr_thr = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "adx_thr1")
      {
         loaded.adx_thr1 = StringToDouble(value);
         has_adx_thr1 = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "adx_thr2")
      {
         loaded.adx_thr2 = StringToDouble(value);
         has_adx_thr2 = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "model_pack_version")
      {
         loaded.model_pack_version = value;
         has_model_pack_version = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "schema_version")
      {
         loaded.schema_version = value;
         has_schema_version = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "regime_policy_version")
      {
         loaded.regime_policy_version = value;
         has_regime_policy_version = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "candidate_policy_version")
      {
         loaded.candidate_policy_version = value;
         has_candidate_policy_version = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "cost_model_version")
      {
         loaded.cost_model_version = value;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "thr_method")
      {
         loaded.thr_method = value;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "thr_seed")
      {
         loaded.thr_seed = value;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "thr_notes")
      {
         loaded.thr_notes = value;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "dist_atr_max_mode")
      {
         loaded.dist_atr_max_mode = value;
         StringToLower(loaded.dist_atr_max_mode);
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "dist_atr_max_q")
      {
         loaded.dist_atr_max_q = StringToDouble(value);
         has_dist_atr_max_q = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "dist_atr_max_w")
      {
         loaded.dist_atr_max_w = (int)StringToInteger(value);
         has_dist_atr_max_w = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "dist_atr_max_clamp_lo")
      {
         loaded.dist_atr_max_clamp_lo = StringToDouble(value);
         has_dist_atr_max_clamp_lo = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else if(key == "dist_atr_max_clamp_hi")
      {
         loaded.dist_atr_max_clamp_hi = StringToDouble(value);
         has_dist_atr_max_clamp_hi = true;
         TS_PM_RegisterSeenKey(seen_keys, key);
      }
      else
      {
         PrintFormat("[TS][PACK_META][WARN] unknown key ignored key=%s", key);
      }
   }

   FileClose(handle);

   if(!has_atr_thr || !has_adx_thr1 || !has_adx_thr2 ||
      !has_model_pack_version || !has_schema_version || !has_regime_policy_version ||
      loaded.model_pack_version == "" || loaded.schema_version == "" || loaded.regime_policy_version == "")
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "missing required fields atr=%s adx1=%s adx2=%s model_pack=%s schema=%s regime=%s",
            has_atr_thr ? "true" : "false",
            has_adx_thr1 ? "true" : "false",
            has_adx_thr2 ? "true" : "false",
            (has_model_pack_version && loaded.model_pack_version != "") ? "true" : "false",
            (has_schema_version && loaded.schema_version != "") ? "true" : "false",
            (has_regime_policy_version && loaded.regime_policy_version != "") ? "true" : "false"
         )
      );
      return false;
   }

   if(!TS_PM_IsSafeVersionToken(loaded.model_pack_version))
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("model_pack_version has invalid chars value=%s", loaded.model_pack_version)
      );
      return false;
   }

   if(loaded.atr_thr <= 0.0 || loaded.adx_thr1 <= 0.0 || loaded.adx_thr2 <= loaded.adx_thr1)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat(
            "invalid thresholds atr_thr=%.8f adx_thr1=%.6f adx_thr2=%.6f",
            loaded.atr_thr,
            loaded.adx_thr1,
            loaded.adx_thr2
         )
      );
      return false;
   }

   if(loaded.schema_version != TS_VER_SCHEMA)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
         StringFormat(
            "schema_version mismatch expected=%s actual=%s",
            TS_VER_SCHEMA,
            loaded.schema_version
         )
      );
      return false;
   }

   if(loaded.regime_policy_version != TS_VER_REGIME_POLICY)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
         StringFormat(
            "regime_policy_version mismatch expected=%s actual=%s",
            TS_VER_REGIME_POLICY,
            loaded.regime_policy_version
         )
      );
      return false;
   }

   if(!has_candidate_policy_version || loaded.candidate_policy_version == "")
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         "candidate_policy_version missing"
      );
      return false;
   }

   if(loaded.candidate_policy_version != TS_VER_CANDIDATE_POLICY)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
         StringFormat(
            "candidate_policy_version mismatch expected=%s actual=%s",
            TS_VER_CANDIDATE_POLICY,
            loaded.candidate_policy_version
         )
      );
      return false;
   }

   if(loaded.dist_atr_max_mode == "")
      loaded.dist_atr_max_mode = "static";

   if(loaded.dist_atr_max_mode != "static" && loaded.dist_atr_max_mode != "adaptive_quantile")
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         StringFormat("dist_atr_max_mode invalid mode=%s", loaded.dist_atr_max_mode)
      );
      return false;
   }

   if(loaded.dist_atr_max_mode == "adaptive_quantile")
   {
      if(!has_dist_atr_max_q || !has_dist_atr_max_w || !has_dist_atr_max_clamp_lo || !has_dist_atr_max_clamp_hi)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_PACK_META_FAIL,
            StringFormat(
               "adaptive dist config missing q=%s w=%s clamp_lo=%s clamp_hi=%s",
               has_dist_atr_max_q ? "true" : "false",
               has_dist_atr_max_w ? "true" : "false",
               has_dist_atr_max_clamp_lo ? "true" : "false",
               has_dist_atr_max_clamp_hi ? "true" : "false"
            )
         );
         return false;
      }

      if(loaded.dist_atr_max_q <= 0.0 || loaded.dist_atr_max_q >= 1.0 ||
         loaded.dist_atr_max_w < 1 || loaded.dist_atr_max_w > 63 ||
         loaded.dist_atr_max_clamp_lo <= 0.0 ||
         loaded.dist_atr_max_clamp_hi < loaded.dist_atr_max_clamp_lo)
      {
         TS_LatchPassOnly(
            TS_PASS_REASON_PACK_META_FAIL,
            StringFormat(
               "adaptive dist config invalid q=%.4f w=%d clamp_lo=%.4f clamp_hi=%.4f",
               loaded.dist_atr_max_q,
               loaded.dist_atr_max_w,
               loaded.dist_atr_max_clamp_lo,
               loaded.dist_atr_max_clamp_hi
            )
         );
         return false;
      }
   }

   if(loaded.cost_model_version == "")
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_PACK_META_FAIL,
         "cost_model_version missing"
      );
      return false;
   }

   if(loaded.cost_model_version != TS_VER_COST_MODEL)
   {
      TS_LatchPassOnly(
         TS_PASS_REASON_SCHEMA_VERSION_MISMATCH,
         StringFormat(
            "cost_model_version mismatch expected=%s actual=%s",
            TS_VER_COST_MODEL,
            loaded.cost_model_version
         )
      );
      return false;
   }

   g_ts_pack_meta = loaded;
   g_ts_pack_meta_ready = true;
   g_ts_pack_meta_relpath = rel_path;

   PrintFormat(
      "[TS][PACK_META] loaded path=%s atr_thr=%.8f adx_thr1=%.6f adx_thr2=%.6f dist_mode=%s dist_q=%.4f dist_w=%d clamp_lo=%.4f clamp_hi=%.4f model_pack=%s schema=%s regime_policy=%s candidate_policy=%s cost_model=%s",
      g_ts_pack_meta_relpath,
      g_ts_pack_meta.atr_thr,
      g_ts_pack_meta.adx_thr1,
      g_ts_pack_meta.adx_thr2,
      g_ts_pack_meta.dist_atr_max_mode,
      g_ts_pack_meta.dist_atr_max_q,
      g_ts_pack_meta.dist_atr_max_w,
      g_ts_pack_meta.dist_atr_max_clamp_lo,
      g_ts_pack_meta.dist_atr_max_clamp_hi,
      g_ts_pack_meta.model_pack_version,
      g_ts_pack_meta.schema_version,
      g_ts_pack_meta.regime_policy_version,
      g_ts_pack_meta.candidate_policy_version,
      g_ts_pack_meta.cost_model_version
   );

   return true;
}

#endif // __TS_PACK_META_MQH__
