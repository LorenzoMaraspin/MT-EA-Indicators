  //+------------------------------------------------------------------+
//|                                                   ICN Indicator |
//|                          Converted from PineScript to MQL5      |
//+------------------------------------------------------------------+
#property strict
#property indicator_chart_window
#property indicator_buffers 0 // No buffers since we're using objects
#property indicator_plots 0   // No plots since we're using objects

// Input parameters
input int MA_LENGTH = 60; // History Kline length

// Global variables
double prices[];
int states[];
double min_Price = 0, max_Price = 0;
int transitions[2][2];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize arrays
   ArrayResize(prices, MA_LENGTH);
   ArrayResize(states, MA_LENGTH);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   // Make sure we have enough bars
   if (rates_total < MA_LENGTH) return 0;

   // Initialize transition matrix
   transitions[0][0] = 0;
   transitions[0][1] = 0;
   transitions[1][0] = 0;
   transitions[1][1] = 0;

   // Loop through all candles (from the last calculated candle to the newest)
   for (int i = prev_calculated; i < rates_total; i++)
   {
      // Fill the prices array (shifted for the current bar `i`)
      for (int offset = 0; offset < MA_LENGTH; offset++)
      {
         if (i - offset >= 0)
            prices[offset] = open[i - offset];
      }

      // Reset min and max prices for the current bar
      min_Price = prices[0];
      max_Price = prices[0];

      // Calculate states
      for (int offset = 1; offset < MA_LENGTH; offset++)
      {
         if (prices[offset] < prices[offset - 1])
            states[offset - 1] = 1;
         else
            states[offset - 1] = 0;

         // Update transition matrix and min/max prices
         if (states[offset] != states[offset - 1])
         {
            transitions[states[offset]][states[offset - 1]]++;
            if (states[offset - 1] == 0 && prices[offset - 1] < min_Price)
               min_Price = prices[offset - 1];
            if (states[offset - 1] == 1 && prices[offset - 1] > max_Price)
               max_Price = prices[offset - 1];
         }
      }

      // Calculate resistance and support levels for the current bar
      double sum0 = transitions[0][0] + transitions[0][1];
      double sum1 = transitions[1][0] + transitions[1][1];
      int current_state = states[0];
      int next_state = (0.5 < transitions[current_state][1]) ? 1 : 0;

      // Draw trend lines for resistance and support
      if (i > 0)
      {
         CreateLines("Resistance_" + IntegerToString(i), max_Price, max_Price, time[i - 1], time[i]);
         CreateLines("Support_" + IntegerToString(i), min_Price, min_Price, time[i - 1], time[i]);
         CreateLines("Connection_Resistance" + IntegerToString(i), min_Price, min_Price, time[i - 1], time[i]);
         CreateLines("Connection_Support" + IntegerToString(i), min_Price, min_Price, time[i - 1], time[i]);
         // Detect Break of Structures (BoS)
         DetectBoS("Resistance_Break_" + IntegerToString(i), high[i], max_Price, time[i], clrRed);
         DetectBoS("Support_Break_" + IntegerToString(i), low[i], min_Price, time[i], clrGreen);
      }
   }

   return rates_total;
}

//+------------------------------------------------------------------+
//| Function to create or update trend lines                         |
//+------------------------------------------------------------------+
void CreateLines(string name, double startPrice, double endPrice, datetime startTime, datetime endTime)
{
   // If the object doesn't exist, create it
   if (ObjectFind(0, name) == -1)
   {
      ObjectCreate(0, name, OBJ_TREND, 0, startTime, startPrice, endTime, endPrice);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false); // No ray extension
   }
   else
   {
      // If the trend line already exists, update its start and end points
      ObjectMove(0, name, 0, startTime, startPrice);
      ObjectMove(0, name, 1, endTime, endPrice);
   }
}

//+------------------------------------------------------------------+
//| Function to detect break of structure (BoS)                      |
//+------------------------------------------------------------------+
void DetectBoS(string name, double currentPrice, double levelPrice, datetime time, color line_color)
{
   // Check if there's a break of structure
   bool isBreakout = false;

   if (StringFind(name, "Resistance_Break") != -1)
      isBreakout = (currentPrice > levelPrice); // Resistance breakout
   else if (StringFind(name, "Support_Break") != -1)
      isBreakout = (currentPrice < levelPrice); // Support breakout

   if (isBreakout)
   {
      // If the breakout line doesn't exist, create it
      if (ObjectFind(0, name) == -1)
      {
         ObjectCreate(0, name, OBJ_TREND, 0, time, 0);
         ObjectSetInteger(0, name, OBJPROP_COLOR, line_color);
         ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
         ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
      }
   }
}
