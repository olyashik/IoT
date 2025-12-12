#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE ("LoraThermalNoise");

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
    
    double ApplyThermalNoise(double signalPowerDbm) {
        double thermalNoisePower = GetThermalNoisePowerDbm();
        
        // Расчет отношения сигнал-шум
        double signalPowerLinear = pow(10.0, signalPowerDbm / 10.0);
        double noisePowerLinear = pow(10.0, thermalNoisePower / 10.0);
        double snrLinear = signalPowerLinear / noisePowerLinear;
        double snrDb = 10 * log10(snrLinear);
        
        NS_LOG_DEBUG("Тепловой шум: " << thermalNoisePower << " dBm, SNR: " << snrDb << " dB");
        
        // Пороговое значение SNR для успешного приема
        if (snrDb > 3.0) { // Более высокий порог для теплового шума
            return signalPowerDbm;
        } else {
            return -1000.0; // Пакет потерян
        }
    }
    
private:
    double temperatureC;
    double bandwidth;
    double noiseFigure;
};

int main (int argc, char *argv[])
{
    // Параметры
    int nDevices = 3;
    double simulationTime = 3600;
    double appPeriod = 600;

    // Настройка логирования
    LogComponentEnable ("LoraThermalNoise", LOG_LEVEL_INFO);
    LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_INFO);

    NS_LOG_INFO("=== LoRa сеть с Тепловым шумом ===");
    NS_LOG_INFO("Создаем сеть с " << nDevices << " устройствами");

    // Создание узлов
    NodeContainer endDevices;
    endDevices.Create (nDevices);
    NodeContainer gateways;
    gateways.Create (1);

    // Мобильность
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> positionAllocGateways = CreateObject<ListPositionAllocator> ();
    positionAllocGateways->Add (Vector (0.0, 0.0, 15.0));
    mobility.SetPositionAllocator (positionAllocGateways);
    mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mobility.Install (gateways);

    MobilityHelper mobilityEd;
    mobilityEd.SetPositionAllocator ("ns3::UniformDiscPositionAllocator",
                                    "X", DoubleValue (0.0),
                                    "Y", DoubleValue (0.0),
                                    "rho", DoubleValue (2000.0));
    mobilityEd.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    mobilityEd.Install (endDevices);

    // Инициализация теплового шума
    ThermalNoiseModel thermalNoise;
    thermalNoise.SetTemperatureCelsius(25.0);
    thermalNoise.SetBandwidth(125000.0);
    thermalNoise.SetNoiseFigure(3.0);

    NS_LOG_INFO("Тепловой шум настроен: температура=25°C, шумовая фигура=3dB");

    // Создание LoRaWAN стека
    PhyLoraPropModelHelper phyHelper;
    phyHelper.SetFrequency(868e6);

    LorawanMacHelper macHelper;
    macHelper.SetRegion(LorawanMacHelper::EU);

    LorawanHelper helper;
    helper.EnablePacketTracking();

    // Установка на устройства
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    helper.Install(phyHelper, macHelper, endDevices);

    macHelper.SetDeviceType(LorawanMacHelper::GW);
    helper.Install(phyHelper, macHelper, gateways);

    // Настройка параметров устройств
    for (int i = 0; i < nDevices; i++) {
        Ptr<Node> node = endDevices.Get(i);
        Ptr<LoraNetDevice> loraNetDev = node->GetDevice(0)->GetObject<LoraNetDevice>();
        Ptr<ClassAEndDeviceLorawanMac> edMac = loraNetDev->GetMac()->GetObject<ClassAEndDeviceLorawanMac>();
        
        switch(i) {
            case 0:
                edMac->SetDataRate(5);
                edMac->SetTransmissionPower(14);
                NS_LOG_INFO("Устройство 0: SF7, мощность 14dBm");
                break;
            case 1:
                edMac->SetDataRate(3);
                edMac->SetTransmissionPower(10);
                NS_LOG_INFO("Устройство 1: SF9, мощность 10dBm");
                break;
            case 2:
                edMac->SetDataRate(1);
                edMac->SetTransmissionPower(6);
                NS_LOG_INFO("Устройство 2: SF11, мощность 6dBm");
                break;
        }
    }

    // Приложение
    Time appStopTime = Seconds (simulationTime);
    PeriodicSenderHelper appHelper = PeriodicSenderHelper ();
    appHelper.SetPeriod (Seconds (appPeriod));
    
    Ptr<RandomVariableStream> rv = CreateObjectWithAttributes<UniformRandomVariable> (
        "Min", DoubleValue (10), "Max", DoubleValue (50));
    appHelper.SetPacketSizeRandomVariable (rv);

    ApplicationContainer appContainer = appHelper.Install (endDevices);
    appContainer.Start (Seconds (0));
    appContainer.Stop (appStopTime);

    // Сервер
    NetworkServerHelper networkServerHelper;
    networkServerHelper.SetGateways (gateways);
    networkServerHelper.SetEndDevices (endDevices);
    networkServerHelper.Install (gateways);

    ApplicationContainer serverContainer;
    ForwarderHelper forwarderHelper;
    forwarderHelper.Install (gateways);

    // Симуляция
    NS_LOG_INFO("Запуск симуляции на " << simulationTime << " секунд");
    Simulator::Stop (appStopTime + Hours (1));
    Simulator::Run ();
    Simulator::Destroy ();

    // Результаты
    LoraPacketTracker& tracker = helper.GetPacketTracker();
    NS_LOG_INFO("=== РЕЗУЛЬТАТЫ С ТЕПЛОВЫМ ШУМОМ ===");
    NS_LOG_INFO("Всего отправлено пакетов: " << tracker.CountMacPacketsSent());
    NS_LOG_INFO("Успешно доставлено: " << tracker.CountMacPacketsGloballyReceived());
    
    double deliveryRatio = (double)tracker.CountMacPacketsGloballyReceived() / 
                          (double)tracker.CountMacPacketsSent() * 100.0;
    NS_LOG_INFO("Коэффициент доставки: " << deliveryRatio << "%");

    return 0;
}
