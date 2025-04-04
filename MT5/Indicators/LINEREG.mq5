#property strict
#property indicator_chart_window
#property indicator_buffers 4

#property indicator_label3  "baseLine"
#property indicator_style3  STYLE_DOT
#property indicator_color3 clrGray

#property indicator_label1  "upperLine"
#property indicator_style1  STYLE_DOT
#property indicator_color1  clrBlue

#property indicator_label2  "lowerLine"
#property indicator_style2  STYLE_DOT
#property indicator_color2 clrRed

#property indicator_label4  "distance"
#property indicator_color4 clrYellow
#property indicator_plots   4

// Input parameters
input int lengthInput = 100;                // Length
input double upperMultInput = 2.0;          // Upper Deviation Multiplier
input double lowerMultInput = 2.0;          // Lower Deviation Multiplier
input bool useUpperDevInput = true;         // Use Upper Deviation
input bool useLowerDevInput = true;         // Use Lower Deviation

double upperStartPrice, upperEndPrice, lowerStartPrice, lowerEndPrice, upperCurrentPrice, lowerCurrentPrice;
double baseBuffer[];
double upperBuffer[];
double lowerBuffer[];
double distanceBuffer[];

// Variables
double g_slope, g_intercept, g_stdDev, g_pearsonR;
double upperDeviation, lowerDeviation;

//+------------------------------------------------------------------+
//| Initialization and Deinitialization functions                    |
//+------------------------------------------------------------------+
int OnInit()
{
    SetIndexBuffer(0, baseBuffer);
    SetIndexBuffer(1, upperBuffer);
    SetIndexBuffer(2, lowerBuffer);
    SetIndexBuffer(3, distanceBuffer);
    IndicatorSetString(INDICATOR_SHORTNAME, "LINEREG");

    // Clear any existing trend lines on initialization
    CreateTrendLines();

    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
    // Delete trend lines when the indicator is removed
    ObjectDelete(0, "LinRegBaseLine");
    ObjectDelete(0, "LinRegUpperLine");
    ObjectDelete(0, "LinRegLowerLine");
}

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
    
    // Calculate slope, intercept, and deviations
    CalcSlope(priceArray, lengthInput, g_slope, priceArray[0], g_intercept);
    CalcDev(priceArray, lengthInput, g_slope, priceArray[0], g_intercept, g_stdDev, g_pearsonR, upperDeviation, lowerDeviation);
    
    int lastBar = rates_total - 1;
    double endPrice = g_intercept + g_slope * (0);
    double startPrice = g_intercept + g_slope * (lengthInput - 1);
    
    // Calculate baseline, upper line, and lower line values
    double baseLine = g_intercept + g_slope * (rates_total - lastBar - 1);
    double upperLine = baseLine + (useUpperDevInput ? upperMultInput * g_stdDev : upperDeviation);
    double lowerLine = baseLine - (useLowerDevInput ? lowerMultInput * g_stdDev : lowerDeviation);
    
    upperBuffer[lastBar] = upperLine;
    lowerBuffer[lastBar] = lowerLine;
    baseBuffer[lastBar] = baseLine;
    // Calculate channel distance and assign it to the buffer
    double channelDistance = MathAbs(upperLine - lowerLine);
    distanceBuffer[lastBar] = channelDistance;
    // Calculate start and end times for the trend lines
    datetime startTime = time[rates_total - lengthInput];
    datetime endTime = time[lastBar];
    
    // Create upper and lower line
    upperStartPrice = startPrice + (useUpperDevInput ? upperMultInput * g_stdDev : upperDeviation);
    upperEndPrice = endPrice + (useUpperDevInput ? upperMultInput * g_stdDev : upperDeviation);
    lowerStartPrice = startPrice - (useLowerDevInput ? lowerMultInput * g_stdDev : lowerDeviation);
    lowerEndPrice = endPrice - (useLowerDevInput ? lowerMultInput * g_stdDev : lowerDeviation);
    // Draw or update trend lines
    CreateOrUpdateTrendLine("LinRegBaseLine", lastBar, startPrice, endPrice, clrGray, startTime, endTime);
    CreateOrUpdateTrendLine("LinRegUpperLine", lastBar, upperStartPrice, upperEndPrice, clrBlue, startTime, endTime);
    CreateOrUpdateTrendLine("LinRegLowerLine", lastBar, lowerStartPrice, lowerEndPrice, clrRed, startTime, endTime);

    return rates_total;
}

//+------------------------------------------------------------------+
//| Create or update trend line                                      |
//+------------------------------------------------------------------+
void CreateOrUpdateTrendLine(string name, int lastBar, double startPrice, double endPrice, color lineColor, datetime startTime, datetime endTime)
{
    int startIndex = lastBar - lengthInput + 1; // Starting index for the trend line

    // If the object doesn't exist, create it
    if (ObjectFind(0, name) == -1)
    {
        ObjectCreate(0, name, OBJ_TREND, 0, startTime, startPrice, endTime, endPrice);
        ObjectSetInteger(0, name, OBJPROP_COLOR, lineColor);
        ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
        ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
        ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
    }
    else
    {
        // If the trend line already exists, update its start and end points
        ObjectMove(0, name, 0, startTime, startPrice);
        ObjectMove(0, name, 1, endTime, endPrice);
    }
}

void CreateTrendLines()
{
    ObjectDelete(0, "LinRegBaseLine");
    ObjectDelete(0, "LinRegUpperLine");
    ObjectDelete(0, "LinRegLowerLine");
}

