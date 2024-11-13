//+------------------------------------------------------------------+
//|                                                   WT_Reader.mq5  |
//|                        Copyright 2024, Your Name                |
//|                                             https://www.mql5.com  |
//+------------------------------------------------------------------+
#property strict
input ENUM_TIMEFRAMES timeframe = PERIOD_M5;     // Timeframe for the indicators
input double lotSize = 0.01;                      // Lot size for trade
input ulong magicNumber = 123456;                // Magic number to identify EA trades
input double slPoints = 500;                      // Stop loss in points
input double tpPoints = 1000;                     // Take profit in points
input double maxDeviation = 15;                  // Max deviation in points
int digit = _Digits;
// Declare variables to store the indicator handles and values
int indicatorHandle = INVALID_HANDLE; // WaveTrend indicator handle
int regressionIndicatorHandle = INVALID_HANDLE; // Regression channel indicator handle

// Flags for crossover events
bool upperCrossed = false, lowerCrossed = false, obCrossed = false, osCrossed = false;
bool buyTradeTriggered = false, sellTradeTriggered = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize the indicator handle for WaveTrend
    indicatorHandle = iCustom(Symbol(), timeframe, "WT");
    if (indicatorHandle == INVALID_HANDLE)
    {
        Print("Failed to initialize WaveTrend indicator. Error: ", GetLastError());
        return INIT_FAILED;
    }
    
    // Initialize the indicator handle for Regression Channel
    regressionIndicatorHandle = iCustom(Symbol(), timeframe, "LINEREG");
    if (regressionIndicatorHandle == INVALID_HANDLE)
    {
        Print("Failed to initialize Regression Channel indicator. Error: ", GetLastError());
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
    // Check if indicator handles are valid
    if (indicatorHandle == INVALID_HANDLE || regressionIndicatorHandle == INVALID_HANDLE)
    {
        Print("Indicator handle is invalid.");
        return;
    }

    // Temporary arrays to store buffer values for WaveTrend
    double wt1Array[], wt2Array[], obLevel1Array[], osLevel1Array[];
    
    // Temporary arrays for Linear Regression Channel buffers
    double upperLineArray[], lowerLineArray[], middleLineArray[];

    // Copy WaveTrend indicator values for the current and previous bars
    if (CopyBuffer(indicatorHandle, 0, 0, 2, wt1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 1, 0, 2, wt2Array) <= 0 ||
        CopyBuffer(indicatorHandle, 2, 0, 2, obLevel1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 4, 0, 2, osLevel1Array) <= 0)
    {
        Print("Error copying WaveTrend buffer values: ", GetLastError());
        ResetLastError();
        return;
    }
    
    // Copy Regression Channel indicator values
    if (CopyBuffer(regressionIndicatorHandle, 0, 0, 2, upperLineArray) <= 0 ||
        CopyBuffer(regressionIndicatorHandle, 1, 0, 2, middleLineArray) <= 0 ||
        CopyBuffer(regressionIndicatorHandle, 2, 0, 2, lowerLineArray) <= 0)
    {
        Print("Error copying Regression Channel buffer values: ", GetLastError());
        ResetLastError();
        return;
    }

    // Assign current and previous values for WaveTrend crossover detection
    double wt1Current = wt1Array[0];
    double wt1Previous = wt1Array[1];
    double wt2Current = wt2Array[0];
    double wt2Previous = wt2Array[1];
    double obLevel1Current = obLevel1Array[0];
    double osLevel1Current = osLevel1Array[0];

    // Assign current values for Regression Channel
    double upperLineCurrent = upperLineArray[0];
    double lowerLineCurrent = lowerLineArray[0];
    
    CheckTradeConditions(wt1Current, wt1Previous, wt2Current, wt2Previous, osLevel1Current, obLevel1Current, upperLineCurrent, lowerLineCurrent);
}

