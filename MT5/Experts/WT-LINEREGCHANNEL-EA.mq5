//+------------------------------------------------------------------+
//|                                                   WT_Reader.mq5  |
//|                        Copyright 2024, Your Name                |
//|                                             https://www.mql5.com  |
//+------------------------------------------------------------------+
#property strict

input string indicatorName = "WT";               // Custom Indicator Name
input ENUM_TIMEFRAMES timeframe = PERIOD_M5;     // Timeframe for the indicator
input double lotSize = 0.1;                      // Lot size for trade
input ulong magicNumber = 123456;                // Magic number to identify EA trades
input double slPoints = 50;                      // Stop loss in points
input double tpPoints = 100;                     // Take profit in points
input double maxDeviation = 10;                  // Max deviation in points

// Declare variables to store the indicator handle and values
double wt1Value, wt2Value, obLevel1, osLevel1;
int indicatorHandle = INVALID_HANDLE; // Indicator handle

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize the indicator handle for WaveTrend
    indicatorHandle = iCustom(Symbol(), timeframe, indicatorName);
    if (indicatorHandle == INVALID_HANDLE)
    {
        Print("Failed to initialize WaveTrend indicator. Error: ", GetLastError());
        return INIT_FAILED;
    }
    
    Print("WaveTrend Reader Initialized");
    return INIT_SUCCEEDED; // Initialization successful
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check if indicator handle is valid
    if (indicatorHandle == INVALID_HANDLE)
    {
        Print("Indicator handle is invalid.");
        return;
    }

    // Temporary arrays to store buffer values
    double wt1Array[], obLevel1Array[], osLevel1Array[];

    // Copy indicator values for the current and previous bars
    if (CopyBuffer(indicatorHandle, 0, 0, 2, wt1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 2, 0, 2, obLevel1Array) <= 0 ||
        CopyBuffer(indicatorHandle, 4, 0, 2, osLevel1Array) <= 0)
    {
        Print("Error copying buffer values: ", GetLastError());
        ResetLastError();
        return;
    }

    // Assign current and previous values for crossover detection
    double wt1Current = wt1Array[0];
    double wt1Previous = wt1Array[1];
    double obLevel1Current = obLevel1Array[0];
    double osLevel1Current = osLevel1Array[0];
// Print the retrieved values
    PrintFormat("Current Values - WT1 current: %f, WT1 previous: %f, OB Level 1 current: %f, OS Level 1 previous: %f",
                wt1Current, wt1Previous, obLevel1Current, osLevel1Current);
    // Check for crossover conditions
    bool buySignal = (wt1Previous < osLevel1Current && wt1Current > osLevel1Current); // WT1 crossing above OS1
    bool sellSignal = (wt1Previous > obLevel1Current && wt1Current < obLevel1Current); // WT1 crossing below OB1

    if (buySignal)
    {
        // Open a Buy trade
        OpenTrade(ORDER_TYPE_BUY, lotSize);
    }
    else if (sellSignal)
    {
        // Open a Sell trade
        OpenTrade(ORDER_TYPE_SELL, lotSize);
    }
}

//+------------------------------------------------------------------+
//| Function to open trades with volume adjustment                   |
//+------------------------------------------------------------------+
void OpenTrade(ENUM_ORDER_TYPE type, double volume)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(Symbol(), SYMBOL_ASK) : SymbolInfoDouble(Symbol(), SYMBOL_BID);
    double stopLevel = SymbolInfoInteger(Symbol(), SYMBOL_TRADE_STOPS_LEVEL) * _Point;

    // Check if trading is allowed on this symbol
    if (!SymbolInfoInteger(Symbol(), SYMBOL_TRADE_MODE))
    {
        Print("Trading not allowed on symbol: ", Symbol());
        return;
    }

    // Retrieve volume constraints
    double minVolume = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
    double maxVolume = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
    double stepVolume = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);

    // Adjust volume to the nearest valid step if needed
    if (volume < minVolume)
    {
        volume = minVolume;
    }
    else if (volume > maxVolume)
    {
        volume = maxVolume;
    }
    else
    {
        volume = MathFloor(volume / stepVolume) * stepVolume;
    }

    // Set Stop Loss and Take Profit, ensuring minimum distance
    double sl = (type == ORDER_TYPE_BUY) ? price - slPoints * _Point : price + slPoints * _Point;
    double tp = (type == ORDER_TYPE_BUY) ? price + tpPoints * _Point : price - tpPoints * _Point;

    // Ensure SL and TP respect the minimum stop level
    if (stopLevel > 0)
    {
        if (type == ORDER_TYPE_BUY)
        {
            sl = MathMax(sl, price - stopLevel);
            tp = MathMin(tp, price + stopLevel);
        }
        else
        {
            sl = MathMin(sl, price + stopLevel);
            tp = MathMax(tp, price - stopLevel);
        }
    }

    // Initialize trade request parameters
    request.action = TRADE_ACTION_DEAL;
    request.symbol = Symbol();
    request.volume = volume;
    request.type = type;
    request.price = price;
    request.sl = sl;
    request.tp = tp;
    request.deviation = maxDeviation;
    request.magic = magicNumber;
    request.type_filling = ORDER_FILLING_RETURN; // More flexible order filling
    request.comment = "WT Crossover Trade";

    // Send trade request and handle result
    if (!OrderSend(request, result))
    {
        Print("Trade request failed. Error: ", GetLastError());
        ResetLastError();
    }
    else
    {
        Print("Trade opened successfully. Ticket: ", result.order, ", Volume: ", volume);
    }
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Release the indicator handle
    if (indicatorHandle != INVALID_HANDLE)
    {
        IndicatorRelease(indicatorHandle);
        indicatorHandle = INVALID_HANDLE;
    }
}
//+------------------------------------------------------------------+
