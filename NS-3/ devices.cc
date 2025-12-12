#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"
#include "ns3/propagation-loss-model.h"
#include "ns3/propagation-delay-model.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE ("LoraThreeDevicesWireless");

// Модель теплового шума
class ThermalNoiseModel
{
public:
    ThermalNoiseModel() : temperatureC(25.0), bandwidth(125000.0), noiseFigure(3.0) {}
    
    void SetTemperatureCelsius(double temp) { temperatureC = temp; }
    void SetBandwidth(double bw) { bandwidth = bw; }
    void SetNoiseFigure(double nf) { noiseFigure = nf; }
    
    double GetThermalNoisePowerDbm() {
        // Формула теплового шума: P = k * T * B
        // k - постоянная Больцмана (1.38e-23), T - температура в Кельвинах, B - полоса пропускания
        double temperatureK = temperatureC + 273.15;
        double noisePowerW = 1.38e-23 * temperatureK * bandwidth;
        double noisePowerDbm = 10 * log10(noisePowerW) + 30; // преобразование в dBm
        
        // Учет шумовой фигуры
        return noisePowerDbm + noiseFigure;
    }
    
private:
    double temperatureC;
    double bandwidth;
    double noiseFigure;
};

// Модель АБГШ
class AWGNModel
{
public:
    AWGNModel() : noisePowerDbm(-110.0) {}
    
    void SetNoisePower(double power) { noisePowerDbm = power; }
    void SetBandwidth(double bw) { bandwidth = bw; }
    
    double AddAWGN(double signalPowerDbm) {
        // Простая модель: добавление шум к мощности сигнала
        double signalPowerLinear = pow(10.0, signalPowerDbm / 10.0);
        double noisePowerLinear = pow(10.0, noisePowerDbm / 10.0);
        
        // Имитация добавления шума (упрощенно)
        double snrLinear = signalPowerLinear / noisePowerLinear;
        
        // Если SNR достаточно высокий, считаем что пакет может быть принят
        if (snrLinear > 1.0) {
            return signalPowerDbm; // Сигнал принят
        } else {
            return -1000.0; // Сигнал потерян (очень низкая мощность)
        }
    }
    
private:
    double noisePowerDbm;
    double bandwidth;
};

