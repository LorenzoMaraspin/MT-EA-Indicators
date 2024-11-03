#property strict
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   3

// Plot properties
#property indicator_label1  "LinRegUpperLine"
#property indicator_type1   DRAW_LINE
#property indicator_style1  STYLE_SOLID
#property indicator_color1  clrBlue
#property indicator_width1  1
#property indicator_label2  "LinRegLowerLine"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrRed
#property indicator_style2  STYLE_SOLID
#property indicator_width2  1
#property indicator_label3  "LinRegBaseLine"
#property indicator_type3   DRAW_LINE
#property indicator_style3  STYLE_SOLID
#property indicator_color3  clrGray
#property indicator_width3  1

// Input parameters
input int lengthInput = 100;                // Length
input double upperMultInput = 2.0;          // Upper Deviation Multiplier
input double lowerMultInput = 2.0;          // Lower Deviation Multiplier
input bool useUpperDevInput = true;         // Use Upper Deviation
input bool useLowerDevInput = true;         // Use Lower Deviation

// Buffers for indicator
double baseBuffer[];
double upperBuffer[];
double lowerBuffer[];

// Variables
double slope, intercept, stdDev, pearsonR;
double upperDeviation, lowerDeviation;
bool upperState, lowerState;

//+------------------------------------------------------------------+
//| Calculate the slope, average, and intercept for linear regression |
//+------------------------------------------------------------------+
void CalcSlope(const double &source[], int length, double &slope, double &average, double &intercept)
{
    double sumX = 0.0, sumY = 0.0, sumXSqr = 0.0, sumXY = 0.0;
    
    for (int i = 0; i < length; i++)
    {
        double val = source[i];
        double per = i + 1.0;
        sumX += per;
        sumY += val;
        sumXSqr += per * per;
        sumXY += val * per;
    }
    
    slope = (length * sumXY - sumX * sumY) / (length * sumXSqr - sumX * sumX);
    average = sumY / length;
    intercept = average - slope * sumX / length + slope;
}

//+------------------------------------------------------------------+
//| Calculate deviation and Pearson's R                               |
//+------------------------------------------------------------------+
void CalcDev(const double &source[], int length, double slope, double average, double intercept,
              double &stdDev, double &pearsonR, double &upDev, double &dnDev)
{
    upDev = 0.0;
    dnDev = 0.0;
    double stdDevAcc = 0.0;
    double dsxx = 0.0, dsyy = 0.0, dsxy = 0.0;
    int periods = length - 1;
    double daY = intercept + slope * periods / 2.0;
    double val = intercept;
    
    for (int j = 0; j <= periods; j++)
    {
        double price = source[j];
        double dxt = price - average;
        double dyt = val - daY;
        price -= val;
        stdDevAcc += price * price;
        dsxx += dxt * dxt;
        dsyy += dyt * dyt;
        dsxy += dxt * dyt;
        val += slope;
    }
    
    stdDev = MathSqrt(stdDevAcc / (periods == 0 ? 1 : periods));
    pearsonR = (dsxx == 0 || dsyy == 0) ? 0 : dsxy / MathSqrt(dsxx * dsyy);
}

//+------------------------------------------------------------------+
//| Indicator initialization function                                |
//+------------------------------------------------------------------+
int OnInit()
{
    // Attach buffers to plots
    SetIndexBuffer(0, baseBuffer, INDICATOR_DATA);
    SetIndexBuffer(1, upperBuffer, INDICATOR_DATA);
    SetIndexBuffer(2, lowerBuffer, INDICATOR_DATA);
    
    IndicatorSetString(INDICATOR_SHORTNAME, "LinRegChannel");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Indicator deinitialization function                              |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    ObjectDelete(0, "LinRegBaseLine");
    ObjectDelete(0, "LinRegUpperLine");
    ObjectDelete(0, "LinRegLowerLine");
}

//+------------------------------------------------------------------+
//| Indicator calculation function                                   |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
{
    if (rates_total < lengthInput)
        return 0;
    
    double priceArray[];
    ArraySetAsSeries(priceArray, true);
    CopyClose(NULL, 0, 0, lengthInput, priceArray);
    
    CalcSlope(priceArray, lengthInput, slope, priceArray[0], intercept);
    CalcDev(priceArray, lengthInput, slope, priceArray[0], intercept, stdDev, pearsonR, upperDeviation, lowerDeviation);
    
    int lastBar = rates_total - 1;
    
    double baseLine = intercept + slope * (rates_total - lastBar - 1);
    double upperLine = baseLine + (useUpperDevInput ? upperMultInput * stdDev : upperDeviation);
    double lowerLine = baseLine - (useLowerDevInput ? lowerMultInput * stdDev : lowerDeviation);
    
    upperBuffer[lastBar] = upperLine;
    lowerBuffer[lastBar] = lowerLine;
    baseBuffer[lastBar] = baseLine;
    
    double startPrice = intercept + slope * (lengthInput - 1);
    double endPrice = intercept;
    datetime startTime = time[lengthInput - 1];
    datetime endTime = time[0];
    
    ObjectCreate(0, "LinRegUpperLine", OBJ_TREND, 0, startTime, startPrice + upperDeviation, endTime, endPrice + upperDeviation);
    ObjectCreate(0, "LinRegLowerLine", OBJ_TREND, 0, startTime, startPrice - lowerDeviation, endTime, endPrice - lowerDeviation);
    ObjectCreate(0, "LinRegBaseLine", OBJ_TREND, 0, startTime, startPrice, endTime, endPrice);
    PrintFormat("upperStartPrice: %f, upperEndPrice: %f, lowerStartPrice: %f, lowerEndPrice: %f, startTime: %d, endTime: %d",startPrice + upperDeviation,endPrice + upperDeviation,startPrice - lowerDeviation,endPrice - lowerDeviation,startTime,endTime);
    
    
    return rates_total;
}
