//+------------------------------------------------------------------+
//|                                                   WT_Reader.mq5  |
//|                        Copyright 2024, Your Name                 |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property strict
// EA VARIABLE DEFINITION
input ENUM_TIMEFRAMES timeframe = PERIOD_M5;     // Timeframe for the indicators
input double lotSize = 0.01;                     // Lot size for trade
input ulong magicNumber = 123456;                // Magic number to identify EA trades
input double slPoints = 15;                      // Stop loss in points
input double tpPoints = 15;                      // Take profit in points
input double maxDeviation = 15;                  // Max deviation in points
// MARTIN GALE VARIABLE DEFINITION
input double lossThreshold = 5;                  // Loss threshold in pips for Martingale logic
input double maxLotSize = 10.0;                  // Maximum allowed lot size
input double lotMultiplier = 2.0;                // Lot size multiplier for Martingale
// INDICATOR VARIABLE DEFINITION
int indicatorHandle = INVALID_HANDLE;            // WaveTrend indicator handle
int regressionIndicatorHandle = INVALID_HANDLE;  // Regression channel indicator handle
// TRADE MANAGEMENT VARIABLE DEFINITION
bool upperCrossed = false, lowerCrossed = false, obCrossed = false, osCrossed = false;
bool buyTradeTriggered = false, sellTradeTriggered = false;

struct MartingaleTrade
{
    ulong orderID;            // Unique ID of the trade
    ENUM_ORDER_TYPE type;     // Buy or Sell type
    double entryPrice;        // Entry price of the trade
    double stopLoss;          // Stop loss price
    double takeProfit;        // Take profit price
    double buyVolume;         // Current sell lot size
    double sellVolume;        // Current buy lot size
    double baseLotSize;       // Initial lot size
    double maxLotSize;        // Maximum allowable lot size
    double multiplier;        // Lot size multiplier
    bool active;              // Flag to check if trade is still active

    // Constructor to initialize a new trade
    MartingaleTrade(ulong id = 0, ENUM_ORDER_TYPE t = ORDER_TYPE_BUY, double price = 0.0, 
                    double sl = 0.0, double tp = 0.0, double buyVol = 0.01, double sellVol = 0.01,
                    double baseVol = 0.01, double maxVol = 1.0, double mult = 2.0)
    {
        orderID = id;
        type = t;
        entryPrice = price;
        stopLoss = sl;
        takeProfit = tp;
        buyVolume = buyVol;
        sellVolume = sellVol;
        baseLotSize = baseVol;
        maxLotSize = maxVol;
        multiplier = mult;
        active = true;
    }

    // Update lot size for the trade
    void UpdateLotSize()
    {
        if (type == ORDER_TYPE_BUY)
        {
            buyVolume = MathMin(buyVolume * multiplier, maxLotSize);
        } else {
            sellVolume = MathMin(sellVolume * multiplier, maxLotSize);
        }
        Print("Updated lot size for ", (type == ORDER_TYPE_BUY ? "BUY" : "SELL"));
    }

    // Reset lot size to base for the trade
    void ResetLotSize()
    {
        if (type == ORDER_TYPE_BUY)
            buyVolume = baseLotSize;
        else
            sellVolume = baseLotSize;
        Print("Reset lot size for ", (type == ORDER_TYPE_BUY ? "BUY" : "SELL"));
    }

    // Get the current lot size
    double GetLotSize()
    {
        if (type == ORDER_TYPE_BUY)
            return buyVolume;
        else
            return sellVolume;
    }

    // Handle Stop Loss logic
    void HandleStopLoss()
    {
        Print("Trade hit Stop Loss. Updating lot size for ", (type == ORDER_TYPE_BUY ? "BUY" : "SELL"), " trades.");
        UpdateLotSize();
        active = false;
    }

    // Handle Take Profit logic
    void HandleTakeProfit()
    {
        Print("Trade hit Take Profit. Resetting lot size for ", (type == ORDER_TYPE_BUY ? "BUY" : "SELL"), " trades.");
        ResetLotSize();
        active = false;
    }

    // Method to determine if the trade hit Stop Loss
    bool HasHitStopLoss(double currentPrice)
    {
        return (type == ORDER_TYPE_BUY && currentPrice <= stopLoss) ||
               (type == ORDER_TYPE_SELL && currentPrice >= stopLoss);
    }

    // Method to determine if the trade hit Take Profit
    bool HasHitTakeProfit(double currentPrice)
    {
        return (type == ORDER_TYPE_BUY && currentPrice >= takeProfit) ||
               (type == ORDER_TYPE_SELL && currentPrice <= takeProfit);
    }