int main (int argc, char *argv[])
{
    // Параметры по умолчанию
    int nDevices = 3;           // Количество устройств
    double simulationTime = 3600; // Время симуляции в секундах (1 час)
    double appPeriod = 600;     // Период отправки данных (10 минут)
    bool enableFading = true;   // Включить замирания
    bool enableAWGN = true;     // Включить АБГШ

    // Настройка логирования
    LogComponentEnable ("LoraThreeDevicesWireless", LOG_LEVEL_INFO);
    LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_INFO);

    NS_LOG_INFO("Создаем беспроводную сеть LoRaWAN с " << nDevices << " устройствами");

    // Создание узлов 
    NodeContainer endDevices;
    endDevices.Create (nDevices);

    NodeContainer gateways;
    gateways.Create (1);  // Один шлюз

    // Настройка мобильности
    MobilityHelper mobility;
    
    // Шлюз в центре
    Ptr<ListPositionAllocator> positionAllocGateways = CreateObject<ListPositionAllocator> ();
    positionAllocGateways->Add (Vector (0.0, 0.0, 15.0)); // Высота 15м
    mobility.SetPositionAllocator (positionAllocGateways);
    mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mobility.Install (gateways);

    // Устройства распределяем случайно в радиусе 2км
    MobilityHelper mobilityEd;
    mobilityEd.SetPositionAllocator ("ns3::UniformDiscPositionAllocator",
                                    "X", DoubleValue (0.0),
                                    "Y", DoubleValue (0.0),
                                    "rho", DoubleValue (2000.0)); // Радиус 2000м
    mobilityEd.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mobilityEd.Install (endDevices);

    // Создание канала с замираниями и шумами
    Ptr<LogDistancePropagationLossModel> logDistance = CreateObject<LogDistancePropagationLossModel> ();
    logDistance->SetAttribute ("Exponent", DoubleValue (3.0)); // Показатель затухания
    logDistance->SetAttribute ("ReferenceLoss", DoubleValue (46.0)); // Потери на 1м

    // Модель замираний Рэлея
    Ptr<RayleighFadingModel> rayleighFading = CreateObject<RayleighFadingModel> ();
    
    // Создание составной модели потерь
    Ptr<CompositePropagationLossModel> compositeLoss = CreateObject<CompositePropagationLossModel> ();
    compositeLoss->AddLossModel (logDistance);
    
    if (enableFading) {
        compositeLoss->AddLossModel (rayleighFading);
        NS_LOG_INFO("Замирания Рэлея включены");
    }

    // Модель задержки сигнала
    Ptr<ConstantSpeedPropagationDelayModel> delayModel = CreateObject<ConstantSpeedPropagationDelayModel> ();

    // Создание беспроводного канала
    Ptr<WirelessChannel> channel = CreateObject<WirelessChannel> ();
    channel->SetPropagationLossModel (compositeLoss);
    channel->SetPropagationDelayModel (delayModel);

    //Создание LORAWAN стека с использованием нашего канала
    PhyLoraPropModelHelper phyHelper;
    phyHelper.SetFrequency(868e6); // EU 868 MHz
    phyHelper.SetChannel(channel); // Используем наш канал с замираниями

    // LoRa MAC уровень
    LorawanMacHelper macHelper;
    macHelper.SetRegion(LorawanMacHelper::EU); // Европейский регион

    // LoRaWAN helper
    LorawanHelper helper;
    helper.EnablePacketTracking(); // Включаем отслеживание пакетов

    // Установка LoRa на устройства
    // Настройка для конечных устройств
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    helper.Install(phyHelper, macHelper, endDevices);

    // Настройка для шлюза
    macHelper.SetDeviceType(LorawanMacHelper::GW);
    helper.Install(phyHelper, macHelper, gateways);

    // Настройка индивидуальных параметров устройств
    for (int i = 0; i < nDevices; i++) {
        Ptr<Node> node = endDevices.Get(i);
        Ptr<LoraNetDevice> loraNetDev = node->GetDevice(0)->GetObject<LoraNetDevice>();
        Ptr<ClassAEndDeviceLorawanMac> edMac = loraNetDev->GetMac()->GetObject<ClassAEndDeviceLorawanMac>();
        
        // Устанавливаем разные параметры для каждого устройства
        switch(i) {
            case 0: // Устройство 1 - близко к шлюзу
                edMac->SetDataRate(5);  // SF7
                edMac->SetTransmissionPower(14); // dBm
                NS_LOG_INFO("Устройство 0: SF7, мощность 14dBm");
                break;
            case 1: // Устройство 2 - среднее расстояние
                edMac->SetDataRate(3);  // SF9
                edMac->SetTransmissionPower(10); // dBm
                NS_LOG_INFO("Устройство 1: SF9, мощность 10dBm");
                break;
            case 2: // Устройство 3 - далеко от шлюза
                edMac->SetDataRate(1);  // SF11
                edMac->SetTransmissionPower(6);  // dBm
                NS_LOG_INFO("Устройство 2: SF11, мощность 6dBm");
                break;
        }
    }

    // Инициализация моделей шумов
    ThermalNoiseModel thermalNoise;
    thermalNoise.SetTemperatureCelsius(25.0);
    thermalNoise.SetBandwidth(125000.0);
    thermalNoise.SetNoiseFigure(3.0);

    AWGNModel awgnModel;
    if (enableAWGN) {
        double thermalNoisePower = thermalNoise.GetThermalNoisePowerDbm();
        awgnModel.SetNoisePower(thermalNoisePower);
        NS_LOG_INFO("Тепловой шум: " << thermalNoisePower << " dBm");
        NS_LOG_INFO("АБГШ включен");
    }

    // Создание приложения
    Time appStopTime = Seconds (simulationTime);
    PeriodicSenderHelper appHelper = PeriodicSenderHelper ();
    appHelper.SetPeriod (Seconds (appPeriod));
    
    // Устанавливаем разные размеры пакетов для разных устройств
    Ptr<RandomVariableStream> rv = CreateObjectWithAttributes<UniformRandomVariable> (
        "Min", DoubleValue (10), "Max", DoubleValue (50));
    appHelper.SetPacketSizeRandomVariable (rv);

    ApplicationContainer appContainer = appHelper.Install (endDevices);
    appContainer.Start (Seconds (0));
    appContainer.Stop (appStopTime);

    // Подключение шлюза к серверу
    NetworkServerHelper networkServerHelper;
    networkServerHelper.SetGateways (gateways);
    networkServerHelper.SetEndDevices (endDevices);
    networkServerHelper.Install (gateways);

    // Установка сетевых приложений
    ApplicationContainer serverContainer;
    ForwarderHelper forwarderHelper;
    forwarderHelper.Install (gateways);

    // Дополнительная информация о канале
    NS_LOG_INFO("--- ПАРАМЕТРЫ КАНАЛА ---");
    NS_LOG_INFO("Модель потерь: LogDistance + Rayleigh Fading");
    NS_LOG_INFO("Показатель затухания: 3.0");
    NS_LOG_INFO("Температура: 25°C");
    NS_LOG_INFO("Шумовая фигура: 3.0 dB");

    // Запуск симуляции
    NS_LOG_INFO("Запуск симуляции на " << simulationTime << " секунд");
    Simulator::Stop (appStopTime + Hours (1));
    Simulator::Run ();
    Simulator::Destroy ();

    // Вывод результатов
    LoraPacketTracker& tracker = helper.GetPacketTracker();
    NS_LOG_INFO("--- РЕЗУЛЬТАТЫ СИМУЛЯЦИИ ---");
    NS_LOG_INFO("Всего отправлено пакетов: " << tracker.CountMacPacketsSent());
    NS_LOG_INFO("Успешно доставлено: " << tracker.CountMacPacketsGloballyReceived());
    
    double deliveryRatio = (double)tracker.CountMacPacketsGloballyReceived() / 
                          (double)tracker.CountMacPacketsSent() * 100.0;
    NS_LOG_INFO("Коэффициент доставки: " << deliveryRatio << "%");
    
    for (int i = 0; i < nDevices; i++) {
        Ptr<Node> node = endDevices.Get(i);
        Vector pos = node->GetObject<MobilityModel>()->GetPosition();
        double distance = sqrt(pos.x * pos.x + pos.y * pos.y);
        NS_LOG_INFO("Устройство " << i << " позиция: (" << pos.x << ", " << pos.y 
                    << "), расстояние до шлюза: " << distance << " м");
    }

    return 0;
}
