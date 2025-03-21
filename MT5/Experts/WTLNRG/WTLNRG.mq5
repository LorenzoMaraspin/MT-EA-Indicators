//+------------------------------------------------------------------+
//|                                                       WTLNRG.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#include<Trade\SymbolInfo.mqh>
#include<Trade\Trade.mqh>
#property tester_indicator "LINEREG"
#property tester_indicator "WT"
//--- input parameters
input double            SL=100;
input double            TP=100;
input double            lot=0.01;
input int               candleLenght=5;
input double            distanceThresold=1;
input bool              distanceCheck=true;
input double            lotSizeLimit=10.0;
input bool              lotSizeLimitFlag=true;
input double            multiplier=2.0;
input bool              multiplierFlag=true;
input ENUM_TIMEFRAMES   timeFrame = PERIOD_M1;
input ulong             maxDeviation = 2;
// INDICATOR VARIABLE DEFINITION
string                  logFileName="EA_Log.csv";
int                     fileHandle = -1;                                // File handle
int                     indicatorHandle = INVALID_HANDLE;               // WaveTrend indicator handle
int                     regressionIndicatorHandle = INVALID_HANDLE;     // Regression channel indicator handle
static bool             isTradeActive = false;                          // Flag to indicate if a trade is currently active
static double           currentLotSize;                                 // Tracks the current lot size to be used
static ulong            lastDealTicketChecked;                          // Last closed trade ticket id
static int              startBarIndex;                                  // Bar index when the pre-signal was detected
static bool             preBuySignal = false, preSellSignal = false;
static bool             openedBuySignal = false, openedSellSignal = false;
static int              preBuyBarIndex = -1;
static int              preSellBarIndex = -1;
int                     MagicNumber=123456;
CTrade                  trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   OutputInitializzationVariables();
   indicatorHandle =             iCustom(Symbol(), timeFrame, "WT");    // Initialize the indicator handle for WaveTrend and Regression Channel
   regressionIndicatorHandle =   iCustom(Symbol(), timeFrame, "LINEREG");
   
   if (indicatorHandle == INVALID_HANDLE || regressionIndicatorHandle == INVALID_HANDLE)
   {
     Print("Failed to initialize WaveTrend or Regression Channel indicator. Error: ", GetLastError());
     return INIT_FAILED;
   }    
   Print("WaveTrend and Regression Channel Indicators Initialized");
   currentLotSize = lot;
   
   // Open the file in CSV write mode
   fileHandle = FileOpen(logFileName, FILE_CSV | FILE_WRITE, ";");
   if (fileHandle < 0)
   {
     Print("Error opening log file: ", GetLastError());
     return INIT_FAILED;
   }
   
   // Write the header to the log file
   FileWrite(
      fileHandle, 
      "Time", 
      "Symbol", 
      "Direction",
      "Distance", 
      "WT1_P", 
      "WT2_P",
      "WT1_C", 
      "WT2_C",
      "Upper"
      "Lower",
      "ConditionMet"
   );
   
   return INIT_SUCCEEDED; // Initialization successful
}
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if (indicatorHandle != INVALID_HANDLE) IndicatorRelease(indicatorHandle);
    if (regressionIndicatorHandle != INVALID_HANDLE) IndicatorRelease(regressionIndicatorHandle);
    if (fileHandle >= 0) FileClose(fileHandle);
}
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
    // Check for closed positions and adjust lot size
    if (multiplierFlag)
      CheckLastTradeClosed();
     // Fetch WaveTrend indicator values and Regression Channel indicator values
    double wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current, upperLineCurrent, lowerLineCurrent, distanceCurrent;
    if (!CopyWaveTrendValues(wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current))
         return;
    if (!CopyRegressionValues(upperLineCurrent, lowerLineCurrent, distanceCurrent))
         return;
    
    CheckTradeConditions(wt1Current, wt1Previous, wt2Current, wt2Previous, osLevel1Current, obLevel1Current, distanceCurrent);
   
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Expert Advisor logic indicator functions                         |
//+------------------------------------------------------------------+
void CheckTradeConditions(double wt1Current, double wt1Previous, double wt2Current, double wt2Previous, 
                          double osCurrent, double obCurrent, double distanceCurrent)
{
    double currentHigh = iHigh(Symbol(), timeFrame, 0);
    double currentLow = iLow(Symbol(), timeFrame, 0);
    double upperCurrentPrice = ObjectGetValueByTime(0, "LinRegUpperLine", iTime(Symbol(), timeFrame, 0));
    double lowerCurrentPrice = ObjectGetValueByTime(0, "LinRegLowerLine", iTime(Symbol(), timeFrame, 0));
    bool wt1CrossOver = (wt1Current > wt2Current && wt1Previous < wt2Previous);
    bool wt1CrossUnder = (wt1Current < wt2Current && wt1Previous > wt2Previous);
    datetime prevCandleTime = iTime(Symbol(), timeFrame, 1);
 
    int currentBarIndex = Bars(_Symbol, timeFrame) - 1;
    
    if (wt1Current > obCurrent && currentHigh > upperCurrentPrice  && preSellBarIndex == -1) {
         preSellSignal = true;
         preSellBarIndex = currentBarIndex;
         FileWrite(fileHandle, TimeToString(prevCandleTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), _Symbol, "SELL", DoubleToString(distanceCurrent), DoubleToString(wt1Previous), DoubleToString(wt2Previous), DoubleToString(wt1Current), DoubleToString(wt2Current), DoubleToString(upperCurrentPrice), DoubleToString(lowerCurrentPrice), "WT1 > OB");
    }
    else if (wt1Current < osCurrent && currentLow < lowerCurrentPrice && preBuyBarIndex == -1) {
         preBuySignal = true;
         preBuyBarIndex = currentBarIndex;
         FileWrite(fileHandle, TimeToString(prevCandleTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), _Symbol, "BUY", DoubleToString(distanceCurrent), DoubleToString(wt1Previous), DoubleToString(wt2Previous), DoubleToString(wt1Current), DoubleToString(wt2Current), DoubleToString(upperCurrentPrice), DoubleToString(lowerCurrentPrice), "WT1 > OB");
    }
    
    if (preBuySignal && currentBarIndex - preBuyBarIndex <= candleLenght) {
         if (wt1CrossOver && !(isTradeOpen(ORDER_TYPE_BUY)) && !openedBuySignal) {
            FileWrite(fileHandle, TimeToString(prevCandleTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), _Symbol, "BUY", DoubleToString(distanceCurrent), DoubleToString(wt1Previous), DoubleToString(wt2Previous), DoubleToString(wt1Current), DoubleToString(wt2Current), DoubleToString(upperCurrentPrice), DoubleToString(lowerCurrentPrice), "WT < OS and PRICE < LOWER");
            OpenTrade(ORDER_TYPE_BUY, currentLotSize, "WT < OS and PRICE < LOWER", distanceCurrent);
            preBuySignal = false;
            openedBuySignal = true;
            preBuyBarIndex = -1;
         }
    } else {
         preBuySignal = false;
         openedBuySignal = false;
         preBuyBarIndex = -1;
    }
    
    if (preSellSignal && currentBarIndex - preSellBarIndex <= candleLenght) {
         if (wt1CrossUnder && !(isTradeOpen(ORDER_TYPE_SELL)) && !openedSellSignal) {
            FileWrite(fileHandle, TimeToString(prevCandleTime, TIME_DATE | TIME_MINUTES | TIME_SECONDS), _Symbol, "SELL", DoubleToString(distanceCurrent), DoubleToString(wt1Previous), DoubleToString(wt2Previous), DoubleToString(wt1Current), DoubleToString(wt2Current), DoubleToString(upperCurrentPrice), DoubleToString(lowerCurrentPrice), "WT > OB and PRICE > UPPER");
            OpenTrade(ORDER_TYPE_SELL, currentLotSize, "WT > OB and PRICE > UPPER", distanceCurrent);
            preSellSignal = false;
            openedSellSignal = true;
            preSellBarIndex = -1;
         }
    } else {
         preSellSignal = false;
         openedSellSignal = false;
         preSellBarIndex = -1;
    }      
}
bool isTradeOpen(ENUM_ORDER_TYPE orderType) {
    int totalPositions = PositionsTotal();
    for (int i=0; i<totalPositions; i++) {
      if (PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_TYPE) == orderType)
         return true;
    }
    return false;
}
ulong OpenTrade(ENUM_ORDER_TYPE type, double volume, string comment, double distanceCurrent)
{
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS); // Decimal places
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);         // Point size
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK); 
   double price = (type == ORDER_TYPE_BUY) ? ask : bid;

   // Get the Stops Level (minimum stop distance in points)
   int stopsLevel = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if (stopsLevel < 0) stopsLevel = 0; // If unavailable, default to 0
   
   // Adjust SL and TP to meet the stops level requirement
   double stopLoss = (type == ORDER_TYPE_BUY) 
                     ? NormalizeDouble(price - MathMax(SL * point, stopsLevel * point), digits)
                     : NormalizeDouble(price + MathMax(SL * point, stopsLevel * point), digits);
                     
   double takeProfit = (type == ORDER_TYPE_BUY) 
                       ? NormalizeDouble(price + MathMax(TP * point, stopsLevel * point), digits)
                       : NormalizeDouble(price - MathMax(TP * point, stopsLevel * point), digits);

   // Ensure trading is allowed and check lot size limits
   if ((!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE)) || ((distanceCurrent < distanceThresold) && distanceCheck == true))
   {
       Print("Trading mode choose not allowed or distance exceeds limit on symbol: ", _Symbol);
       return 0;
   }
   if (currentLotSize >= lotSizeLimit && lotSizeLimitFlag) {
       Print("Trading not allowed lot size exceeds limit on symbol: ", _Symbol);
       return 0;      
   }
   
   // Place the trade
   if (type == ORDER_TYPE_BUY) 
   {
       if (!trade.Buy(volume, _Symbol, price, stopLoss, takeProfit, comment))
       {
           Print("Buy() method failed. Return code=", trade.ResultRetcode(),". Code description: ", trade.ResultRetcodeDescription());
       }
       else
       {
           Print("Buy() method executed successfully. Return code=", trade.ResultRetcode()," (", trade.ResultRetcodeDescription(), ")");
       }
   } 
   else if (type == ORDER_TYPE_SELL) 
   {
       if (!trade.Sell(volume, _Symbol, price, stopLoss, takeProfit, comment))
       {
           Print("Sell() method failed. Return code=", trade.ResultRetcode(),". Code description: ", trade.ResultRetcodeDescription());
       }
       else
       {
           Print("Sell() method executed successfully. Return code=", trade.ResultRetcode()," (", trade.ResultRetcodeDescription(), ")");
       }
   }
   return 0;
}
void CheckLastTradeClosed() {
   datetime endTime = TimeCurrent(); 
   datetime startTime = endTime - 5 * 60;
   if (HistorySelect(startTime, endTime)) {
      for (int i = HistoryDealsTotal() - 1; i >= 0; i--)
      {
           ulong ticket = HistoryDealGetTicket(i); // Get the deal ticket
           ENUM_DEAL_ENTRY dealEntry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);
           ENUM_DEAL_REASON dealReason = (ENUM_DEAL_REASON)HistoryDealGetInteger(ticket, DEAL_REASON);
           // Only process closed deals
           if (dealEntry == DEAL_ENTRY_OUT)
           {
               if (dealReason == DEAL_REASON_SL && ticket != lastDealTicketChecked) // Closed by Stop Loss
               {
                   currentLotSize *= multiplier; // Double the lot size
                   lastDealTicketChecked = ticket;
               }
               else if (dealReason == DEAL_REASON_TP) // Closed by Take Profit
               {
                   currentLotSize = lot; // Reset lot size
               }
               // Break after processing the latest closed deal
               break;
           }
      }
   }
}
bool CopyWaveTrendValues(double &wt1Current, double &wt1Previous, double &wt2Current, double &wt2Previous,
                         double &obLevel1Current, double &osLevel1Current)
{
    double wt1Array[], wt2Array[], obLevel1Array[], osLevel1Array[];

    if (CopyBuffer(indicatorHandle, 0, 0, 2, wt1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 1, 0, 2, wt2Array) <= 0 ||
        CopyBuffer(indicatorHandle, 2, 0, 2, obLevel1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 4, 0, 2, osLevel1Array) <= 0)
    {
        Print("Error copying WaveTrend buffer values: ", GetLastError());
        ResetLastError();
        return false;
    }

    wt1Current = wt1Array[0];
    wt1Previous = wt1Array[1];
    wt2Current = wt2Array[0];
    wt2Previous = wt2Array[1];
    obLevel1Current = obLevel1Array[0];
    osLevel1Current = osLevel1Array[0];
    return true;
}
bool CopyRegressionValues(double &upperLineCurrent, double &lowerLineCurrent, double &distanceCurrent)
{
    double upperLineArray[], lowerLineArray[], distanceArray[];

    if (CopyBuffer(regressionIndicatorHandle, 0, 0, 2, upperLineArray) <= 0 ||
        CopyBuffer(regressionIndicatorHandle, 2, 0, 2, lowerLineArray) <= 0 ||
        CopyBuffer(regressionIndicatorHandle, 3, 0, 2, distanceArray) <= 0)
    {
        Print("Error copying Regression Channel buffer values: ", GetLastError());
        ResetLastError();
        return false;
    }

    upperLineCurrent = upperLineArray[0];
    lowerLineCurrent = lowerLineArray[0];
    distanceCurrent = distanceArray[0];
    return true;
}
void OutputInitializzationVariables() {
   CSymbolInfo symbol_info;         //--- object for receiving symbol settings
   symbol_info.Name(_Symbol);       //--- set the name for the appropriate symbol
   symbol_info.RefreshRates();      //--- receive current rates and display
   
   Print(symbol_info.Name()," (",symbol_info.Description(),")","  Bid=",symbol_info.Bid(),"   Ask=",symbol_info.Ask());
   Print("StopsLevel=",symbol_info.StopsLevel()," pips, FreezeLevel=",symbol_info.FreezeLevel()," pips");
   Print("Digits=",symbol_info.Digits(),", Point=",DoubleToString(symbol_info.Point(),symbol_info.Digits()));
   Print("SpreadFloat=",symbol_info.SpreadFloat(),", Spread(current)=",symbol_info.Spread()," pips");
   Print("Limitations for trade operations: ",EnumToString(symbol_info.TradeMode())," (",symbol_info.TradeModeDescription(),")");
   Print("Trades execution mode: ",EnumToString(symbol_info.TradeExecution())," (",symbol_info.TradeExecutionDescription(),")");
   Print("Contract price calculation: ",EnumToString(symbol_info.TradeCalcMode())," (",symbol_info.TradeCalcModeDescription(),")");
   Print("Standard contract size: ",symbol_info.ContractSize()," (",symbol_info.CurrencyBase(),")");
   Print("Volume info: LotsMin=",symbol_info.LotsMin(),"  LotsMax=",symbol_info.LotsMax(),"  LotsStep=",symbol_info.LotsStep());
   
   trade.SetExpertMagicNumber(MagicNumber);                 //--- set available slippage in points when buying/selling 
   trade.SetDeviationInPoints(maxDeviation);                //--- order filling mode, the mode allowed by the server should be used
   trade.SetTypeFilling(ORDER_FILLING_IOC);                 //--- logging mode: it would be better not to declare this method at all, the class will set the best mode on its own
   trade.LogLevel(1); 
   trade.SetAsyncMode(true);
}
//+------------------------------------------------------------------+