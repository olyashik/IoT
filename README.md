

# IoT LoRa
Matlab: https://github.com/bhomssi/LoRaMatlab/blob/master/Pilot.m
Реализация передачи пакетов LoRa в беспроводном канале

GNS3:
*https://www.gns3.com/*

Для добавления VM и иных компонентов: 
*https://gns3.com/marketplace/appliances*

Стоит установить VM (в данном случае использовался VirtualBox с Debian 13) и установить в него NS-3:
*https://www.nsnam.org/docs/release/3.46/tutorial/html/index.html*

### Сетевой уровень:

Сетевой уровень описывается в GNS3. Основными устройствами являются: маршрутизаторы MikroTikCHR, коммутаторы Switch ethernet и виртуальные машины (VirtualBox). 
Оборудование настроено.

1. С DHCP-сервером (DHCP)
<img width="860" height="651" alt="image" src="https://github.com/user-attachments/assets/c8421d5f-bfe7-45c1-82b4-5a056dea4346" />

2. Без DHCP-сервера (NoDHCP)
<img width="860" height="651" alt="image" src="https://github.com/user-attachments/assets/0448e06b-f998-4be2-acb3-f77939357fc5" />

3. Без коммутатора (NoSwitch)
<img width="860" height="651" alt="image" src="https://github.com/user-attachments/assets/12a4a091-f176-494e-bae7-2dd2261fe28c" />


 ### Физический уровень

Для создания физ.уровня используется NS-3. В симмуляторе описываются устройства LoRa с различными параметрами.

Все модели имеют одинаковый набор устройств, но с разными шумами:

1. VM NIR
   
```
// Замирания Рэлея
Ptr<RayleighFadingModel> rayleighFading = CreateObject<RayleighFadingModel>();
rayleighFading->SetAttribute("Sigma", DoubleValue(1.0));

// Накладка замираний на сигнал
double fadedPower = rayleighFading->DoCalcRxPower(txPowerDbm, nullptr, nullptr);
```

2. VM NIR 1
   
```
// АБГШ
AWGNModel awgnModel;
awgnModel.SetNoisePower(-110.0); // -110 dBm
awgnModel.SetBandwidth(125000.0); // 125 kHz

// АБГШ + сигнал
double finalRxPower = awgnModel.AddAWGN(fadedPower);
```

3. VM NIR 2

```
// Тепловой шум
ThermalNoiseModel thermalNoise;
thermalNoise.SetTemperatureCelsius(25.0); // 25°C
thermalNoise.SetBandwidth(125000.0);
thermalNoise.SetNoiseFigure(3.0);

// Тепловой шум как мощность АБГШ
awgnModel.SetNoisePower(thermalNoise.GetThermalNoisePowerDbm());
```
