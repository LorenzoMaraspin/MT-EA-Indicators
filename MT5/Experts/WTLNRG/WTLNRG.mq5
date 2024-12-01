//+------------------------------------------------------------------+
//|                                                       WTLNRG.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property tester_indicator "LINEREG"
#property tester_indicator "WT"

//--- input parameters
input double   tp=10;
input double   sl=10;
input double   lot=0.01;
input int      candleLenght=5;
input double   distanceThresold;
input double   lotSizeLimit=10.0;
input bool     lotSizeLimitFlag=true;
input double   multiplier=2.0;
input bool     multiplierFlag=true;
input ENUM_TIMEFRAMES timeFrame = PERIOD_M1;
input ulong maxDeviation = 2;

// INDICATOR VARIABLE DEFINITION
int indicatorHandle = INVALID_HANDLE;              // WaveTrend indicator handle
int regressionIndicatorHandle = INVALID_HANDLE;    // Regression channel indicator handle
static bool isTradeActive = false;                 // Flag to indicate if a trade is currently active
static double currentLotSize;                      // Tracks the current lot size to be used
static ulong lastDealTicketChecked;                // Last closed trade ticket id
static int startBarIndex;                          // Bar index when the pre-signal was detected
static bool preBuySignal = false, preSellSignal = false;
static bool openedBuySignal = false, openedSellSignal = false;
static int preBuyBarIndex = -1;
static int preSellBarIndex = -1;
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize the indicator handle for WaveTrend and Regression Channel
    indicatorHandle = iCustom(Symbol(), timeFrame, "WT");
    regressionIndicatorHandle = iCustom(Symbol(), timeFrame, "LINEREG");
    
    if (indicatorHandle == INVALID_HANDLE || regressionIndicatorHandle == INVALID_HANDLE)
    {
        Print("Failed to initialize WaveTrend or Regression Channel indicator. Error: ", GetLastError());
        return INIT_FAILED;
    }    
    Print("WaveTrend and Regression Channel Indicators Initialized");
    currentLotSize = lot;
    return INIT_SUCCEEDED; // Initialization successful
}
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
    // Release the indicator handles
    if (indicatorHandle != INVALID_HANDLE)
    {
        IndicatorRelease(indicatorHandle);
        indicatorHandle = INVALID_HANDLE;
    }
    if (regressionIndicatorHandle != INVALID_HANDLE)
    {
        IndicatorRelease(regressionIndicatorHandle);
        regressionIndicatorHandle = INVALID_HANDLE;
    }
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
    double wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current, upperLineCurrent, lowerLineCurrent;
    if (!CopyWaveTrendValues(wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current) && !CopyRegressionValues(upperLineCurrent, lowerLineCurrent))
        return;
    
    CheckTradeConditions(wt1Current, wt1Previous, wt2Current, wt2Previous, osLevel1Current, obLevel1Current);
   
  }
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Expert Advisor logic indicator functions                         |
//+------------------------------------------------------------------+
void CheckTradeConditions(double wt1Current, double wt1Previous, double wt2Current, double wt2Previous, 
                          double osCurrent, double obCurrent)
{
    double currentHigh = iHigh(Symbol(), timeFrame, 0);
    double currentLow = iLow(Symbol(), timeFrame, 0);
    double upperCurrentPrice = ObjectGetValueByTime(0, "LinRegUpperLine", iTime(Symbol(), timeFrame, 0));
    double lowerCurrentPrice = ObjectGetValueByTime(0, "LinRegLowerLine", iTime(Symbol(), timeFrame, 0));
    bool wt1CrossOver = (wt1Current > wt2Current && wt1Previous < wt2Previous);
    bool wt1CrossUnder = (wt1Current < wt2Current && wt1Previous > wt2Previous);    
    
    int currentBarIndex = Bars(_Symbol, timeFrame);
    
    if (wt1Current > obCurrent && currentHigh > upperCurrentPrice  && preSellBarIndex == -1) {
         preSellSignal = true;
         preSellBarIndex = currentBarIndex;
         DrawShape("preSellSignal", iTime(_Symbol, timeFrame, 0), currentLow + (300 * _Point), clrRed, 13);
    }
    else if (wt1Current < osCurrent && currentLow < lowerCurrentPrice && preBuyBarIndex == -1) {
         preBuySignal = true;
         preBuyBarIndex = currentBarIndex;
         DrawShape("preBuySignal", iTime(_Symbol, timeFrame, 0), currentHigh + (300 * _Point), clrGreen, 13);
    }
    
    if (preBuySignal && currentBarIndex - preBuyBarIndex <= candleLenght) {
         if (wt1CrossOver && !(isTradeOpen(ORDER_TYPE_BUY)) && !openedBuySignal) {  
            OpenTrade(ORDER_TYPE_BUY, currentLotSize, "WT < OS and PRICE < LOWER");
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
            OpenTrade(ORDER_TYPE_SELL, currentLotSize, "WT > OB and PRICE > UPPER");
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

ulong OpenTrade(ENUM_ORDER_TYPE type, double volume, string comment)
{
    // Check if a trade of the same type is already active
    if (currentLotSize >= lotSizeLimit && lotSizeLimitFlag)
    {
        Print("Trade of this type is already active. Skipping trade.");
        return 0; // Skip opening a new trade
    }

    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    MqlTick latestPrice;

    // Check if trading is allowed on this symbol
    if (!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
    {
        Print("Trading not allowed on symbol: ", _Symbol);
        return 0;
    }

    // Get the last price quote
    if (!SymbolInfoTick(_Symbol, latestPrice))
    {
        Print("Error getting the latest price quote - error:", GetLastError());
        return 0;
    }

    double price = (type == ORDER_TYPE_BUY) ? NormalizeDouble(latestPrice.ask, _Digits) : NormalizeDouble(latestPrice.bid, _Digits);

    // Set Stop Loss and Take Profit, ensuring minimum distance from price
    double stopLoss = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price - sl * _Point, _Digits) : NormalizeDouble(price + sl * _Point, _Digits);
    double takeProfit = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price + tp * _Point, _Digits): NormalizeDouble(price - tp * _Point, _Digits);
    // Ensure SL/TP respect the broker's minimum stop level
    
    double minStopLevel = GetMinimumStopLevel();
    if (type == ORDER_TYPE_BUY)
    {
        if ((price - stopLoss) < minStopLevel)
            stopLoss = NormalizeDouble(price - minStopLevel, _Digits);
        if ((takeProfit - price) < minStopLevel)
            takeProfit = NormalizeDouble(price + minStopLevel, _Digits);
    }
    else if (type == ORDER_TYPE_SELL)
    {
        if ((stopLoss - price) < minStopLevel)
            stopLoss = NormalizeDouble(price + minStopLevel, _Digits);
        if ((price - takeProfit) < minStopLevel)
            takeProfit = NormalizeDouble(price - minStopLevel, _Digits);
    }
    // Log trade details for debugging purposes
    Print("Preparing to open trade. Type: ", type, ", Price: ", price, ", SL: ", stopLoss, ", TP: ", takeProfit, " Digit: ", _Digits);

    // Initialize trade request parameters
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = volume;
    request.type = type;
    request.price = price;
    request.sl = stopLoss;
    request.tp = takeProfit;
    request.type_filling = ORDER_FILLING_FOK;
    request.comment = comment;
    request.deviation = maxDeviation;

    // Send the trade request and handle result
    if (!OrderSend(request, result))
    {
        Print("Failed to send order - Error: ", GetLastError());
        PrintFormat("retcode=%u  deal=%I64u  order=%I64u ", result.retcode, result.deal, result.order);
        ResetLastError();
        return 0;
    }
    if (result.retcode == TRADE_RETCODE_DONE) {
        Print("Trade opened successfully - Ticket: ", result.order);
        return result.order;
    } else {
        Print("Order failed - Retcode: ", result.retcode);
    }
    return 0;
}
double GetMinimumStopLevel()
{
    int stopLevelPoints = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
    if (stopLevelPoints == INVALID_HANDLE)
    {
        Print("Error fetching stop level - ", GetLastError());
        return 0;
    }
    return stopLevelPoints * _Point; // Convert points to price
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

// Helper function to copy Regression Channel values
bool CopyRegressionValues(double &upperLineCurrent, double &lowerLineCurrent)
{
    double upperLineArray[], lowerLineArray[];

    if (CopyBuffer(regressionIndicatorHandle, 0, 0, 2, upperLineArray) <= 0 ||
        CopyBuffer(regressionIndicatorHandle, 2, 0, 2, lowerLineArray) <= 0)
    {
        Print("Error copying Regression Channel buffer values: ", GetLastError());
        ResetLastError();
        return false;
    }

    upperLineCurrent = upperLineArray[0];
    lowerLineCurrent = lowerLineArray[0];
    return true;
} 
void DrawShape(string name, datetime time, double price, color clr, int arrowSymbol)
{
    // Ensure unique names for each arrow by appending the time
    string arrowName = name + "_" + IntegerToString(time);
    
    // Create the arrow object on the chart
    if (ObjectFind(0, arrowName) == -1) // Check if object already exists
    {
        ObjectCreate(0, arrowName, OBJ_ARROW, 0, time, price);
        ObjectSetInteger(0, arrowName, OBJPROP_COLOR, clr);
        ObjectSetInteger(0, arrowName, OBJPROP_WIDTH, 2);
        ObjectSetInteger(0, arrowName, OBJPROP_ARROWCODE, arrowSymbol);
    }
}
//+------------------------------------------------------------------+