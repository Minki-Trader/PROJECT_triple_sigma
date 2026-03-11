#ifndef __TS_DEFINES_MQH__
#define __TS_DEFINES_MQH__

// Version strings are intentionally macro-based for STEP01 stability.
#define TS_VER_EA                 "0.2.0"
#define TS_VER_SCHEMA             "1.0"
#define TS_VER_LOG_SCHEMA         "2.0"
#define TS_VER_CANDIDATE_POLICY   "0.1.2"
#define TS_VER_REGIME_POLICY      "0.1.0q"
#define TS_VER_COST_MODEL         "0.1"
#define TS_VER_MODEL_PACK         "unset"
#define TS_VER_CLF                "unset"
#define TS_VER_PRM                "unset"
#define TS_LOG_DIR                "triple_sigma_logs"

const int TS_X_TIME_STEPS = 64;
const int TS_X_FEATURE_DIM = 22;
const int TS_Y_DIM = 6;
const int TS_X_FLAT_SIZE = TS_X_TIME_STEPS * TS_X_FEATURE_DIM;

const double TS_EPSILON = 1e-9;
const double TS_TWO_PI = 6.2831853071795864769;

const int TS_REGIME_COUNT = 6;
const int TS_STAGE_COUNT = 2;
const int TS_MODEL_FILE_COUNT = TS_REGIME_COUNT * TS_STAGE_COUNT;

const int TS_HOLD_BARS_MAX = 72;
const int TS_PASS_DEFAULT_HOLD_BARS = 24;
const double TS_PASS_DEFAULT_K_SL = 1.5;
const double TS_PASS_DEFAULT_K_TP = 2.0;

const double TS_PROB_SUM_WARN_THRESHOLD = 0.005;
const double TS_PROB_SUM_TOLERANCE = 0.01;

const ENUM_TIMEFRAMES TS_DECISION_TIMEFRAME = PERIOD_M5;
const int TS_REQUIRED_BARS = 64;
const int TS_HISTORY_KEEP_BARS = 256;
const int TS_IND_EMA20_PERIOD = 20;
const int TS_IND_EMA50_PERIOD = 50;
const int TS_IND_RSI14_PERIOD = 14;
const int TS_IND_ATR14_PERIOD = 14;
const int TS_IND_ADX14_PERIOD = 14;
const int TS_ADX_MAIN_BUFFER = 0;

// STEP04 baseline thresholds (model-pack wiring in STEP05/STEP07).
const double TS_REGIME_ATR_THR = 0.0005;
const double TS_REGIME_ADX_THR1 = 20.0;
const double TS_REGIME_ADX_THR2 = 30.0;
const double TS_CAND_DIST_ATR_MAX_STATIC = 2.5;

// Contract feature index constants (single source of truth).
const int TS_FEAT_RET_1 = 0;
const int TS_FEAT_RET_3 = 1;
const int TS_FEAT_RET_12 = 2;
const int TS_FEAT_RANGE_ATR = 3;
const int TS_FEAT_BODY_ATR = 4;
const int TS_FEAT_CLOSE_POS = 5;
const int TS_FEAT_EMA20_DIST = 6;
const int TS_FEAT_EMA50_DIST = 7;
const int TS_FEAT_EMA20_SLOPE = 8;
const int TS_FEAT_RSI_NORM = 9;
const int TS_FEAT_ADX_NORM = 10;
const int TS_FEAT_SPREAD_ATR = 11;
const int TS_FEAT_TIME_SIN = 12;
const int TS_FEAT_TIME_COS = 13;
const int TS_FEAT_REG_0 = 14;
const int TS_FEAT_REG_1 = 15;
const int TS_FEAT_REG_2 = 16;
const int TS_FEAT_REG_3 = 17;
const int TS_FEAT_REG_4 = 18;
const int TS_FEAT_REG_5 = 19;
const int TS_FEAT_CAND_LONG = 20;
const int TS_FEAT_CAND_SHORT = 21;

void TS_LogVersionSnapshot()
{
   PrintFormat(
      "[TS][META] ea=%s schema=%s candidate=%s regime=%s cost=%s model_pack=%s clf=%s prm=%s",
      TS_VER_EA,
      TS_VER_SCHEMA,
      TS_VER_CANDIDATE_POLICY,
      TS_VER_REGIME_POLICY,
      TS_VER_COST_MODEL,
      TS_VER_MODEL_PACK,
      TS_VER_CLF,
      TS_VER_PRM
   );
}

bool TS_ValidateStaticContract()
{
   // compile-time tautology: documents expected CONTRACT dimensions explicitly.
   if(TS_X_TIME_STEPS != 64 || TS_X_FEATURE_DIM != 22 || TS_Y_DIM != 6 || TS_X_FLAT_SIZE != 1408)
   {
      PrintFormat(
         "[TS][ERROR] Contract dimensions invalid X=[%d,%d] X_flat=%d Y=[%d]",
         TS_X_TIME_STEPS,
         TS_X_FEATURE_DIM,
         TS_X_FLAT_SIZE,
         TS_Y_DIM
      );
      return false;
   }

   if(TS_PROB_SUM_WARN_THRESHOLD <= 0.0 || TS_PROB_SUM_TOLERANCE <= TS_PROB_SUM_WARN_THRESHOLD)
   {
      PrintFormat(
         "[TS][ERROR] Probability thresholds invalid warn=%.6f tolerance=%.6f",
         TS_PROB_SUM_WARN_THRESHOLD,
         TS_PROB_SUM_TOLERANCE
      );
      return false;
   }

   if(TS_PASS_DEFAULT_HOLD_BARS < 1 || TS_PASS_DEFAULT_HOLD_BARS > TS_HOLD_BARS_MAX)
   {
      PrintFormat(
         "[TS][ERROR] PASS hold bars invalid hold=%d max=%d",
         TS_PASS_DEFAULT_HOLD_BARS,
         TS_HOLD_BARS_MAX
      );
      return false;
   }

   if(TS_PASS_DEFAULT_K_SL <= 0.0 || TS_PASS_DEFAULT_K_TP <= 0.0)
   {
      PrintFormat(
         "[TS][ERROR] PASS defaults invalid k_sl=%.6f k_tp=%.6f",
         TS_PASS_DEFAULT_K_SL,
         TS_PASS_DEFAULT_K_TP
      );
      return false;
   }

   if(TS_REGIME_ATR_THR <= 0.0 || TS_REGIME_ADX_THR1 <= 0.0 || TS_REGIME_ADX_THR2 <= TS_REGIME_ADX_THR1)
   {
      PrintFormat(
         "[TS][ERROR] Regime thresholds invalid atr_thr=%.8f adx_thr1=%.4f adx_thr2=%.4f",
         TS_REGIME_ATR_THR,
         TS_REGIME_ADX_THR1,
         TS_REGIME_ADX_THR2
      );
      return false;
   }

   if(TS_CAND_DIST_ATR_MAX_STATIC <= 0.0)
   {
      PrintFormat(
         "[TS][ERROR] Candidate dist threshold invalid dist_atr_max=%.4f",
         TS_CAND_DIST_ATR_MAX_STATIC
      );
      return false;
   }

   if(TS_HISTORY_KEEP_BARS < (TS_X_TIME_STEPS + 63))
   {
      PrintFormat(
         "[TS][ERROR] History keep bars too small keep=%d required_min=%d",
         TS_HISTORY_KEEP_BARS,
         TS_X_TIME_STEPS + 63
      );
      return false;
   }

   return true;
}

#endif // __TS_DEFINES_MQH__
