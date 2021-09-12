
int moisture;
int ldr;
int waterLevel;

unsigned long startMillis;  
unsigned long currentMillis = 0;
const unsigned long period = 1000; 

int i = 0;
int k = 0;

float sumMoisture = 0;
float sumLdr = 0;
float sumWaterLevel = 0;

void setup() {
  Serial.begin(9600); 
}

void loop() {

    currentMillis = millis();
    
    if ((currentMillis - startMillis) > period) {
      
      moisture = analogRead(A3);
      ldr = analogRead(A4);
      waterLevel = analogRead(A5);
 
      sumMoisture = sumMoisture + moisture;
      sumLdr = sumLdr + ldr;
      sumWaterLevel = sumWaterLevel + waterLevel;
      i++;
      
      if(i == 5){
        Serial.print("{\"data\":");
        Serial.print("{\"M\":");
        Serial.print(sumMoisture/i);
        Serial.print(",\"L\":");
        Serial.print(sumLdr/i);
        Serial.print(",\"W\":");
        Serial.print(sumWaterLevel/i);
        Serial.println("}}");
        
        i = 0;
        sumMoisture = 0;
        sumLdr = 0;
        sumWaterLevel = 0;
      }
      
      startMillis = currentMillis;
    }
}