    // Method to apply Martingale logic based on loss threshold
    bool ShouldApplyMartingale(double currentPrice, double lossThreshold)
    {
        double priceDifference = (type == ORDER_TYPE_BUY) ? 
                                 entryPrice - currentPrice : 
                                 currentPrice - entryPrice;
        return priceDifference >= lossThreshold * _Point;
    }
};
MartingaleTrade currentTrade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize the indicator handle for WaveTrend and Regression Channel
    indicatorHandle = iCustom(Symbol(), timeframe, "WT");
    regressionIndicatorHandle = iCustom(Symbol(), timeframe, "LINEREG");
    
    if (indicatorHandle == INVALID_HANDLE || regressionIndicatorHandle == INVALID_HANDLE)
    {
        Print("Failed to initialize WaveTrend or Regression Channel indicator. Error: ", GetLastError());
        return INIT_FAILED;
    }    
    Print("WaveTrend and Regression Channel Indicators Initialized");
    return INIT_SUCCEEDED; // Initialization successful
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Fetch WaveTrend indicator values
    double wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current;
    if (!CopyWaveTrendValues(wt1Current, wt1Previous, wt2Current, wt2Previous, obLevel1Current, osLevel1Current))
        return;

    // Fetch Regression Channel indicator values
    double upperLineCurrent, lowerLineCurrent;
    if (!CopyRegressionValues(upperLineCurrent, lowerLineCurrent))
        return;

    // Handle active trade logic
    if (currentTrade.active)
    {
        ManageActiveTrade();
    }
    else
    {
        // Check trade conditions if no active trade
        CheckTradeConditions(wt1Current, wt1Previous, wt2Current, wt2Previous, 
                             osLevel1Current, obLevel1Current, upperLineCurrent, lowerLineCurrent);
    }
}

// Helper function to copy WaveTrend buffer values
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