//+------------------------------------------------------------------+
//| Function to detect the trading condition to open trades          |
//+------------------------------------------------------------------+
void CheckTradeConditions(double wt1Current, double wt1Previous, double wt2Current, double wt2Previous, double osCurrent, double obCurrent, double upperCurrent, double lowerCurrent)
{
    int tradeSelection = 0;
    // Check for WaveTrend crossover conditions
    bool buySignalWT = (wt1Previous < osCurrent && wt1Current > osCurrent); // WT1 crossing above OS1
    bool sellSignalWT = (wt1Previous > obCurrent && wt1Current < obCurrent); // WT1 crossing below OB1
    bool wt1CrossOverWt2 = (wt1Previous < wt2Previous && wt1Current > wt2Current);
    bool wt1CrossUnderWt2 = (wt1Previous > wt2Previous && wt1Current < wt2Current);

    // Check for LineReg crossover conditions
    double currentHighPrice = iHigh(Symbol(), timeframe, 0);
    double currentLowPrice = iLow(Symbol(), timeframe, 0);
    double upperCurrentPrice = ObjectGetValueByTime(0, "LinRegUpperLine", iTime(Symbol(), timeframe, 0));
    double lowerCurrentPrice = ObjectGetValueByTime(0, "LinRegLowerLine", iTime(Symbol(), timeframe, 0));
    bool lineCrossoverUpper = currentHighPrice >= upperCurrentPrice && currentLowPrice <= upperCurrentPrice;
    bool lineCrossoverLower = currentLowPrice <= lowerCurrentPrice && currentHighPrice >= lowerCurrentPrice;

    // Wavetrend OB and OS checks
    if (buySignalWT && !buyTradeTriggered)
    {
        tradeSelection = 1;
        DrawArrow("UpperCrossArrow", iTime(Symbol(), timeframe, 0), currentHighPrice + (300 * _Point), clrGreen, 13);
        Print("TradeSelection: ", tradeSelection, " BUY, WT < OS");
    }
    else if (sellSignalWT && !sellTradeTriggered)
    {
        tradeSelection = 2;
        DrawArrow("UpperCrossArrow", iTime(Symbol(), timeframe, 0), currentHighPrice + (300 * _Point), clrOrange, 13);
        Print("TradeSelection: ", tradeSelection, " SELL, WT > OB");
    }

    // Check for price crossing the Regression Channel lines only once
    if (lineCrossoverUpper && !upperCrossed) 
    {
        DrawArrow("UpperCrossArrow", iTime(Symbol(), timeframe, 0), currentHighPrice + (300 * _Point), clrYellow, 234);
        Print("TradeSelection: ", tradeSelection, " PRICE > UPPER LINE");
        upperCrossed = true;
        lowerCrossed = false;
    }
    else if (currentHighPrice < upperCurrentPrice)
    {
        upperCrossed = false;
    }
    if (lineCrossoverLower && !lowerCrossed)
    {
        DrawArrow("LowerCrossArrow", iTime(Symbol(), timeframe, 0), currentLowPrice - (300 * _Point), clrViolet, 233);
        Print("TradeSelection: ", tradeSelection, " PRICE < LOWER LINE");
        lowerCrossed = true;
        upperCrossed = false;
    }
    else if (currentLowPrice > lowerCurrentPrice)
    {
        lowerCrossed = false;
    }

    if (upperCrossed && wt1CrossUnderWt2 && !sellTradeTriggered)
    {
        tradeSelection = 2;
    }
    else if (lowerCrossed && wt1CrossOverWt2 && !buyTradeTriggered)
    {
        tradeSelection = 1;
    }

    // Execute trades based on tradeSelection, ensuring only one trade per condition confirmation
    switch (tradeSelection)
    {
        case 1:
            if (!buyTradeTriggered)
            {
                Print("Opening LONG Position");
                DrawArrow("LowerCrossArrow", iTime(Symbol(), timeframe, 0), currentLowPrice - (250 * _Point), clrBlue, 241);
                OpenTrade(ORDER_TYPE_BUY, lotSize);
                buyTradeTriggered = true; // Set flag to prevent further trades
                sellTradeTriggered = false; // Reset sell flag
            }
            break;

        case 2:
            if (!sellTradeTriggered)
            {
                Print("Opening SHORT Position");
                DrawArrow("UpperCrossArrow", iTime(Symbol(), timeframe, 0), currentHighPrice + (250 * _Point), clrRed, 242);
                OpenTrade(ORDER_TYPE_SELL, lotSize);
                sellTradeTriggered = true; // Set flag to prevent further trades
                buyTradeTriggered = false; // Reset buy flag
            }
            break;

        case 0:
            // No action required
            break;
    }

    // Reset flags when the conditions no longer hold
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
void OpenTrade(ENUM_ORDER_TYPE type, double volume)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    MqlTick latest_price;

    // Check if trading is allowed on this symbol
    if (!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
    {
        Print("Trading not allowed on symbol: ", _Symbol);
        return;
    }

    // Get the last price quote
    if (!SymbolInfoTick(_Symbol, latest_price))
    {
        Print("Error getting the latest price quote - error:", GetLastError());
        return;
    }

    double price = (type == ORDER_TYPE_BUY) ? NormalizeDouble(latest_price.ask, digit) : NormalizeDouble(latest_price.bid, digit);

    // Set Stop Loss and Take Profit, ensuring minimum distance from price
    double sl = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price - slPoints * _Point, digit) : NormalizeDouble(price + slPoints * _Point, digit);
    double tp = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price + tpPoints * _Point, digit): NormalizeDouble(price - tpPoints * _Point, digit);

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
    request.comment = "WT-LN-Trade";
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
        }
        else
        {
            Print("Trade request unsuccessful. Retcode: ", result.retcode);
        }
    }
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
        //Print("Arrow ", name, " drawn on chart at time: ", TimeToString(time), " and price: ", price);
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
