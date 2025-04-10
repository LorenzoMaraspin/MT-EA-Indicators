//+------------------------------------------------------------------+
//|                                                         WT-1.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"
#property indicator_separate_window
#property indicator_buffers 10     // Total buffers for indicators
#property indicator_maximum    80.0
#property indicator_minimum    -80.0
#property indicator_plots   6

// Indicator plot properties
#property indicator_label1  "WT1"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrBlue

#property indicator_label2  "WT2"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrRed

#property indicator_label3  "OB Level 1"
#property indicator_type3   DRAW_LINE
#property indicator_style3  STYLE_DASHDOT
#property indicator_color3  clrOrangeRed
#property indicator_width3  2

#property indicator_label4  "OB Level 2"
#property indicator_type4   DRAW_LINE
#property indicator_style4  STYLE_DASHDOT
#property indicator_color4  clrOrangeRed
#property indicator_width4  2

#property indicator_label5  "OS Level 1"
#property indicator_type5   DRAW_LINE
#property indicator_style5  STYLE_DASHDOT
#property indicator_color5  clrGreen
#property indicator_width5  2

#property indicator_label6  "OS Level 2"
#property indicator_type6   DRAW_LINE
#property indicator_style6  STYLE_DASHDOT
#property indicator_color6  clrGreen
#property indicator_width6  2

// Define input parameters similar to PineScript
input int n1 = 10;                    // Channel Length
input int n2 = 21;                    // Average Length
input double obLevel1 = 60.0;         // Over Bought Level 1
input double obLevel2 = 53.0;         // Over Bought Level 2
input double osLevel1 = -60.0;        // Over Sold Level 1
input double osLevel2 = -53.0;        // Over Sold Level 2

// Define a structure to hold WaveTrend data buffers
struct WaveTrendData
{
    double wt1Buffer[];    // WaveTrend Line 1
    double wt2Buffer[];    // WaveTrend Line 2
    double esaBuffer[];    // ESA (EMA of average price)
    double dBuffer[];      // D (EMA of absolute difference)
    double ciBuffer[];     // CI calculation
    double tciBuffer[];    // TCI (EMA of CI)
    double obBuffer1[];    // Overbought Level 1
    double obBuffer2[];    // Overbought Level 2
    double osBuffer1[];    // Oversold Level 1
    double osBuffer2[];    // Oversold Level 2
};

// Create an instance of WaveTrendData
WaveTrendData waveTrend;

// Function to check for and log errors
void CheckForErrors(string functionName)
{
    int error_code = GetLastError();
    if (error_code != 0)
    {
        PrintFormat("Error in %s: %d", functionName, error_code);
        ResetLastError();
    }
}

// Initialization function
int OnInit()
{
    Print("WT Indicator initialization!");

    // Link indicator buffers to the plot buffers
    SetIndexBuffer(0, waveTrend.wt1Buffer);
    SetIndexBuffer(1, waveTrend.wt2Buffer);
    CheckForErrors("OnInit - SetIndexBuffer WT buffers");
    
    // Link overbought and oversold level buffers
    SetIndexBuffer(2, waveTrend.obBuffer1);
    SetIndexBuffer(3, waveTrend.obBuffer2);
    SetIndexBuffer(4, waveTrend.osBuffer1);
    SetIndexBuffer(5, waveTrend.osBuffer2);
    CheckForErrors("OnInit - SetIndexBuffer OB/OS buffers");
    
    // Link auxiliary buffers for calculations
    SetIndexBuffer(6, waveTrend.esaBuffer);
    SetIndexBuffer(7, waveTrend.dBuffer);
    SetIndexBuffer(8, waveTrend.ciBuffer);
    SetIndexBuffer(9, waveTrend.tciBuffer);
    CheckForErrors("OnInit - SetIndexBuffer calculation buffers");



    return INIT_SUCCEEDED;
}

// Custom EMA function
double CustomEMA(int period, double prevEma, double price)
{
    double alpha = 2.0 / (period + 1.0);
    return alpha * price + (1.0 - alpha) * prevEma;
}

// Calculation function
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
    // Ensure all buffers are sized correctly to avoid out-of-range errors
    ArrayResize(waveTrend.wt1Buffer, rates_total);
    ArrayResize(waveTrend.wt2Buffer, rates_total);
    ArrayResize(waveTrend.esaBuffer, rates_total);
    ArrayResize(waveTrend.dBuffer, rates_total);
    ArrayResize(waveTrend.ciBuffer, rates_total);
    ArrayResize(waveTrend.tciBuffer, rates_total);
    ArrayResize(waveTrend.obBuffer1, rates_total);
    ArrayResize(waveTrend.obBuffer2, rates_total);
    ArrayResize(waveTrend.osBuffer1, rates_total);
    ArrayResize(waveTrend.osBuffer2, rates_total);

    // Set the overbought and oversold levels for all bars
    for (int i = 0; i < rates_total; i++)
    {
        waveTrend.obBuffer1[i] = obLevel1; // Overbought Level 1
        waveTrend.obBuffer2[i] = obLevel2; // Overbought Level 2
        waveTrend.osBuffer1[i] = osLevel1; // Oversold Level 1
        waveTrend.osBuffer2[i] = osLevel2; // Oversold Level 2
    }

    int begin = MathMax(n1, n2) + 1;

    if (rates_total < begin)
        return 0;

    // Adjust loop to start at begin to avoid array out of range
    for (int i = begin; i < rates_total; i++)
    {
        // Average price calculation
        double ap = (high[i] + low[i] + close[i]) / 3.0;

        // Calculate ESA (EMA of average price)
        waveTrend.esaBuffer[i] = (i == begin) ? ap : CustomEMA(n1, waveTrend.esaBuffer[i - 1], ap);
        CheckForErrors("OnCalculate - ESA calculation");

        // Calculate D (EMA of absolute difference)
        double absDiff = MathAbs(ap - waveTrend.esaBuffer[i]);
        waveTrend.dBuffer[i] = (i == begin) ? absDiff : CustomEMA(n1, waveTrend.dBuffer[i - 1], absDiff);
        CheckForErrors("OnCalculate - D calculation");

        // Calculate CI, checking for zero in waveTrend.dBuffer[i] to avoid division by zero
        waveTrend.ciBuffer[i] = (waveTrend.dBuffer[i] != 0.0) 
                                 ? (ap - waveTrend.esaBuffer[i]) / (0.015 * waveTrend.dBuffer[i])
                                 : 0.0; // Default to 0 if dBuffer[i] is zero
        CheckForErrors("OnCalculate - CI calculation");

        // Calculate TCI (EMA of CI)
        waveTrend.tciBuffer[i] = (i == begin) ? waveTrend.ciBuffer[i] : CustomEMA(n2, waveTrend.tciBuffer[i - 1], waveTrend.ciBuffer[i]);
        CheckForErrors("OnCalculate - TCI calculation");

        // Final WaveTrend calculations
        waveTrend.wt1Buffer[i] = waveTrend.tciBuffer[i];

        // WT2 calculation using a simple moving average (SMA) of WT1 over 4 periods
        if (i >= begin + 3)
        {
            waveTrend.wt2Buffer[i] = (waveTrend.wt1Buffer[i] + waveTrend.wt1Buffer[i - 1] +
                                       waveTrend.wt1Buffer[i - 2] + waveTrend.wt1Buffer[i - 3]) / 4.0;
        }
        else
        {
            waveTrend.wt2Buffer[i] = 0.0;  // Default to 0 if SMA period isn't satisfied
        }
        CheckForErrors("OnCalculate - WT calculations");
    }
    return rates_total;
}
