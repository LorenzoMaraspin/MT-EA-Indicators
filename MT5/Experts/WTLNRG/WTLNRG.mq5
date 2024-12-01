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
input double   lotSizeLimit;
input bool     lotSizeLimitFlag=false;
input int      multiplier;
input bool     multiplierFlag=false;
input ENUM_TIMEFRAMES timeFrame = PERIOD_M1;
input ulong maxDeviation = 2;

// INDICATOR VARIABLE DEFINITION
int indicatorHandle = INVALID_HANDLE;              // WaveTrend indicator handle
int regressionIndicatorHandle = INVALID_HANDLE;    // Regression channel indicator handle
struct TradeInfo
{
    ulong ticket;                                  // Trade ticket
    ENUM_ORDER_TYPE type;                          // Trade type (buy/sell)
    double openPrice;                              // Trade opening price
    double stopLoss;                               // Trade SL
    double takeProfit;                             // Trade TP
};
TradeInfo activeTrade;
static bool isTradeActive = false;                        // Flag to indicate if a trade is currently active
double currentLotSize;                             // Tracks the current lot size to be used

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
    AdjustLotSizeOnPositionClose();
    // Manage existing active trades
    ManageActiveTrade();
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
    
    static bool preBuySignal = false;
    static bool preSellSignal = false;
    static int startBarIndex = 0; // Bar index when the pre-signal was detected
    
    int currentBarIndex = Bars(_Symbol, timeFrame);
    
    if (wt1Current > obCurrent && currentHigh > upperCurrentPrice) {
         preSellSignal = true;
         startBarIndex = currentBarIndex;
    }
    else if (wt1Current < osCurrent && currentLow < lowerCurrentPrice) {
         preBuySignal = true;
         startBarIndex = currentBarIndex;
    }
    
    if ((startBarIndex - currentBarIndex) <= candleLenght) {
         if (preBuySignal && wt1CrossOver) {  
            OpenTrade(ORDER_TYPE_BUY, lot, "WT < OS and PRICE < LOWER");
            preBuySignal = false;
         } 
         else if (preSellSignal && wt1CrossUnder) {
            OpenTrade(ORDER_TYPE_SELL, lot, "WT > OB and PRICE > UPPER");
            preSellSignal = false;
         }
    }
    else {
         preBuySignal = false;
         preSellSignal = false;
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

void ManageActiveTrade()
{
    // If no active trade, exit
    if (!isTradeActive)
        return;

    // Check if the position is still open
    if (!PositionSelect(_Symbol))
    {
        Print("Active trade closed. Resetting trade tracker.");
        isTradeActive = false;  // Reset the tracker
        return;
    }

    // Retrieve position details
    double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
    ENUM_ORDER_TYPE type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    double stopLoss = PositionGetDouble(POSITION_SL);
    double takeProfit = PositionGetDouble(POSITION_TP);

    Print("Monitoring active trade - Open Price: ", openPrice, ", SL: ", stopLoss, ", TP: ", takeProfit);

    // Optionally log or handle additional monitoring logic here
}

void AdjustLotSizeOnPositionClose()
{
    // Loop through the deals history, starting from the most recent
    for (int i = HistoryDealsTotal() - 1; i >= 0; i--)
    {
        ulong ticket = HistoryDealGetTicket(i); // Get the deal ticket
        if (ticket == 0)
            continue;

        // Check the deal type (buy/sell) and reason for closure
        ENUM_DEAL_ENTRY dealEntry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);
        ENUM_DEAL_REASON dealReason = (ENUM_DEAL_REASON)HistoryDealGetInteger(ticket, DEAL_REASON);

        // Only process closed deals
        if (dealEntry == DEAL_ENTRY_OUT)
        {
            if (dealReason == DEAL_REASON_SL) // Closed by Stop Loss
            {
                currentLotSize *= 2; // Double the lot size
                Print("Deal closed by SL. Doubling lot size to: ", currentLotSize);
            }
            else if (dealReason == DEAL_REASON_TP) // Closed by Take Profit
            {
                currentLotSize = lot; // Reset lot size
                Print("Deal closed by TP. Resetting lot size to: ", currentLotSize);
            }

            // Break after processing the latest closed deal
            break;
        }
    }
}

ulong OpenTrade(ENUM_ORDER_TYPE type, double volume, string comment)
{
    // Check if a trade of the same type is already active
    if (isTradeActive && activeTrade.type == type)
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
    if (!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("Trade request failed with error: ", error);
        PrintFormat("retcode=%u  deal=%I64u  order=%I64u ", result.retcode, result.deal, result.order);
        ResetLastError();
    }
    if (result.retcode == TRADE_RETCODE_DONE)
    {
        // Update active trade details
        activeTrade.ticket = result.order;
        activeTrade.type = type;
        activeTrade.openPrice = price;
        activeTrade.stopLoss = stopLoss;
        activeTrade.takeProfit = takeProfit;
        isTradeActive = true;

        Print("Trade opened successfully - Ticket: ", result.order);
        return result.order;
    }
    else
    {
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
//+------------------------------------------------------------------+