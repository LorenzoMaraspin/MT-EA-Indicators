import together
import logging
import json

logger = logging.getLogger("telegramListener")

class tradesAnalyzer:
    def __init__(self, config):
        self.config = config
        self.api_key = config["LLAMA_API_KEY"]
        #self.model = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        self.model = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free"
        # Improved prompt with structured extraction rules
        self.prompt = """
        Sei un assistente di trading Forex. Il tuo compito è analizzare il messaggio ricevuto ed estrarre i dati in un JSON **senza aggiungere testo extra**.  
        ---
        
        📌 **TIPO 1 - Apertura di un nuovo trade**  
        I messaggi di apertura contengono un **simbolo, direzione e prezzo di ingresso**.  
        Se il messaggio è di apertura, estrai:  
        - `"symbol"` → Simbolo dell'asset (XAUUSD, US30, EURUSD, ecc.).  
        - `"direction"` → BUY, SELL, BUY LIMIT, SELL LIMIT, BUY STOP, SELL STOP.  
        - `"entry_price"` → Prezzo di ingresso.  
        - `"stop_loss"` (se presente) → Prezzo di stop loss.  
        - `"take_profit"` (se presente) → Lista di target TP.  
        - `"action"` → `"open"` per indicare che è un nuovo trade.  
        
        📌 **Esempio di output per apertura**:
        {
            "symbol": "XAUUSD",
            "direction": "SELL",
            "entry_price": 2863.00,
            "stop_loss": 2869.00,
            "take_profit": [2861.50, 2860.00, 2858.50],
            "action": "open"
        }
        📌 TIPO 2 - Modifica di un trade già aperto
        Se il messaggio contiene modifiche al trade, estrai:
        
        "action" → "modify", "close", "move", "sl", "tp", "be", a seconda dell'azione richiesta.
        "stop_loss" (se presente) → Nuovo SL.
        "take_profit" (se presente) → Nuovo TP.
        📌 Esempio di output per modifica SL a BE:
        {
            "be": true,
            "action": "modify"
        }
        📌 Esempio di output per modifica SL:
        {
            "sl": 2924,
            "action": "modify"
        }
        📌 REGOLE IMPORTANTI
        1️⃣ Rispondi SOLO con il JSON → Non aggiungere testo, spiegazioni o commenti.
        2️⃣ Formato sempre valido → Assicurati che il JSON sia corretto.
        3️⃣ Rispetta le regole → Non modificare i campi richiesti. 
        4️⃣ Nessun testo extra → Non aggiungere testo o commenti.
        """

        together.api_key = self.api_key

    def analyze_trade(self, message):
        """
        Sends a request to the Together API to analyze a trading message.
        """
        try:
            response = together.Complete.create(
                prompt=self.prompt + "\n\nMessage: " + message,
                model=self.model
            )

            if "choices" in response and len(response["choices"]) > 0:
                result = response["choices"][0]["text"].strip()

                # Ensure the response is valid JSON
                trade_data = json.loads(result)

                return trade_data
            else:
                logger.error("No valid response from LLaMA API")
                return None

        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from LLaMA API")
            return None

        except Exception as e:
            logger.error(f"Error analyzing trade message: {str(e)}")
            return None




