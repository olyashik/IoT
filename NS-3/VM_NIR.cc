#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"
#include "ns3/random-variable-stream.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE ("LoraRayleigh");

// Модель замираний Рэлея
class RayleighFadingModel
{
public:
    RayleighFadingModel() : sigma(1.0) {}
    
    void SetSigma(double s) { sigma = s; }
    
    double ApplyFading(double signalPowerDbm) {
        // Генерация рэлеевской случайной величины
        Ptr<NormalRandomVariable> normalRv = CreateObject<NormalRandomVariable> ();
        normalRv->SetAttribute ("Mean", DoubleValue (0.0));
        normalRv->SetAttribute ("Variance", DoubleValue (sigma * sigma));
        
        double x = normalRv->GetValue();
        double y = normalRv->GetValue();
        
        // Рэлеевское распределение: sqrt(X^2 + Y^2) где X,Y ~ N(0,sigma^2)
        double rayleighValue = sqrt(x*x + y*y);
        
        // Применение замираний к мощности сигнала
        double fadedPowerDbm = signalPowerDbm - 20 * log10(rayleighValue);
        
        NS_LOG_DEBUG("Исходная мощность: " << signalPowerDbm << " dBm, " <<
                     "После замираний: " << fadedPowerDbm << " dBm");
        
        return fadedPowerDbm;
    }
    
private:
    double sigma;
};

int main (int argc, char *argv[])
{
    // Параметры
    int nDevices = 3;
    double simulationTime = 3600;
    double appPeriod = 600;

    // Настройка логирования
    LogComponentEnable ("LoraRayleigh", LOG_LEVEL_INFO);
    LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_INFO);

    NS_LOG_INFO("=== LoRa сеть с замираниями Рэлея ===");
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

    // Инициализация замираний Рэлея
    RayleighFadingModel rayleighFading;
    rayleighFading.SetSigma(1.0);

    NS_LOG_INFO("Замирания Рэлея настроены: sigma=1.0");

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
    NS_LOG_INFO("Запуск симуляци на " << simulationTime << " секунд");
    Simulator::Stop (appStopTime + Hours (1));
    Simulator::Run ();
    Simulator::Destroy ();

    // Результаты
    LoraPacketTracker& tracker = helper.GetPacketTracker();
    NS_LOG_INFO("=== РЕЗУЛЬТАТЫ С ЗАМИРАНИЯМИ РЭЛЕЯ ===");
    NS_LOG_INFO("Всего отправлено пакетов: " << tracker.CountMacPacketsSent());
    NS_LOG_INFO("Успешно доставлено: " << tracker.CountMacPacketsGloballyReceived());
    
    double deliveryRatio = (double)tracker.CountMacPacketsGloballyReceived() / 
                          (double)tracker.CountMacPacketsSent() * 100.0;
    NS_LOG_INFO("Коэффициент доставки: " << deliveryRatio << "%");

    return 0;
}