// Manage logic for active trades
void ManageActiveTrade()
{
    double currentPrice = (currentTrade.type == ORDER_TYPE_BUY) ?
                          SymbolInfoDouble(Symbol(), SYMBOL_BID) :
                          SymbolInfoDouble(Symbol(), SYMBOL_ASK);

    if (currentTrade.active)
    {
        if (currentTrade.HasHitStopLoss(currentPrice))
        {
            Print("Trade hit Stop Loss: ", (currentTrade.type == ORDER_TYPE_BUY ? "BUY" : "SELL"));
            currentTrade.HandleStopLoss();
        }
        else if (currentTrade.HasHitTakeProfit(currentPrice))
        {
            Print("Trade hit Take Profit: ", (currentTrade.type == ORDER_TYPE_BUY ? "BUY" : "SELL"));
            currentTrade.HandleTakeProfit();
        }
    }
    else if (currentTrade.ShouldApplyMartingale(currentPrice, lossThreshold))
    {
        Print("Loss threshold reached. Opening a new Martingale trade for ", 
              (currentTrade.type == ORDER_TYPE_BUY ? "BUY" : "SELL"));

        // Update the lot size for the new trade
        currentTrade.UpdateLotSize();
        ulong newOrderID = 0;
        if (currentTrade.type == ORDER_TYPE_BUY)
            newOrderID = OpenTrade(currentTrade.type, currentTrade.buyVolume, "MartinGale increase");
        else
            newOrderID = OpenTrade(currentTrade.type, currentTrade.sellVolume, "MartinGale increase");
        // Open a new trade
        //ulong newOrderID = OpenTrade(currentTrade.type, currentTrade.volume, "MartinGale increase");

        // Update the current trade details with the new trade
        if (newOrderID > 0)  // Ensure trade was successfully opened
        {
            currentTrade.orderID = newOrderID;
            currentTrade.entryPrice = currentPrice;
            currentTrade.active = true;
        }
        else
        {
            Print("Failed to open a new trade for ", (currentTrade.type == ORDER_TYPE_BUY ? "BUY" : "SELL"));
        }
    }
}
//+------------------------------------------------------------------+
//| Function to detect the trading condition to open trades          |
//+------------------------------------------------------------------+
void CheckTradeConditions(double wt1Current, double wt1Previous, double wt2Current, double wt2Previous, 
                          double osCurrent, double obCurrent, double upperCurrent, double lowerCurrent)
{
    // Determine WaveTrend signals
    bool buySignalWT = (wt1Previous < osCurrent && wt1Current > osCurrent); // WT1 crossing above OS
    bool sellSignalWT = (wt1Previous > obCurrent && wt1Current < obCurrent); // WT1 crossing below OB
    bool wt1CrossOverWt2 = (wt1Previous < wt2Previous && wt1Current > wt2Current);
    bool wt1CrossUnderWt2 = (wt1Previous > wt2Previous && wt1Current < wt2Current);

    // Fetch regression line price levels
    double currentHighPrice = iHigh(Symbol(), timeframe, 0);
    double currentLowPrice = iLow(Symbol(), timeframe, 0);
    double upperCurrentPrice = ObjectGetValueByTime(0, "LinRegUpperLine", iTime(Symbol(), timeframe, 0));
    double lowerCurrentPrice = ObjectGetValueByTime(0, "LinRegLowerLine", iTime(Symbol(), timeframe, 0));
    bool lineCrossoverUpper = currentHighPrice >= upperCurrentPrice && currentLowPrice <= upperCurrentPrice;
    bool lineCrossoverLower = currentLowPrice <= lowerCurrentPrice && currentHighPrice >= lowerCurrentPrice;

    // Manage crossover states
    if (lineCrossoverUpper && !upperCrossed)
    {
        upperCrossed = true;
        lowerCrossed = false;
    }
    else if (currentHighPrice < upperCurrentPrice)
    {
        upperCrossed = false;
    }

    if (lineCrossoverLower && !lowerCrossed)
    {
        lowerCrossed = true;
        upperCrossed = false;
    }
    else if (currentLowPrice > lowerCurrentPrice)
    {
        lowerCrossed = false;
    }

    int tradeSelection = 0;
    string comment = "";

    // Check for WaveTrend and price-level based trade signals
    if (buySignalWT && !buyTradeTriggered && !obCrossed)
    {
        tradeSelection = 1;
        comment = "WT < OS";
        obCrossed = true;
        osCrossed = false;
    }
    else if (sellSignalWT && !sellTradeTriggered && !osCrossed)
    {
        tradeSelection = 2;
        comment = "WT > OB";
        osCrossed = true;
        obCrossed = false;
    }

    if (upperCrossed && wt1CrossUnderWt2 && !sellTradeTriggered)
    {
        tradeSelection = 2;
        comment = "PRICE > UPPER & WT1 crossunder WT2";
    }
    else if (lowerCrossed && wt1CrossOverWt2 && !buyTradeTriggered)
    {
        tradeSelection = 1;
        comment = "PRICE < LOWER & WT1 crossover WT2";
    }

    // Execute trade actions
    if (tradeSelection == 1 && !buyTradeTriggered)
    {
        OpenTrade(ORDER_TYPE_BUY, currentTrade.buyVolume, comment);
        buyTradeTriggered = true;
        sellTradeTriggered = false;
    }
    else if (tradeSelection == 2 && !sellTradeTriggered)
    {
        OpenTrade(ORDER_TYPE_SELL, currentTrade.sellVolume, comment);
        sellTradeTriggered = true;
        buyTradeTriggered = false;
    }

    // Reset trade triggers
    if (!buySignalWT && !lowerCrossed)
    {
        buyTradeTriggered = false;
    }
    if (!sellSignalWT && !upperCrossed)
    {
        sellTradeTriggered = false;
    }
}
//+------------------------------------------------------------------+
//| Function to open trades with volume adjustment                   |
//+------------------------------------------------------------------+
ulong OpenTrade(ENUM_ORDER_TYPE type, double volume, string comment)
{
    MqlTradeRequest request={};
    MqlTradeResult  result={};
    MqlTick latest_price;

    // Check if trading is allowed on this symbol
    if (!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
    {
        Print("Trading not allowed on symbol: ", _Symbol);
        return -1;
    }

    // Get the last price quote
    if (!SymbolInfoTick(_Symbol, latest_price))
    {
        Print("Error getting the latest price quote - error:", GetLastError());
        return -1;
    }

    double price = (type == ORDER_TYPE_BUY) ? NormalizeDouble(latest_price.ask, _Digits) : NormalizeDouble(latest_price.bid, _Digits);

    // Set Stop Loss and Take Profit, ensuring minimum distance from price
    double sl = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price - slPoints * _Point, _Digits) : NormalizeDouble(price + slPoints * _Point, _Digits);
    double tp = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price + tpPoints * _Point, _Digits): NormalizeDouble(price - tpPoints * _Point, _Digits);

    // Log trade details for debugging purposes
    Print("Preparing to open trade. Type: ", type, ", Price: ", price, ", SL: ", sl, ", TP: ", tp, " Digit: ", _Digits);

    // Initialize trade request parameters
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = volume;
    request.type = type;
    request.price = price;
    request.sl = sl;
    request.tp = tp;
    request.comment = comment;
    request.deviation = maxDeviation;

    // Send the trade request and handle result
    if (!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("Trade request failed with error: ", error);
        PrintFormat("retcode=%u  deal=%I64u  order=%I64u ", result.retcode, result.deal, result.order);
        ResetLastError();
    }
    else
    {
        if (result.retcode == TRADE_RETCODE_DONE)
        {
            Print("Trade opened successfully. Ticket: ", result.order, ", Volume: ", volume);
            currentTrade = MartingaleTrade(result.order, type, price, sl, tp, volume);
            
            
        }
        else
        {
            Print("Trade request unsuccessful. Retcode: ", result.retcode);
        }
    }
    return result.order;
}
//+------------------------------------------------------------------+
//| Function to draw a cross on the chart                            |
//+------------------------------------------------------------------+
void DrawArrow(string name, datetime time, double price, color clr, int arrowSymbol)
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
